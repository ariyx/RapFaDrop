"""Conservative Spotify metadata to verified full-audio queue bridge."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from media_pipeline.models import MediaCandidate
from media_pipeline.providers import PROVIDERS
from sources.models import Artist, ArtistSource, SourceItem

from .models import CanonicalRelease, IdentityAuditEvent, ProcessingQueueItem, ReleaseCredit, ReleaseTrack, SourceMatch, TrackCredit
from .normalization import edition_markers, normalize_text


def _shape(item):
    metadata = item.metadata or {}
    kind = {"single": CanonicalRelease.ReleaseType.SINGLE, "album": CanonicalRelease.ReleaseType.LP,
            "ep": CanonicalRelease.ReleaseType.EP}.get(metadata.get("album_type"))
    tracks = metadata.get("tracks")
    if kind is None or not isinstance(tracks, list) or not 1 <= len(tracks) <= 100:
        raise ValueError("Spotify release type or complete track list is unavailable")
    if metadata.get("track_count") != len(tracks):
        raise ValueError("Spotify release track count is incomplete")
    if kind == CanonicalRelease.ReleaseType.SINGLE and len(tracks) != 1:
        raise ValueError("Spotify single has more than one track")
    if edition_markers(item.title):
        raise ValueError("Spotify release edition requires review")
    accepted = {normalize_text(item.source.artist.official_name),
                *[normalize_text(alias) for alias in item.source.artist.aliases or []]}
    credits = {normalize_text(value) for value in metadata.get("artist_credits") or []}
    if not credits.intersection(accepted):
        raise ValueError("Spotify release credits do not verify the source artist")
    seen = set()
    for position, track in enumerate(tracks, 1):
        if not isinstance(track, dict) or track.get("position") != position or not track.get("id") or not track.get("title"):
            raise ValueError("Spotify track identity or order is incomplete")
        if track["id"] in seen or edition_markers(track["title"]):
            raise ValueError("Spotify track is repeated or has an edition marker")
        seen.add(track["id"])
        try:
            duration = float(track["duration_seconds"])
        except (KeyError, TypeError, ValueError, OverflowError):
            raise ValueError("Spotify track duration is unavailable") from None
        if duration <= 0:
            raise ValueError("Spotify track duration is unavailable")
        track_credits = {normalize_text(value) for value in track.get("artist_credits") or []}
        if track_credits and not track_credits.intersection(accepted):
            raise ValueError("Spotify track credits do not verify the source artist")
    return kind, tracks


def _membership_tracks(release, tracks):
    memberships = list(release.release_tracks.select_related("track").order_by("position", "pk"))
    if len(memberships) != len(tracks):
        raise ValueError("Canonical release track count differs from Spotify")
    for position, (membership, spotify_track) in enumerate(zip(memberships, tracks), 1):
        if membership.position != position or normalize_text(membership.track.official_title) != normalize_text(spotify_track["title"]):
            raise ValueError("Canonical release track order or title differs from Spotify")
        known = membership.track.duration_seconds
        expected = float(spotify_track["duration_seconds"])
        if known and abs(known - expected) > max(5, expected * 0.05):
            raise ValueError("Canonical track duration differs from Spotify")
    return memberships


def _soundcloud_match(item, track, spotify_track):
    """Only an existing confident identity on the same verified artist can supply audio."""
    from .services import _uploader_mismatch

    provider = PROVIDERS.get("yt-dlp")
    if provider is None:
        return None
    choices = []
    for match in SourceMatch.objects.filter(
        track=track, confidence__gte=90,
        state__in=(SourceMatch.State.MATCHED, SourceMatch.State.APPROVED, SourceMatch.State.CORRECTED),
        source_item__platform=ArtistSource.Platform.SOUNDCLOUD,
        source_item__source__artist=item.source.artist,
        source_item__source__verification=ArtistSource.Verification.VERIFIED,
    ).select_related("source_item__source"):
        source_item = match.source_item
        if source_item.from_baseline or source_item.first_observed_at < timezone.now() - timedelta(days=14):
            continue
        if not provider.can_handle(source_item.canonical_url) or _uploader_mismatch(source_item):
            continue
        if normalize_text(source_item.title) != normalize_text(spotify_track["title"]):
            continue
        try:
            duration = float((source_item.metadata or {})["duration"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        expected = float(spotify_track["duration_seconds"])
        if duration <= 0 or abs(duration - expected) > max(5, expected * 0.05):
            continue
        if not item.source_release_at or not source_item.source_release_at:
            continue
        if abs((item.source_release_at.date() - source_item.source_release_at.date()).days) > 14:
            continue
        choices.append(match)
    return choices[0] if len(choices) == 1 else None


def _candidate_release(item, kind):
    matches = [release for release in CanonicalRelease.objects.filter(
        credited_artists=item.source.artist, release_type=kind, edition="original",
    ).distinct() if normalize_text(release.title) == normalize_text(item.title)]
    return matches[0] if len(matches) == 1 else None


def _apply_official_credits(item, release, memberships, tracks):
    """Preserve verified Spotify contributors without enabling monitoring for them."""
    def apply(model, parent_field, parent, names):
        artists = []
        for name in names:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Spotify artist credit is incomplete")
            normalized = normalize_text(name)
            matches = [artist for artist in Artist.objects.all() if normalized in {
                normalize_text(artist.official_name), *[normalize_text(alias) for alias in artist.aliases or []]}]
            if len(matches) > 1:
                raise ValueError("Spotify artist credit matches multiple identities")
            artist = matches[0] if matches else Artist.objects.create(official_name=name.strip(), enabled=False)
            if artist not in artists:
                artists.append(artist)
        if not artists:
            raise ValueError("Spotify artist credits are unavailable")
        rows = model.objects.filter(**{parent_field: parent})
        rows.exclude(artist__in=artists).delete()
        for position, artist in enumerate(artists, 1):
            model.objects.update_or_create(**{parent_field: parent, "artist": artist}, defaults={"position": position})
    apply(ReleaseCredit, "release", release, item.metadata["artist_credits"])
    for membership, track in zip(memberships, tracks):
        apply(TrackCredit, "track", membership.track, track.get("artist_credits") or item.metadata["artist_credits"])


def try_auto_bridge(item, now=None):
    """Return (result, reason, candidate release); no queue on uncertain evidence."""
    from .services import _queue_item
    from media_pipeline.services import request_candidate

    now = now or timezone.now()
    if item.from_baseline:
        return None, "Historical Spotify baseline item cannot enter the media bridge", None
    try:
        kind, tracks = _shape(item)
    except ValueError as exc:
        return None, str(exc), None
    if not item.source_release_at or not now - timedelta(days=14) <= item.source_release_at <= now + timedelta(days=1):
        return None, "Spotify catalog appearance has no corroborated recent release date", None
    release = _candidate_release(item, kind)
    if release is None:
        return None, "No unique same-artist canonical release exists", None
    try:
        memberships = _membership_tracks(release, tracks)
    except ValueError as exc:
        return None, str(exc), release
    matches = [_soundcloud_match(item, membership.track, track)
               for membership, track in zip(memberships, tracks)]
    if any(match is None for match in matches):
        return None, "No unique verified full-audio SoundCloud match for every track", release

    _apply_official_credits(item, release, memberships, tracks)

    spotify_match = SourceMatch.objects.create(
        source_item=item, release=release,
        track=memberships[0].track if kind == CanonicalRelease.ReleaseType.SINGLE else None,
        confidence=95, state=SourceMatch.State.MATCHED, matching_method="spotify_verified_soundcloud_bridge",
        evidence={"spotify_release_id": item.native_item_id, "soundcloud_match_ids": [match.pk for match in matches],
                  "release_date": item.source_release_at.date().isoformat(), "audio_provider": "yt-dlp"},
    )
    queue_ids = []
    created_any = False
    for membership, match in zip(memberships, matches):
        queue, created = _queue_item(release=match.release, track=membership.track, now=now)
        queue_ids.append(queue.pk)
        created_any |= created
        if queue.state in {ProcessingQueueItem.State.PENDING, ProcessingQueueItem.State.RETRY_WAIT}:
            candidate = MediaCandidate.objects.filter(
                track=membership.track, source_match=match, provider="yt-dlp",
                state__in=(MediaCandidate.State.CANDIDATE, MediaCandidate.State.RETRY_WAIT),
            ).first()
            if candidate is None and (created or not MediaCandidate.objects.filter(track=membership.track).exists()):
                candidate = request_candidate(queue, provider_name="yt-dlp")
                if candidate.source_match_id != match.pk:
                    raise ValueError("Media candidate source differs from verified SoundCloud match")
            if candidate is not None:
                candidate.provenance = {**candidate.provenance, "spotify_bridge_release_id": item.native_item_id}
                candidate.save(update_fields=("provenance", "updated_at"))
    IdentityAuditEvent.objects.create(source_match=spotify_match, source_item=item, action="spotify_bridge_queued",
                                      detail={"queue_ids": queue_ids, "created": created_any})
    return "queued" if created_any else "matched", "", release


def _materialize_approved(item, release, tracks, kind):
    from .services import _create_canonical_release, _create_canonical_track, _ensure_membership

    artist = item.source.artist
    if release is None:
        release = _create_canonical_release(artist, item.title, kind,
                                            item.source_release_at.date() if item.source_release_at else None)[0]
        for position, spotify_track in enumerate(tracks, 1):
            title = spotify_track["title"]
            expected = float(spotify_track["duration_seconds"])
            track, _ = _create_canonical_track(artist, title, normalize_text(title), round(expected))
            if track.duration_seconds and abs(track.duration_seconds - expected) > max(5, expected * 0.05):
                raise ValueError("Existing canonical track duration conflicts with Spotify")
            prior_single = None
            if kind != CanonicalRelease.ReleaseType.SINGLE:
                prior_single = ReleaseTrack.objects.filter(track=track, release__release_type=CanonicalRelease.ReleaseType.SINGLE).first()
            _ensure_membership(release, track, position, prior_single=prior_single)
    if (release.release_type != kind or normalize_text(release.title) != normalize_text(item.title) or
            not release.credited_artists.filter(pk=artist.pk).exists()):
        raise ValueError("Selected canonical release does not match Spotify identity")
    memberships = _membership_tracks(release, tracks)
    _apply_official_credits(item, release, memberships, tracks)
    return release, memberships


def _manual_match(item, primary_match, release, membership, spotify_track, now):
    if primary_match.track_id == membership.track_id and primary_match.release_id == release.pk:
        return primary_match
    native_id = f"release-track:{item.native_item_id}:{spotify_track['id']}"
    child, _ = SourceItem.objects.get_or_create(
        platform=ArtistSource.Platform.SPOTIFY, native_item_id=native_id,
        defaults={"source": item.source, "title": spotify_track["title"],
                  "canonical_url": f"https://open.spotify.com/track/{spotify_track['id']}",
                  "source_release_at": item.source_release_at, "first_observed_at": now,
                  "metadata": {"spotify_release_track": True, "release_id": item.native_item_id},
                  "sanitized_raw_data": {"release_id": item.native_item_id, "track_id": spotify_track["id"]}},
    )
    match, _ = SourceMatch.objects.get_or_create(
        source_item=child,
        defaults={"release": release, "track": membership.track, "confidence": 100,
                  "state": SourceMatch.State.APPROVED, "matching_method": "spotify_reviewed_track",
                  "evidence": {"parent_release_item_id": item.pk}},
    )
    if match.release_id != release.pk or match.track_id != membership.track_id:
        raise ValueError("Spotify reviewed track identity conflicts with an existing match")
    return match


def bridge_approved_review(review, match, *, resolution, now=None):
    """After explicit operator approval, queue each canonical track exactly once."""
    from .services import _queue_item
    from media_pipeline.services import request_candidate

    now = now or timezone.now()
    item = review.source_item
    if not settings.SPOTIFY_MEDIA_BRIDGE_ENABLED or item.from_baseline:
        return []
    if not resolution.strip():
        raise ValueError("Spotify media approval requires an explicit operator resolution")
    kind, tracks = _shape(item)
    release, memberships = _materialize_approved(item, match.release, tracks, kind)
    if match.track_id and kind == CanonicalRelease.ReleaseType.SINGLE and match.track_id != memberships[0].track_id:
        raise ValueError("Selected canonical track differs from Spotify")
    match.release = release
    match.track = memberships[0].track if kind == CanonicalRelease.ReleaseType.SINGLE else None
    match.confidence = 100
    match.save(update_fields=("release", "track", "confidence", "updated_at"))
    queue_ids = []
    for membership, spotify_track in zip(memberships, tracks):
        sc_match = _soundcloud_match(item, membership.track, spotify_track)
        queue_release = sc_match.release if sc_match else release
        queue, created = _queue_item(release=queue_release, track=membership.track, now=now)
        queue_ids.append(queue.pk)
        if queue.state == ProcessingQueueItem.State.COMPLETE or MediaCandidate.objects.filter(track=membership.track).exists():
            continue
        if sc_match and queue.release_id == sc_match.release_id:
            candidate = request_candidate(queue, provider_name="yt-dlp")
            candidate.provenance = {**candidate.provenance, "spotify_bridge_release_id": item.native_item_id}
            candidate.save(update_fields=("provenance", "updated_at"))
        elif created or queue.release_id == release.pk:
            manual_match = _manual_match(item, match, release, membership, spotify_track, now)
            MediaCandidate.objects.get_or_create(
                track=membership.track, release=release, source_match=manual_match, provider="manual",
                defaults={"state": MediaCandidate.State.REVIEW_REQUIRED,
                          "last_outcome": "manual_audio_required",
                          "last_error": "No verified full-audio provider match; operator must supply complete audio.",
                          "expected_duration_seconds": float(spotify_track["duration_seconds"]),
                          "provenance": {"source_platform": "spotify", "source_item_id": item.pk,
                                         "spotify_track_id": spotify_track["id"], "review_id": review.pk}},
            )
    IdentityAuditEvent.objects.create(review_item=review, source_match=match, source_item=item,
                                      action="spotify_bridge_approved", detail={"queue_ids": queue_ids})
    return queue_ids
