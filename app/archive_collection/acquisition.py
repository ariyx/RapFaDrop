"""Bounded official-source catalogs. Acquisition identities never enable discovery."""
import json,re,time
from datetime import timedelta
from urllib.parse import urlsplit
from django.db import transaction
from django.utils import timezone
from media_pipeline.providers import ProviderError,YtDlpProvider,YouTubeProvider,redact_diagnostic
from sources.models import ArtistSource,SourceAuditEvent
from releases.normalization import normalize_text,edition_markers
from .models import AcquisitionSource


def display_title(value,names):
    from .services import _credit_block,_recording_title
    # Explicit production annotations do not identify a different musical version.
    text=re.sub(r'\s*[\[(](?:prod\.?|produced by)\s+[^\])]+[\])]\s*',' ',str(value),flags=re.I).strip()
    text=re.sub(r'\s*[\[(](?:official audio|official lyric video|official music video|official visualizer|lyrics)[\])]\s*',' ',text,flags=re.I).strip()
    normalized=_recording_title(text,names)
    if '-' in text:
        left,right=re.split(r'\s*-\s*',text,maxsplit=1)
        if _credit_block(left,names):normalized=_recording_title(right,names)
        elif _credit_block(right,names):normalized=_recording_title(left,names)
    return normalized


def title_matches(title,metadata):
    names=[normalize_text(c['name']) for c in metadata['credits']]
    names += [name.replace(' ','') for name in names if ' ' in name and len(name.replace(' ',''))>4]
    return display_title(title,names)==display_title(metadata['title'],names) and edition_markers(title)==edition_markers(metadata['title'])


@transaction.atomic
def verify_source(artist,platform,native_id,profile_url,evidence):
    """Persist checked crosslinks/native response, not a guessed display-name identity."""
    parts=urlsplit(profile_url)
    allowed=bool(platform=='soundcloud' and parts.hostname=='soundcloud.com' and re.fullmatch(r'/[\w-]+',parts.path) and str(native_id).isdigit())
    allowed|=platform=='youtube' and parts.hostname in {'youtube.com','www.youtube.com'} and parts.path=='/channel/'+str(native_id) and bool(re.fullmatch(r'UC[\w-]{22}',str(native_id)))
    spotify=ArtistSource.objects.get(artist=artist,platform='spotify')
    if (not allowed or parts.scheme!='https' or parts.query or parts.fragment or parts.username or parts.port not in (None,443)
            or evidence.get('spotify_artist_id')!=spotify.native_profile_id or not evidence.get('checked_at')
            or not evidence.get('independent_links') or evidence.get('response_native_id')!=str(native_id)):
        raise ValueError('Acquisition identity requires checked independent official links and exact native response')
    obj,created=AcquisitionSource.objects.get_or_create(artist=artist,platform=platform,native_id=str(native_id),defaults={
        'profile_url':profile_url,'evidence':evidence,'verified_at':timezone.now()})
    if not created and obj.profile_url!=profile_url:
        raise ValueError('Existing native acquisition source URL is preserved; reconcile profile change')
    if created:
        SourceAuditEvent.objects.create(artist=artist,event_type='acquisition_source_verified',detail={'acquisition_source_id':obj.pk,'platform':platform,'native_id':str(native_id),'profile_url':profile_url,'evidence':evidence,'discovery_enabled':False})
    return obj


def safe_row(row):
    keys=('id','title','duration','uploader','uploader_id','uploader_url','channel_id','channel_url','webpage_url','url')
    out={k:row.get(k) for k in keys}
    # Only stable public URLs, never formats, signed transport URLs or raw payloads.
    for key in ('url','webpage_url','uploader_url','channel_url'):
        value=out.get(key)
        if value:
            parts=urlsplit(str(value))
            if parts.scheme!='https' or parts.hostname not in {'soundcloud.com','www.soundcloud.com','youtube.com','www.youtube.com','music.youtube.com'}:
                out[key]=None
    return out


def catalog(source,provider):
    if source.retry_due_at and source.retry_due_at>timezone.now():
        return source.catalog,{'cache':True,'backoff':True,'error':source.last_error}
    if source.catalog_checked_at and source.catalog_checked_at>timezone.now()-timedelta(hours=6):
        return source.catalog,{'cache':True,'entries':len(source.catalog)}
    url=source.profile_url if source.platform=='soundcloud' else source.profile_url+'/videos'
    start=time.monotonic()
    try:
        raw=json.loads(provider._run(['--socket-timeout','10','--skip-download','--flat-playlist','--playlist-end','50','--dump-single-json','--',url],60))
        entries=raw.get('entries')
        if not isinstance(entries,list) or len(entries)>50:
            raise ProviderError('Bounded official catalog response malformed')
        source.catalog=[safe_row(r) for r in entries if isinstance(r,dict)]
        source.catalog_checked_at=timezone.now();source.last_error='';source.retry_due_at=None
        source.save(update_fields=('catalog','catalog_checked_at','last_error','retry_due_at'))
        return source.catalog,{'cache':False,'entries':len(entries),'bounded_to':50,'seconds':round(time.monotonic()-start,3)}
    except Exception as exc:
        source.last_error=redact_diagnostic(exc);source.retry_due_at=timezone.now()+timedelta(minutes=15)
        source.save(update_fields=('last_error','retry_due_at'))
        return source.catalog,{'cache':bool(source.catalog),'error':source.last_error,'seconds':round(time.monotonic()-start,3)}


def find(recording):
    from .services import identity_matches
    m=recording.metadata
    sources=list(AcquisitionSource.objects.filter(artist__sources__platform='spotify',artist__sources__native_profile_id__in=[c['id'] for c in m['credits']]).distinct())
    checks=[];budget=6
    for source in sorted(sources,key=lambda s:s.platform!='soundcloud'):
        if source.evidence.get('scope_recordings') and recording.spotify_id not in source.evidence['scope_recordings']:
            continue
        provider=YtDlpProvider() if source.platform=='soundcloud' else YouTubeProvider()
        rows,metrics=catalog(source,provider);checks.append({'acquisition_source_id':source.pk,'catalog':metrics})
        candidates=[r for r in rows if title_matches(r.get('title'),m)]
        # Reuse exact stable results on retry; search only if a direct catalog failed.
        if not candidates and source.platform=='soundcloud' and not metrics.get('backoff'):
            cache=recording.evidence.get('provider_search_cache',{}).get(str(source.pk))
            if cache and cache.get('checked_at') and timezone.now()-timezone.datetime.fromisoformat(cache['checked_at'])<timedelta(hours=6):
                search=cache['rows']
            else:
                try:
                    query=source.artist.official_name+' '+m['title']
                    raw=json.loads(provider._run(['--socket-timeout','10','--skip-download','--flat-playlist','--dump-single-json','--playlist-end','20','--',f'scsearch20:{query}'],45))
                    search=[safe_row(r) for r in (raw.get('entries') or [])[:20] if isinstance(r,dict)]
                    cachemap={**recording.evidence.get('provider_search_cache',{}),str(source.pk):{'checked_at':timezone.now().isoformat(),'rows':search}}
                    recording.evidence={**recording.evidence,'provider_search_cache':cachemap};recording.save(update_fields=('evidence','updated_at'))
                except Exception as exc:
                    checks.append({'acquisition_source_id':source.pk,'search_error':redact_diagnostic(exc)})
                    search=[]
            candidates=[r for r in search if title_matches(r.get('title'),m)]
        for row in candidates:
            if budget<=0:break
            url=row.get('webpage_url') or row.get('url') or ''
            if url in recording.evidence.get('failed_source_urls',[]):continue
            if not provider.can_handle(url):continue
            budget-=1
            try:
                probe=provider.probe(url,timeout=30)
                evidence=probe.evidence or {}
                actual={**row,'id':probe.provider_item_id,'title':probe.title,'duration':probe.duration_seconds,
                    'uploader':probe.uploader,'uploader_url':evidence.get('uploader_url') or row.get('uploader_url'),
                    'uploader_id':evidence.get('uploader_id'),'channel_id':evidence.get('channel_id')}
                if source.platform=='soundcloud':
                    valid=str(actual['uploader_id'])==source.native_id and title_matches(probe.title,m)
                else:
                    # An official channel does not turn a music video/live take into the studio recording.
                    valid=actual['channel_id']==source.native_id and title_matches(probe.title,m)
                valid &= bool(probe.duration_seconds and abs(probe.duration_seconds-m['duration_seconds'])<=5)
                checks.append({'acquisition_source_id':source.pk,'id':probe.provider_item_id,'title':probe.title,'duration':probe.duration_seconds,'matched':bool(valid)})
                if valid:return (source,actual,url),{'checks':checks,'reason':'Verified official native uploader/channel, complete recording/version and duration','provider_probes':6-budget}
            except Exception as exc:
                checks.append({'acquisition_source_id':source.pk,'id':str(row.get('id')),'probe_error':redact_diagnostic(exc)})
    return None,{'checks':checks,'provider_probes':6-budget,'reason':'No complete confidently matched recording in bounded verified catalogs/searches; inspect source/match evidence before manual upload.' if sources else 'No corroborated credited acquisition profile yet; independent official links are required.'}
