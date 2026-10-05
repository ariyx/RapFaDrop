import hashlib
from datetime import timedelta
from html import escape
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from media_pipeline.models import MediaCandidate
from media_pipeline.providers import redact_diagnostic
from media_pipeline.services import best_ready_candidate
from media_pipeline.tagging import validate_artwork
from media_pipeline.validation import quality_improved
from releases.models import CanonicalRelease, SourceMatch

from .captions import DEFAULT_CONFIG, render_caption, safe_url
from .gateway import GatewayError, GatewayResult, UncertainGatewayError, guard_target
from .models import AlbumSession, CaptionTemplate, Publication, PublicationAttempt, PublicationAuditEvent, PublicationChannel, PublicationReconciliation


AUDIO_KINDS = (Publication.Kind.SINGLE, Publication.Kind.TRACK, Publication.Kind.EDITION, Publication.Kind.ARCHIVE)
CONFIDENT_STATES = (SourceMatch.State.MATCHED, SourceMatch.State.APPROVED, SourceMatch.State.CORRECTED)
SEND_OPERATIONS = {"send_audio", "send_intro", "send_text", "reply", "notify"}


class PublicationError(ValueError):
    pass


def _audit(pub, action, *, attempt=None, actor=None, detail=None):
    return PublicationAuditEvent.objects.create(publication=pub, action=action, attempt=attempt, actor=actor, detail=detail or {})


@transaction.atomic
def schedule_publication_retry(publication, *, actor, now=None):
    """Make a definitely failed retry-wait publication due; never send from an admin request."""
    now = now or timezone.now()
    pub = Publication.objects.select_for_update().get(pk=publication.pk)
    if pub.state != Publication.State.RETRY_WAIT:
        raise PublicationError("Only definitely failed retry-wait publications can be rescheduled")
    attempt = pub.attempts.filter(state=PublicationAttempt.State.FAILED).order_by("-pk").first()
    if attempt is None:
        raise PublicationError("No definite failed attempt is available to retry")
    old_due = pub.retry_due_at.isoformat() if pub.retry_due_at else None
    pub.retry_due_at = now
    pub.save(update_fields=("retry_due_at", "updated_at"))
    _audit(pub, "operator_retry_scheduled", attempt=attempt, actor=actor, detail={"previous_due_at": old_due, "retry_due_at": now.isoformat()})
    return pub


def _path(value):
    root = Path(settings.MEDIA_ROOT).resolve()
    path = Path(value).resolve() if value else None
    if path is None or not path.is_relative_to(root) or not path.is_file() or Path(value).is_symlink():
        raise PublicationError("Media must be a retained file inside configured storage")
    return path


def require_ready(candidate):
    candidate = MediaCandidate.objects.select_related("source_match", "release", "track").get(pk=candidate.pk)
    match = candidate.source_match
    if candidate.state != MediaCandidate.State.READY or candidate.preparation_state != MediaCandidate.PreparationState.READY or candidate.validation_report.get("complete") is not True:
        raise PublicationError("Only complete M3 ready media is eligible for publication")
    if match.state not in CONFIDENT_STATES or match.confidence < 90 or match.track_id != candidate.track_id or match.release_id != candidate.release_id:
        raise PublicationError("Publication requires a confident matching canonical identity")
    if candidate.release.state not in {CanonicalRelease.State.IDENTIFIED, CanonicalRelease.State.APPROVED}:
        raise PublicationError("Release is not approved for publication")
    path = _path(candidate.prepared_path)
    if path.suffix.lower() not in {".mp3", ".m4a"} or not 0 < path.stat().st_size <= 50_000_000:
        raise PublicationError("Telegram audio must be ready MP3/M4A within the Bot API file limit")
    return candidate


def _template(kind):
    template = CaptionTemplate.objects.filter(kind=kind, enabled=True).order_by("-version").first()
    if template is None:
        template, _ = CaptionTemplate.objects.get_or_create(kind=kind, version=1, defaults={"config": DEFAULT_CONFIG})
    return template


def _channel(target):
    channel, _ = PublicationChannel.objects.get_or_create(target=guard_target(target))
    return channel


def _audio_context(candidate, channel):
    track, release = candidate.track, candidate.release
    context = {"title": track.official_title, "artists": list(track.artist_credits.order_by("position", "pk").values_list("artist__official_name", flat=True)), "release_type": release.release_type, "channel_target": channel.target}
    version = track.edition if track.edition != "original" else release.edition
    if version in {"instrumental", "reissue", "deluxe"}:
        context["version_type"] = version
    matches = SourceMatch.objects.filter(track=track, confidence__gte=90, state__in=CONFIDENT_STATES).select_related("source_item").order_by("pk")
    for match in matches:
        source = match.source_item
        if source.platform in {"spotify", "soundcloud"}:
            context[f"{source.platform}_url"] = safe_url(source.canonical_url)
        if source.metadata.get("official_music_video_url"):
            context["music_video_url"] = safe_url(source.metadata["official_music_video_url"])
    original = Publication.objects.filter(channel=channel, track=track.edition_of, message_id__isnull=False).first() if track.edition_of_id else None
    if original and original.message_url:
        context["original_track_post_url"] = original.message_url
        context["original_confirmed"] = original.state == Publication.State.PUBLISHED
    elif release.edition_of_id:
        original_album = Publication.objects.filter(channel=channel, release=release.edition_of, kind=Publication.Kind.INTRO, state=Publication.State.PUBLISHED, message_id__isnull=False).first()
        if original_album:
            context.update(original_album_post_url=original_album.message_url, original_confirmed=True)
    album = AlbumSession.objects.filter(channel=channel, release__release_tracks__track=track, intro__message_id__isnull=False).select_related("intro").order_by("pk").first()
    if album and album.intro.message_url:
        context["album_post_url"] = album.intro.message_url
        context["album_intro_confirmed"] = album.intro.state == Publication.State.PUBLISHED
    return context, original


def reserve_audio(candidate, target, *, kind=None, album_session=None):
    candidate = require_ready(candidate)
    channel = _channel(target)
    kind = kind or (Publication.Kind.EDITION if candidate.track.edition_of_id else Publication.Kind.SINGLE)
    if kind not in AUDIO_KINDS:
        raise PublicationError("Invalid audio publication kind")
    with transaction.atomic():
        channel = PublicationChannel.objects.select_for_update().get(pk=channel.pk)
        existing = Publication.objects.filter(channel=channel, track=candidate.track).first()
        if existing:
            return existing
        # Channel serialization also prevents two concurrent identical-edition reservations.
        if candidate.sha256:
            identical = Publication.objects.filter(channel=channel, kind__in=AUDIO_KINDS, candidate__sha256=candidate.sha256).first()
            if identical:
                _audit(identical, "identical_audio_reused", detail={"requested_track_id": candidate.track_id})
                return identical
        context, original = _audio_context(candidate, channel)
        if album_session:
            context["album_post_url"] = album_session.intro.message_url
            context["album_intro_confirmed"] = album_session.intro.state == Publication.State.PUBLISHED
            context["release_type"] = album_session.release.release_type
        template = _template(kind)
        pub = Publication.objects.create(channel=channel, identity_key=f"audio:{candidate.track.canonical_id}", kind=kind, track=candidate.track, release=candidate.release, candidate=candidate, original=original, template=template, context=context, caption_html=render_caption(kind, context, template.config).html, album_session=album_session)
        _audit(pub, "publication_reserved", detail={"candidate_id": candidate.pk})
        return pub


def _audio_payload(pub, candidate=None):
    candidate = require_ready(candidate or pub.candidate)
    artwork = str(_path(candidate.artwork_path)) if candidate.artwork_path else ""
    return {"audio_path": str(_path(candidate.prepared_path)), "artwork_path": artwork, "title": candidate.track.official_title, "performer": " × ".join(pub.context.get("artists", [])), "duration": int(candidate.observed_facts.get("duration_seconds") or 0), "caption_html": pub.caption_html, "context": pub.context}


def publish_single(candidate, target, *, gateway, now=None):
    pub = reserve_audio(candidate, target)
    if pub.message_id:
        return pub
    return perform(pub, "send_audio", "initial", _audio_payload(pub), gateway=gateway, candidate=pub.candidate, now=now)


def _release_album_if_expired(channel, now):
    if channel.active_album_id:
        session = AlbumSession.objects.get(pk=channel.active_album_id)
        if session.failed_since and session.failed_since <= now - timedelta(seconds=settings.PUBLICATION_ALBUM_HOLD_SECONDS):
            session.state = "paused"
            session.save(update_fields=("state", "updated_at"))
            channel.active_album = None
            channel.save(update_fields=("active_album",))


def _mark_uncertain(attempt, message):
    attempt.state = PublicationAttempt.State.UNCERTAIN
    attempt.error = message
    attempt.finished_at = timezone.now()
    attempt.save(update_fields=("state", "error", "finished_at"))
    pub = attempt.publication
    pub.state = Publication.State.UNCERTAIN
    pub.last_error = message
    pub.retry_due_at = None
    pub.save(update_fields=("state", "last_error", "retry_due_at", "updated_at"))
    PublicationReconciliation.objects.get_or_create(attempt=attempt)
    _audit(pub, "reconciliation_required", attempt=attempt)


def perform(pub, operation, operation_key, payload, *, gateway, candidate=None, now=None, session_id=None, correction_notice=True):
    """Commit an attempt and channel lease BEFORE a network operation; never blind-resend."""
    now = now or timezone.now()
    if getattr(gateway, "collection_id", None) is not None:
        from archive_collection.services import authorize_publication
        authorize_publication(gateway.collection_id, pub, operation, payload, allow_paused_caption_edits=getattr(gateway, 'allow_paused_caption_edits', False))
    else:
        guard_target(pub.channel.target)
    with transaction.atomic():
        channel = PublicationChannel.objects.select_for_update().get(pk=pub.channel_id)
        pub = Publication.objects.select_for_update().get(pk=pub.pk)
        if channel.in_flight_id:
            if channel.lease_until and channel.lease_until <= now:
                stale = PublicationAttempt.objects.get(pk=channel.in_flight_id)
                if stale.state == PublicationAttempt.State.PENDING:
                    _mark_uncertain(stale, "Worker lease expired without a recorded response")
                channel.in_flight = None
                channel.lease_until = None
                channel.save(update_fields=("in_flight", "lease_until"))
                pub.refresh_from_db()
            else:
                return pub
        _release_album_if_expired(channel, now)
        if channel.active_album_id and channel.active_album_id != session_id:
            return pub
        if pub.state in {Publication.State.UNCERTAIN, Publication.State.REVIEW} or pub.attempts.filter(reconciliation__state="open").exists():
            return pub
        if pub.attempts.filter(operation_key=operation_key, state=PublicationAttempt.State.SUCCEEDED).exists():
            return pub
        if pub.retry_due_at and pub.retry_due_at > now:
            return pub
        if operation in SEND_OPERATIONS and pub.message_id:
            return pub
        if operation not in SEND_OPERATIONS and not pub.message_id:
            raise PublicationError("An edit/delete requires a stored message ID")
        if operation in {"send_audio", "edit_media"}:
            candidate = require_ready(candidate or pub.candidate)
            if _path(payload.get("audio_path")) != _path(candidate.prepared_path):
                raise PublicationError("Audio operation must use the recorded ready candidate")
        payload = {**payload}
        if operation not in SEND_OPERATIONS:
            payload["message_id"] = pub.message_id
        attempt = PublicationAttempt.objects.create(publication=pub, operation=operation, operation_key=operation_key, candidate=candidate, previous_candidate=pub.candidate if operation == "edit_media" else None, payload=payload, started_at=now)
        channel.in_flight = attempt
        channel.lease_until = now + timedelta(seconds=settings.TELEGRAM_TIMEOUT_SECONDS + 60)
        channel.save(update_fields=("in_flight", "lease_until"))
        pub.state = Publication.State.SENDING
        pub.save(update_fields=("state", "updated_at"))
        _audit(pub, "operation_pending", attempt=attempt, detail={"operation": operation})
    result, error, uncertain = None, "", False
    retry_after = 60
    try:
        result = gateway.execute(operation, channel.target, payload)
        if not isinstance(result, GatewayResult) or not result.message_id or (operation not in SEND_OPERATIONS and result.message_id != pub.message_id):
            raise UncertainGatewayError("Gateway response did not confirm the expected message identity")
    except GatewayError as exc:
        error = redact_diagnostic(str(exc).replace(settings.TELEGRAM_BOT_TOKEN, "[redacted]") if settings.TELEGRAM_BOT_TOKEN else exc)
        uncertain = isinstance(exc, UncertainGatewayError)
        retry_after = exc.retry_after
    except Exception:
        error, uncertain = "Unexpected gateway failure after reservation; outcome requires reconciliation", True
    with transaction.atomic():
        channel = PublicationChannel.objects.select_for_update().get(pk=channel.pk)
        attempt = PublicationAttempt.objects.select_for_update().get(pk=attempt.pk)
        pub = Publication.objects.select_for_update().get(pk=pub.pk)
        if attempt.state != PublicationAttempt.State.PENDING:
            if result:
                attempt.response = {"late_message_id": result.message_id, "chat_id": result.chat_id}
                attempt.save(update_fields=("response",))
            return pub
        if error:
            if uncertain:
                _mark_uncertain(attempt, error)
                pub.refresh_from_db()
            else:
                attempt.state = PublicationAttempt.State.FAILED
                attempt.error = error
                attempt.finished_at = now
                attempt.save(update_fields=("state", "error", "finished_at"))
                failures = pub.attempts.filter(state=PublicationAttempt.State.FAILED).count()
                pub.state = Publication.State.RETRY_WAIT
                pub.retry_due_at = now + timedelta(seconds=max(retry_after, min(60 * 2 ** min(failures - 1, 8), 21600)))
                pub.last_error = error
                pub.save(update_fields=("state", "retry_due_at", "last_error", "updated_at"))
                _audit(pub, "operation_failed", attempt=attempt, detail={"retry_due_at": pub.retry_due_at.isoformat()})
        else:
            attempt.state = PublicationAttempt.State.SUCCEEDED
            attempt.response = {"message_id": result.message_id, "chat_id": result.chat_id, "message_url": result.message_url, "media": result.media or {}, "correction_notice": correction_notice,
                "caption_text": result.caption_text, "caption_entities": list(result.caption_entities)}
            attempt.finished_at = now
            attempt.save(update_fields=("state", "response", "finished_at"))
            _apply_success(pub, attempt, result, now)
        if channel.in_flight_id == attempt.pk:
            channel.in_flight = None
            channel.lease_until = None
            channel.save(update_fields=("in_flight", "lease_until"))
    if error and operation != "notify":
        _notify_failure(pub, attempt, gateway=gateway, now=now)
    if not error and operation == "edit_media" and correction_notice:
        ensure_correction(pub, attempt, gateway=gateway, now=now)
    return pub


def _apply_success(pub, attempt, result, now):
    if attempt.operation in SEND_OPERATIONS:
        pub.message_id, pub.message_url = result.message_id, result.message_url
        pub.published_at = now
    if attempt.operation == "edit_media":
        pub.candidate = attempt.candidate
    pub.state = Publication.State.DELETED if attempt.operation == "delete" else Publication.State.PUBLISHED
    pub.last_error, pub.retry_due_at = "", None
    if "caption_html" in attempt.payload and attempt.operation != "delete":
        pub.caption_html = attempt.payload["caption_html"]
    if "context" in attempt.payload:
        pub.context = attempt.payload["context"]
    if pub.kind == Publication.Kind.CORRECTION and attempt.operation == "reply":
        from operations.services import active_correction_delete_seconds
        seconds = active_correction_delete_seconds(settings.PUBLICATION_CORRECTION_DELETE_SECONDS)
        pub.delete_due_at = now + timedelta(seconds=seconds)
    pub.save()
    _audit(pub, "operation_succeeded", attempt=attempt, detail={"message_id": result.message_id})


def _notify_failure(pub, attempt, *, gateway, now):
    target = settings.TELEGRAM_REVIEW_CHAT_ID
    if not target or guard_target(target) == pub.channel.target:
        _audit(pub, "notification_not_configured", attempt=attempt)
        return
    channel = _channel(target)
    notice, _ = Publication.objects.get_or_create(channel=channel, identity_key=f"notify:{attempt.pk}", defaults={"kind": Publication.Kind.NOTIFICATION, "context": {"publication_id": pub.pk, "attempt_id": attempt.pk}, "caption_html": f"Publication {pub.pk}: {escape(pub.state)}. Inspect its recorded attempt and reconciliation in the authenticated admin."})
    perform(notice, "notify", "initial", {"caption_html": notice.caption_html}, gateway=gateway, now=now)


def upgrade_single(pub, candidate, *, gateway, now=None, correction_notice=True):
    candidate = require_ready(candidate)
    pub.refresh_from_db()
    if not pub.message_id or candidate.track_id != pub.track_id:
        raise PublicationError("An upgrade requires the same canonical track and a published message")
    old = pub.candidate
    if old.pk == candidate.pk:
        return pub
    if candidate.quality_rank.get("transcoded_from_lossy"):
        raise PublicationError("A known lossy transcode cannot replace an existing recording as an upgrade")
    better = quality_improved(candidate.quality_rank, old.quality_rank)
    tagging_changed = candidate.preparation_report != old.preparation_report
    if not better and not tagging_changed:
        raise PublicationError("Candidate does not provide a measured quality or recorded tag improvement")
    return perform(pub, "edit_media", f"upgrade:{candidate.pk}", _audio_payload(pub, candidate), gateway=gateway, candidate=candidate, now=now, correction_notice=correction_notice)


def ensure_correction(pub, attempt, *, gateway, now=None):
    if attempt.operation != "edit_media" or attempt.state != PublicationAttempt.State.SUCCEEDED:
        return
    if attempt.response.get("correction_notice", True) is False:
        return
    # Historical archive policy edits predate the durable flag. Their recorded
    # identical-original binding also excludes a later maintenance reply.
    if (pub.kind == Publication.Kind.ARCHIVE and attempt.candidate_id and attempt.previous_candidate_id and
            attempt.candidate.provenance.get("policy_retag_of") == attempt.previous_candidate_id and
            attempt.candidate.sha256 == attempt.previous_candidate.sha256):
        return
    notice, _ = Publication.objects.get_or_create(channel=pub.channel, identity_key=f"correction:{pub.pk}:{attempt.operation_key}", defaults={"kind": Publication.Kind.CORRECTION, "original": pub, "caption_html": escape(settings.PUBLICATION_CORRECTION_TEXT), "context": {"reply_to_message_id": pub.message_id}})
    return perform(notice, "reply", "initial", {"caption_html": notice.caption_html, **notice.context}, gateway=gateway, now=now)


def edit_caption(pub, changes, *, gateway, now=None, session_id=None):
    pub.refresh_from_db()
    if not pub.message_id or not pub.template_id:
        raise PublicationError("Caption edit requires a published templated message")
    allowed = {"music_video_url", "spotify_url", "soundcloud_url", "album_post_url", "original_track_post_url", "original_album_post_url"}
    if set(changes) - allowed:
        raise PublicationError("Only verified late link fields may be edited")
    context = {**pub.context}
    for key, value in changes.items():
        context[key] = safe_url(value, channel=key.endswith("post_url"))
        if key == 'album_post_url':
            context['album_intro_confirmed'] = Publication.objects.filter(channel_id=pub.channel_id,kind=Publication.Kind.INTRO,state=Publication.State.PUBLISHED,message_id__isnull=False,message_url=context[key]).exists()
    rendered = render_caption(pub.kind, context, pub.template.config)
    key = "caption:" + hashlib.sha256(rendered.html.encode()).hexdigest()
    return perform(pub, "edit_caption", key, {"caption_html": rendered.html, "context": context}, gateway=gateway, now=now, session_id=session_id)


def reconcile(attempt, *, actor, decision, evidence, message_id=None, remote_chat_id=None, now=None):
    """Operator evidence is required; no automatic history lookup/resend is claimed."""
    if not actor or not actor.is_staff or not evidence.strip():
        raise PublicationError("Reconciliation requires an authenticated staff actor and observed evidence")
    now = now or timezone.now()
    with transaction.atomic():
        channel = PublicationChannel.objects.select_for_update().get(pk=attempt.publication.channel_id)
        attempt = PublicationAttempt.objects.select_for_update().get(pk=attempt.pk)
        record = PublicationReconciliation.objects.select_for_update().get(attempt=attempt)
        pub = Publication.objects.select_for_update().get(pk=attempt.publication_id)
        if record.state != "open":
            return pub
        if decision == "confirmed_success":
            if not message_id or not remote_chat_id or str(remote_chat_id) != channel.target:
                raise PublicationError("Confirm the observed message ID and exact target channel")
            if attempt.operation not in SEND_OPERATIONS and int(message_id) != pub.message_id:
                raise PublicationError("Edit reconciliation must preserve the original message ID")
            from .gateway import message_url
            result = GatewayResult(int(message_id), str(remote_chat_id), message_url(remote_chat_id, int(message_id), channel.target.lstrip("@") if channel.target.startswith("@") else ""))
            attempt.state = PublicationAttempt.State.SUCCEEDED
            attempt.response = {"message_id": result.message_id, "chat_id": result.chat_id, "operator_confirmed": True}
            _apply_success(pub, attempt, result, now)
        elif decision == "confirmed_not_delivered":
            attempt.state = PublicationAttempt.State.FAILED
            pub.state, pub.retry_due_at = Publication.State.RETRY_WAIT, now
            pub.save(update_fields=("state", "retry_due_at", "updated_at"))
        else:
            raise PublicationError("Unsupported reconciliation decision")
        attempt.finished_at = now
        attempt.save(update_fields=("state", "response", "finished_at"))
        record.state, record.decision, record.evidence, record.actor, record.resolved_at = "resolved", decision, redact_diagnostic(evidence), actor, now
        record.save()
        if pub.album_session_id:
            AlbumSession.objects.filter(pk=pub.album_session_id).update(state="retry_wait")
        if channel.in_flight_id == attempt.pk:
            channel.in_flight, channel.lease_until = None, None
            channel.save(update_fields=("in_flight", "lease_until"))
        _audit(pub, "operator_reconciled", attempt=attempt, actor=actor, detail={"decision": decision})
        return pub


def prepare_album(release, target, *, context=None):
    if release.release_type not in {"lp", "ep"} or release.state not in {"identified", "approved"} or not release.source_matches.filter(confidence__gte=90, state__in=CONFIDENT_STATES).exists():
        raise PublicationError("Album requires a confidently typed canonical LP/EP")
    channel = _channel(target)
    with transaction.atomic():
        channel = PublicationChannel.objects.select_for_update().get(pk=channel.pk)
        session, _ = AlbumSession.objects.get_or_create(channel=channel, release=release)
        if session.intro_id and (session.intro.message_id or session.intro.attempts.exists()):
            return session
        if context:
            session.context = {**session.context, **context}
            session.save(update_fields=("context", "updated_at"))
        entries, previous, candidates = [], [], []
        memberships = list(release.release_tracks.select_related("track").order_by("position", "pk"))
        if not memberships:
            raise PublicationError("An album requires a verified ordered track list")
        for member in memberships:
            existing = Publication.objects.filter(channel=channel, track=member.track, message_id__isnull=False).first()
            candidate = best_ready_candidate(member.track)
            if existing:
                previous.append({"title": member.track.official_title, "url": existing.message_url})
                if existing.candidate_id:
                    candidates.append(require_ready(existing.candidate))
            elif candidate:
                candidate = require_ready(candidate)
                candidates.append(candidate)
            else:
                session.state = "waiting_media"
                session.save(update_fields=("state", "updated_at"))
                return session
            entries.append({"track_id": member.track_id, "position": member.position, "candidate_id": candidate.pk if candidate else None, "prior_publication_id": existing.pk if existing else None})
        cover = next((candidate for candidate in candidates if candidate.artwork_path and candidate.release_id == release.pk), None)
        if cover is None:
            album_cover_candidate = MediaCandidate.objects.filter(release=release, state="ready").exclude(artwork_path="").first()
            if album_cover_candidate:
                cover = require_ready(album_cover_candidate)
        if not cover:
            session.state, session.last_error = "waiting_media", "Official validated cover is required before the introduction"
            session.save(update_fields=("state", "last_error", "updated_at"))
            return session
        validate_artwork(_path(cover.artwork_path))
        intro_context = {"title": release.title, "release_type": release.release_type.upper(), "artists": list(release.artist_credits.order_by("position", "pk").values_list("artist__official_name", flat=True)), "features": session.context.get("features", []), "previous_singles": previous}
        for match in release.source_matches.filter(track__isnull=True, confidence__gte=90, state__in=CONFIDENT_STATES).select_related("source_item"):
            item = match.source_item
            if item.platform in {"spotify", "soundcloud"}:
                intro_context.setdefault(f"{item.platform}_url", safe_url(item.canonical_url))
        original = Publication.objects.filter(channel=channel, kind=Publication.Kind.INTRO, release=release.edition_of, message_id__isnull=False).first() if release.edition_of_id else None
        if original:
            intro_context["original_album_post_url"] = original.message_url
        template = session.intro.template if session.intro_id else _template(Publication.Kind.INTRO)
        rendered = render_caption(Publication.Kind.INTRO, intro_context, template.config)
        intro, _ = Publication.objects.get_or_create(channel=channel, identity_key=f"intro:{release.pk}", defaults={"kind": Publication.Kind.INTRO, "release": release, "candidate": cover, "original": original, "template": template, "context": intro_context, "caption_html": rendered.html, "album_session": session})
        if not intro.attempts.exists():
            intro.candidate, intro.context = cover, intro_context
            intro.caption_html = render_caption(Publication.Kind.INTRO, intro_context, intro.template.config).html
            intro.save(update_fields=("candidate", "context", "caption_html", "updated_at"))
        session.intro, session.entries, session.overflow, session.context, session.state = intro, entries, list(rendered.overflow), intro_context, "prepared"
        session.save()
        _audit(intro, "album_prestaged", detail={"ordered_track_ids": [entry["track_id"] for entry in entries]})
        return session


def _album_failure(session, pub, now):
    if pub.state in {Publication.State.RETRY_WAIT, Publication.State.UNCERTAIN}:
        session.state = "uncertain" if pub.state == Publication.State.UNCERTAIN else "retry_wait"
        session.failed_since = session.failed_since or now
        session.last_error = pub.last_error
        session.save(update_fields=("state", "failed_since", "last_error", "updated_at"))
        with transaction.atomic():
            channel = PublicationChannel.objects.select_for_update().get(pk=session.channel_id)
            _release_album_if_expired(channel, now)


def advance_album(session, *, gateway, now=None):
    now = now or timezone.now()
    session.refresh_from_db()
    if session.intro_id and not session.intro.attempts.exists():
        session = prepare_album(session.release, session.channel.target, context=session.context)
    if not session.intro_id or session.state in {"complete", "waiting_media"}:
        return session
    if not session.intro.message_id:
        # Recheck the entire staged snapshot immediately before the first intro call.
        for entry in session.entries:
            if not entry["prior_publication_id"]:
                try:
                    require_ready(MediaCandidate.objects.get(pk=entry["candidate_id"]))
                except PublicationError as exc:
                    session.state, session.last_error = "waiting_media", str(exc)
                    session.save(update_fields=("state", "last_error", "updated_at"))
                    return session
    with transaction.atomic():
        channel = PublicationChannel.objects.select_for_update().get(pk=session.channel_id)
        _release_album_if_expired(channel, now)
        if channel.active_album_id and channel.active_album_id != session.pk:
            return session
        if channel.in_flight_id:
            # perform() handles expired leases below, otherwise leave this cursor alone.
            if not channel.lease_until or channel.lease_until > now:
                return session
        channel.active_album = session
        channel.save(update_fields=("active_album",))
    intro = session.intro
    if not intro.message_id:
        intro = perform(intro, "send_intro", "initial", {"artwork_path": str(_path(intro.candidate.artwork_path)), "caption_html": intro.caption_html, "context": intro.context}, gateway=gateway, candidate=intro.candidate, now=now, session_id=session.pk)
        if intro.state != Publication.State.PUBLISHED:
            _album_failure(session, intro, now)
            return session
    # reserve_audio reads the session's related intro. Refresh its cached value
    # after a first send so the first track links to the confirmed cover post.
    session.intro = intro
    for index, caption in enumerate(session.overflow):
        overflow, _ = Publication.objects.get_or_create(channel=session.channel, identity_key=f"overflow:{session.pk}:{index}", defaults={"kind": Publication.Kind.OVERFLOW, "release": session.release, "album_session": session, "caption_html": caption})
        overflow = perform(overflow, "send_text", "initial", {"caption_html": caption}, gateway=gateway, now=now, session_id=session.pk)
        if overflow.state != Publication.State.PUBLISHED:
            _album_failure(session, overflow, now)
            return session
    while session.cursor < len(session.entries):
        entry = session.entries[session.cursor]
        if entry["prior_publication_id"]:
            prior = Publication.objects.get(pk=entry["prior_publication_id"])
            edit_caption(prior, {"album_post_url": intro.message_url}, gateway=gateway, now=now, session_id=session.pk)
        else:
            candidate = MediaCandidate.objects.get(pk=entry["candidate_id"])
            pub = reserve_audio(candidate, session.channel.target, kind=Publication.Kind.TRACK, album_session=session)
            pub = perform(pub, "send_audio", "initial", _audio_payload(pub), gateway=gateway, candidate=pub.candidate, now=now, session_id=session.pk)
            if pub.state != Publication.State.PUBLISHED:
                _album_failure(session, pub, now)
                return session
        with transaction.atomic():
            locked = AlbumSession.objects.select_for_update().get(pk=session.pk)
            locked.cursor = max(locked.cursor, session.cursor + 1)
            locked.failed_since, locked.last_error, locked.state = None, "", "sending"
            locked.save(update_fields=("cursor", "failed_since", "last_error", "state", "updated_at"))
            session = locked
    with transaction.atomic():
        channel = PublicationChannel.objects.select_for_update().get(pk=session.channel_id)
        session.state = "complete"
        session.save(update_fields=("state", "updated_at"))
        if channel.active_album_id == session.pk:
            channel.active_album = None
            channel.save(update_fields=("active_album",))
    return session


def run_due(*, gateway, now=None):
    now = now or timezone.now()
    for channel_id in PublicationChannel.objects.filter(in_flight__isnull=False, lease_until__lte=now).values_list("pk", flat=True):
        with transaction.atomic():
            channel = PublicationChannel.objects.select_for_update().get(pk=channel_id)
            if channel.in_flight_id and channel.lease_until <= now:
                attempt = PublicationAttempt.objects.get(pk=channel.in_flight_id)
                if attempt.state == PublicationAttempt.State.PENDING:
                    _mark_uncertain(attempt, "Worker lease expired without a recorded response")
                    if attempt.publication.album_session_id:
                        AlbumSession.objects.filter(pk=attempt.publication.album_session_id).update(state="uncertain", failed_since=now)
                channel.in_flight, channel.lease_until = None, None
                channel.save(update_fields=("in_flight", "lease_until"))
    for session in AlbumSession.objects.exclude(state__in=("complete", "uncertain")):
        if not session.intro_id or session.state == "waiting_media":
            session = prepare_album(session.release, session.channel.target)
        try:
            advance_album(session, gateway=gateway, now=now)
        except PublicationError as exc:
            session.state, session.last_error = "waiting_media", str(exc)
            session.failed_since = session.failed_since or now
            session.save(update_fields=("state", "last_error", "failed_since", "updated_at"))
    for pub in Publication.objects.filter(state=Publication.State.PENDING, kind__in=AUDIO_KINDS, album_session__isnull=True):
        try:
            perform(pub, "send_audio", "initial", _audio_payload(pub), gateway=gateway, candidate=pub.candidate, now=now)
        except PublicationError as exc:
            pub.state, pub.last_error = Publication.State.REVIEW, str(exc)
            pub.save(update_fields=("state", "last_error", "updated_at"))
            _audit(pub, "local_media_review_required")
    for pub in Publication.objects.filter(state=Publication.State.RETRY_WAIT, retry_due_at__lte=now, album_session__isnull=True):
        attempt = pub.attempts.filter(state=PublicationAttempt.State.FAILED).order_by("-pk").first()
        if attempt:
            try:
                perform(pub, attempt.operation, attempt.operation_key, attempt.payload, gateway=gateway, candidate=attempt.candidate, now=now)
            except PublicationError as exc:
                pub.state, pub.last_error = Publication.State.REVIEW, str(exc)
                pub.save(update_fields=("state", "last_error", "updated_at"))
                _audit(pub, "local_media_review_required")
    for pub in Publication.objects.filter(kind=Publication.Kind.CORRECTION, state=Publication.State.PUBLISHED, delete_due_at__lte=now):
        perform(pub, "delete", "scheduled-delete", {}, gateway=gateway, now=now)
    for attempt in PublicationAttempt.objects.filter(operation="edit_media", state=PublicationAttempt.State.SUCCEEDED).select_related("publication"):
        ensure_correction(attempt.publication, attempt, gateway=gateway, now=now)
