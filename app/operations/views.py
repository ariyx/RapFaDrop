from functools import wraps
import re

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from media_pipeline.models import MediaCandidate, MediaAttempt
from media_pipeline.services import MediaRequestError, retry_candidate
from publication.models import AlbumSession, CaptionTemplate, Publication, PublicationAttempt, PublicationReconciliation
from publication.services import PublicationError, schedule_publication_retry
from releases.models import IdentityAuditEvent, ProcessingQueueItem, ReviewItem
from releases.services import resolve_review, retry_queue_item
from sources.models import Artist, ArtistSource, BaselineRun, SourceAuditEvent

from .forms import OperatorSettingsForm, TemplatePreviewForm
from .models import OperatorActionRequest, OperatorAuditEvent, OperatorSettings
from .services import audit, has_operator_access, request_source_action


def operator_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not has_operator_access(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


@operator_required
def dashboard(request):
    from sources.adapters import SpotifyAdapter
    from releases.models import FreshProviderBackoff
    fresh_alerts = FreshProviderBackoff.objects.filter(due_at__gt=timezone.now())
    q = request.GET.get("q", "").strip()
    artists = Artist.objects.prefetch_related("sources").order_by("official_name")
    platform = request.GET.get("platform", "")
    verification = request.GET.get("verification", "")
    enabled = request.GET.get("enabled", "")
    if q:
        artists = [a for a in artists if q.casefold() in a.official_name.casefold() or any(q.casefold() in str(alias).casefold() for alias in (a.aliases or []))]
    if platform or verification or enabled:
        artists = [a for a in artists if any((not platform or s.platform == platform) and (not verification or s.verification == verification) and (not enabled or s.enabled == (enabled == "true")) for s in a.sources.all())]
    ready_deltas, publish_deltas = [], []
    for candidate in MediaCandidate.objects.filter(state=MediaCandidate.State.READY).select_related("track").prefetch_related("track__source_matches__source_item"):
        observed = min((match.source_item.first_observed_at for match in candidate.track.source_matches.all()), default=None)
        if observed:
            ready_deltas.append(max(0, int((candidate.updated_at - observed).total_seconds())))
    for publication in Publication.objects.filter(state=Publication.State.PUBLISHED, published_at__isnull=False, track__isnull=False).select_related("track").prefetch_related("track__source_matches__source_item"):
        observed = min((match.source_item.first_observed_at for match in publication.track.source_matches.all()), default=None)
        if observed:
            publish_deltas.append(max(0, int((publication.published_at - observed).total_seconds())))
    metrics = {
        "source_success": ArtistSource.objects.filter(last_success_at__isnull=False).count(),
        "source_failure": ArtistSource.objects.filter(consecutive_failures__gt=0).count(),
        "open_reviews": ReviewItem.objects.filter(state__in=("open", "requeued")).count(),
        "queue": list(ProcessingQueueItem.objects.values("state").annotate(count=Count("pk")).order_by("state")),
        "media": list(MediaAttempt.objects.values("provider", "state").annotate(count=Count("pk")).order_by("provider", "state")),
        "published": Publication.objects.filter(state="published").count(),
        "publication_attempts": PublicationAttempt.objects.count(),
        "reconciliations": PublicationReconciliation.objects.filter(state="open").count(),
        "album_sessions": list(AlbumSession.objects.values("state").annotate(count=Count("pk")).order_by("state")),
        "avg_ready_seconds": round(sum(ready_deltas) / len(ready_deltas)) if ready_deltas else None,
        "avg_published_seconds": round(sum(publish_deltas) / len(publish_deltas)) if publish_deltas else None,
    }
    from django.contrib.auth import get_user_model
    from .services import OPERATOR_GROUP
    admins = get_user_model().objects.filter(is_staff=True, groups__name=OPERATOR_GROUP).distinct().order_by("username")
    return render(request, "operations/dashboard.html", {"fresh_alerts":fresh_alerts, "spotify_discovery_status": SpotifyAdapter.status(), "artists": artists, "query": q, "platform": platform, "verification": verification, "enabled": enabled, "metrics": metrics, "requests": OperatorActionRequest.objects.select_related("source", "actor")[:10], "admins": admins, "queue_items": ProcessingQueueItem.objects.exclude(state="complete").order_by("due_at")[:30], "media_candidates": MediaCandidate.objects.exclude(state="ready")[:20], "retry_publications": Publication.objects.filter(state=Publication.State.RETRY_WAIT).order_by("retry_due_at")[:20]})


@operator_required
def source_action(request, source_id, action):
    if request.method != "POST":
        raise PermissionDenied
    source = get_object_or_404(ArtistSource.objects.select_related("artist"), pk=source_id)
    before = {"verification": source.verification, "enabled": source.enabled, "baseline_completed": bool(source.baseline_completed_at)}
    note = request.POST.get("notes", "")[:500].strip()
    if action in {"verify", "reject"} and not note:
        messages.error(request, "Record a short evidence note before verifying or rejecting this profile.")
        return redirect("operations:dashboard")
    try:
        if action == "verify":
            source.verification = ArtistSource.Verification.VERIFIED
        elif action == "reject":
            source.verification = ArtistSource.Verification.UNAVAILABLE
            source.enabled = False
        elif action == "enable":
            if source.verification != ArtistSource.Verification.VERIFIED:
                messages.warning(request, "Source must be verified before it can be enabled.")
                return redirect("operations:dashboard")
            if not source.baseline_completed_at:
                messages.warning(request, "Source enabled with warning: baseline is not complete; monitoring must establish a baseline first.")
            source.enabled = True
            if not source.artist.enabled:
                source.artist.enabled = True
                source.artist.save(update_fields=("enabled", "updated_at"))
        elif action == "disable":
            source.enabled = False
        elif action in {"poll", "baseline"}:
            request_source_action(request.user, source, action)
            messages.success(request, f"{action.title()} request recorded; no provider request was run.")
            return redirect("operations:dashboard")
        else:
            raise PermissionDenied
        source.save(update_fields=("verification", "enabled", "updated_at"))
        after = {"verification": source.verification, "enabled": source.enabled, "baseline_completed": bool(source.baseline_completed_at)}
        if re.search(r"https?://|token=|signature=|sig=", note, re.I):
            note = "Evidence reference recorded (URL/query omitted)"
        audit(request.user, f"source_{action}", source, before, {**after, "evidence_or_note": note})
        SourceAuditEvent.objects.create(source=source, artist=source.artist, actor=request.user, event_type=f"operator_{action}", detail={"before": before, "after": after, "evidence_or_note": note})
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("operations:dashboard")


@operator_required
def reviews(request):
    queryset = ReviewItem.objects.select_related("source_item__source__artist", "source_match__release", "source_match__track").order_by("state", "-created_at")
    state = request.GET.get("state")
    if state:
        queryset = queryset.filter(state=state)
    from releases.models import CanonicalRelease, Track
    return render(request, "operations/reviews.html", {"reviews": queryset[:200], "actions": ("approve", "reject", "correct", "requeue"), "releases": CanonicalRelease.objects.order_by("title")[:200], "tracks": Track.objects.order_by("official_title")[:300]})


@operator_required
def review_action(request, review_id, action):
    if request.method != "POST":
        raise PermissionDenied
    review = get_object_or_404(ReviewItem.objects.select_related("source_match", "source_item"), pk=review_id)
    before = {"state": review.state, "action": review.admin_action}
    try:
        from releases.models import CanonicalRelease, Track
        release_id, track_id = request.POST.get("release_id"), request.POST.get("track_id")
        release = CanonicalRelease.objects.filter(pk=release_id).first() if release_id else review.resolved_release
        track = Track.objects.filter(pk=track_id).first() if track_id else review.resolved_track
        resolve_review(review, action, actor=request.user, release=release, track=track, resolution=request.POST.get("resolution", "")[:1000])
    except (ValueError, ValidationError) as exc:
        messages.error(request, str(exc))
        return redirect("operations:reviews")
    review.refresh_from_db()
    audit(request.user, f"review_{action}", review, before, {"state": review.state, "action": review.admin_action})
    return redirect("operations:reviews")


@operator_required
def settings_view(request):
    from django.conf import settings
    obj, _ = OperatorSettings.objects.get_or_create(pk=1, defaults={"tag_fields": sorted(settings.MEDIA_CHANNEL_TAG_FIELDS), "correction_delete_seconds": settings.PUBLICATION_CORRECTION_DELETE_SECONDS})
    form = OperatorSettingsForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        old = {"tag_fields": obj.tag_fields, "correction_delete_seconds": obj.correction_delete_seconds, "notification_mode": obj.notification_mode, "notification_target": obj.notification_target, "version": obj.version}
        updated = form.save(commit=False)
        updated.version += 1
        updated.updated_by = request.user
        updated.pk = 1
        updated.save()
        audit(request.user, "settings_updated", updated, old, {"tag_fields": updated.tag_fields, "correction_delete_seconds": updated.correction_delete_seconds, "notification_mode": updated.notification_mode, "notification_target": updated.notification_target, "version": updated.version})
        messages.success(request, "Settings saved as a new version.")
        return redirect("operations:settings")
    return render(request, "operations/settings.html", {"form": form, "obj": obj})


@operator_required
def template_preview(request):
    form = TemplatePreviewForm(request.POST or None)
    result = None
    if request.method == "POST" and form.is_valid():
        result = form.preview()
        template = form.cleaned_data["template"]
        template.previewed_at = timezone.now()
        template.previewed_by = request.user
        template.save(update_fields=("previewed_at", "previewed_by"))
        audit(request.user, "caption_template_previewed", template, after={"kind": template.kind, "version": template.version, "omitted_rows": list(result.omitted_rows)})
    previewed_template = form.cleaned_data["template"] if result and form.is_valid() else None
    return render(request, "operations/template_preview.html", {"form": form, "result": result, "previewed_template": previewed_template})


@operator_required
def template_activate(request, template_id):
    if request.method != "POST":
        raise PermissionDenied
    from django.db import transaction
    template = get_object_or_404(CaptionTemplate, pk=template_id)
    if not template.previewed_at:
        messages.error(request, "Preview this template successfully before activation.")
        return redirect("operations:template_preview")
    with transaction.atomic():
        locked = CaptionTemplate.objects.select_for_update().get(pk=template.pk)
        for previous in CaptionTemplate.objects.select_for_update().filter(kind=locked.kind, enabled=True).exclude(pk=locked.pk):
            before_previous = {"enabled": previous.enabled, "kind": previous.kind, "version": previous.version}
            previous.enabled = False
            previous.save(update_fields=("enabled",))
            audit(request.user, "caption_template_deactivated", previous, before_previous, {"enabled": False, "kind": previous.kind, "version": previous.version})
        before = {"enabled": locked.enabled, "kind": locked.kind, "version": locked.version}
        locked.enabled = True
        locked.save(update_fields=("enabled",))
        audit(request.user, "caption_template_activated", locked, before, {"enabled": True, "kind": locked.kind, "version": locked.version})
    messages.success(request, f"Activated {locked}.")
    return redirect("operations:template_preview")


@operator_required
def password_reset(request, user_id):
    User = get_user_model()
    from .services import OPERATOR_GROUP
    target = get_object_or_404(User, pk=user_id, is_staff=True, groups__name=OPERATOR_GROUP)
    if target.pk == request.user.pk:
        raise PermissionDenied
    if request.method == "POST":
        password = request.POST.get("new_password", "")
        try:
            validate_password(password, target)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            target.set_password(password)
            target.save(update_fields=("password",))
            audit(request.user, "admin_password_reset", target, after={"target_user_id": target.pk})
            messages.success(request, "Password reset. The password is not retained in audit data.")
            return redirect("operations:dashboard")
    return render(request, "operations/password_reset.html", {"target": target})


@operator_required
def queue_retry(request, queue_id):
    if request.method != "POST": raise PermissionDenied
    item = get_object_or_404(ProcessingQueueItem, pk=queue_id)
    before = {"state": item.state, "attempt_count": item.attempt_count, "due_at": item.due_at.isoformat()}
    if item.state not in {ProcessingQueueItem.State.PENDING, ProcessingQueueItem.State.RETRY_WAIT}:
        messages.error(request, "Only pending or retry-wait items can be scheduled again.")
        return redirect("operations:dashboard")
    updated = retry_queue_item(item, "Operator requested retry")
    audit(request.user, "queue_retry_requested", updated, before, {"state": updated.state, "attempt_count": updated.attempt_count, "due_at": updated.due_at.isoformat()})
    return redirect("operations:dashboard")


@operator_required
def media_retry(request, candidate_id):
    if request.method != "POST":
        raise PermissionDenied
    candidate = get_object_or_404(MediaCandidate, pk=candidate_id)
    before = {"state": candidate.state, "attempt_count": candidate.attempt_count}
    try:
        result = retry_candidate(candidate)
    except MediaRequestError as exc:
        messages.error(request, str(exc))
        return redirect("/admin/media_pipeline/mediacandidate/")
    audit(request.user, "media_retry", result, before, {"state": result.state, "attempt_count": result.attempt_count, "outcome": result.last_outcome})
    return redirect("/admin/media_pipeline/mediacandidate/")


@operator_required
def publication_retry(request, publication_id):
    if request.method != "POST":
        raise PermissionDenied
    publication = get_object_or_404(Publication, pk=publication_id)
    before = {"state": publication.state, "retry_due_at": publication.retry_due_at.isoformat() if publication.retry_due_at else None}
    try:
        updated = schedule_publication_retry(publication, actor=request.user)
    except PublicationError as exc:
        messages.error(request, str(exc))
        return redirect("operations:dashboard")
    audit(request.user, "publication_retry_requested", updated, before, {"state": updated.state, "retry_due_at": updated.retry_due_at.isoformat()})
    messages.success(request, "Retry scheduled through the publication service; no Telegram call was made by this request.")
    return redirect("operations:dashboard")
