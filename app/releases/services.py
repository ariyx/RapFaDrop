import hashlib
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from sources.models import ArtistSource, SourceItem

from .models import (
    CanonicalRelease,
    IdentityAuditEvent,
    ProcessingQueueItem,
    ReleaseCredit,
    ReleaseTrack,
    ReviewItem,
    SourceMatch,
    Track,
    TrackCredit,
)
from .normalization import base_title_for_edition, edition_markers, normalize_text


def _identity_key(*parts):
    raw = "|".join(str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _credits_match(track, artist):
    return track.credited_artists.filter(pk=artist.pk).exists()


def _duration(metadata):
    value = metadata.get("duration")
    try:
        seconds = int(round(float(value)))
        return seconds if seconds > 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def _profile_names(source):
    from urllib.parse import urlsplit

    slug = urlsplit(source.canonical_url or "").path.strip("/").split("/")[-1]
    return {normalize_text(value) for value in (source.native_profile_id, slug) if value}


def _uploader_mismatch(source_item):
    metadata = source_item.metadata or {}
    uploader = normalize_text(metadata.get("uploader") or metadata.get("channel") or "")
    if not uploader:
        return None
    artist = source_item.source.artist
    acceptable = {normalize_text(artist.official_name), *[normalize_text(alias) for alias in artist.aliases or []], *_profile_names(source_item.source)}
    acceptable.discard("")
    return uploader if uploader not in acceptable else None


def _edition_of_track(artist, base_title, exclude_edition=None):
    matches = list(
        Track.objects.filter(normalized_title=base_title, credited_artists=artist)
        .exclude(edition=exclude_edition or "original")
        .distinct()[:2]
    )
    # Original editions are the only safe parent for a detected version.
    if exclude_edition is None:
        matches = list(Track.objects.filter(normalized_title=base_title, edition="original", credited_artists=artist).distinct()[:2])
    return matches[0] if len(matches) == 1 else None


def _review(source_item, category, reason, evidence, *, release=None, track=None, confidence=0, method="review"):
    if release is None and track is not None:
        candidate_membership = track.release_memberships.select_related("release").order_by("created_at", "pk").first()
        if candidate_membership:
            release = candidate_membership.release
        else:
            track = None
    match, created = SourceMatch.objects.get_or_create(
        source_item=source_item,
        defaults={
            "release": release,
            "track": track,
            "confidence": confidence,
            "evidence": evidence,
            "matching_method": method,
            "state": SourceMatch.State.REVIEW_REQUIRED,
        },
    )
    if not created:
        match.release = release
        match.track = track
        match.confidence = confidence
        match.evidence = evidence
        match.matching_method = method
        match.state = SourceMatch.State.REVIEW_REQUIRED
        match.save(update_fields=("release", "track", "confidence", "evidence", "matching_method", "state", "updated_at"))
    review, made = ReviewItem.objects.get_or_create(
        source_item=source_item,
        defaults={
            "source_match": match,
            "category": category,
            "reason": reason[:500],
            "evidence": evidence,
        },
    )
    if not made and review.state in {ReviewItem.State.OPEN, ReviewItem.State.REQUEUED}:
        review.source_match = match
        review.category = category
        review.reason = reason[:500]
        review.evidence = evidence
        review.save(update_fields=("source_match", "category", "reason", "evidence", "updated_at"))
    if made:
        IdentityAuditEvent.objects.create(review_item=review, source_match=match, source_item=source_item, action="review_created", detail={"category": category, "reason": reason[:500]})
    return "review_required", match, review


def _create_canonical_track(artist, title, normalized, duration, edition="original", edition_of=None):
    identity = _identity_key("track", artist.pk, normalized, edition)
    track, created = Track.objects.get_or_create(
        identity_key=identity,
        defaults={
            "official_title": title,
            "normalized_title": normalized,
            "duration_seconds": duration,
            "edition": edition,
            "edition_of": edition_of,
        },
    )
    if created:
        TrackCredit.objects.create(track=track, artist=artist, position=1)
    return track, created


def _create_canonical_release(artist, title, release_type, release_date, edition="original", edition_of=None):
    normalized = normalize_text(title)
    identity = _identity_key("release", artist.pk, normalized, release_type, edition)
    release, created = CanonicalRelease.objects.get_or_create(
        identity_key=identity,
        defaults={
            "title": title,
            "release_type": release_type,
            "edition": edition,
            "release_date": release_date,
            "edition_of": edition_of,
        },
    )
    if created:
        ReleaseCredit.objects.create(release=release, artist=artist, position=1)
    return release, created


def _ensure_membership(release, track, position, prior_single=None):
    position = max(1, min(int(position or 1), 32767))
    occupied = ReleaseTrack.objects.filter(release=release, position=position).exclude(track=track).first()
    if occupied:
        raise IntegrityError("Release track position is already occupied by a different canonical track")
    membership, _ = ReleaseTrack.objects.get_or_create(
        release=release,
        track=track,
        defaults={"position": position, "prior_single": prior_single},
    )
    if prior_single and membership.prior_single_id is None:
        membership.prior_single = prior_single
        membership.save(update_fields=("prior_single",))
    return membership


def _queue_item(release=None, track=None, now=None):
    now = now or timezone.now()
    if track is not None:
        item, created = ProcessingQueueItem.objects.get_or_create(track=track, defaults={"release": release, "due_at": now})
    else:
        item, created = ProcessingQueueItem.objects.get_or_create(release=release, track=None, defaults={"due_at": now})
    return item, created


def _existing_result(match):
    if match.state == SourceMatch.State.REJECTED:
        return "ignored_duplicate"
    if match.state == SourceMatch.State.REVIEW_REQUIRED:
        return "review_required"
    queue = ProcessingQueueItem.objects.filter(track=match.track).first() if match.track_id else None
    if queue is None and match.release_id:
        queue = ProcessingQueueItem.objects.filter(release=match.release, track__isnull=True).first()
    if queue and queue.state in {ProcessingQueueItem.State.PENDING, ProcessingQueueItem.State.RETRY_WAIT}:
        return "queued"
    return "matched"


def _date_conflict(source_item, matches):
    incoming = source_item.source_release_at
    if incoming is None:
        return False
    for match in matches:
        previous = match.source_item.source_release_at
        if previous and abs((incoming.date() - previous.date()).days) > 180:
            return True
    return False


def _duration_evidence(candidate, duration):
    existing = candidate.duration_seconds
    if existing is None or duration is None:
        return {"existing_duration": existing, "incoming_duration": duration, "comparison": "missing"}, "unknown"
    difference = abs(existing - duration)
    tolerance = max(5, round(max(existing, duration) * 0.05))
    material = max(8, round(max(existing, duration) * 0.10))
    classification = "match" if difference <= tolerance else "material_mismatch" if difference > material else "uncertain"
    return {"existing_duration": existing, "incoming_duration": duration, "difference_seconds": difference, "tolerance_seconds": tolerance, "material_threshold_seconds": material}, classification


@transaction.atomic
def ingest_source_item(source_item, now=None):
    """Deterministically identity-match a stored source fact; never start media/publication work."""
    now = now or timezone.now()
    source_item = SourceItem.objects.select_for_update().select_related("source__artist").get(pk=source_item.pk)
    existing = SourceMatch.objects.filter(source_item=source_item).first()
    if existing:
        return _existing_result(existing)

    artist = source_item.source.artist
    metadata = source_item.metadata or {}
    title = str(source_item.title or "").strip()
    normalized = normalize_text(title)
    if not normalized:
        return _review(source_item, ReviewItem.Category.INVALID_SOURCE, "Source item has no usable title", {"source_title": title})[0]
    if not source_item.source.enabled or source_item.source.verification != ArtistSource.Verification.VERIFIED or not artist.enabled:
        return _review(source_item, ReviewItem.Category.INVALID_SOURCE, "Source or artist is not enabled and verified", {"artist": artist.official_name, "source_enabled": source_item.source.enabled, "verification": source_item.source.verification, "artist_enabled": artist.enabled})[0]
    if source_item.source.platform == ArtistSource.Platform.SPOTIFY and metadata.get("spotify_discovery"):
        # A newly visible regional catalog ID need not be a newly published work.
        # Keep this release fact in the existing review/match workflow without
        # creating a media or publication queue item.
        credits = [normalize_text(name) for name in metadata.get("artist_credits") or []]
        accepted = {normalize_text(artist.official_name), *[normalize_text(alias) for alias in artist.aliases or []]}
        if credits and not accepted.intersection(credits):
            return _review(source_item, ReviewItem.Category.ARTIST_MISMATCH, "Spotify release credits omit the verified artist", {"artist": artist.official_name, "credits": metadata.get("artist_credits")})[0]
        bridge_reason = ""
        bridge_release = None
        if settings.SPOTIFY_MEDIA_BRIDGE_ENABLED and not settings.FRESH_PIPELINE_ENABLED:
            from .spotify_bridge import try_auto_bridge
            result, bridge_reason, bridge_release = try_auto_bridge(source_item, now=now)
            if result:
                return result
        candidates = [release for release in CanonicalRelease.objects.filter(credited_artists=artist).distinct() if normalize_text(release.title) == normalized]
        candidate = bridge_release or (candidates[0] if len(candidates) == 1 else None)
        evidence = {"spotify_release_id": source_item.native_item_id, "artist": artist.official_name,
                    "title": title, "release_type": metadata.get("album_type") or None,
                    "release_date": source_item.source_release_at.date().isoformat() if source_item.source_release_at else None,
                    "candidate_release_id": candidate.pk if candidate else None,
                    "regional_backfill_possible": True, "bridge_reason": bridge_reason or None}
        return _review(source_item, ReviewItem.Category.POSSIBLE_DUPLICATE if candidate else ReviewItem.Category.LOW_CONFIDENCE,
                       "New Spotify ID requires release-time and cross-platform identity review", evidence,
                       release=candidate, confidence=65 if candidate else 0, method="spotify_release_id_review")[0]
    mismatched_uploader = _uploader_mismatch(source_item)
    if mismatched_uploader:
        return _review(source_item, ReviewItem.Category.ARTIST_MISMATCH, "Provider uploader does not match the verified artist/source identity", {"uploader": metadata.get("uploader"), "artist": artist.official_name, "accepted_names": [artist.official_name, *artist.aliases, *_profile_names(source_item.source)]})[0]

    album_title = str(metadata.get("album") or metadata.get("collection_title") or "").strip()
    markers = list(dict.fromkeys([*edition_markers(title), *edition_markers(album_title)]))
    raw_type = str(metadata.get("album_type") or metadata.get("release_type") or "").strip().casefold()
    type_map = {"single": CanonicalRelease.ReleaseType.SINGLE, "album": CanonicalRelease.ReleaseType.LP, "lp": CanonicalRelease.ReleaseType.LP, "ep": CanonicalRelease.ReleaseType.EP}
    release_type = type_map.get(raw_type)
    if raw_type and raw_type not in type_map:
        return _review(source_item, ReviewItem.Category.COLLECTION_TYPE, "Collection type is not a supported explicit album/EP/single type", {"album": album_title, "album_type": raw_type})[0]
    if album_title and raw_type not in {"album", "lp", "ep", "single"}:
        return _review(source_item, ReviewItem.Category.COLLECTION_TYPE, "Collection context exists without an explicit album or EP type", {"album": album_title, "album_type": raw_type or None})[0]
    if release_type in {CanonicalRelease.ReleaseType.LP, CanonicalRelease.ReleaseType.EP} and not album_title:
        return _review(source_item, ReviewItem.Category.COLLECTION_TYPE, "Album or EP type has no collection title", {"album_type": raw_type, "source_title": title})[0]
    if release_type is None:
        release_type = CanonicalRelease.ReleaseType.SINGLE
    release_title = album_title if release_type in {CanonicalRelease.ReleaseType.LP, CanonicalRelease.ReleaseType.EP} else title
    duration = _duration(metadata)
    release_date = source_item.source_release_at.date() if source_item.source_release_at else None
    evidence = {
        "source_title": title,
        "normalized_title": normalized,
        "source_artist_id": artist.pk,
        "source_artist": artist.official_name,
        "source_aliases": artist.aliases,
        "duration_seconds": duration,
        "release_date": release_date.isoformat() if release_date else None,
        "album_title": album_title or None,
        "album_type": raw_type or release_type,
    }

    # Version markers are never silently folded into an original canonical track.
    edition = markers[0] if markers else "original"
    if markers:
        if len(markers) > 1:
            return _review(source_item, ReviewItem.Category.EDITION, "Multiple edition markers require operator review", {**evidence, "edition_markers": markers})[0]
        track_markers = edition_markers(title)
        base_normalized = base_title_for_edition(title, track_markers or markers)
        original = _edition_of_track(artist, base_normalized)
        track, _ = _create_canonical_track(artist, title, normalized, duration, edition=edition, edition_of=original)
        original_release = None
        if original:
            original_release_title = base_title_for_edition(release_title, edition_markers(release_title) or markers)
            original_release = CanonicalRelease.objects.filter(credited_artists=artist, release_type=release_type, edition="original", identity_key=_identity_key("release", artist.pk, original_release_title, release_type, "original")).first()
        release, _ = _create_canonical_release(artist, release_title, release_type, release_date, edition=edition, edition_of=original_release)
        try:
            _ensure_membership(release, track, metadata.get("track_number") or 1)
        except (IntegrityError, TypeError, ValueError):
            return _review(source_item, ReviewItem.Category.POSSIBLE_DUPLICATE, "Edition track position conflicts with another track", {**evidence, "edition": edition}, release=release, track=track)
        match = SourceMatch.objects.create(source_item=source_item, release=release, track=track, confidence=90, evidence={**evidence, "edition": edition, "original_track_id": original.pk if original else None}, matching_method="explicit_edition_marker", state=SourceMatch.State.REVIEW_REQUIRED)
        _review(source_item, ReviewItem.Category.EDITION, "Explicit version marker is kept distinct and awaits edition review", match.evidence, release=release, track=track, confidence=90, method=match.matching_method)
        release.state = CanonicalRelease.State.REVIEW_REQUIRED
        release.save(update_fields=("state", "updated_at"))
        return "review_required"

    existing_tracks = list(Track.objects.filter(normalized_title=normalized, edition="original", credited_artists=artist).distinct()[:3])
    if len(existing_tracks) > 1:
        return _review(source_item, ReviewItem.Category.POSSIBLE_DUPLICATE, "More than one same-artist canonical track has this normalized title", {**evidence, "candidate_track_ids": [track.pk for track in existing_tracks]})[0]

    candidate = existing_tracks[0] if existing_tracks else None
    method = "verified_source_identity"
    confidence = 90
    if candidate:
        duration_details, duration_status = _duration_evidence(candidate, duration)
        evidence["duration_comparison"] = duration_details
        if duration_status == "material_mismatch":
            return _review(source_item, ReviewItem.Category.POSSIBLE_DUPLICATE, "Same title/artist candidate has a materially different duration", evidence, track=candidate, confidence=60, method="title_artist_duration_conflict")[0]
        if duration_status in {"unknown", "uncertain"}:
            return _review(source_item, ReviewItem.Category.LOW_CONFIDENCE, "Same title/artist candidate lacks a conclusive duration comparison", evidence, track=candidate, confidence=75, method="title_artist_low_confidence")[0]
        previous_matches = list(SourceMatch.objects.filter(track=candidate, state__in=(SourceMatch.State.MATCHED, SourceMatch.State.APPROVED, SourceMatch.State.CORRECTED)).select_related("source_item"))
        if release_type == CanonicalRelease.ReleaseType.SINGLE and _date_conflict(source_item, previous_matches):
            return _review(source_item, ReviewItem.Category.POSSIBLE_DUPLICATE, "Matching title/artist has a release-date conflict suggesting a rerelease or distinct work", evidence, track=candidate, confidence=75, method="title_artist_date_conflict")[0]
        method = "normalized_title_artist_duration"
        confidence = 98
    else:
        candidate, _ = _create_canonical_track(artist, title, normalized, duration)

    release_edition = "original"
    original_release_key = _identity_key("release", artist.pk, normalize_text(release_title), release_type, release_edition)
    edition_of = None
    if candidate.edition_of_id:
        edition_of = CanonicalRelease.objects.filter(identity_key=original_release_key).first()
    release, _ = _create_canonical_release(artist, release_title, release_type, release_date, edition=release_edition, edition_of=edition_of)
    single_membership = ReleaseTrack.objects.filter(
        track=candidate, release__release_type=CanonicalRelease.ReleaseType.SINGLE
    ).order_by("created_at", "pk").first()
    prior_single = single_membership if release_type in {CanonicalRelease.ReleaseType.LP, CanonicalRelease.ReleaseType.EP} else None
    try:
        with transaction.atomic():
            membership = _ensure_membership(release, candidate, metadata.get("track_number") or 1, prior_single=prior_single)
    except (IntegrityError, TypeError, ValueError):
        return _review(source_item, ReviewItem.Category.POSSIBLE_DUPLICATE, "Release track order conflicts with a different canonical track", evidence, release=release, track=candidate, confidence=60, method="release_position_conflict")[0]

    match, made = SourceMatch.objects.get_or_create(
        source_item=source_item,
        defaults={"release": release, "track": candidate, "confidence": confidence, "evidence": evidence, "matching_method": method, "state": SourceMatch.State.MATCHED},
    )
    if not made:
        return _existing_result(match)
    queue, queued = _queue_item(release=release, track=candidate, now=now)
    if queued:
        IdentityAuditEvent.objects.create(source_match=match, source_item=source_item, action="canonical_item_queued", detail={"release_id": release.pk, "track_id": candidate.pk, "queue_id": queue.pk})
        return "queued"
    return "matched"


@transaction.atomic
def resolve_review(review_item, action, actor=None, *, release=None, track=None, resolution="", now=None):
    """Audited, idempotent admin decision API. No action starts processing."""
    now = now or timezone.now()
    # Avoid a nullable outer join to source_match in PostgreSQL FOR UPDATE.
    review = ReviewItem.objects.select_for_update().select_related("source_item").get(pk=review_item.pk)
    if action == "requeue":
        if review.state == ReviewItem.State.OPEN:
            return review
        review.state = ReviewItem.State.REQUEUED
        review.admin_action = ReviewItem.AdminAction.REQUEUE
        review.actor = actor
        review.reviewed_at = now
        review.resolution = resolution or "Explicitly reopened for human review"
        review.save(update_fields=("state", "admin_action", "actor", "reviewed_at", "resolution", "updated_at"))
        if review.source_match_id:
            review.source_match.state = SourceMatch.State.REVIEW_REQUIRED
            review.source_match.admin_decision = "requeue"
            review.source_match.decided_by = actor
            review.source_match.decided_at = now
            review.source_match.save(update_fields=("state", "admin_decision", "decided_by", "decided_at", "updated_at"))
        IdentityAuditEvent.objects.create(review_item=review, source_match=review.source_match, source_item=review.source_item, actor=actor, action="review_requeued", detail={"resolution": resolution})
        return review

    desired_state = {"approve": ReviewItem.State.APPROVED, "reject": ReviewItem.State.REJECTED, "correct": ReviewItem.State.CORRECTED}.get(action)
    if desired_state is None:
        raise ValueError(f"Unsupported review action: {action}")
    if review.state == desired_state and review.actor_id == getattr(actor, "pk", None):
        return review
    if review.state not in {ReviewItem.State.OPEN, ReviewItem.State.REQUEUED}:
        raise ValueError("Resolved review must be explicitly requeued before another decision")
    match = review.source_match
    if match is None:
        raise ValueError("Review has no source match to decide")
    if action == "correct":
        release = release or review.resolved_release
        track = track or review.resolved_track
        if release is None:
            raise ValueError("Correction requires a canonical release")
        if track is not None and not release.release_tracks.filter(track=track).exists():
            raise ValueError("Corrected track must be a member of the selected release")
        match.release = release
        match.track = track
        match.confidence = 100
    elif action == "approve" and match.release_id is None and not (
        settings.SPOTIFY_MEDIA_BRIDGE_ENABLED and review.source_item.metadata.get("spotify_discovery")
    ):
        raise ValueError("Review needs a corrected canonical release before approval")
    match.state = {"approve": SourceMatch.State.APPROVED, "reject": SourceMatch.State.REJECTED, "correct": SourceMatch.State.CORRECTED}[action]
    match.admin_decision = action
    match.decided_by = actor
    match.decided_at = now
    match.save(update_fields=("release", "track", "confidence", "state", "admin_decision", "decided_by", "decided_at", "updated_at"))
    review.state = desired_state
    review.admin_action = action
    review.actor = actor
    review.reviewed_at = now
    review.resolution = resolution
    if action == "correct":
        review.resolved_release = release
        review.resolved_track = track
    review.save(update_fields=("state", "admin_action", "actor", "reviewed_at", "resolution", "resolved_release", "resolved_track", "updated_at"))
    queue = None
    queue_ids = []
    if action in {"approve", "correct"}:
        if review.source_item.metadata.get("spotify_discovery"):
            if settings.SPOTIFY_MEDIA_BRIDGE_ENABLED:
                if settings.FRESH_PIPELINE_ENABLED:
                    from .fresh import classify
                    from .models import FreshDispatch
                    disposition, reason, evidence = classify(review.source_item, now=now)
                    dispatch, _ = FreshDispatch.objects.get_or_create(source_item=review.source_item)
                    dispatch.disposition, dispatch.reason, dispatch.evidence = disposition, reason, evidence
                    dispatch.save()
                else:
                    from .spotify_bridge import bridge_approved_review
                    queue_ids = bridge_approved_review(review, match, resolution=resolution, now=now)
        else:
            queue, _ = _queue_item(release=match.release, track=match.track, now=now)
    audit_action = {"approve": "review_approved", "reject": "review_rejected", "correct": "review_corrected"}[action]
    IdentityAuditEvent.objects.create(review_item=review, source_match=match, source_item=review.source_item, actor=actor, action=audit_action, detail={"release_id": match.release_id, "track_id": match.track_id, "resolution": resolution, "queue_id": queue.pk if queue else None, "queue_ids": queue_ids})
    return review


@transaction.atomic
def retry_queue_item(queue_item, error, now=None, base_delay_seconds=60, maximum_delay_seconds=21600):
    now = now or timezone.now()
    item = ProcessingQueueItem.objects.select_for_update().get(pk=queue_item.pk)
    item.attempt_count += 1
    delay = min(base_delay_seconds * (2 ** (item.attempt_count - 1)), maximum_delay_seconds)
    item.state = ProcessingQueueItem.State.RETRY_WAIT
    item.due_at = now + timedelta(seconds=delay)
    item.last_error = str(error)[:1000]
    item.save(update_fields=("attempt_count", "state", "due_at", "last_error", "updated_at"))
    IdentityAuditEvent.objects.create(action="queue_retry_scheduled", detail={"queue_id": item.pk, "attempt": item.attempt_count, "retry_seconds": delay, "error": item.last_error})
    return item
