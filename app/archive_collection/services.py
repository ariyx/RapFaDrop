import hashlib
import json
import time
import subprocess
import tempfile
import re
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from media_pipeline.models import MediaCandidate
from media_pipeline.providers import ProviderError, YtDlpProvider, redact_diagnostic
from media_pipeline.services import retry_candidate
from publication.captions import render_caption
from publication.gateway import TargetBlocked
from publication.models import Publication, PublicationChannel
from publication.services import _audio_payload, _template, perform, require_ready
from releases.models import CanonicalRelease, SourceMatch, Track
from releases.normalization import normalize_text, edition_markers
from sources.models import ArtistSource, SourceItem

from .models import ArtistSelection, Collection, Recording, Slot
from .popular import fetch_popular

TARGET = "-1004311149640"


def assert_collection_safe(collection, *, allow_paused=False):
    if (not collection.frozen_at or (collection.paused and not allow_paused) or collection.target != TARGET or
            settings.SPOTIFY_MEDIA_BRIDGE_ENABLED or settings.PUBLICATION_WORKER_ENABLED or
            settings.TELEGRAM_LIVE_ENABLED or settings.TELEGRAM_MODE != "disabled"):
        raise TargetBlocked("Only an unpaused frozen archive may publish, with future-release switches OFF")


def authorize_publication(collection_id, pub, operation, payload, *, allow_paused_caption_edits=False):
    collection = Collection.objects.get(pk=collection_id)
    assert_collection_safe(collection, allow_paused=allow_paused_caption_edits and operation == 'edit_caption')
    recording = collection.recordings.filter(publication=pub).first()
    if (operation not in {"send_audio", "edit_caption", "edit_media"} or pub.channel.target != TARGET or recording is None or
            pub.kind != Publication.Kind.ARCHIVE or pub.track_id != recording.track_id or
            (operation != "edit_media" and pub.candidate_id != recording.candidate_id)):
        raise TargetBlocked("Publication is outside the frozen collection audio capability")
    if operation == "edit_caption":
        core = {key: value for key, value in payload.items() if key != "message_id"}
        if (not pub.message_id or payload.get("message_id", pub.message_id) != pub.message_id or
                core != {"caption_html": render_caption(pub.kind, pub.context, pub.template.config).html, "context": pub.context}):
            raise TargetBlocked("Only the current archive template for this exact stored message may be applied")
        return
    candidate = require_ready(recording.candidate if operation == "edit_media" else pub.candidate)
    core = {key: value for key, value in payload.items() if key != "message_id"}
    if core != _audio_payload(pub, candidate):
        raise TargetBlocked("Audio payload is not the recorded prepared file")
    if operation == "edit_media":
        from media_pipeline.validation import quality_improved
        retag = candidate.provenance.get('policy_retag_of') == pub.candidate_id and candidate.sha256 == pub.candidate.sha256
        genuine_upgrade = (candidate.provenance.get('genuine_quality_upgrade_of') == pub.candidate_id
            and candidate.provenance.get('conversion') == 'none requested'
            and quality_improved(candidate.quality_rank,pub.candidate.quality_rank)
            and not candidate.quality_rank.get('transcoded_from_lossy'))
        if (not pub.message_id or payload.get('message_id',pub.message_id)!=pub.message_id or
                candidate.track_id!=pub.track_id or candidate.validation_report.get('full_decode')!='passed' or
                not (retag or genuine_upgrade)):
            raise TargetBlocked('Only an identical recording retag or validated genuine quality upgrade may edit the stored message')
    if candidate.source_match.evidence.get("archive_spotify_id") != recording.spotify_id:
        raise TargetBlocked("Candidate is not bound to the frozen recording")


def approved_sources():
    manifest = json.loads((Path(settings.BASE_DIR) / "sources/data/approved_roster.json").read_text(encoding="utf-8"))
    sources = []
    for row in manifest:
        source = ArtistSource.objects.select_related("artist").get(artist__official_name=row["official_name"], platform="spotify")
        if not source.enabled or not source.artist.enabled or source.verification != "verified" or not source.baseline_completed_at:
            raise ValueError(f"Approved Spotify source {source.pk} is not active/verified/baselined")
        if source.native_profile_id != row["sources"]["spotify"]["native_profile_id"]:
            raise ValueError(f"Approved source identity drift: {source.pk}")
        sources.append(source)
    if len(sources) != 83 or len({s.artist_id for s in sources}) != 83:
        raise ValueError("Expected all 83 approved artists exactly once")
    return sources


def freeze(name, sha, *, fetch=fetch_popular, stagger_seconds=1):
    sources = approved_sources()
    collection, created = Collection.objects.get_or_create(name=name, defaults={
        "application_sha": sha, "roster": [{"artist_id": s.artist_id, "name": s.artist.official_name,
            "source_id": s.pk, "spotify_artist_id": s.native_profile_id} for s in sources]})
    if collection.frozen_at:
        return collection
    if collection.roster != [{"artist_id": s.artist_id, "name": s.artist.official_name,
            "source_id": s.pk, "spotify_artist_id": s.native_profile_id} for s in sources]:
        raise ValueError("Roster changed during freeze; refusing to replace existing selections")
    for position, source in enumerate(sources):
        selection, _ = ArtistSelection.objects.get_or_create(collection=collection, source=source,
            defaults={"roster_position": position})
        if selection.observed_at:
            continue
        try:
            evidence = fetch(source)
            commit_selection(selection, evidence)
        except Exception as exc:
            selection.error = redact_diagnostic(exc)
            selection.evidence = getattr(exc, "probe", {})
            selection.observed_at = timezone.now()
            selection.save(update_fields=("error", "evidence", "observed_at"))
        print(json.dumps({"artist": source.artist.official_name, "slots": selection.slots.count(), "error": selection.error}), flush=True)
        time.sleep(stagger_seconds)
    collection.frozen_at = timezone.now()
    collection.save(update_fields=("frozen_at",))
    return collection


@transaction.atomic
def commit_selection(selection, evidence):
    collection = Collection.objects.select_for_update().get(pk=selection.collection_id)
    selection = ArtistSelection.objects.select_for_update().get(pk=selection.pk)
    if collection.frozen_at or selection.observed_at:
        return selection
    if evidence["artist_id"] != selection.source.native_profile_id or len(evidence["selected"]) > 2:
        raise ValueError("Popular identity/two-slot constraint failed")
    for number, row in enumerate(evidence["selected"], 1):
        recording, _ = Recording.objects.get_or_create(collection=collection, spotify_id=row["id"], defaults={
            "metadata": row, "order": selection.roster_position * 100 + row["rank"]})
        if (recording.metadata["title"] != row["title"] or recording.metadata["credits"] != row["credits"] or
                abs(recording.metadata["duration_seconds"] - row["duration_seconds"]) > 1):
            raise ValueError("Shared stable ID has conflicting version/credit metadata")
        Slot.objects.get_or_create(selection=selection, number=number,
            defaults={"popular_rank": row["rank"], "recording": recording})
    selection.evidence = evidence
    selection.observed_at = timezone.now()
    selection.error = "" if len(evidence["selected"]) == 2 else "Fewer than two eligible full-music entries in complete returned Popular section"
    selection.save()
    return selection


def _credit_block(value, names):
    remaining = normalize_text(value)
    matched = False
    for name in sorted(names, key=len, reverse=True):
        remaining, count = re.subn(r"(?<!\w)" + re.escape(name) + r"(?!\w)", " ", remaining)
        matched |= bool(count)
    remaining = re.sub(r"\b(?:feat|and|x)\b", " ", remaining)
    return matched and not remaining.strip()


def _recording_title(value, names):
    normalized = normalize_text(value)
    if " feat " in normalized:
        core, credits = normalized.split(" feat ", 1)
        if _credit_block(credits, names):
            return core.strip()
    return normalized


def identity_matches(row, metadata, profiles):
    """Strict profile + recording/version + duration; fuzzy search never grants identity."""
    profile = str(row.get("uploader_url") or "").rstrip("/").lower()
    source = next((s for s in profiles if s.canonical_url.rstrip("/").lower() == profile), None)
    if source is None:
        return None, "Uploader profile is not a verified credited artist source"
    names = [normalize_text(c["name"]) for c in metadata["credits"]]
    title = _recording_title(row.get("title"), names)
    expected = _recording_title(metadata["title"], names)
    # Explicit display credits may surround the title, but every credited name
    # must exist in the frozen Spotify track credits. Version labels are retained.
    if title != expected and " - " in str(row.get("title", "")):
        left, right = str(row["title"]).split(" - ", 1)
        if _credit_block(left, names):
            title = _recording_title(right, names)
        elif _credit_block(right, names):
            title = _recording_title(left, names)
    if title != expected or edition_markers(row.get("title")) != edition_markers(metadata["title"]):
        return None, "Recording title/version does not match exactly"
    try:
        if abs(float(row.get("duration")) - metadata["duration_seconds"]) > 5:
            return None, "Provider duration differs by more than five seconds"
    except (TypeError, ValueError):
        return None, "Provider has no complete duration evidence"
    return source, "Verified credited profile, exact recording/version and duration"


def discover_candidate(recording, provider=None, *, blocked_providers=None):
    from .models import AcquisitionSource
    if provider is None and AcquisitionSource.objects.exists():
        from .acquisition import find
        return find(recording,blocked_providers=blocked_providers)
    provider = provider or YtDlpProvider()
    m = recording.metadata
    credited_ids = [c["id"] for c in m["credits"]]
    profiles = list(ArtistSource.objects.filter(platform="soundcloud", verification="verified",
        artist__sources__platform="spotify", artist__sources__native_profile_id__in=credited_ids).select_related("artist").distinct())
    if not profiles:
        return None, {"reason": "No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only.", "searches": 0}
    for item in SourceItem.objects.filter(platform="soundcloud", source__in=profiles).select_related("source"):
        row = {"id": item.native_item_id, "title": item.title, "duration": item.metadata.get("duration"),
               "uploader_url": item.source.canonical_url, "uploader": item.metadata.get("uploader")}
        source, reason = identity_matches(row, m, profiles)
        if source and provider.can_handle(item.canonical_url):
            return (source, row, item.canonical_url), {"searches": 0, "existing_official_source_item_id": item.pk, "reason": reason}
    query = " ".join([m["credits"][0]["name"], m["title"]])
    output = provider._run(["--socket-timeout", "10", "--skip-download", "--dump-single-json", "--playlist-end", "5", "--", f"scsearch5:{query}"], 45)
    body = json.loads(output)
    entries = body.get("entries")
    if not isinstance(entries, list) or len(entries) > 5:
        raise ProviderError("SoundCloud bounded search response is malformed")
    checks = []
    for row in entries:
        if not isinstance(row, dict):
            continue
        source, reason = identity_matches(row, m, profiles)
        url = row.get("webpage_url") or ""
        checks.append({"id": str(row.get("id") or ""), "title": row.get("title"),
            "uploader_url": row.get("uploader_url"), "duration": row.get("duration"), "reason": reason})
        if source and provider.can_handle(url):
            return (source, row, url), {"searches": 1, "query": query, "checks": checks}
    return None, {"searches": 1, "checks": checks, "reason": "No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required."}


@transaction.atomic
def bind_candidate(recording, found):
    recording = Recording.objects.select_for_update().get(pk=recording.pk)
    if recording.candidate_id and recording.candidate.provider != "manual":
        return recording.candidate
    source, row, url = found
    from .models import AcquisitionSource
    if isinstance(source, AcquisitionSource) and source.platform == 'youtube':
        return bind_youtube_candidate(recording, source, row, url)
    acquisition_source = source if isinstance(source, AcquisitionSource) else None
    if acquisition_source:
        source, _ = ArtistSource.objects.get_or_create(artist=source.artist, platform='soundcloud', defaults={
            'canonical_url':source.profile_url,'native_profile_id':source.native_id,'enabled':False,'verification':'unverified'})
    m = recording.metadata
    digest = hashlib.sha256(f"spotify:track:{recording.spotify_id}".encode()).hexdigest()
    track, _ = Track.objects.get_or_create(identity_key=digest,
        defaults={"official_title": m["title"], "duration_seconds": round(m["duration_seconds"])})
    release, _ = CanonicalRelease.objects.get_or_create(identity_key=hashlib.sha256(f"archive:album:{m['album_id']}".encode()).hexdigest(),
        defaults={"title": m["album_title"], "release_type": {"album": "lp", "ep": "ep"}.get(m.get("album_type"), "single"), "release_date": m.get("release_date"), "state": "identified"})
    item, _ = SourceItem.objects.get_or_create(platform="soundcloud", native_item_id=str(row["id"]), defaults={
        "source": source, "title": row["title"], "canonical_url": url, "first_observed_at": timezone.now(),
        "metadata": {"archive_collection": recording.collection.name, "duration": m["duration_seconds"], "uploader": row.get("uploader")},
        "sanitized_raw_data": {"archive_acquisition_fact": True}})
    match, created = SourceMatch.objects.get_or_create(source_item=item, defaults={"track": track, "release": release,
        "confidence": 95, "state": "matched", "matching_method": "archive_spotify_soundcloud",
        "evidence": {"archive_spotify_id": recording.spotify_id, "archive_official_metadata": {
            "title": m["title"], "artists": [c["name"] for c in m["credits"]], "album": m["album_title"],
            "album_artists": m.get("album_artists"), "artwork_url": m.get("artwork_url"), "track_number": m.get("track_number"),
            "disc_number": m.get("disc_number"), "release_date": m.get("release_date")}, "match": recording.evidence}})
    if not created and (match.track_id != track.pk or match.matching_method != "archive_spotify_soundcloud" or
            match.evidence.get("archive_spotify_id") != recording.spotify_id):
        raise ValueError("Existing source identity/review cannot be overwritten; recording requires reconciliation")
    candidate, _ = MediaCandidate.objects.get_or_create(track=track, release=release, source_match=match, provider="yt-dlp", defaults={
        "expected_duration_seconds": m["duration_seconds"], "provenance": {"provider": "yt-dlp", "source_url": url,
            "native_item_id": str(row["id"]), "spotify_track_id": recording.spotify_id, "provenance_confidence": 95,
            "official_profile": source.canonical_url, "conversion": "none requested", "archive_collection": recording.collection.name}})
    if acquisition_source and not candidate.provenance.get('acquisition_source_id'):
        candidate.provenance={**candidate.provenance,'acquisition_source_id':acquisition_source.pk,'acquisition_platform':'soundcloud'}
        candidate.save(update_fields=('provenance',))
    recording.candidate, recording.track = candidate, track
    recording.save(update_fields=("candidate", "track", "updated_at"))
    return candidate


def acquire(recording, *, fallback_budget=1, blocked_providers=None):
    started = time.monotonic()
    recording.attempts += 1
    recording.state = "acquiring"
    recording.save(update_fields=("attempts", "state", "updated_at"))
    try:
        if not recording.candidate_id or (recording.candidate.provider == "manual" and recording.candidate.state != "ready"):
            found, evidence = discover_candidate(recording,blocked_providers=blocked_providers)
            recording.evidence = {**recording.evidence, "matching": evidence}
            recording.save(update_fields=("evidence", "updated_at"))
            if not found:
                ensure_manual_candidate(recording)
                recording.refresh_from_db()
                raise ProviderError(evidence["reason"])
            bind_candidate(recording, found)
            recording.refresh_from_db()
        candidate = retry_candidate(recording.candidate)
        if candidate.state == "ready":
            # Decode the entire file, bounded independently from downloader timeout.
            decoded = subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", candidate.prepared_path,
                "-map", "0:a:0", "-f", "null", "-"], capture_output=True, timeout=90)
            if decoded.returncode:
                candidate.state = "review_required"
                candidate.last_error = "Full-file decode failed; manual recording review required"
                candidate.validation_report = {**candidate.validation_report, "complete": False, "decode": "failed"}
            else:
                candidate.validation_report = {**candidate.validation_report, "full_decode": "passed"}
            advertised = candidate.provenance.get("provider_duration_seconds")
            if advertised and abs(candidate.observed_facts["duration_seconds"] - advertised) > 2:
                candidate.state = "review_required"
                candidate.last_error = "Decoded file differs from complete provider recording duration by more than two seconds"
                candidate.validation_report = {**candidate.validation_report, "complete": False}
            if (not 0 < Path(candidate.prepared_path).stat().st_size <= 50_000_000 or
                    candidate.observed_facts.get("codec_name") not in {"mp3", "aac"}):
                candidate.state = "review_required"
                candidate.last_error = "Complete file is outside Telegram MP3/AAC compressed delivery bounds"
            candidate.save()
        recording.state = "ready" if candidate.state == "ready" else "review" if candidate.state in {"invalid", "review_required"} else "pending"
        recording.reason = candidate.last_error
        recording.retry_due_at = candidate.retry_due_at
        recording.evidence = {**recording.evidence, "media_total_seconds": round(time.monotonic() - started, 3)}
    except Exception as exc:
        if not recording.candidate_id:
            try:
                ensure_manual_candidate(recording)
                recording.refresh_from_db()
            except Exception as manual_error:
                recording.reason = redact_diagnostic(manual_error)
        recording.state = "pending"
        recording.reason = redact_diagnostic(exc)
        recording.retry_due_at = timezone.now() + timedelta(seconds=min(300 * 2 ** min(recording.attempts - 1, 6), 21600))
    recording.evidence = {**recording.evidence, "last_acquisition_attempt_seconds": round(time.monotonic() - started, 3)}
    recording.save()
    # A failed provider candidate is retained as evidence; try one independently
    # verified source rather than permanently pinning every retry to that file.
    if fallback_budget and recording.state in {'pending','review'} and recording.candidate_id and recording.candidate.provider!='manual':
        failed=recording.candidate
        failed_urls=list(dict.fromkeys([*recording.evidence.get('failed_source_urls',[]),failed.provenance.get('source_url','')]))
        recording.evidence={**recording.evidence,'failed_source_urls':failed_urls,'provider_failures':[*recording.evidence.get('provider_failures',[]),{'candidate_id':failed.pk,'provider':failed.provider,'source_url':failed.provenance.get('source_url'),'reason':recording.reason,'at':timezone.now().isoformat()}]}
        recording.candidate=None
        recording.save(update_fields=('candidate','evidence','updated_at'))
        return acquire(recording,fallback_budget=fallback_budget-1,blocked_providers=blocked_providers)
    return recording


def bind_youtube_candidate(recording,source,row,url):
    ensure_manual_candidate(recording)
    recording.refresh_from_db()
    base=recording.candidate
    # Frozen Spotify SourceMatch remains authoritative; provider identity is
    # corroborated separately, so no YouTube feed is attached to discovery.
    candidate,_=MediaCandidate.objects.get_or_create(track=recording.track,release=base.release,
        source_match=base.source_match,provider='yt-dlp-youtube',provenance__source_url=url,defaults={
            'expected_duration_seconds':recording.metadata['duration_seconds'],'provenance':{
                'provider':'yt-dlp-youtube','source_url':url,'native_item_id':str(row['id']),
                'source_recording_title':row['title'],'official_channel_id':source.native_id,
                'acquisition_platform':'youtube','acquisition_source_id':source.pk,
                'official_profile':source.profile_url,'spotify_track_id':recording.spotify_id,
                'archive_collection':recording.collection.name,'conversion':'none requested','provenance_confidence':95}})
    recording.candidate=candidate;recording.save(update_fields=('candidate','updated_at'))
    return candidate


@transaction.atomic
def ensure_manual_candidate(recording):
    """Expose unavailable recordings to the existing authenticated manual-upload panel."""
    recording = Recording.objects.select_for_update().get(pk=recording.pk)
    if recording.candidate_id:
        return recording.candidate
    m = recording.metadata
    selection = recording.slots.select_related("selection__source").order_by("selection__roster_position").first().selection
    digest = hashlib.sha256(f"spotify:track:{recording.spotify_id}".encode()).hexdigest()
    track, _ = Track.objects.get_or_create(identity_key=digest,
        defaults={"official_title": m["title"], "duration_seconds": round(m["duration_seconds"])})
    release, _ = CanonicalRelease.objects.get_or_create(identity_key=hashlib.sha256(f"archive:album:{m['album_id']}".encode()).hexdigest(),
        defaults={"title": m["album_title"], "release_type": {"album": "lp", "ep": "ep"}.get(m.get("album_type"), "single"), "release_date": m.get("release_date"), "state": "identified"})
    item, _ = SourceItem.objects.get_or_create(platform="spotify", native_item_id=recording.spotify_id, defaults={
        "source": selection.source, "title": m["title"], "canonical_url": m["spotify_url"],
        "first_observed_at": timezone.now(), "metadata": {"archive_collection": recording.collection.name,
        "archive_only": True, "duration": m["duration_seconds"]}, "sanitized_raw_data": {"archive_only": True}})
    match, created = SourceMatch.objects.get_or_create(source_item=item, defaults={"track": track, "release": release,
        "confidence": 100, "state": "matched", "matching_method": "archive_frozen_spotify",
        "evidence": {"archive_spotify_id": recording.spotify_id, "archive_official_metadata": {
            "title": m["title"], "artists": [c["name"] for c in m["credits"]], "album": m["album_title"],
            "album_artists": m.get("album_artists"), "artwork_url": m.get("artwork_url"), "track_number": m.get("track_number"),
            "disc_number": m.get("disc_number"), "release_date": m.get("release_date")}}})
    if not created and (match.track_id != track.pk or match.matching_method != "archive_frozen_spotify"):
        raise ValueError("Existing Spotify identity/review requires reconciliation; not overwritten")
    candidate = MediaCandidate.objects.create(track=track, release=release, source_match=match, provider="manual",
        expected_duration_seconds=m["duration_seconds"], state="review_required",
        last_error="Complete officially matched manual audio/artwork required; Spotify is metadata only.",
        provenance={"spotify_track_id": recording.spotify_id, "archive_collection": recording.collection.name})
    recording.candidate, recording.track = candidate, track
    recording.save(update_fields=("candidate", "track", "updated_at"))
    return candidate


@transaction.atomic
def reserve(recording):
    collection = Collection.objects.select_for_update().get(pk=recording.collection_id)
    assert_collection_safe(collection)
    recording = Recording.objects.select_for_update().get(pk=recording.pk)
    if recording.publication_id:
        return recording.publication
    candidate = require_ready(recording.candidate)
    if candidate.validation_report.get("full_decode") != "passed":
        raise ValueError("Collection audio requires a recorded full-file decode before reservation")
    if recording.metadata.get('artwork_url') and candidate.preparation_report.get('readback',{}).get('artwork_read_back') is not True:
        recording.state='review';recording.reason='Frozen official artwork was not embedded/read back; complete audio retained for preparation review.'
        recording.save(update_fields=('state','reason','updated_at'))
        return None
    channel, _ = PublicationChannel.objects.get_or_create(target=TARGET)
    channel = PublicationChannel.objects.select_for_update().get(pk=channel.pk)
    existing = Publication.objects.filter(channel=channel, track=recording.track).first()
    if existing is None and candidate.sha256:
        identical = Publication.objects.filter(channel=channel, candidate__sha256=candidate.sha256, message_id__isnull=False).first()
        if identical:
            recording.state = "review"
            recording.reason = "Identical audio bytes under different stable recording IDs; version/reissue identity must be reconciled before merging or sending"
            recording.save()
            return None
    if existing:
        recording.publication = existing
        recording.state = "reused" if existing.message_id else existing.state
        recording.save()
        return existing
    m = recording.metadata
    context = {"title": m["title"], "artists": [c["name"] for c in m["credits"]],
        "spotify_url": m["spotify_url"], "soundcloud_url": candidate.provenance.get("source_url", "") if candidate.provenance.get("acquisition_platform", "soundcloud") == "soundcloud" else "", "channel_target": TARGET}
    template = _template(Publication.Kind.ARCHIVE)
    pub = Publication.objects.create(channel=channel, track=recording.track, release=candidate.release,
        candidate=candidate, kind=Publication.Kind.ARCHIVE, identity_key=f"audio:{recording.track.canonical_id}",
        template=template, context=context, caption_html=render_caption(Publication.Kind.ARCHIVE, context, template.config).html)
    recording.publication = pub
    recording.save(update_fields=("publication", "updated_at"))
    return pub


def run(collection, gateway, *, limit=166):
    assert_collection_safe(collection)
    processed = 0
    blocked_providers={}
    # Dedicated CLI only; no Celery task or beat entry can dispatch this path.
    for recording in collection.recordings.order_by("order", "pk"):
        collection.refresh_from_db()
        if collection.paused or processed >= limit:
            break
        if recording.publication_id and recording.publication.message_id:
            continue
        if not recording.publication_id:
            prior = Publication.objects.filter(channel__target=TARGET, state="published", message_id__isnull=False,
                track__source_matches__source_item__platform="spotify",
                track__source_matches__source_item__native_item_id=recording.spotify_id,
                track__source_matches__confidence__gte=90, track__source_matches__state__in=("matched", "approved", "corrected")).first()
            if prior:
                recording.publication, recording.track, recording.candidate = prior, prior.track, prior.candidate
                recording.state = "reused"
                recording.evidence = {**recording.evidence, "reuse": "Exact Spotify stable recording ID and existing production publication"}
                recording.save()
                continue
        ready = recording.candidate_id and recording.candidate.state == "ready"
        if (recording.state == "review" and not ready) or (recording.retry_due_at and recording.retry_due_at > timezone.now() and not ready):
            continue
        if recording.publication_id and recording.publication.state == "uncertain":
            continue
        processed += 1
        if not recording.candidate_id or recording.candidate.state != "ready":
            acquire(recording,blocked_providers=blocked_providers)
            recording.refresh_from_db()
        if recording.candidate_id and recording.candidate.state == "ready":
            if recording.candidate.validation_report.get("full_decode") != "passed":
                acquire(recording,blocked_providers=blocked_providers)
                recording.refresh_from_db()
                if recording.candidate.state != "ready":
                    continue
            pub = reserve(recording)
            if pub is None:
                continue
            # Reservation persists the Publication FK on a separately locked instance.
            # Reload before saving timings/state, otherwise the stale instance clears it.
            recording.refresh_from_db()
            if not pub.message_id:
                started = time.monotonic()
                pub = perform(pub, "send_audio", "initial", _audio_payload(pub), gateway=gateway, candidate=pub.candidate)
                recording.evidence = {**recording.evidence, "upload_seconds": round(time.monotonic() - started, 3)}
                recording.state, recording.reason, recording.retry_due_at = pub.state, pub.last_error, pub.retry_due_at
                recording.save()
                if pub.state in {"uncertain", "retry_wait", "sending"}:
                    # Stop channel sends on uncertain/RetryAfter, preserving ordering.
                    break
                if pub.message_id:
                    try:
                        readback = gateway.readback(recording)
                    except Exception:
                        readback = {"status": "blocked", "reason": "Readback request failed; confirmed publication retained"}
                    recording.evidence = {**recording.evidence, "telegram_readback": readback,
                        "end_to_end_processing_seconds": sum(recording.evidence.get(k, 0) for k in ("media_total_seconds", "upload_seconds"))}
                    recording.save(update_fields=("evidence", "updated_at"))
                time.sleep(1)
        print(json.dumps({"spotify_id": recording.spotify_id, "state": recording.state,
            "reason": recording.reason, "message_id": recording.publication.message_id if recording.publication_id else None}), flush=True)
        time.sleep(1)
    return status(collection)


def status(collection):
    from .models import RecordingAlias
    alias_count=RecordingAlias.objects.filter(recording__collection=collection).count()
    return {"name": collection.name, "paused": collection.paused, "frozen_at": str(collection.frozen_at),
        "artists": collection.selections.count(), "selected_slots": Slot.objects.filter(selection__collection=collection).count(),
        "unique_recordings": collection.recordings.count(), "published": collection.recordings.filter(publication__message_id__isnull=False).count(),
        "reused_posts": collection.recordings.filter(state="reused").count(),
        "new_posts": collection.recordings.filter(state="published").count(),
        "unresolved_artists": collection.selections.exclude(error="").count(),
        "frozen_recording_rows":collection.recordings.count(), "canonical_recordings":collection.recordings.count()-alias_count,
        "confirmed_unique_messages":collection.recordings.filter(publication__message_id__isnull=False).values('publication_id').distinct().count(),
        "states": {s: collection.recordings.filter(state=s).count() for s in collection.recordings.values_list("state", flat=True).distinct()},
        "verification": collection.verification}


@transaction.atomic
def reconcile_recording_alias(recording,canonical,evidence):
    """Keep frozen rows/source facts, satisfy alternate slots with a corroborated post."""
    from .models import RecordingAlias
    from .acquisition import title_matches
    r=Recording.objects.select_for_update().get(pk=recording.pk)
    c=Recording.objects.select_for_update(of=('self',)).select_related('publication__channel','candidate__source_match__source_item').get(pk=canonical.pk)
    existing=RecordingAlias.objects.filter(recording=r).first()
    if existing:
        if existing.canonical_id!=c.pk or r.publication_id!=c.publication_id:
            raise ValueError('Existing alias binding differs; manual reconciliation required')
        return existing
    m,n=r.metadata,c.metadata
    credited=lambda data:{normalize_text(x['name']) for x in data['credits']}
    if (r.collection_id!=c.collection_id or not r.collection.paused or r.pk==c.pk or r.publication_id or
            not c.publication_id or c.publication.state!='published' or not c.publication.message_id or c.publication.channel.target!=TARGET or
            not title_matches(m['title'],n) or credited(m)!=credited(n) or abs(m['duration_seconds']-n['duration_seconds'])>2 or
            not evidence.get('checked_at') or not evidence.get('independent_links') or
            str(evidence.get('shared_native_item_id'))!=c.candidate.source_match.source_item.native_item_id or
            evidence.get('shared_recording_url')!=c.candidate.provenance.get('source_url') or
            evidence.get('both_recordings_match_official_source') is not True):
        raise ValueError('Alias requires corroborated identical official recording, complete credits/duration and confirmed same-channel post')
    alias,created=RecordingAlias.objects.get_or_create(recording=r,defaults={'canonical':c,'evidence':evidence})
    if not created and alias.canonical_id!=c.pk:raise ValueError('Alias identity cannot be replaced')
    r.publication,r.candidate,r.track=c.publication,c.candidate,c.track
    r.state='reused';r.reason='Alternate Spotify native identity reconciled to the same official recording; existing post reused.';r.retry_due_at=None
    r.evidence={**r.evidence,'alias_reconciliation':evidence,'canonical_spotify_id':c.spotify_id}
    r.save(update_fields=('publication','candidate','track','state','reason','retry_due_at','evidence','updated_at'))
    return alias


def cleanup_confirmed(collection):
    removed, retained = [], []
    root = Path(settings.MEDIA_ROOT).resolve()
    for r in collection.recordings.filter(publication__message_id__isnull=False).select_related("candidate"):
        if not r.candidate_id or r.evidence.get("telegram_readback", {}).get("status") != "passed":
            retained.append(r.spotify_id)
            continue
        for field in ("candidate_path", "prepared_path", "artwork_path"):
            value = getattr(r.candidate, field)
            if not value:
                continue
            path = Path(value).resolve()
            if not path.is_relative_to(root) or Path(value).is_symlink():
                raise ValueError("Cleanup path escaped media storage")
            if MediaCandidate.objects.exclude(pk=r.candidate_id).filter(**{field: value}).exists():
                retained.append(value)
                continue
            if path.is_file():
                path.unlink()
                removed.append(value)
        r.evidence = {**r.evidence, "confirmed_media_cleanup_at": timezone.now().isoformat()}
        r.save(update_fields=("evidence", "updated_at"))
    return {"removed_files": len(removed), "retained": retained, "production_messages_deleted": 0}


@transaction.atomic
def link_confirmed_publications(collection):
    """Recover archive links using exact candidate/track identities, never a network resend."""
    collection = Collection.objects.select_for_update().get(pk=collection.pk)
    if not collection.frozen_at or not collection.paused:
        raise ValueError("Link repair requires a frozen paused collection")
    repaired = []
    for r in collection.recordings.filter(publication__isnull=True, candidate__isnull=False).select_related("candidate__source_match"):
        if r.candidate.source_match.evidence.get("archive_spotify_id") != r.spotify_id:
            continue
        pub = Publication.objects.filter(channel__target=TARGET, track=r.track,
            candidate=r.candidate, kind="archive_audio", state="published", message_id__isnull=False).first()
        if pub:
            r.publication = pub
            r.state = "published"
            r.evidence = {**r.evidence, "publication_link_recovered_at": timezone.now().isoformat()}
            r.save()
            repaired.append({"spotify_id": r.spotify_id, "message_id": pub.message_id})
    return repaired


def refresh_published(collection, gateway):
    from publication.services import edit_caption
    assert_collection_safe(collection, allow_paused=getattr(gateway, 'allow_paused_caption_edits', False))
    results = []
    for r in collection.recordings.filter(publication__message_id__isnull=False).select_related("publication__template", "publication__channel"):
        pub = r.publication
        if pub.kind != Publication.Kind.ARCHIVE or pub.channel.target != collection.target or pub.track_id != r.track_id or pub.candidate_id != r.candidate_id:
            raise TargetBlocked("Confirmed publication binding differs from frozen recording")
        from operations.management.commands.refresh_owner_defaults import known_audio_default
        if not known_audio_default(pub.template.config):
            results.append({'message_id': pub.message_id, 'state': 'custom_template_conflict'})
            continue
        current = _template(pub.kind)
        if current.pk != pub.template_id:
            pub.template = current
            pub.save(update_fields=('template', 'updated_at'))
        started = time.monotonic()
        desired = render_caption(pub.kind, pub.context, pub.template.config).html
        if pub.caption_html != desired:
            pub = edit_caption(pub, {}, gateway=gateway)
        if pub.state != "published":
            results.append({"message_id": pub.message_id, "state": pub.state})
            break
        r.evidence = {**r.evidence, "caption_refresh": {"message_id": pub.message_id, "state": pub.state, "caption_html": pub.caption_html, "seconds": round(time.monotonic()-started, 3), "at": timezone.now().isoformat()}}
        r.save(update_fields=("evidence", "updated_at"))
        results.append({"message_id": pub.message_id, "state": pub.state, "readback": r.evidence.get("telegram_readback")})
    return results


def retag_published(collection, gateway):
    """Prepare immutable copies from retained originals; edit the existing messages only."""
    from media_pipeline.models import MediaAttempt
    from media_pipeline.services import _accept_audio_file, _safe_media_path
    from operations.services import active_media_tag_fields
    from media_pipeline.tagging import CHANNEL_POLICY_VERSION
    from publication.services import upgrade_single
    assert_collection_safe(collection)
    fields = set(active_media_tag_fields(settings.MEDIA_CHANNEL_TAG_FIELDS))
    results = []
    for r in collection.recordings.filter(publication__message_id__isnull=False).order_by("order"):
        pub = r.publication
        old = pub.candidate
        if old.preparation_report.get("channel_policy_version") == CHANNEL_POLICY_VERSION and fields <= set(old.preparation_report.get("mapped_fields", [])) and (not r.metadata.get("artwork_url") or old.preparation_report.get("readback", {}).get("artwork_read_back") is True):
            continue
        # A restart reuses its persisted prepared replacement; never creates another send.
        new = r.candidate if r.candidate_id != old.pk else None
        if new is None:
            raw = _safe_media_path(old.candidate_path)
            artwork = _safe_media_path(old.artwork_path) if old.artwork_path else None
            new = MediaCandidate.objects.create(track=old.track, release=old.release,
                source_match=old.source_match, provider="manual", expected_duration_seconds=old.expected_duration_seconds,
                provenance={**old.provenance, "policy_retag_of": old.pk, "retagged_at_utc": timezone.now().isoformat()})
            attempt = MediaAttempt.objects.create(candidate=new, provider="policy-retag", started_at=timezone.now())
            with tempfile.TemporaryDirectory(prefix="archive-artwork-", dir=settings.MEDIA_ROOT) as directory:
                if artwork is None and r.metadata.get("artwork_url"):
                    from media_pipeline.artwork import fetch_recorded_spotify_artwork
                    from media_pipeline.tagging import validate_artwork
                    artwork = fetch_recorded_spotify_artwork(r.metadata["artwork_url"], Path(directory) / "cover")
                    validate_artwork(artwork)
                    new.provenance = {**new.provenance, "official_artwork_source_url": r.metadata["artwork_url"]}
                    new.save(update_fields=("provenance",))
                new = _accept_audio_file(new, attempt, raw, expected=old.expected_duration_seconds,
                    artwork_path=artwork, share_prepared=False)
            require_ready(new)
            decoded = subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", new.prepared_path,
                "-map", "0:a:0", "-f", "null", "-"], capture_output=True, timeout=90)
            if decoded.returncode or new.sha256 != old.sha256:
                raise ValueError("Retagging failed complete decoding or original recording byte identity")
            new.validation_report = {**new.validation_report, "full_decode": "passed"}
            new.save(update_fields=("validation_report",))
            r.candidate = new
            r.save(update_fields=("candidate", "updated_at"))
        pub = upgrade_single(pub, new, gateway=gateway, correction_notice=False)
        if pub.state != "published" or pub.candidate_id != new.pk:
            results.append({"message_id": pub.message_id, "state": pub.state})
            break
        r.refresh_from_db()
        r.evidence = {**r.evidence, "telegram_readback": gateway.readback(r),
            "policy_retag": {"previous_candidate_id": old.pk, "candidate_id": new.pk,
                "message_id": pub.message_id, "fields": sorted(fields), "readback": new.preparation_report["readback"]}}
        r.save(update_fields=("evidence", "updated_at"))
        results.append({"message_id": pub.message_id, "state": pub.state, "readback": r.evidence["telegram_readback"]})
    return results


def upgrade_ready_published(collection,gateway):
    """No acquisition or tag changes: use a separately validated better recording if present."""
    from media_pipeline.validation import quality_improved
    from publication.services import upgrade_single
    assert_collection_safe(collection)
    results=[]
    for r in collection.recordings.filter(state='published',publication__message_id__isnull=False):
        old=r.publication.candidate
        candidates=MediaCandidate.objects.filter(track=r.track,state='ready').exclude(pk=old.pk)
        better=next((c for c in candidates if c.source_match.evidence.get('archive_spotify_id')==r.spotify_id
            and quality_improved(c.quality_rank,old.quality_rank) and not c.quality_rank.get('transcoded_from_lossy')
            and c.validation_report.get('full_decode')=='passed' and c.provenance.get('conversion')=='none requested'
            and c.preparation_report.get('readback',{}).get('channel_fields_read_back') is True
            and (not r.metadata.get('artwork_url') or c.preparation_report.get('readback',{}).get('artwork_read_back') is True)),None)
        if better is None:continue
        better.provenance={**better.provenance,'genuine_quality_upgrade_of':old.pk};better.save(update_fields=('provenance',))
        r.candidate=better;r.save(update_fields=('candidate','updated_at'))
        pub=upgrade_single(r.publication,better,gateway=gateway,correction_notice=False)
        if pub.state!='published':break
        r.evidence={**r.evidence,'telegram_readback':gateway.readback(r),'genuine_quality_upgrade':{'previous_candidate_id':old.pk,'candidate_id':better.pk,'message_id':pub.message_id}}
        r.save(update_fields=('evidence','updated_at'));results.append({'message_id':pub.message_id,'candidate_id':better.pk})
    return results
