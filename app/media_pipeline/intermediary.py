"""Owner-permitted public Spotsaver path. No shared keys or default fallback chain.

Protocol inspected at musicdl e5c3bd51b518642c24027921e63f482865809b61,
SpotifyMusicClient._parsewithspotsaverapi. Spotify is identity metadata here;
original encoding and final output/video binding can remain unreported.
"""
import ipaddress
import json
import re
import socket
import time
import threading
from pathlib import Path
from urllib.parse import urlsplit, urljoin

import requests
from django.conf import settings
from releases.normalization import normalize_text, edition_markers
from .providers import ProviderError, ProviderProbe, DownloadResult


class SpotsaverProvider:
    name='spotsaver'

    def __init__(self):
        self._local=threading.local()

    def can_handle(self,url):
        p=urlsplit(url or '')
        return bool(p.scheme=='https' and p.hostname=='open.spotify.com' and
                    not p.username and not p.password and p.port in (None,443) and
                    not p.query and not p.fragment and re.fullmatch(r'/track/[A-Za-z0-9]{22}',p.path))

    def _context(self,timeout):
        return {'deadline':time.monotonic()+min(int(timeout or 60),60),'requests':[], 'cookies':requests.cookies.RequestsCookieJar()}

    def _request(self,ctx,method,url,*,payload=None,binary=False):
        if len(ctx['requests'])>=7 or time.monotonic()>=ctx['deadline']:
            raise ProviderError('Spotsaver shared request/time budget exhausted')
        parts=urlsplit(url)
        allowed=parts.hostname=='spotsaver.net' or (method=='GET' and parts.hostname=='www.youtube.com' and parts.path=='/oembed') or (binary and parts.hostname and parts.hostname.endswith('.dlsrv.online'))
        if not allowed or parts.scheme!='https' or parts.username or parts.password or parts.port not in (None,443):
            raise ProviderError('Intermediary URL outside permitted public providers',retryable=False)
        try:
            addresses=socket.getaddrinfo(parts.hostname,443,type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global or a[4][0]=='91.107.178.12' for a in addresses):
                raise ProviderError('Intermediary address is not public',retryable=False)
            start=time.monotonic();metric={'domain':parts.hostname,'method':method};ctx['requests'].append(metric)
            with requests.Session() as session:
                session.trust_env=False
                session.cookies=ctx['cookies']
                session.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36',
                    'Referer':'https://spotsaver.net/results/','Accept':'*/*','Cache-Control':'no-cache'})
                response=session.request(method,url,json=payload,stream=True,allow_redirects=False,
                    timeout=(min(5,max(0.1,ctx['deadline']-time.monotonic())),min(10,max(0.1,ctx['deadline']-time.monotonic()))))
                with response:
                    metric['http_status']=response.status_code
                    if response.is_redirect:
                        if method!='GET':raise ProviderError('Intermediary POST redirect rejected',retryable=False)
                        return self._request(ctx,'GET',urljoin(url,response.headers.get('Location','')),binary=binary)
                    if response.status_code>=400:
                        shared=response.status_code in (401,403,429) or response.status_code>=500
                        raise ProviderError(f'Spotsaver {"shared " if shared else ""}HTTP {response.status_code}',retryable=shared)
                    limit=min(settings.MEDIA_MAX_UPLOAD_BYTES,45_000_000) if binary else 1_000_000
                    data=bytearray()
                    for chunk in response.iter_content(65536):
                        if time.monotonic()>=ctx['deadline']:raise ProviderError('Spotsaver shared transfer timed out')
                        data.extend(chunk)
                        if len(data)>limit:raise ProviderError('Intermediary response exceeds bounded size',retryable=False)
                    metric.update(bytes=len(data),seconds=round(time.monotonic()-start,3))
                    if binary:return bytes(data)
                    result=json.loads(data)
                    if not isinstance(result,dict):raise ValueError('Expected object response')
                    return result
        except (requests.RequestException,socket.gaierror) as exc:
            raise ProviderError('Spotsaver shared network '+type(exc).__name__) from None
        except (ValueError,TypeError) as exc:
            raise ProviderError('Intermediary malformed response',retryable=False) from None

    def probe(self,url,timeout=None,*,expected=None):
        if not self.can_handle(url) or not expected:
            raise ProviderError('Intermediary requires complete official fresh-track metadata',retryable=False)
        from types import SimpleNamespace
        from archive_collection.acquisition import title_matches,credits_match
        ctx=self._context(timeout)
        raw=self._request(ctx,'GET','https://spotsaver.net/api/spotify/?url='+url)
        items=raw.get('items')
        if not isinstance(items,list) or len(items)!=1 or not isinstance(items[0],dict):
            raise ProviderError('Intermediary single-track response incomplete',retryable=False)
        track=items[0];title=str(track.get('title') or '');artists=str(track.get('artist') or '')
        for key in ('id','trackId','spotifyId'):
            if track.get(key) and str(track[key])!=url.rsplit('/',1)[-1]:
                raise ProviderError('Intermediary returned another Spotify native ID',retryable=False)
        preliminary=ProviderProbe(self.name,url,'',title,expected['duration_seconds'],artists)
        if not title_matches(title,expected) or not credits_match(preliminary,expected,SimpleNamespace(evidence={'identity_role':'intermediary'})):
            raise ProviderError('Intermediary title/version or full credits mismatch',retryable=False)
        if track.get('album') and normalize_text(track['album'])!=normalize_text(expected['album_title']):
            raise ProviderError('Intermediary album/version mismatch',retryable=False)
        selected=self._request(ctx,'POST','https://spotsaver.net/api/get-id/',payload={'title':title,'artist':artists})
        video=selected.get('videoId')
        if not isinstance(video,str) or not re.fullmatch(r'[\w-]{11}',video):
            raise ProviderError('Intermediary selected recording identity missing',retryable=False)
        public=self._request(ctx,'GET','https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v='+video+'&format=json')
        text=normalize_text(public.get('title',''));author=normalize_text(public.get('author_name',''))
        wanted=normalize_text(expected['title']);primary=normalize_text(expected['credits'][0]['name'])
        if (not re.search(r'(?<!\w)'+re.escape(wanted)+r'(?!\w)',text) or
            not re.search(r'(?<!\w)'+re.escape(primary)+r'(?!\w)',text+' '+author) or
            edition_markers(public.get('title',''))!=edition_markers(expected['title']) or
            re.search(r'\b(?:reaction|demo|cover|preview|teaser|slowed|sped[ -]?up|music video)\b',text)):
            raise ProviderError('Intermediary public video recording/version mismatch',retryable=False)
        duration=track.get('duration')
        if duration:
            try:duration=float(duration)
            except (ValueError,TypeError):raise ProviderError('Intermediary duration metadata malformed',retryable=False) from None
            if not 0<duration or abs(duration-expected['duration_seconds'])>5:
                raise ProviderError('Intermediary duration metadata mismatch',retryable=False)
        self._local.context=(url,video,ctx)
        return ProviderProbe(self.name,url,video,title,expected['duration_seconds'],artists,evidence={
            'selected_video_id':video,'public_video_title':public['title'],'public_video_author':public.get('author_name'),
            'source_origin':'public intermediary; direct Spotify audio unproven','source_quality_unknown':True,
            'duration_basis':'official Spotify expected duration; actual full file validated after download',
            'output_video_binding':'unreported until download; owner permits omitted binding',
            'metadata_requests':list(ctx['requests']),'upstream_reference':'musicdl e5c3bd51b518642c24027921e63f482865809b61 selected Spotsaver method'})

    def download(self,probe,destination,timeout=None):
        cached=getattr(self._local,'context',None);self._local.context=None
        ctx=cached[2] if cached and cached[:2]==(probe.source_url,probe.provider_item_id) else self._context(timeout)
        result=self._request(ctx,'POST','https://spotsaver.net/api/download/',payload={
            'videoId':probe.provider_item_id,'candidateIds':[],'format':'mp3','title':probe.title+' - '+probe.uploader})
        resolved=result.get('videoId') or result.get('video_id')
        if resolved and resolved!=probe.provider_item_id:
            raise ProviderError('Intermediary resolved another video',retryable=False)
        if result.get('duration') and abs(float(result['duration'])-probe.duration_seconds)>5:
            raise ProviderError('Intermediary download duration mismatch',retryable=False)
        if result.get('title') and normalize_text(result['title'])!=normalize_text(probe.title):
            raise ProviderError('Intermediary resolved another title',retryable=False)
        url=result.get('downloadUrl') or result.get('url') or result.get('fileUrl') or result.get('mediaUrl')
        if not isinstance(url,str):raise ProviderError('Intermediary file response incomplete',retryable=False)
        data=self._request(ctx,'GET',url,binary=True)
        extension='.mp3' if data.startswith(b'ID3') or data[:2] in (b'\xff\xfb',b'\xff\xf3',b'\xff\xf2') else '.m4a' if b'ftyp' in data[:32] else None
        if not extension:raise ProviderError('Intermediary output is not a permitted complete audio container',retryable=False)
        destination=Path(destination);destination.mkdir(mode=0o700,parents=True,exist_ok=True)
        path=destination/('source'+extension)
        with path.open('xb') as output:output.write(data)
        path.chmod(0o600)
        return DownloadResult(path,probe.provider_item_id,probe.title,probe.duration_seconds,probe.uploader,{
            'provider_domains':list(dict.fromkeys(c['domain'] for c in ctx['requests'])),
            'download_requests':ctx['requests'],'resolved_video_id':resolved,
            'output_video_binding':'matched' if resolved else 'unreported_owner_permitted',
            'source_quality_unknown':True,'conversion':'none locally; intermediary conversion unknown'})


def find_spotsaver(recording,blocked):
    from types import SimpleNamespace
    from django.utils import timezone
    from datetime import timedelta
    from .providers import redact_diagnostic
    if 'spotsaver' in blocked:return None,{'reason':'Intermediary provider hold active','checks':[]}
    cache=recording.evidence.get('spotsaver_failed_lookup',{})
    if cache.get('retry_at') and timezone.datetime.fromisoformat(cache['retry_at'])>timezone.now():
        return None,{'reason':cache['reason'],'checks':[]}
    try:
        url='https://open.spotify.com/track/'+(getattr(recording,'native_id',None) or recording.spotify_id)
        probe=SpotsaverProvider().probe(url,timeout=40,expected=recording.metadata)
        if url in recording.evidence.get('failed_source_urls',[]):return None,{'reason':'Prior invalid intermediary candidate preserved for review','checks':[]}
        source=SimpleNamespace(pk=None,platform='spotsaver',native_id=probe.provider_item_id,profile_url='',evidence={'identity_role':'intermediary'})
        row={'id':probe.provider_item_id,'title':probe.title}
        return (source,row,url),{'reason':'Owner-permitted intermediary metadata match; full file validation still required', 'checks':[probe.evidence]}
    except ProviderError as exc:
        reason=redact_diagnostic(exc)
        if 'Spotsaver shared' in reason:blocked['spotsaver']=reason
        recording.evidence={**recording.evidence,'spotsaver_failed_lookup':{'reason':reason,'retry_at':(timezone.now()+timedelta(seconds=60)).isoformat()}}
        recording.save(update_fields=('evidence','updated_at'))
        return None,{'reason':reason,'checks':[{'intermediary_error':reason}]}
