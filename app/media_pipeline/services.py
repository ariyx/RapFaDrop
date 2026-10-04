import shutil
import time
import uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from releases.models import ProcessingQueueItem, SourceMatch

from .artwork import fetch_recorded_soundcloud_artwork, fetch_recorded_spotify_artwork
from .models import MediaAttempt, MediaAuditEvent, MediaCandidate
from .providers import PROVIDERS, ProviderError, redact_diagnostic
from .tagging import TaggingError, prepare_tagged_copy, validate_artwork
from .validation import MediaValidationError, compare_duration, probe_audio, quality_rank, quality_key, delivery_eligible


class MediaRequestError(ValueError):
    pass


def media_root():
    root = Path(settings.MEDIA_ROOT).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    return root


def _candidate_dir(candidate):
    root = media_root()
    directory = (root / f"track-{candidate.track_id}" / f"candidate-{candidate.pk}").resolve()
    if not directory.is_relative_to(root):
        raise MediaRequestError("Media path escaped the configured media root")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    return directory


def _staging_dir(candidate, prefix="attempt"):
    root = media_root()
    directory = (root / ".staging" / f"candidate-{candidate.pk}-{prefix}-{uuid.uuid4().hex}").resolve()
    if not directory.is_relative_to(root):
        raise MediaRequestError("Staging path escaped the configured media root")
    directory.mkdir(parents=True, mode=0o700)
    return directory


def _safe_media_path(path):
    if not path:
        return None
    root = media_root()
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(root):
        raise MediaRequestError("Stored candidate path is outside configured media storage")
    return resolved


def best_ready_candidate(track):
    candidates = [item for item in MediaCandidate.objects.filter(track=track, state=MediaCandidate.State.READY) if delivery_eligible(item.observed_facts)]
    if not candidates:
        return None
    return max(candidates, key=lambda item: quality_key(item.quality_rank))


def request_candidate(queue_item, provider_name=None, *, provider_instance=None):
    """Create/find the candidate for an eligible M2 queue item; network work is opt-in via acquire_candidate()."""
    provider_name = _provider_name(provider_name, provider_instance)
    provider = provider_instance or PROVIDERS.get(provider_name)
    if provider is None:
        raise MediaRequestError("Unknown media provider")
    with transaction.atomic():
        queue = ProcessingQueueItem.objects.select_for_update().get(pk=queue_item.pk)
        if queue.track_id is None or queue.state not in {ProcessingQueueItem.State.PENDING, ProcessingQueueItem.State.RETRY_WAIT}:
            raise MediaRequestError("Media is available only for an identified pending queue track")
        matches = list(SourceMatch.objects.filter(
            track_id=queue.track_id,
            release_id=queue.release_id,
            confidence__gte=90,
            state__in=(SourceMatch.State.MATCHED, SourceMatch.State.APPROVED, SourceMatch.State.CORRECTED),
        ).select_related("source_item").order_by("created_at", "pk"))
        match = next((row for row in matches if provider.can_handle(row.source_item.canonical_url)),
                     matches[0] if matches else None)
        if match is None:
            raise MediaRequestError("Queue item has no confidently identified source match")
        source_item = match.source_item
        if not provider.can_handle(source_item.canonical_url):
            candidate, _ = MediaCandidate.objects.get_or_create(
                track=queue.track, release=queue.release, source_match=match, provider=provider_name,
                defaults={
                    "expected_duration_seconds": _source_duration(source_item),
                    "state": MediaCandidate.State.REVIEW_REQUIRED,
                    "last_outcome": "unsupported_source",
                    "last_error": "No M3 full-audio provider is configured for this source.",
                    "provenance": _provenance(source_item, match, provider_name),
                },
            )
            return candidate
        try:
            candidate, created = MediaCandidate.objects.get_or_create(
                track=queue.track, release=queue.release, source_match=match, provider=provider_name,
                defaults={
                    "expected_duration_seconds": _source_duration(source_item),
                    "provenance": _provenance(source_item, match, provider_name),
                },
            )
        except IntegrityError:
            candidate = MediaCandidate.objects.get(track=queue.track, source_match=match, provider=provider_name)
            created = False
        if created:
            MediaAuditEvent.objects.create(candidate=candidate, action="candidate_created", detail={"queue_item_id": queue.pk, "source_item_id": source_item.pk})
        return candidate


def acquire_candidate(queue_item, provider_name=None, *, provider=None, now=None):
    provider_name = _provider_name(provider_name, provider)
    provider = provider or PROVIDERS.get(provider_name)
    if provider is None:
        raise MediaRequestError("Unknown media provider")
    candidate = request_candidate(queue_item, provider_name, provider_instance=provider)
    return _run_provider(candidate, provider, now=now)


def _provider_name(requested, provider_instance=None):
    if requested:
        return requested
    if provider_instance is not None:
        return provider_instance.name
    return next((name for name in settings.MEDIA_PROVIDER_ORDER if name in PROVIDERS), "")


def retry_candidate(candidate, *, provider=None, now=None):
    provider_instance = provider or PROVIDERS.get(candidate.provider)
    if provider_instance is None:
        raise MediaRequestError("Candidate provider is not registered")
    return _run_provider(candidate, provider_instance, now=now)


def _run_provider(candidate, provider, now=None):
    now = now or timezone.now()
    with transaction.atomic():
        candidate = MediaCandidate.objects.select_for_update().select_related("source_match__source_item").get(pk=candidate.pk)
        if candidate.state == MediaCandidate.State.READY:
            return candidate
        if candidate.state == MediaCandidate.State.DOWNLOADING:
            lease_expired = candidate.updated_at <= now - timedelta(seconds=settings.MEDIA_DOWNLOAD_TIMEOUT_SECONDS + 60)
            if not lease_expired:
                return candidate
            candidate.state = MediaCandidate.State.RETRY_WAIT
            candidate.last_outcome = "interrupted"
            candidate.last_error = "Previous download attempt did not complete; eligible for bounded retry."
        if candidate.retry_due_at and candidate.retry_due_at > now:
            return candidate
        if candidate.state in {MediaCandidate.State.INVALID, MediaCandidate.State.REVIEW_REQUIRED} and candidate.attempt_count:
            return candidate
        source_item = candidate.source_match.source_item
        source_url = candidate.provenance.get('source_url', source_item.canonical_url) if candidate.provenance.get('acquisition_platform') == 'youtube' else source_item.canonical_url
        if not provider.can_handle(source_url):
            candidate.state = MediaCandidate.State.REVIEW_REQUIRED
            candidate.last_outcome = "unsupported_source"
            candidate.last_error = "No configured provider can acquire audio from this source."
            candidate.save(update_fields=("state", "last_outcome", "last_error", "updated_at"))
            MediaAuditEvent.objects.create(candidate=candidate, action="provider_unsupported", detail={"platform": source_item.platform, "source_item_id": source_item.pk})
            return candidate
        started_at = now
        candidate.state = MediaCandidate.State.DOWNLOADING
        candidate.attempt_count += 1
        candidate.last_attempt_at = started_at
        candidate.retry_due_at = None
        candidate.last_outcome = "downloading"
        candidate.last_error = ""
        attempt = MediaAttempt.objects.create(candidate=candidate, provider=candidate.provider, state=MediaAttempt.State.RUNNING, started_at=started_at)
        candidate.save(update_fields=("state", "attempt_count", "last_attempt_at", "retry_due_at", "last_outcome", "last_error", "updated_at"))
        MediaAuditEvent.objects.create(candidate=candidate, action="download_started", detail={"attempt_id": attempt.pk, "provider": candidate.provider})

    staging = _staging_dir(candidate)
    try:
        probe_started = time.monotonic()
        probe = provider.probe(source_url, timeout=settings.MEDIA_DOWNLOAD_TIMEOUT_SECONDS)
        probe_seconds = round(time.monotonic() - probe_started, 3)
        if provider.name == "yt-dlp" and source_item.platform == "soundcloud":
            from releases.normalization import normalize_text
            from releases.services import _uploader_mismatch
            recorded_uploader = source_item.metadata.get("uploader")
            identity_changed = (probe.provider_item_id != source_item.native_item_id or
                                normalize_text(probe.title) != normalize_text(source_item.title))
            if recorded_uploader:
                identity_changed |= normalize_text(probe.uploader) != normalize_text(recorded_uploader)
            else:
                source_item.metadata = {**source_item.metadata, "uploader": probe.uploader}
                identity_changed |= not probe.uploader or bool(_uploader_mismatch(source_item))
            if identity_changed:
                candidate.state = MediaCandidate.State.REVIEW_REQUIRED
                candidate.last_outcome = "provider_identity_mismatch"
                candidate.last_error = "Provider ID, title, or uploader differs from the approved source identity."
                candidate.retry_due_at = None
                candidate.save(update_fields=("state", "last_outcome", "last_error", "retry_due_at", "updated_at"))
                MediaAttempt.objects.filter(pk=attempt.pk).update(state=MediaAttempt.State.REVIEW_REQUIRED,
                    finished_at=timezone.now(), outcome=candidate.last_outcome, error=candidate.last_error)
                MediaAuditEvent.objects.create(candidate=candidate, action="provider_identity_review",
                                              detail={"attempt_id": attempt.pk})
                return candidate
        if provider.name == 'yt-dlp-youtube':
            from releases.normalization import normalize_text
            expected=candidate.provenance
            if (probe.provider_item_id!=expected.get('native_item_id') or (probe.evidence or {}).get('channel_id')!=expected.get('official_channel_id')
                    or normalize_text(probe.title)!=normalize_text(expected.get('source_recording_title'))):
                raise ProviderError('YouTube recording/channel identity changed after validation',retryable=False)
        acquisition_started = time.monotonic()
        result = provider.download(probe, staging, timeout=settings.MEDIA_DOWNLOAD_TIMEOUT_SECONDS)
        acquisition_seconds = round(time.monotonic() - acquisition_started, 3)
        downloaded_path = Path(result.path)
        if downloaded_path.is_symlink() or not downloaded_path.resolve().is_relative_to(staging.resolve()):
            raise ProviderError("Provider output was outside its assigned staging directory", retryable=False)
        candidate.expected_duration_seconds = candidate.expected_duration_seconds or probe.duration_seconds
        candidate.provenance = {
            **candidate.provenance,
            "provider_probe": probe.evidence or {},
            "provider_item_id": probe.provider_item_id,
            "provider_title": probe.title,
            "provider_uploader": probe.uploader,
            "provider_duration_seconds": probe.duration_seconds,
            "acquisition_seconds": acquisition_seconds,
            "provider_probe_seconds": probe_seconds,
            "artwork_source_url": _safe_evidence_url(probe.artwork_source_url) if probe.artwork_source_url else "",
        }
        candidate.save(update_fields=("expected_duration_seconds", "provenance", "updated_at"))
        artwork = None
        artwork_state = MediaCandidate.ArtworkState.NOT_PROVIDED
        frozen_artwork = candidate.source_match.evidence.get("archive_official_metadata", {}).get("artwork_url") if candidate.source_match.matching_method in {"archive_spotify_soundcloud", "archive_frozen_spotify"} else None
        artwork_url = frozen_artwork or probe.artwork_source_url
        if artwork_url:
            art_staging = staging / "source-artwork"
            try:
                artwork = (fetch_recorded_spotify_artwork if frozen_artwork else fetch_recorded_soundcloud_artwork)(artwork_url, art_staging)
                validate_artwork(artwork)
                artwork_state = MediaCandidate.ArtworkState.EMBEDDED
                candidate.provenance = {**candidate.provenance, "official_artwork_source_url": _safe_evidence_url(artwork_url)}
                candidate.save(update_fields=("provenance",))
            except (ProviderError, TaggingError):
                artwork_state = MediaCandidate.ArtworkState.INVALID
                artwork = None
        final = _accept_audio_file(candidate, attempt, result.path, expected=candidate.expected_duration_seconds, artwork_path=artwork, artwork_state=artwork_state, now=now)
        return final
    except ProviderError as exc:
        return _record_failure(candidate.pk, attempt.pk, exc, now=now, retryable=exc.retryable)
    except MediaValidationError as exc:
        return _record_failure(candidate.pk, attempt.pk, exc, now=now, retryable=False)
    except (OSError, TaggingError) as exc:
        return _record_failure(candidate.pk, attempt.pk, exc, now=now, retryable=isinstance(exc, OSError))
    except Exception as exc:
        # Persist a redacted diagnostic rather than leaking an exception that could contain signed URLs.
        return _record_failure(candidate.pk, attempt.pk, f"{type(exc).__name__}: unexpected provider processing failure", now=now, retryable=True)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def process_manual_upload(candidate, audio_upload, *, actor, artwork_upload=None, artwork_source_url="", now=None):
    """Authenticated admin entry point; validate/tag the upload using the acquisition pipeline."""
    now = now or timezone.now()
    candidate = MediaCandidate.objects.select_related("source_match__source_item").get(pk=candidate.pk)
    if candidate.state == MediaCandidate.State.READY or candidate.sha256 or candidate.candidate_path or candidate.prepared_path:
        raise MediaRequestError("A ready candidate is immutable; create a separate candidate for a comparison")
    match = candidate.source_match
    if match.confidence < 90 or match.state not in {SourceMatch.State.MATCHED, SourceMatch.State.APPROVED, SourceMatch.State.CORRECTED}:
        raise MediaRequestError("Manual upload requires a confidently identified source match")
    if artwork_upload and not artwork_source_url:
        raise MediaRequestError("Artwork requires an operator-recorded official source URL")
    with transaction.atomic():
        locked = MediaCandidate.objects.select_for_update().get(pk=candidate.pk)
        if locked.state == MediaCandidate.State.READY or locked.sha256 or locked.candidate_path or locked.prepared_path:
            raise MediaRequestError("A ready candidate is immutable")
        locked.attempt_count += 1
        locked.last_attempt_at = now
        locked.state = MediaCandidate.State.PREPARING
        locked.last_outcome = "upload_received"
        locked.last_error = ""
        locked.save(update_fields=("attempt_count", "last_attempt_at", "state", "last_outcome", "last_error", "updated_at"))
        attempt = MediaAttempt.objects.create(candidate=locked, provider="manual", state=MediaAttempt.State.RUNNING, started_at=now)
        MediaAuditEvent.objects.create(candidate=locked, actor=actor, action="manual_upload_received", detail={"attempt_id": attempt.pk, "artwork_source_url": _safe_evidence_url(artwork_source_url) if artwork_source_url else None})
    staging = _staging_dir(candidate, "manual")
    audio_path = None
    art_path = None
    try:
        audio_path = _copy_upload(audio_upload, staging, "manual-audio")
        if artwork_upload:
            art_path = _copy_upload(artwork_upload, staging, "manual-artwork", image=True)
            try:
                validate_artwork(art_path)
            except TaggingError:
                art_path = None
                artwork_state = MediaCandidate.ArtworkState.INVALID
            else:
                artwork_state = MediaCandidate.ArtworkState.EMBEDDED
        else:
            artwork_state = MediaCandidate.ArtworkState.NOT_PROVIDED
        provenance = {
            **candidate.provenance,
            "provider": "manual",
            "uploaded_by_id": actor.pk,
            "uploaded_at_utc": now.isoformat(),
            "official_artwork_source_url": _safe_evidence_url(artwork_source_url) if artwork_source_url else None,
            "official_artwork_attested_by_id": actor.pk if artwork_upload else None,
        }
        MediaCandidate.objects.filter(pk=candidate.pk).update(provenance=provenance)
        expected = candidate.expected_duration_seconds or _source_duration(candidate.source_match.source_item)
        return _accept_audio_file(candidate, attempt, audio_path, expected=expected, artwork_path=art_path, artwork_state=artwork_state, now=now, actor=actor)
    except (MediaRequestError, MediaValidationError, TaggingError, OSError) as exc:
        return _record_failure(candidate.pk, attempt.pk, exc, now=now, retryable=False, actor=actor)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _accept_audio_file(candidate, attempt, source_path, *, expected, artwork_path=None, artwork_state=None, now=None, actor=None, share_prepared=True):
    preparation_started = time.monotonic()
    now = now or timezone.now()
    source_path = Path(source_path)
    if source_path.is_symlink():
        raise MediaValidationError("Candidate audio is not a regular file")
    source_path = source_path.resolve(strict=True)
    if not source_path.is_file():
        raise MediaValidationError("Candidate audio is not a regular file")
    if source_path.stat().st_size > settings.MEDIA_MAX_UPLOAD_BYTES:
        raise MediaValidationError("Candidate exceeds the configured media size limit")
    extension = source_path.suffix.lower()
    if extension not in settings.MEDIA_ALLOWED_AUDIO_EXTENSIONS:
        raise MediaValidationError("Candidate file extension is not permitted")
    facts = probe_audio(source_path)
    comparison, duration_status = compare_duration(facts["duration_seconds"], expected)
    if expected and not candidate.expected_duration_seconds:
        MediaCandidate.objects.filter(pk=candidate.pk, expected_duration_seconds__isnull=True).update(expected_duration_seconds=expected)
    if duration_status == "invalid":
        candidate = MediaCandidate.objects.get(pk=candidate.pk)
        candidate.sha256 = facts["sha256"]
        candidate.file_size_bytes = facts["file_size_bytes"]
        candidate.observed_facts = facts
        candidate.duration_comparison = comparison
        candidate.validation_report = {"status": "invalid", "reason": "audio is truncated or preview-length", "complete": False}
        candidate.state = MediaCandidate.State.INVALID
        candidate.preparation_state = MediaCandidate.PreparationState.FAILED
        candidate.artwork_state = (MediaCandidate.ArtworkState.AVAILABLE if artwork_path else artwork_state) or MediaCandidate.ArtworkState.NOT_PROVIDED
        candidate.last_outcome = "truncated_or_preview"
        candidate.last_error = "Observed audio duration is below the configured completeness ratio."
        candidate.retry_due_at = None
        candidate.save()
        MediaAttempt.objects.filter(pk=attempt.pk).update(state=MediaAttempt.State.INVALID, finished_at=now, outcome=candidate.last_outcome, evidence={"facts": facts, "duration_comparison": comparison})
        MediaAuditEvent.objects.create(candidate=candidate, actor=actor, action="candidate_invalid", detail={"reason": candidate.last_outcome, "sha256": facts["sha256"]})
        return candidate
    if duration_status == "review_required":
        directory = _candidate_dir(candidate)
        raw_target = directory / f"source-{uuid.uuid4().hex}{extension}"
        shutil.copyfile(source_path, raw_target)
        raw_target.chmod(0o600)
        artwork_target = _store_artwork(directory, artwork_path)
        candidate = MediaCandidate.objects.get(pk=candidate.pk)
        candidate.candidate_path = str(raw_target)
        candidate.artwork_path = str(artwork_target) if artwork_target else ""
        candidate.sha256 = facts["sha256"]
        candidate.file_size_bytes = facts["file_size_bytes"]
        candidate.observed_facts = facts
        candidate.duration_comparison = comparison
        candidate.validation_report = {"status": "review_required", "reason": comparison["status"], "complete": None, "audio_stream_present": True}
        candidate.state = MediaCandidate.State.REVIEW_REQUIRED
        candidate.preparation_state = MediaCandidate.PreparationState.PENDING
        candidate.artwork_state = artwork_state or MediaCandidate.ArtworkState.NOT_PROVIDED
        candidate.last_outcome = "duration_review_required"
        candidate.last_error = "Expected duration evidence is missing or conflicts materially."
        candidate.retry_due_at = None
        candidate.quality_rank = quality_rank(facts, candidate.provenance)
        candidate.save()
        MediaAttempt.objects.filter(pk=attempt.pk).update(state=MediaAttempt.State.REVIEW_REQUIRED, finished_at=now, outcome=candidate.last_outcome, evidence={"facts": facts, "duration_comparison": comparison})
        MediaAuditEvent.objects.create(candidate=candidate, actor=actor, action="duration_review_required", detail={"duration_comparison": comparison})
        return candidate

    candidate = MediaCandidate.objects.select_related("track", "release").get(pk=candidate.pk)
    directory = _candidate_dir(candidate)
    raw_target = directory / f"source-{uuid.uuid4().hex}{extension}"
    shutil.copyfile(source_path, raw_target)
    raw_target.chmod(0o600)
    artwork_target = _store_artwork(directory, artwork_path)
    # If identical verified bytes already exist for this track, share their immutable files.
    identical = MediaCandidate.objects.filter(track=candidate.track, state=MediaCandidate.State.READY, sha256=facts["sha256"]).exclude(pk=candidate.pk).first() if share_prepared else None
    if identical:
        raw_target.unlink(missing_ok=True)
        if artwork_target:
            artwork_target.unlink(missing_ok=True)
        raw_target = _safe_media_path(identical.candidate_path)
        prepared_target = _safe_media_path(identical.prepared_path)
        prep_report = {**identical.preparation_report, "shared_from_candidate_id": identical.pk}
    else:
        metadata = _official_metadata(candidate)
        prepared_target = directory / f"prepared-{uuid.uuid4().hex}{extension}"
        try:
            prep_report = prepare_tagged_copy(raw_target, prepared_target, metadata, artwork_path=artwork_path)
            artwork_state = MediaCandidate.ArtworkState.EMBEDDED if artwork_path else MediaCandidate.ArtworkState.NOT_PROVIDED
        except TaggingError as exc:
            prepared_target.unlink(missing_ok=True)
            candidate = MediaCandidate.objects.get(pk=candidate.pk)
            candidate.candidate_path = str(raw_target)
            candidate.artwork_path = str(artwork_target) if artwork_target else ""
            candidate.sha256 = facts["sha256"]
            candidate.file_size_bytes = facts["file_size_bytes"]
            candidate.observed_facts = facts
            candidate.duration_comparison = comparison
            candidate.validation_report = {"status": "valid_audio", "complete": True, "audio_stream_present": True}
            candidate.state = MediaCandidate.State.REVIEW_REQUIRED
            candidate.preparation_state = MediaCandidate.PreparationState.FAILED
            candidate.artwork_state = (MediaCandidate.ArtworkState.AVAILABLE if artwork_path else artwork_state) or MediaCandidate.ArtworkState.NOT_PROVIDED
            candidate.last_outcome = "tagging_review_required"
            candidate.last_error = redact_diagnostic(exc)
            candidate.quality_rank = quality_rank(facts, candidate.provenance)
            candidate.save()
            MediaAttempt.objects.filter(pk=attempt.pk).update(state=MediaAttempt.State.REVIEW_REQUIRED, finished_at=now, outcome=candidate.last_outcome, error=candidate.last_error, evidence={"facts": facts})
            MediaAuditEvent.objects.create(candidate=candidate, actor=actor, action="tagging_review_required", detail={"error": candidate.last_error})
            return candidate

    candidate = MediaCandidate.objects.get(pk=candidate.pk)
    candidate.candidate_path = str(raw_target)
    candidate.prepared_path = str(prepared_target)
    candidate.artwork_path = str(artwork_target) if artwork_target else (identical.artwork_path if identical else "")
    candidate.sha256 = facts["sha256"]
    candidate.file_size_bytes = facts["file_size_bytes"]
    candidate.observed_facts = facts
    candidate.duration_comparison = comparison
    candidate.validation_report = {"status": "valid", "complete": True, "audio_stream_present": True}
    candidate.preparation_state = MediaCandidate.PreparationState.READY
    candidate.preparation_report = prep_report
    candidate.provenance = {**candidate.provenance, "validation_and_preparation_seconds": round(time.monotonic() - preparation_started, 3)}
    candidate.artwork_state = (artwork_state or MediaCandidate.ArtworkState.NOT_PROVIDED) if not artwork_path else MediaCandidate.ArtworkState.EMBEDDED
    candidate.state = MediaCandidate.State.READY
    candidate.last_outcome = "ready"
    candidate.last_error = ""
    candidate.retry_due_at = None
    candidate.quality_rank = quality_rank(facts, candidate.provenance)
    candidate.save()
    MediaAttempt.objects.filter(pk=attempt.pk).update(state=MediaAttempt.State.SUCCEEDED, finished_at=now, outcome="ready", evidence={"facts": facts, "duration_comparison": comparison, "readback": prep_report.get("readback", {})})
    MediaAuditEvent.objects.create(candidate=candidate, actor=actor, action="candidate_ready", detail={"sha256": candidate.sha256, "file_size_bytes": facts["file_size_bytes"], "quality_rank": candidate.quality_rank})
    return candidate


def _record_failure(candidate_id, attempt_id, error, *, now=None, retryable=True, actor=None):
    now = now or timezone.now()
    message = redact_diagnostic(error)
    with transaction.atomic():
        candidate = MediaCandidate.objects.select_for_update().get(pk=candidate_id)
        candidate.last_error = message
        candidate.last_outcome = "provider_error" if retryable else "invalid_upload"
        if retryable:
            seconds = min(60 * (2 ** max(candidate.attempt_count - 1, 0)), 21600)
            candidate.retry_due_at = now + timedelta(seconds=seconds)
            candidate.state = MediaCandidate.State.RETRY_WAIT
            attempt_state = MediaAttempt.State.RETRY_WAIT
            action = "candidate_retry_scheduled"
            candidate.validation_report = {"status": "not_validated"}
        else:
            candidate.retry_due_at = None
            candidate.state = MediaCandidate.State.INVALID
            candidate.preparation_state = MediaCandidate.PreparationState.FAILED
            attempt_state = MediaAttempt.State.INVALID
            action = "candidate_invalid"
        candidate.save()
        MediaAttempt.objects.filter(pk=attempt_id).update(state=attempt_state, finished_at=now, outcome=candidate.last_outcome, error=message)
        MediaAuditEvent.objects.create(candidate=candidate, actor=actor, action=action, detail={"attempt_id": attempt_id, "retry_due_at": candidate.retry_due_at.isoformat() if candidate.retry_due_at else None, "error": message})
        return candidate


def _official_metadata(candidate):
    archive = candidate.source_match.evidence.get("archive_official_metadata")
    if archive and candidate.source_match.matching_method in {"archive_spotify_soundcloud", "archive_frozen_spotify"}:
        return archive
    track = candidate.track
    release = candidate.release
    credits = [row.artist.official_name for row in track.artist_credits.select_related("artist").order_by("position", "pk")]
    if not credits:
        credits = [row.artist.official_name for row in release.artist_credits.select_related("artist").order_by("position", "pk")]
    membership = release.release_tracks.filter(track=track).first()
    source_item = candidate.source_match.source_item
    metadata = source_item.metadata or {}
    return {
        "title": track.official_title,
        "artists": credits,
        "album": release.title,
        "release_date": release.release_date.isoformat() if release.release_date else None,
        "track_number": membership.position if membership else None,
        "disc_number": metadata.get("disc_number") or 1,
    }


def _source_duration(source_item):
    try:
        duration = float((source_item.metadata or {}).get("duration"))
        return duration if duration > 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def _safe_evidence_url(value):
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(str(value or ""))
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        return ""
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _provenance(source_item, match, provider):
    return {
        "provider": provider,
        "source_platform": source_item.platform,
        "source_item_id": source_item.pk,
        "native_item_id": source_item.native_item_id,
        "source_url": source_item.canonical_url,
        "matching_method": match.matching_method,
        "matching_confidence": match.confidence,
        "provenance_confidence": match.confidence,
        "source_recorded_at": source_item.first_observed_at.isoformat() if source_item.first_observed_at else None,
    }


def _copy_upload(upload, directory, stem, image=False):
    original_name = str(getattr(upload, "name", "")).lower()
    suffix = Path(original_name).suffix
    allowed = {".jpg", ".jpeg", ".png"} if image else set(settings.MEDIA_ALLOWED_AUDIO_EXTENSIONS)
    if suffix not in allowed:
        raise MediaRequestError("Uploaded filename extension is not allowed")
    max_size = settings.MEDIA_MAX_ARTWORK_BYTES if image else settings.MEDIA_MAX_UPLOAD_BYTES
    target = Path(directory) / f"{stem}-{uuid.uuid4().hex}{suffix}"
    total = 0
    try:
        with target.open("xb") as output:
            for chunk in upload.chunks() if hasattr(upload, "chunks") else iter(lambda: upload.read(1024 * 1024), b""):
                total += len(chunk)
                if total > max_size:
                    raise MediaRequestError("Upload exceeds the configured size limit")
                output.write(chunk)
        if total <= 0:
            raise MediaRequestError("Upload is empty")
        target.chmod(0o600)
        return target
    except Exception:
        target.unlink(missing_ok=True)
        raise


def _store_artwork(directory, artwork_path):
    if not artwork_path:
        return None
    artwork_path = Path(artwork_path)
    target = Path(directory) / f"artwork-{uuid.uuid4().hex}{artwork_path.suffix.lower()}"
    shutil.copyfile(artwork_path, target)
    target.chmod(0o600)
    return target
