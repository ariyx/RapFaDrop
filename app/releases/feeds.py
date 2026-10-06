"""Owner-enabled independent upload discovery, with exact upload watermarks."""
import json,re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone as utc
from types import SimpleNamespace
from urllib.parse import urlsplit
from xml.etree import ElementTree

import requests
from django.conf import settings
from django.db import connection,transaction,close_old_connections
from django.utils import timezone
from archive_collection.models import AcquisitionSource
from archive_collection.acquisition import shared_blocker
from media_pipeline.providers import PROVIDERS,ProviderError,redact_diagnostic
from sources.models import ArtistSource,SourceItem,Artist
from .models import FreshDiscoveryFeed,FreshDispatch,FreshProviderBackoff,IdentityAuditEvent,ReviewItem
from .normalization import normalize_text,edition_markers
from .wakeups import wake_media


def feed_source(feed):
    if bool(feed.acquisition_source_id)==bool(feed.search_artist_id):raise ValueError('Exactly one upload profile or search artist required')
    if feed.acquisition_source_id:return feed.acquisition_source
    return SimpleNamespace(pk=None,artist=feed.search_artist,artist_id=feed.search_artist_id,platform='soundcloud',native_id='artist:'+str(feed.search_artist_id),
        profile_url='',evidence={'identity_role':'independent_uploader','discovery_search':True})


def list_uploads(source):
    if source.platform=='youtube':
        if not re.fullmatch(r'UC[\w-]{22}',source.native_id):raise ValueError('Invalid registered channel ID')
        with requests.get('https://www.youtube.com/feeds/videos.xml',params={'channel_id':source.native_id},timeout=8,stream=True,allow_redirects=False) as response:
            response.raise_for_status();data=bytearray()
            for chunk in response.iter_content(8192):
                data.extend(chunk)
                if len(data)>256000:raise ValueError('Video feed exceeds bounded size')
        if b'<!DOCTYPE' in data:raise ValueError('Invalid video feed XML')
        root=ElementTree.fromstring(data);ns={'a':'http://www.w3.org/2005/Atom','yt':'http://www.youtube.com/xml/schemas/2015'}
        if root.findtext('yt:channelId',namespaces=ns)!=source.native_id:raise ValueError('Video feed channel mismatch')
        rows=[{'id':e.findtext('yt:videoId',namespaces=ns),'title':e.findtext('a:title',namespaces=ns),
            'url':'https://www.youtube.com/watch?v='+str(e.findtext('yt:videoId',namespaces=ns)),
            'published_at':e.findtext('a:published',namespaces=ns)} for e in root.findall('a:entry',ns)]
    elif source.platform=='soundcloud':
        search=source.evidence.get('discovery_search')
        url='scsearch10:'+source.artist.official_name if search else source.profile_url.rstrip('/')+'/tracks'
        raw=json.loads(PROVIDERS['yt-dlp']._run(['--socket-timeout','8','--retries','0','--extractor-retries','0','--skip-download','--flat-playlist','--playlist-end','20','--dump-single-json','--',url],30))
        if not search and str(raw.get('id') or '')!=source.native_id:raise ValueError('SoundCloud feed account identity mismatch')
        if not isinstance(raw.get('entries'),list):raise ValueError('SoundCloud feed lacks entries')
        rows=[{'id':str(e.get('id') or ''),'title':e.get('title'),'url':e.get('webpage_url') or e.get('url')} for e in raw['entries'] if isinstance(e,dict)]
    else:raise ValueError('Unsupported upload platform')
    if len(rows)>20 or len({r['id'] for r in rows})!=len(rows):raise ValueError('Malformed/repeated upload window')
    for r in rows:
        p=urlsplit(r['url'] or '')
        valid=(source.platform=='youtube' and re.fullmatch(r'[\w-]{11}',r['id']) and r['url']=='https://www.youtube.com/watch?v='+r['id'])
        valid|=(source.platform=='soundcloud' and r['id'].isdigit() and p.scheme=='https' and p.hostname=='soundcloud.com' and
            (source.evidence.get('discovery_search') or p.path.startswith(urlsplit(source.profile_url).path.rstrip('/')+'/')) and len(p.path.strip('/').split('/'))==2 and not p.query and not p.fragment)
        if not valid or not r['title']:raise ValueError('Upload URL/native/title outside verified feed')
    return rows


def poll_feed(feed,*,reader=list_uploads,now=None):
    now=now or timezone.now();source=feed_source(feed)
    if not feed.enabled or not source.artist.enabled:return 'disabled'
    rows=reader(source)
    with transaction.atomic():
        feed=FreshDiscoveryFeed.objects.select_for_update().get(pk=feed.pk)
        bootstrap=feed.baseline_at is None
        if bootstrap:feed.baseline_at=now
        known=set(feed.seen_ids);root=ArtistSource.objects.get(artist=source.artist,platform='spotify',enabled=True,verification='verified')
        created=0
        for row in rows:
            if row['id'] in known or (bootstrap and row['id'] not in feed.catchup_native_ids):continue
            published=datetime.fromisoformat(row['published_at'].replace('Z','+00:00')) if row.get('published_at') else None
            if published and published<=feed.baseline_at and row['id'] not in feed.catchup_native_ids:continue
            item,new=SourceItem.objects.get_or_create(platform=source.platform,native_item_id=row['id'],defaults={
                'source':root,'title':row['title'],'canonical_url':row['url'],'source_release_at':published,'first_observed_at':now,
                'metadata':{'feed_discovery':True,'feed_id':feed.pk,'feed_native_id':source.native_id,
                    'discovery_profile':source.profile_url,'catchup_authorized':row['id'] in feed.catchup_native_ids}})
            if new:
                FreshDispatch.objects.create(source_item=item,disposition='eligible',reason='Independent verified upload feed; exact metadata and freshness must pass before media')
                created+=1
        feed.seen_ids=list(dict.fromkeys([r['id'] for r in rows]+feed.seen_ids))[:5000]
        feed.last_success_at=now;feed.next_poll_at=now+timedelta(seconds=45);feed.last_error='';feed.consecutive_failures=0
        feed.evidence={**feed.evidence,'window_size':len(rows),'baseline_kind':'bounded latest-upload IDs plus exact-time watermark; not complete historical catalog',
            'last_created':created,'successful_polls':feed.evidence.get('successful_polls',0)+1}
        feed.save()
        if created:wake_media()
    return 'baselined' if bootstrap else 'success'


def _poll_one(pk):
    close_old_connections()
    feed=None
    try:
        feed=FreshDiscoveryFeed.objects.select_related('acquisition_source__artist','search_artist').get(pk=pk)
        source=feed_source(feed)
        hold=FreshProviderBackoff.objects.filter(platform='discovery-'+source.platform,due_at__gt=timezone.now()).first()
        if hold:
            FreshDiscoveryFeed.objects.filter(pk=pk).update(next_poll_at=hold.due_at,last_error=hold.reason);return 'provider hold'
        return poll_feed(feed)
    except Exception as exc:
        if feed is None:return 'missing feed'
        error=redact_diagnostic(exc);feed.consecutive_failures+=1
        feed.last_error=error;feed.next_poll_at=timezone.now()+timedelta(seconds=min(45*2**min(feed.consecutive_failures,8),900));feed.save()
        if shared_blocker(error):
            FreshProviderBackoff.objects.update_or_create(platform='discovery-'+source.platform,defaults={'due_at':timezone.now()+timedelta(minutes=15),'reason':error[:500]})
        return 'failed'
    finally:close_old_connections()


def poll_due_feeds():
    if not settings.FRESH_FEED_DISCOVERY_ENABLED:return {'disabled':True}
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_try_advisory_lock(728319433)')
        if not cursor.fetchone()[0]:return {'busy':True}
    try:
        ids=list(FreshDiscoveryFeed.objects.filter(enabled=True,next_poll_at__lte=timezone.now()).order_by('next_poll_at','pk').values_list('pk',flat=True)[:6])
        with ThreadPoolExecutor(max_workers=2) as pool:return dict(zip(ids,pool.map(_poll_one,ids)))
    finally:
        with connection.cursor() as cursor:cursor.execute('SELECT pg_advisory_unlock(728319433)')


def validate_feed_boundary(item,feed,uploaded):
    source=feed_source(feed)
    if (not feed.enabled or not feed.baseline_at or not source.artist.enabled or
        item.source.artist_id!=source.artist_id or item.platform!=source.platform or
        item.metadata.get('feed_native_id')!=source.native_id):raise ValueError('Upload discovery authority mismatch')
    if not uploaded or uploaded>timezone.now()+timedelta(seconds=30):raise ValueError('Exact upload timestamp unavailable/future')
    catchup=item.native_item_id in feed.catchup_native_ids and item.metadata.get('catchup_authorized') is True
    if uploaded<=feed.baseline_at and not catchup:raise ValueError('Historical upload predates independent discovery watermark')


def provider_metadata(item):
    feed=FreshDiscoveryFeed.objects.select_related('acquisition_source__artist','search_artist').get(pk=item.metadata['feed_id']);source=feed_source(feed)
    hold=FreshProviderBackoff.objects.filter(platform=source.platform,due_at__gt=timezone.now()).first()
    if hold:raise ProviderError('Recording provider hold active')
    provider=PROVIDERS['yt-dlp' if source.platform=='soundcloud' else 'yt-dlp-youtube']
    p=provider.probe(item.canonical_url,timeout=30);e=p.evidence or {}
    actual_uploader=str(e.get('uploader_id') if source.platform=='soundcloud' else e.get('channel_id'))
    if p.provider_item_id!=item.native_item_id or (not source.evidence.get('discovery_search') and actual_uploader!=source.native_id):
        raise ValueError('Independent upload recording/account identity mismatch')
    if source.evidence.get('discovery_search'):
        from archive_collection.acquisition import credits_match
        if not actual_uploader.isdigit() or not credits_match(p,{'credits':[{'id':item.source.native_profile_id,'name':source.artist.official_name}]},source):
            raise ValueError('Independent discovery upload lacks explicit performer/uploader evidence')
    timestamp=e.get('timestamp') or e.get('release_timestamp')
    uploaded=datetime.fromtimestamp(float(timestamp),tz=utc.utc) if timestamp else item.source_release_at
    validate_feed_boundary(item,feed,uploaded)
    if not p.duration_seconds or p.duration_seconds<=0 or not p.artwork_source_url:raise ValueError('Complete recording duration and recorded artwork required')
    if edition_markers(p.title) or re.search(r'(?i)\b(teaser|preview|trailer|reaction|interview|podcast|vlog|shorts|slowed|sped.?up|live|mixset)\b',p.title):raise ValueError('Upload is a preview, non-music item or unresolved version')
    if e.get('album') and e.get('track_number'):raise ValueError('Upload declares album membership; complete album classification/staging required')
    primary=source.artist;credit_names=[primary.official_name]
    if ' - ' in p.title:
        from archive_collection.services import _credit_block
        left=p.title.split(' - ',1)[0]
        candidates=[a.official_name for a in Artist.objects.all() if re.search(r'(?<!\w)'+re.escape(normalize_text(a.official_name))+r'(?!\w)',normalize_text(left))]
        if candidates:
            if not _credit_block(left,[normalize_text(n) for n in candidates]):raise ValueError('Explicit upload credit block has unresolved performers')
            credit_names=list(dict.fromkeys([primary.official_name,*candidates]))
    # Structured additional credits and explicit featuring cannot silently disappear.
    extra=e.get('artist') or ''
    if extra and normalize_text(extra)!=normalize_text(primary.official_name):
        for name in re.split(r'(?i)\s*(?:,|&|\bfeat\.?\b|\bft\.?\b|\bx\b)\s*',extra):
            matches=list(Artist.objects.filter(official_name__iexact=name.strip())[:2])
            if len(matches)!=1:raise ValueError('Structured performer credit is unresolved')
            if matches[0].official_name not in credit_names:credit_names.append(matches[0].official_name)
    if re.search(r'(?i)\b(feat|ft)\.?\s',p.title):raise ValueError('Explicit featured title requires complete performer credit review')
    if source.evidence.get('identity_role','artist')=='collaborator' and normalize_text(primary.official_name) not in normalize_text(p.title+' '+extra):
        raise ValueError('Collaborator upload does not explicitly credit monitored artist')
    title=p.title.strip()
    if ' - ' in title:
        from archive_collection.services import _credit_block
        left,right=title.split(' - ',1)
        if _credit_block(left,[normalize_text(n) for n in credit_names]):title=right.strip()
    for name in credit_names:
        title=re.sub(r'^'+re.escape(name)+r'\s*[-–—:]\s*','',title,flags=re.I)
    title=re.sub(r'(?i)\s*[\[(](?:official audio|official music video|official video|official visualizer|lyrics|lyric video)[\])]\s*',' ',title).strip()
    artist_ids=[ArtistSource.objects.get(artist__official_name=name,platform='spotify').native_profile_id for name in credit_names]
    item.source_release_at=uploaded;item.metadata={**item.metadata,'validated_upload_at':uploaded.isoformat(),'provider_recording_title':p.title,
        'provider_artwork_url':p.artwork_source_url,'duration':p.duration_seconds,'uploader':p.uploader}
    if source.evidence.get('discovery_search'):item.metadata.update(recording_uploader_id=actual_uploader,recording_uploader_profile=e.get('uploader_url') or '')
    item.save(update_fields=('source_release_at','metadata'))
    return {'album_type':'single','classification_basis':'standalone provider upload; no claim of a complete LP/EP',
        'official_release_title':item.title,'display_release_title':title,'artist_ids':artist_ids,'artist_credits':credit_names,
        'track_count':1,'artwork_url':p.artwork_source_url,'tracks':[{'id':item.native_item_id,'title':title,'position':1,
        'duration_seconds':p.duration_seconds,'artist_ids':artist_ids,'artist_credits':credit_names}]}


def direct_candidate(ft,blocked):
    item=ft.dispatch.source_item
    if not item.metadata.get('feed_discovery') or item.platform in blocked:return None
    if item.canonical_url in ft.evidence.get('failed_source_urls',[]):return None
    feed=FreshDiscoveryFeed.objects.select_related('acquisition_source__artist','search_artist').get(pk=item.metadata['feed_id']);source=feed_source(feed)
    if source.evidence.get('discovery_search'):
        source=SimpleNamespace(pk=None,platform='soundcloud',native_id=item.metadata['recording_uploader_id'],profile_url=item.metadata['recording_uploader_profile'],
            evidence={'identity_role':'independent_uploader'},artist=source.artist)
    return source,{'id':item.native_item_id,'title':item.metadata['provider_recording_title']},item.canonical_url
