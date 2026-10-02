from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils.html import format_html

from .forms import ManualMediaUploadForm, MediaCandidateAdminForm
from .models import MediaAttempt, MediaAuditEvent, MediaCandidate
from .services import MediaRequestError, process_manual_upload
from .providers import redact_diagnostic
import re
from operations.services import audit, safe_audit_json


@admin.register(MediaCandidate)
class MediaCandidateAdmin(admin.ModelAdmin):
    form = MediaCandidateAdminForm
    list_display = ("track", "release", "provider", "state", "preparation_state", "file_size_bytes", "attempt_count", "created_at")
    list_filter = ("state", "provider", "preparation_state", "artwork_state")
    search_fields = ("track__official_title", "release__title", "source_match__source_item__native_item_id", "sha256")
    readonly_fields = (
        "track", "release", "state", "preparation_state", "artwork_state", "attempt_count",
        "last_attempt_at", "retry_due_at", "last_outcome", "safe_diagnostic", "candidate_stored",
        "prepared_stored", "artwork_stored", "sha256", "file_size_bytes", "expected_duration_seconds",
        "observed_facts", "duration_comparison", "validation_report", "preparation_report",
        "quality_rank", "created_by", "created_at", "updated_at",
    )
    fields = ("source_match", "provider", *readonly_fields)
    change_form_template = "admin/media_pipeline/mediacandidate/change_form.html"

    def get_urls(self):
        custom = [
            path("<int:object_id>/manual-upload/", self.admin_site.admin_view(self.manual_upload_view), name="media_pipeline_mediacandidate_manual_upload"),
        ]
        return custom + super().get_urls()

    def save_model(self, request, obj, form, change):
        obj.track = obj.source_match.track
        obj.release = obj.source_match.release
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Safe diagnostic")
    def safe_diagnostic(self, obj):
        value = redact_diagnostic(obj.last_error)
        value = re.sub(r"(?:[A-Za-z]:\\[^\s]+|/(?:[^\s/]+/)*[^\s]*)", "[path omitted]", value)
        return value

    @admin.display(boolean=True, description="Candidate stored")
    def candidate_stored(self, obj): return bool(obj.candidate_path)

    @admin.display(boolean=True, description="Prepared copy stored")
    def prepared_stored(self, obj): return bool(obj.prepared_path)

    @admin.display(boolean=True, description="Artwork stored")
    def artwork_stored(self, obj): return bool(obj.artwork_path)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        candidate = get_object_or_404(MediaCandidate, pk=object_id)
        context = {**(extra_context or {}), "manual_upload_url": reverse("admin:media_pipeline_mediacandidate_manual_upload", args=(candidate.pk,))}
        return super().change_view(request, object_id, form_url, extra_context=context)

    def manual_upload_view(self, request, object_id):
        candidate = get_object_or_404(MediaCandidate.objects.select_related("track", "release", "source_match"), pk=object_id)
        if not self.has_change_permission(request, candidate):
            raise PermissionDenied
        if candidate.state == MediaCandidate.State.READY:
            self.message_user(request, "Ready media candidates are immutable. Create another candidate for comparison.", level=messages.ERROR)
            return HttpResponseRedirect(reverse("admin:media_pipeline_mediacandidate_change", args=(candidate.pk,)))
        form = ManualMediaUploadForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            result = process_manual_upload(
                candidate,
                form.cleaned_data["audio_file"],
                actor=request.user,
                artwork_upload=form.cleaned_data.get("artwork_file"),
                artwork_source_url=form.cleaned_data.get("artwork_source_url", ""),
            )
            if result.state == MediaCandidate.State.READY:
                self.message_user(request, "Upload validated and prepared; no publication was attempted.", level=messages.SUCCESS)
            else:
                self.message_user(request, f"Upload recorded as {result.get_state_display()}: {result.last_error}", level=messages.WARNING)
            audit(request.user, "media_manual_upload", result, after={"state": result.state, "attempt_count": result.attempt_count, "outcome": result.last_outcome, "file_size_bytes": result.file_size_bytes})
            return HttpResponseRedirect(reverse("admin:media_pipeline_mediacandidate_change", args=(candidate.pk,)))
        return render(request, "admin/media_pipeline/mediacandidate/manual_upload.html", {**self.admin_site.each_context(request), "opts": self.model._meta, "candidate": candidate, "form": form}, status=400 if request.method == "POST" and form.errors else 200)

    @admin.display(description="Upload validated audio")
    def manual_upload_link(self, obj):
        if obj.state == MediaCandidate.State.READY:
            return "Ready candidate is immutable"
        return format_html('<a class="button" href="{}">Upload audio</a>', reverse("admin:media_pipeline_mediacandidate_manual_upload", args=(obj.pk,)))


@admin.register(MediaAttempt)
class MediaAttemptAdmin(admin.ModelAdmin):
    list_display = ("candidate", "provider", "state", "started_at", "finished_at", "outcome")
    list_filter = ("provider", "state")
    readonly_fields = ("candidate", "provider", "state", "started_at", "finished_at", "outcome", "safe_diagnostic")
    fields = readonly_fields

    @admin.display(description="Safe diagnostic")
    def safe_diagnostic(self, obj):
        value = redact_diagnostic(obj.error)
        return re.sub(r"(?:[A-Za-z]:\\[^\s]+|/(?:[^\s/]+/)*[^\s]*)", "[path omitted]", value)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(MediaAuditEvent)
class MediaAuditEventAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "candidate", "actor", "action")
    list_filter = ("action",)
    readonly_fields = tuple(field.name for field in MediaAuditEvent._meta.fields if field.name != "detail") + ("safe_detail",)

    @admin.display(description="Redacted event detail")
    def safe_detail(self, event):
        return safe_audit_json(event.detail)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
