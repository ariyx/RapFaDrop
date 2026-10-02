from django.contrib import admin

from .models import OperatorActionRequest, OperatorAuditEvent, OperatorSettings


class ReadOnlyAdmin(admin.ModelAdmin):
    readonly_fields = tuple(field.name for field in OperatorAuditEvent._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OperatorAuditEvent)
class OperatorAuditAdmin(ReadOnlyAdmin):
    list_display = ("created_at", "actor", "action", "object_type", "object_id", "correlation_id")
    search_fields = ("action", "object_type", "object_id", "actor__username")


@admin.register(OperatorActionRequest)
class OperatorRequestAdmin(ReadOnlyAdmin):
    readonly_fields = tuple(field.name for field in OperatorActionRequest._meta.fields)
    list_display = ("created_at", "actor", "action", "source", "state", "correlation_id")
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(OperatorSettings)
class OperatorSettingsAdmin(admin.ModelAdmin):
    readonly_fields = tuple(field.name for field in OperatorSettings._meta.fields)
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
