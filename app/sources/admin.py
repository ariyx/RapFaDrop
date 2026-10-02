from django.contrib import admin
from django.contrib import messages
from django import forms
import re
from media_pipeline.providers import redact_diagnostic

from .models import Artist, ArtistSource, BaselineRun, SourceAuditEvent, SourceItem
from .adapters import SpotifyAdapter
from operations.services import audit, safe_audit_json


class ArtistSourceAdminForm(forms.ModelForm):
    class Meta:
        model = ArtistSource
        exclude = ("last_error",)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("enabled") and cleaned.get("verification") != ArtistSource.Verification.VERIFIED:
            self.add_error("enabled", "Only a verified source can be enabled.")
        return cleaned


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ("official_name", "aliases_display", "enabled", "source_count")
    search_fields = ("official_name",)
    list_filter = ("enabled",)

    @admin.display(description="Sources")
    def source_count(self, artist):
        return artist.sources.count()

    @admin.display(description="Aliases")
    def aliases_display(self, artist):
        return ", ".join(artist.aliases or [])

    def save_model(self, request, obj, form, change):
        old = Artist.objects.get(pk=obj.pk) if change else None
        old_enabled = old.enabled if old else None
        super().save_model(request, obj, form, change)
        changes = {}
        if old and old.official_name != obj.official_name:
            changes["official_name"] = {"from": old.official_name, "to": obj.official_name}
        if old and old.aliases != obj.aliases:
            changes["aliases"] = {"from": old.aliases, "to": obj.aliases}
        if obj.enabled and old_enabled is False:
            from django.utils import timezone
            obj.sources.filter(enabled=True, verification=ArtistSource.Verification.VERIFIED).update(next_poll_at=timezone.now())
        if change and old_enabled != obj.enabled:
            SourceAuditEvent.objects.create(artist=obj, actor=request.user, event_type="artist_configured", detail={"enabled_from": old_enabled, "enabled_to": obj.enabled})
            changes["enabled"] = {"from": old_enabled, "to": obj.enabled}
        if changes:
            audit(request.user, "artist_updated", obj, {key: value["from"] for key, value in changes.items()}, {key: value["to"] for key, value in changes.items()})
        elif not change:
            SourceAuditEvent.objects.create(artist=obj, actor=request.user, event_type="artist_created")
            audit(request.user, "artist_created", obj, after={"official_name": obj.official_name, "aliases": obj.aliases})


@admin.register(ArtistSource)
class ArtistSourceAdmin(admin.ModelAdmin):
    form = ArtistSourceAdminForm
    list_display = ("artist", "platform", "native_profile_id", "enabled", "verification", "baseline_completed_at", "next_poll_at", "consecutive_failures", "release_polling_available")
    list_filter = ("platform", "enabled", "verification")
    search_fields = ("artist__official_name", "native_profile_id", "canonical_url", "last_error")
    readonly_fields = ("baseline_started_at", "baseline_completed_at", "last_success_at", "last_error_at", "safe_error_recorded", "consecutive_failures")
    exclude = ("last_error",)

    @admin.display(description="Last error (redacted)")
    def safe_error_recorded(self, source):
        if not source.last_error:
            return "—"
        value = redact_diagnostic(source.last_error)
        return re.sub(r"(?:[A-Za-z]:\\[^\s]+|/(?:[^\s/]+/)*[^\s]*)", "[path omitted]", value)

    @admin.display(description="Release polling")
    def release_polling_available(self, source):
        return "Implemented; candidate profile unprobed" if source.release_polling_available else SpotifyAdapter.status()

    def save_model(self, request, obj, form, change):
        old = None
        if change:
            old = ArtistSource.objects.get(pk=obj.pk)
        if obj.enabled and not obj.baseline_completed_at:
            self.message_user(request, "Warning: baseline is not complete; source monitoring may baseline existing history before new-release polling.", level=messages.WARNING)
        if obj.enabled and obj.verification == ArtistSource.Verification.VERIFIED and (not old or old.enabled != obj.enabled or old.verification != obj.verification):
            from django.utils import timezone
            obj.next_poll_at = timezone.now()
        super().save_model(request, obj, form, change)
        changes = {}
        if old:
            for field in ("enabled", "verification", "native_profile_id", "canonical_url"):
                before, after = getattr(old, field), getattr(obj, field)
                if before != after:
                    changes[field] = {"from": str(before), "to": str(after)}
        if changes:
            SourceAuditEvent.objects.create(source=obj, artist=obj.artist, actor=request.user, event_type="source_configured", detail=changes)
            audit(request.user, "source_configured", obj, {field: change["from"] for field, change in changes.items()}, {field: change["to"] for field, change in changes.items()})


@admin.register(SourceItem)
class SourceItemAdmin(admin.ModelAdmin):
    list_display = ("platform", "native_item_id", "title", "source", "source_release_at", "first_observed_at", "from_baseline")
    list_filter = ("platform", "from_baseline")
    search_fields = ("native_item_id", "title", "source__artist__official_name")
    readonly_fields = tuple(field.name for field in SourceItem._meta.fields if field.name not in {"metadata", "sanitized_raw_data"})
    exclude = ("metadata", "sanitized_raw_data")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(BaselineRun)
class BaselineRunAdmin(admin.ModelAdmin):
    list_display = ("source", "status", "started_at", "completed_at", "item_count", "safe_error")
    readonly_fields = tuple(field.name for field in BaselineRun._meta.fields if field.name != "error") + ("safe_error",)
    exclude = ("error",)

    @admin.display(description="Redacted error")
    def safe_error(self, obj):
        if not obj.error: return ""
        value = redact_diagnostic(obj.error)
        return re.sub(r"(?:[A-Za-z]:\\[^\s]+|/(?:[^\s/]+/)*[^\s]*)", "[path omitted]", value)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SourceAuditEvent)
class SourceAuditEventAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "event_type", "artist", "source", "actor")
    list_filter = ("event_type",)
    readonly_fields = tuple(field.name for field in SourceAuditEvent._meta.fields if field.name != "detail") + ("safe_detail",)

    @admin.display(description="Redacted event detail")
    def safe_detail(self, event):
        return safe_audit_json(event.detail)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
