from django.contrib import admin

from .models import AlbumSession, CaptionTemplate, Publication, PublicationAttempt, PublicationAuditEvent, PublicationChannel, PublicationReconciliation


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


@admin.register(PublicationReconciliation)
class ReconciliationAdmin(ReadOnlyAdmin):
    list_display = ("attempt", "state", "decision", "actor", "created_at")
    list_filter = ("state",)


@admin.register(CaptionTemplate)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("kind", "version", "enabled")

    def get_readonly_fields(self, request, obj=None):
        return ("kind", "version", "config") if obj and obj.publications.exists() else ()

    def has_delete_permission(self, request, obj=None):
        return not (obj and obj.publications.exists())


for model in (PublicationAttempt, PublicationAuditEvent, AlbumSession, PublicationChannel):
    admin.site.register(model, ReadOnlyAdmin)
