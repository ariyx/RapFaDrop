from django.contrib import admin
import re
from media_pipeline.providers import redact_diagnostic

from .models import AlbumSession, CaptionTemplate, Publication, PublicationAttempt, PublicationAuditEvent, PublicationChannel, PublicationReconciliation
from .forms import CaptionTemplateForm
from operations.services import audit, safe_audit_json


class ReadOnlyAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Publication)
class PublicationAdmin(ReadOnlyAdmin):
    list_display = ("id", "kind", "track", "release", "state", "message_id", "retry_due_at")
    list_filter = ("state", "kind", "channel")
    search_fields = ("track__official_title", "release__title", "identity_key")
    exclude = ("last_error",)

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields if field.name != "last_error") + ("safe_error",)

    def safe_error(self, obj):
        value = redact_diagnostic(obj.last_error)
        return re.sub(r"(?:[A-Za-z]:\\[^\s]+|/(?:[^\s/]+/)*[^\s]*)", "[path omitted]", value)


@admin.register(PublicationReconciliation)
class ReconciliationAdmin(ReadOnlyAdmin):
    list_display = ("attempt", "state", "decision", "actor", "created_at")
    list_filter = ("state",)


@admin.register(CaptionTemplate)
class TemplateAdmin(admin.ModelAdmin):
    form = CaptionTemplateForm
    list_display = ("kind", "version", "enabled")

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields) if obj else ()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        audit(request.user, "caption_template_created", obj, after={"kind": obj.kind, "version": obj.version, "enabled": obj.enabled})

    def has_delete_permission(self, request, obj=None):
        return not (obj and obj.publications.exists())


for model in (PublicationAttempt, PublicationAuditEvent, AlbumSession, PublicationChannel):
    if model is not PublicationAttempt:
        admin.site.register(model, ReadOnlyAdmin)


@admin.register(PublicationAttempt)
class PublicationAttemptAdmin(ReadOnlyAdmin):
    list_display = ("publication", "operation", "state", "started_at", "finished_at")
    list_filter = ("operation", "state")
    readonly_fields = ("publication", "operation", "operation_key", "state", "candidate", "previous_candidate", "error_redacted", "started_at", "finished_at")
    fields = readonly_fields

    @admin.display(description="Redacted diagnostic")
    def error_redacted(self, obj):
        value = redact_diagnostic(obj.error)
        return re.sub(r"(?:[A-Za-z]:\\[^\s]+|/(?:[^\s/]+/)*[^\s]*)", "[path omitted]", value)


class PublicationAuditAdmin(ReadOnlyAdmin):
    readonly_fields = tuple(field.name for field in PublicationAuditEvent._meta.fields if field.name != "detail") + ("safe_detail",)

    @admin.display(description="Redacted event detail")
    def safe_detail(self, event):
        return safe_audit_json(event.detail)


admin.site.unregister(PublicationAuditEvent)
admin.site.register(PublicationAuditEvent, PublicationAuditAdmin)
