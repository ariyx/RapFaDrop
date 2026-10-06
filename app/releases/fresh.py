"""Post-baseline dispatch. Archive selections alone never authorize fresh work."""
import hashlib
import subprocess
import logging
from collections import Counter
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from archive_collection.models import Recording
from media_pipeline.models import MediaCandidate
from media_pipeline.providers import PROVIDERS, redact_diagnostic
from media_pipeline.services import retry_candidate
from publication.models import AlbumSession, Publication
from publication.services import prepare_album, reserve_audio, require_ready
from sources.models import Artist, ArtistSource, BaselineRun, SourceItem
from .models import (CanonicalRelease, FreshControl, FreshDispatch, FreshProviderBackoff, FreshTrack,
                     IdentityAuditEvent, ProcessingQueueItem, ReleaseCredit, ReleaseTrack,
                     ReviewItem, SourceMatch, Track, TrackCredit)
from .normalization import edition_markers, normalize_text


def _generic_review(match, item):
    if match.matching_method == 'spotify_release_id_review':
        return True
    # A spelling-only legacy rejection can be checked against native credits;
    # it is not auto-approved until validate_official has verified those IDs.
    return (match.matching_method == 'review' and item.metadata.get('artist_id') == item.source.native_profile_id and
            ReviewItem.objects.filter(source_item=item, category='artist_mismatch',
                reason='Spotify release credits omit the verified artist', state='open').exists())


def classify(item, *, now=None):
    now = now or timezone.now()
    source = item.source
    evidence = {"observed_at": item.first_observed_at.isoformat(),
                "release_at": item.source_release_at.isoformat() if item.source_release_at else None,
                "baseline_completed_at": source.baseline_completed_at.isoformat() if source.baseline_completed_at else None}
    if item.from_baseline:
        return "excluded", "Historical baseline item", evidence
    if item.metadata.get('feed_discovery'):
        from .models import FreshDiscoveryFeed
        feed=FreshDiscoveryFeed.objects.filter(pk=item.metadata.get('feed_id'),enabled=True,baseline_at__isnull=False).first()
        if not feed or not source.enabled or source.verification!='verified' or not source.artist.enabled:
            return 'review','Independent upload feed lacks enabled baseline authority',evidence
        return 'eligible','Independent upload observation; exact native metadata/time required before media',evidence
    if not item.metadata.get("spotify_discovery") or item.metadata.get("archive_only"):
        return "excluded", "Archive/acquisition fact, not a discovery", evidence
    baseline = BaselineRun.objects.filter(source=source, status="complete").order_by("completed_at").first()
    if not baseline or not baseline.completed_at or item.first_observed_at <= baseline.completed_at:
        return "review", "Missing successful post-baseline observation boundary", evidence
    evidence["baseline_run_id"] = baseline.pk
    if not source.enabled or source.verification != "verified" or not source.artist.enabled:
        return "review", "Artist/source is not enabled and verified", evidence
    release_at = item.source_release_at
    if not release_at:
        return "review", "Release date unavailable: catalog addition cannot establish freshness", evidence
    # Provider dates have day precision. Same baseline day cannot prove newness.
    if release_at.date() < baseline.completed_at.date():
        return "excluded", "Historical catalog addition predates baseline", evidence
    if release_at.date() == baseline.completed_at.date():
        return "review", "Day-only release date overlaps baseline; freshness unresolved", evidence
    if release_at > now or release_at.date() > item.first_observed_at.date():
        return "review", "Future/conflicting release date", evidence
    match = SourceMatch.objects.filter(source_item=item).first()
    if match and (match.state == "rejected" or
                  (match.state == "review_required" and not _generic_review(match, item))):
        return "review", "Existing unresolved/rejected identity decision must be resolved", evidence
    tracks = item.metadata.get("tracks") or []
    if item.metadata.get('album_type') == 'single' and tracks and all(Recording.objects.filter(spotify_id=t.get("id")).exists() for t in tracks):
        if all(Recording.objects.filter(spotify_id=t.get("id"), publication__state="published").exists() for t in tracks):
            return "excluded", "Recording already published in frozen collection", evidence
        return "excluded", "Frozen popular selection; not fresh dispatch authority", evidence
    return "eligible", "Complete observation after baseline and later official release day", evidence


@transaction.atomic
def build_manifest(now=None):
    """No network, downloads or sends; decisions are persisted before queueing."""
    from django.db.models import Q
    for item in SourceItem.objects.filter(Q(metadata__spotify_discovery=True)|Q(metadata__feed_discovery=True), freshdispatch__isnull=True).select_related("source__artist").order_by("pk"):
        disposition, reason, evidence = classify(item, now=now)
        FreshDispatch.objects.get_or_create(source_item=item, defaults={
            "disposition": disposition, "reason": reason, "evidence": evidence})
    return dict(Counter(FreshDispatch.objects.values_list("disposition", flat=True)))


def validate_official(item, metadata):
    from sources.spotify_scraper import SPOTIFY_ID
    kind = {"single": "single", "album": "lp", "ep": "ep"}.get(metadata.get("album_type"))
    if metadata.get('official_release_title') and normalize_text(metadata['official_release_title']) != normalize_text(item.title):
        raise ValueError('Official release title conflicts with stored discovery')
    tracks = metadata.get("tracks")
    if kind is None or not isinstance(tracks, list) or not 1 <= len(tracks) <= 100 or len(tracks) != metadata.get("track_count"):
        raise ValueError("Complete explicit release classification/track list required")
    if kind == "single" and len(tracks) != 1:
        raise ValueError("Multi-track single classification requires review")
    if item.source.native_profile_id not in metadata.get("artist_ids", []):
        raise ValueError("Official native artist credits omit the monitored artist")
    if edition_markers(item.title):
        raise ValueError("Release edition relationship requires review")
    seen = set()
    import re
    native_pattern = SPOTIFY_ID if item.platform=='spotify' else re.compile(r'\d{1,22}' if item.platform=='soundcloud' else r'[\w-]{11}')
    if item.platform!='spotify' and not item.metadata.get('feed_discovery'):
        raise ValueError('Non-Spotify dispatch requires independent upload feed evidence')
    for position, row in enumerate(tracks, 1):
        ids, names = row.get("artist_ids") or [], row.get("artist_credits") or []
        if (row.get("position") != position or not native_pattern.fullmatch(row.get("id", "")) or row["id"] in seen or
                not row.get("title") or not row.get("duration_seconds") or float(row["duration_seconds"]) <= 0 or
                not ids or len(ids) != len(names) or any(not SPOTIFY_ID.fullmatch(i) for i in ids)):
            raise ValueError("Incomplete ordered native track/credit/duration evidence")
        if edition_markers(row["title"]):
            raise ValueError("Track edition relationship requires review")
        seen.add(row["id"])
    return kind, tracks


def _artist(native, name):
    source = ArtistSource.objects.filter(platform="spotify", native_profile_id=native).select_related("artist").first()
    if source:
        return source.artist
    matches = list(Artist.objects.filter(official_name=name)[:2])
    if len(matches) == 1:
        return matches[0]
    return Artist.objects.create(official_name=name, enabled=False)


def _track_identity(row, platform='spotify'):
    # Exact Spotify IDs and evidenced archive aliases take precedence over names.
    native = row["id"]
    record = Recording.objects.filter(spotify_id=native).select_related("track", "canonical_alias__canonical__track").first() if platform=='spotify' else None
    if record and record.track_id:
        track = record.canonical_alias.canonical.track if hasattr(record, "canonical_alias") else record.track
        if ({c['id'] for c in record.metadata.get('credits', [])} != set(row['artist_ids']) or
                normalize_text(track.official_title) != normalize_text(row["title"]) or
                not track.duration_seconds or abs(track.duration_seconds - row["duration_seconds"]) > 5):
            raise ValueError("Stored native recording conflicts with official title/duration")
        return track
    existing = SourceMatch.objects.filter(source_item__platform=platform, source_item__native_item_id=native,
        state__in=("matched", "approved", "corrected"), track__isnull=False).select_related("track").first()
    if existing:
        return existing.track
    artists = [_artist(native, name) for native, name in zip(row["artist_ids"], row["artist_credits"])]
    candidates = list(Track.objects.filter(normalized_title=normalize_text(row["title"]), edition="original").distinct())
    comparable = [t for t in candidates if set(t.credited_artists.values_list("pk", flat=True)) == {a.pk for a in artists}]
    if comparable:
        if len(comparable) != 1 or not comparable[0].duration_seconds or abs(comparable[0].duration_seconds - row["duration_seconds"]) > 5:
            raise ValueError("Cross-platform same-credit/title recording is ambiguous")
        return comparable[0]
    track, created = Track.objects.get_or_create(identity_key=hashlib.sha256(f"{platform}:track:{row['id']}".encode()).hexdigest(),
        defaults={"official_title": row["title"], "normalized_title": normalize_text(row['title']), "duration_seconds": round(row["duration_seconds"])})
    if created:
        for position, artist in enumerate(artists, 1):
            TrackCredit.objects.create(track=track, artist=artist, position=position)
    return track


@transaction.atomic
def materialize(dispatch, metadata, *, append=False):
    dispatch = FreshDispatch.objects.select_for_update().select_related("source_item__source__artist").get(pk=dispatch.pk)
    if dispatch.release_id and not append:
        return dispatch
    item = dispatch.source_item
    kind, tracks = validate_official(item, metadata)
    if append:
        previous = list(dispatch.tracks.order_by('position'))
        if len(tracks) < len(previous) or any(row['id'] != old.native_id or
                normalize_text(row['title']) != normalize_text(old.metadata['title']) or
                abs(row['duration_seconds'] - old.metadata['duration_seconds']) > 1
                for row, old in zip(tracks, previous)):
            raise ValueError('Published album changed existing track order/version; append-only update requires review')
    # Credits appearing on every track establish primary attribution. Other
    # release-level/track contributors remain guests, not assumed album primaries.
    common = set(tracks[0]["artist_ids"])
    for row in tracks:
        common &= set(row["artist_ids"])
    primary = [(native, name) for native, name in zip(metadata["artist_ids"], metadata["artist_credits"]) if native in common]
    if not primary:
        raise ValueError("Primary album attribution unresolved from complete credits")
    canonical_tracks = [_track_identity(row,item.platform) for row in tracks]
    release_title=metadata.get('display_release_title') or item.title
    primary_artists = [_artist(native, name) for native, name in primary]
    same = []
    for other in CanonicalRelease.objects.filter(release_type=kind, state__in=('identified','approved')):
        if (normalize_text(other.title) == normalize_text(release_title) and
                set(other.credited_artists.values_list('pk',flat=True)) == {a.pk for a in primary_artists} and
                list(other.release_tracks.order_by('position').values_list('track_id',flat=True)) == [t.pk for t in canonical_tracks]):
            same.append(other)
    if len(same) > 1:
        raise ValueError('More than one canonical ordered release matches; cross-platform review required')
    if dispatch.release_id:
        release, created = dispatch.release, False
    elif same:
        release, created = same[0], False
    else:
        release, created = CanonicalRelease.objects.get_or_create(
            identity_key=hashlib.sha256(f"{item.platform}:release:{item.native_item_id}".encode()).hexdigest(),
            defaults={"title": release_title, "release_type": kind, "release_date": item.source_release_at.date(), "state": "approved"})
    if release.release_type != kind or normalize_text(release.title) != normalize_text(release_title):
        raise ValueError("Existing native release classification conflicts")
    if created:
        for position, (native, name) in enumerate(primary, 1):
            ReleaseCredit.objects.create(release=release, artist=_artist(native, name), position=position)
    match, _ = SourceMatch.objects.get_or_create(source_item=item, defaults={"matching_method": "fresh_official_release", "state": "matched"})
    if match.state == "rejected" or (match.state == "review_required" and not _generic_review(match, item)):
        raise ValueError("Unresolved identity decision cannot be overwritten")
    match.release, match.state, match.confidence = release, "matched", 100
    match.matching_method = "fresh_official_release"
    match.evidence = {**match.evidence, "fresh_manifest_id": dispatch.pk, "official_metadata": metadata}
    match.save()
    generic = ReviewItem.objects.filter(source_item=item, state="open", source_match=match).first()
    if generic:
        generic.state, generic.resolution = "approved", "Owner-authorized catch-up: native official identity and post-baseline date verified"
        generic.reviewed_at = timezone.now()
        generic.save(update_fields=("state", "resolution", "reviewed_at", "updated_at"))
    for row, track in zip(tracks, canonical_tracks):
        prior = ReleaseTrack.objects.filter(track=track, release__release_type="single").first() if kind != "single" else None
        member, _ = ReleaseTrack.objects.get_or_create(release=release, position=row["position"], defaults={"track": track, "prior_single": prior})
        if member.track_id != track.pk:
            raise ValueError("Native release track order conflict")
        m = {"title": row["title"], "duration_seconds": row["duration_seconds"],
             "credits": [{"id": native, "name": name} for native, name in zip(row["artist_ids"], row["artist_credits"])],
             "spotify_url": f"https://open.spotify.com/track/{row['id']}" if item.platform=='spotify' else '', "album_id": item.native_item_id,
             "album_title": release_title, "album_type": metadata["album_type"], "album_artists": [name for _, name in primary],
             "artwork_url": metadata.get("artwork_url", ""), "release_date": release.release_date.isoformat(),
             "track_number": row.get("track_number") or row["position"], "disc_number": row.get("disc_number") or 1}
        if item.platform!='spotify':m.update(discovery_platform=item.platform,discovery_url=item.canonical_url)
        ft, _ = FreshTrack.objects.get_or_create(dispatch=dispatch, position=row["position"], defaults={"track": track, "native_id": row["id"], "metadata": m})
        child, _ = SourceItem.objects.get_or_create(platform=item.platform, native_item_id=f"fresh-track:{item.native_item_id}:{row['id']}",
            defaults={"source": item.source, "title": row["title"], "canonical_url": m["spotify_url"] or item.canonical_url,
                      "source_release_at": item.source_release_at, "first_observed_at": item.first_observed_at,
                      "metadata": {"fresh_track": True, "duration": row["duration_seconds"]}})
        SourceMatch.objects.get_or_create(source_item=child, defaults={"track": track, "release": release, "confidence": 100,
            "state": "matched", "matching_method": "fresh_official_track", "evidence": {"fresh_manifest_id": dispatch.pk,
            "official_metadata": {"title": row["title"], "artists": row["artist_credits"], "album": release_title,
                "album_artists": m["album_artists"], "artwork_url": m["artwork_url"], "release_date": m["release_date"],
                "track_number": m["track_number"], "disc_number": m["disc_number"]}}})
        ProcessingQueueItem.objects.get_or_create(track=track, defaults={"release": release, "due_at": timezone.now()})
    dispatch.release = release
    dispatch.evidence = {**dispatch.evidence, "official": metadata, "features": [name for row in tracks for native, name in zip(row["artist_ids"], row["artist_credits"]) if native not in common]}
    dispatch.save()
    IdentityAuditEvent.objects.create(source_item=item, source_match=match, action="fresh_manifest_queued", detail={"dispatch_id": dispatch.pk})
    return dispatch


def refresh_completed_album(dispatch):
    from sources.adapters import SpotifyAdapter
    item = dispatch.source_item
    detail = {'native_item_id':item.native_item_id, 'metadata':dict(item.metadata), 'sanitized_raw_data':{}}
    adapter = SpotifyAdapter()
    adapter.fetch_item(item.source, detail)
    if not detail.get('source_release_at') or detail['source_release_at'].date() != item.source_release_at.date():
        raise ValueError('Published album release date changed; version review required')
    updated = materialize(dispatch, detail['metadata'], append=True)
    if updated.tracks.count() > len(dispatch.evidence['official']['tracks']):
        updated.processing_state, updated.attempts, updated.reason = 'pending', 0, 'New appended official tracks; original album session remains frozen'
        updated.save(update_fields=('processing_state', 'attempts', 'reason', 'updated_at'))
    updated.due_at = timezone.now() + timedelta(seconds=item.source.poll_interval_seconds)
    updated.save(update_fields=('due_at', 'updated_at'))
    return updated


def _candidate(ft, found):
    import hashlib
    source, row, url = found
    match = SourceMatch.objects.get(track=ft.track, release=ft.dispatch.release, matching_method="fresh_official_track",
                                   evidence__fresh_manifest_id=ft.dispatch_id)
    provider = {'soundcloud':'yt-dlp', 'youtube':'yt-dlp-youtube', 'spotsaver':'spotsaver'}[source.platform]
    # Keep official Spotify identity as authority; independently matched transport
    # identity is rechecked by the media provider before downloading.
    candidate, _ = MediaCandidate.objects.get_or_create(track=ft.track, source_match=match, provider=provider,
        transport_identity=hashlib.sha256((str(row['id'])+'\n'+url).encode()).hexdigest(), defaults={
        "release": ft.dispatch.release, "expected_duration_seconds": ft.metadata["duration_seconds"], "provenance": {
            "provider": provider, "source_url": url, "acquisition_platform": source.platform,
            "native_item_id": str(row["id"]), "source_recording_title": row["title"],
            "official_channel_id": source.native_id, "official_profile": source.profile_url,
            "acquisition_source_id": source.pk, "spotify_track_id": ft.native_id,
            "fresh_manifest_id": ft.dispatch_id, "conversion": "none requested", "provenance_confidence": 95}})
    if source.evidence.get('identity_role') == 'independent_uploader' and not candidate.attempt_count:
        candidate.provenance={**candidate.provenance,'origin_status':'independent_uploader',
            'official_profile':'','uploader_profile':source.profile_url,'recording_uploader_id':source.native_id,
            'matched_credits':ft.metadata['credits'],
            'source_quality_unknown':True,'provenance_confidence':90}
        candidate.save(update_fields=('provenance','updated_at'))
    if source.platform == 'spotsaver' and not candidate.attempt_count:
        candidate.provenance={**candidate.provenance,'origin_status':'intermediary', 'source_quality_unknown':True,
            'official_channel_id':'','official_profile':'','selected_video_id':row['id'],
            'matched_metadata':ft.metadata,'source_origin':'public Spotsaver intermediary; direct Spotify audio unproven',
            'owner_policy':'Original sources preferred; complete matched intermediary output permitted, original encoding may be unknown',
            'output_video_binding':'unreported_owner_permitted','provenance_confidence':90}
        candidate.save(update_fields=('provenance','updated_at'))
    ft.candidate = candidate
    ft.save(update_fields=("candidate", "updated_at"))
    return candidate


def verified_ready(candidate):
    candidate = require_ready(candidate)
    readback = candidate.preparation_report.get('readback', {})
    if (not candidate.artwork_path or candidate.artwork_state != "embedded" or
            not all(readback.get(k) is True for k in ('title_matches', 'main_artists_match', 'album_suffix_matches',
                                                     'channel_fields_read_back', 'artwork_read_back'))):
        raise ValueError("Official artwork and actual tag readback required")
    if candidate.validation_report.get("full_decode") != "passed":
        decoded = subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", candidate.prepared_path,
                                  "-map", "0:a:0", "-f", "null", "-"], capture_output=True, timeout=60)
        if decoded.returncode:
            raise ValueError("Full-file decoding failed")
        candidate.validation_report = {**candidate.validation_report, "full_decode": "passed"}
        candidate.save(update_fields=("validation_report", "updated_at"))
    return candidate


def process_dispatch(dispatch, blocked):
    from archive_collection.acquisition import find, shared_blocker
    from sources.adapters import SpotifyAdapter
    if not dispatch.release_id:
        item = dispatch.source_item
        if item.metadata.get('feed_discovery'):
            from .feeds import provider_metadata
            from media_pipeline.providers import ProviderError
            try:metadata=provider_metadata(item)
            except ProviderError as exc:
                platform=item.platform;reason=redact_diagnostic(exc)[:500]
                if shared_blocker(reason):
                    blocked[platform]=reason
                    FreshProviderBackoff.objects.update_or_create(platform=platform,defaults={'due_at':timezone.now()+timedelta(minutes=15),'reason':reason})
                dispatch.due_at=timezone.now()+timedelta(seconds=45);dispatch.reason=reason;dispatch.save(update_fields=('due_at','reason','updated_at'));return
            dispatch = materialize(dispatch,metadata)
        else:
            detail = {"native_item_id": item.native_item_id, "metadata": dict(item.metadata), "sanitized_raw_data": {}}
            adapter = SpotifyAdapter()
            adapter.fetch_item(item.source, detail)
            if not detail.get("source_release_at") or detail["source_release_at"].date() != item.source_release_at.date():
                raise ValueError("Refreshed official release date conflicts with stored discovery")
            dispatch = materialize(dispatch, detail["metadata"])
    if dispatch.tracks.exists() and all(Publication.objects.filter(track=ft.track, channel__target=settings.TELEGRAM_PRODUCTION_CHAT_ID,
                state='published').exists() for ft in dispatch.tracks.all()):
        if dispatch.release.release_type == 'single' or AlbumSession.objects.filter(release=dispatch.release, state='complete').exists():
            dispatch.processing_state, dispatch.reason = 'complete', 'All required recordings durably published/reused'
            dispatch.due_at = timezone.now() + timedelta(seconds=dispatch.source_item.source.poll_interval_seconds)
            dispatch.save(update_fields=('processing_state', 'reason', 'due_at', 'updated_at'))
            ProcessingQueueItem.objects.filter(track_id__in=dispatch.tracks.values_list('track_id', flat=True),
                state__in=('pending','retry_wait')).update(state='complete', updated_at=timezone.now())
            return
    all_ready = True
    acquisition_budget = 2
    ready_before = dispatch.tracks.filter(candidate__state='ready').count()
    for ft in dispatch.tracks.select_related("track", "candidate", "dispatch__release").order_by("updated_at", "pk"):
        prior = Publication.objects.filter(track=ft.track, channel__target=settings.TELEGRAM_PRODUCTION_CHAT_ID, state="published").first()
        if prior:
            ft.publication = prior
            ft.save(update_fields=("publication", "updated_at"))
            continue
        candidate = ft.candidate
        manual = MediaCandidate.objects.filter(track=ft.track, source_match__matching_method='fresh_official_track', state='ready').first()
        if manual and (candidate is None or candidate.state != 'ready'):
            candidate = manual
            ft.candidate = manual
            ft.save(update_fields=('candidate', 'updated_at'))
        terminal_failure = bool(candidate and candidate.attempt_count and candidate.state in {'invalid', 'review_required'})
        alternative_during_hold = bool(candidate and candidate.state != 'ready' and
            candidate.provenance.get('acquisition_platform') in blocked and
            ((settings.FRESH_INDEPENDENT_UPLOADERS_ENABLED and 'soundcloud' not in blocked) or
             (settings.FRESH_SPOTSAVER_ENABLED and 'spotsaver' not in blocked)))
        if terminal_failure or alternative_during_hold:
            failed_url = candidate.provenance.get('source_url')
            if failed_url and terminal_failure:
                ft.evidence = {**ft.evidence, 'failed_source_urls':list(dict.fromkeys(
                    [*ft.evidence.get('failed_source_urls', []), failed_url]))}
                ft.save(update_fields=('evidence', 'updated_at'))
            candidate = None
        if candidate is None:
            if acquisition_budget <= 0:
                all_ready = False
                continue
            acquisition_budget -= 1
            from .feeds import direct_candidate
            found=direct_candidate(ft,blocked)
            evidence={'reason':'Direct verified upload source; complete media validation required'}
            if not found:found, evidence = find(ft, blocked_providers=blocked,
                                   cache_age=timedelta(seconds=dispatch.source_item.source.poll_interval_seconds),
                                   allow_independent=settings.FRESH_INDEPENDENT_UPLOADERS_ENABLED)
            if not found and settings.FRESH_SPOTSAVER_ENABLED and ft.metadata.get('spotify_url'):
                from media_pipeline.intermediary import find_spotsaver
                found, fallback = find_spotsaver(ft,blocked)
                evidence={**evidence, 'intermediary':fallback}
                if found:evidence['reason']=fallback['reason']
            ft.evidence = {**ft.evidence, "acquisition": evidence}
            ft.save(update_fields=("evidence", "updated_at"))
            if not found:
                ensure_review_candidate(ft, evidence['reason'])
                all_ready = False
                continue
            candidate = _candidate(ft, found)
        if candidate.state != "ready":
            platform = candidate.provenance.get("acquisition_platform")
            if platform not in blocked and acquisition_budget > 0 and (not candidate.retry_due_at or candidate.retry_due_at <= timezone.now()):
                acquisition_budget -= 1
                candidate = retry_candidate(candidate)
                ft.save(update_fields=('updated_at',))
                if shared_blocker(candidate.last_error):
                    blocked[platform] = candidate.last_error
            if candidate.state != "ready":
                all_ready = False
                continue
        try:
            verified_ready(candidate)
        except ValueError as exc:
            all_ready = False
            ft.evidence = {**ft.evidence, "preparation_blocker": str(exc)}
            ft.save(update_fields=("evidence", "updated_at"))
        if candidate.state == 'ready' and Publication.objects.filter(channel__target=settings.TELEGRAM_PRODUCTION_CHAT_ID,
                candidate__sha256=candidate.sha256, message_id__isnull=False).exclude(track=ft.track).exists():
            raise ValueError('Identical published bytes under another canonical recording require version/alias review')
    for platform, reason in blocked.items():
        if not FreshProviderBackoff.objects.filter(platform=platform, due_at__gt=timezone.now(), reason=redact_diagnostic(reason)[:500]).exists():
            FreshProviderBackoff.objects.update_or_create(platform=platform, defaults={"due_at": timezone.now() + timedelta(minutes=15), "reason": redact_diagnostic(reason)[:500]})
            IdentityAuditEvent.objects.create(action='fresh_provider_alert', detail={'platform':platform,
                'reason':redact_diagnostic(reason)[:500], 'action':'Refresh protected owner session or inspect provider status; no anonymous fallback. Retry after bounded 15-minute hold.'})
            logging.getLogger(__name__).warning('Fresh provider %s paused for 15 minutes; inspect admin provider-backoff evidence', platform)
    if all_ready:
        if dispatch.release.release_type == "single" or AlbumSession.objects.filter(release=dispatch.release, state='complete').exists():
            for ft in dispatch.tracks.all():
                if not ft.publication_id:
                    ft.publication = reserve_audio(verified_ready(ft.candidate), settings.TELEGRAM_PRODUCTION_CHAT_ID)
                    ft.save(update_fields=("publication", "updated_at"))
        else:
            session = prepare_album(dispatch.release, settings.TELEGRAM_PRODUCTION_CHAT_ID,
                          context={"features": list(dict.fromkeys(dispatch.evidence.get("features", [])))})
            if session.state == 'waiting_media':
                all_ready = False
    ready_after = dispatch.tracks.filter(candidate__state='ready').count()
    # Successful incremental preparation is progress, not a provider failure.
    # Do not exponentially delay remaining album tracks while files are arriving.
    dispatch.attempts = 0 if all_ready or ready_after > ready_before else dispatch.attempts + 1
    # A not-yet-available recording is not a failed provider operation. Revisit it
    # at the source cadence; candidate retry_due_at and provider backoff still
    # prevent network retries while their independent holds are active.
    delay = 15 if dispatch.attempts == 0 else min(60 * 2 ** min(dispatch.attempts, 8),
                                                 dispatch.source_item.source.poll_interval_seconds)
    dispatch.due_at = timezone.now() + timedelta(seconds=delay)
    dispatch.reason = "Publication staged" if all_ready else "Waiting for complete matched media; album introduction withheld"
    dispatch.save(update_fields=("attempts", "due_at", "reason", "updated_at"))
    if all_ready:
        from .wakeups import wake_publication
        wake_publication()


def ensure_review_candidate(ft, reason):
    """Unavailable complete audio remains visible in the existing upload panel."""
    match = SourceMatch.objects.get(track=ft.track, release=ft.dispatch.release,
        matching_method='fresh_official_track', evidence__fresh_manifest_id=ft.dispatch_id)
    MediaCandidate.objects.get_or_create(track=ft.track, release=ft.dispatch.release, source_match=match, provider='manual',
        defaults={'expected_duration_seconds':ft.metadata['duration_seconds'], 'state':'review_required',
                  'last_error':reason[:1000], 'provenance':{'fresh_manifest_id':ft.dispatch_id}})


def process_due():
    if not settings.FRESH_PIPELINE_ENABLED or not settings.SPOTIFY_MEDIA_BRIDGE_ENABLED or is_paused():
        return {"skipped": "fresh bridge disabled"}
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(728319431)")
        if not cursor.fetchone()[0]:
            return {"skipped": "dispatcher busy"}
    try:
        build_manifest()
        now = timezone.now()
        blocked = dict(FreshProviderBackoff.objects.filter(due_at__gt=now).values_list("platform", "reason"))
        rows = list(FreshDispatch.objects.filter(disposition="eligible", processing_state='pending', due_at__lte=now).select_related("source_item__source__artist", "release").order_by("due_at", "pk")[:2])
        for row in rows:
            try:
                process_dispatch(row, blocked)
            except ValueError as exc:
                row.disposition, row.reason = "review", str(exc)[:500]
                row.save(update_fields=("disposition", "reason", "updated_at"))
            except Exception as exc:
                row.attempts += 1
                row.due_at = now + timedelta(seconds=min(60 * 2 ** min(row.attempts, 8), 21600))
                row.reason = redact_diagnostic(exc)[:500]
                row.save(update_fields=("attempts", "due_at", "reason", "updated_at"))
        completed = FreshDispatch.objects.filter(disposition='eligible', processing_state='complete',
            release__release_type__in=('lp','ep'), due_at__lte=now).select_related('source_item__source__artist').order_by('due_at').first()
        if completed:
            try:
                refresh_completed_album(completed)
            except ValueError as exc:
                completed.disposition, completed.reason = 'review', str(exc)[:500]
                completed.save(update_fields=('disposition','reason','updated_at'))
            except Exception as exc:
                completed.due_at = now + timedelta(minutes=15)
                completed.reason = redact_diagnostic(exc)[:500]
                completed.save(update_fields=('due_at','reason','updated_at'))
        return {"processed": [r.pk for r in rows], "manifest": dict(Counter(FreshDispatch.objects.values_list("disposition", flat=True)))}
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(728319431)")


def publication_scope():
    releases = FreshDispatch.objects.filter(disposition="eligible", release__isnull=False).values_list("release_id", flat=True)
    ids = set(FreshTrack.objects.filter(dispatch__disposition="eligible", publication__kind__in=("single_audio", "edition")).values_list("publication_id", flat=True))
    ids.update(Publication.objects.filter(album_session__release_id__in=releases).values_list("pk", flat=True))
    ids.update(Publication.objects.filter(kind='correction', original_id__in=ids).values_list('pk', flat=True))
    return ids - {None}, set(AlbumSession.objects.filter(release_id__in=releases).values_list("pk", flat=True))


def authorize_fresh_operation(pub, operation):
    from publication.gateway import TargetBlocked
    if is_paused():
        raise TargetBlocked('Fresh publication is durably paused')
    pubs, sessions = publication_scope()
    if pub.kind == 'notification' and operation == 'notify' and pub.channel.target == str(settings.TELEGRAM_REVIEW_CHAT_ID):
        if pub.context.get('publication_id') in pubs:
            return
    if pub.channel.target != '-1004311149640':
        raise TargetBlocked('Fresh dispatch exact channel required')
    owned = pub.pk in pubs or pub.album_session_id in sessions
    prior_edit = operation == 'edit_caption' and pub.message_id and FreshTrack.objects.filter(
        publication=pub, dispatch__disposition='eligible', dispatch__release__album_sessions__pk__in=sessions).exists()
    if not owned and not prior_edit:
        raise TargetBlocked('Publication is outside durable fresh dispatch scope')
    if operation in {'send_audio', 'edit_media'}:
        if pub.kind == 'archive_audio':
            raise TargetBlocked('Fresh worker cannot send or upgrade archive items')
        verified_ready(pub.candidate)


def is_paused():
    return FreshControl.objects.filter(name='production', paused=False).exists() is False
