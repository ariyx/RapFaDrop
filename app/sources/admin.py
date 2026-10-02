from django.contrib import admin

from .models import Artist, ArtistSource, BaselineRun, SourceAuditEvent, SourceItem


@admin.register(Artist)
class ArtistAdmin(admin.ModelAdmin):
    list_display = ("official_name", "enabled", "source_count")
    search_fields = ("official_name",)
    list_filter = ("enabled",)

    @admin.display(description="Sources")
    def source_count(self, artist):
        return artist.sources.count()

    def save_model(self, request, obj, form, change):
        old_enabled = Artist.objects.filter(pk=obj.pk).values_list("enabled", flat=True).first() if change else None
        super().save_model(request, obj, form, change)
        if obj.enabled and old_enabled is False:
            from django.utils import timezone
            obj.sources.filter(enabled=True, verification=ArtistSource.Verification.VERIFIED).update(next_poll_at=timezone.now())
        if change and old_enabled != obj.enabled:
            SourceAuditEvent.objects.create(artist=obj, actor=request.user, event_type="artist_configured", detail={"enabled_from": old_enabled, "enabled_to": obj.enabled})


@admin.register(ArtistSource)
class ArtistSourceAdmin(admin.ModelAdmin):
    list_display = ("artist", "platform", "native_profile_id", "enabled", "verification", "baseline_completed_at", "next_poll_at", "consecutive_failures", "release_polling_available")
    list_filter = ("platform", "enabled", "verification")
    search_fields = ("artist__official_name", "native_profile_id", "canonical_url", "last_error")
    readonly_fields = ("baseline_started_at", "baseline_completed_at", "last_success_at", "last_error_at", "last_error", "consecutive_failures")

    @admin.display(description="Release polling")
    def release_polling_available(self, source):
        return "Implemented; candidate profile unprobed" if source.release_polling_available else "Unavailable (identity metadata only)"

    def save_model(self, request, obj, form, change):
        old = None
        if change:
            old = ArtistSource.objects.get(pk=obj.pk)
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


@admin.register(SourceItem)
class SourceItemAdmin(admin.ModelAdmin):
    list_display = ("platform", "native_item_id", "title", "source", "source_release_at", "first_observed_at", "from_baseline")
    list_filter = ("platform", "from_baseline")
    search_fields = ("native_item_id", "title", "source__artist__official_name")
    readonly_fields = tuple(field.name for field in SourceItem._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(BaselineRun)
class BaselineRunAdmin(admin.ModelAdmin):
    list_display = ("source", "status", "started_at", "completed_at", "item_count", "error")
    readonly_fields = tuple(field.name for field in BaselineRun._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SourceAuditEvent)
class SourceAuditEventAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "event_type", "artist", "source", "actor")
    list_filter = ("event_type",)
    readonly_fields = tuple(field.name for field in SourceAuditEvent._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
