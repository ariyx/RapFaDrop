from django.contrib import admin, messages
from django.core.exceptions import ValidationError

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
from .services import resolve_review
from operations.services import audit, safe_audit_json


class ReleaseCreditInline(admin.TabularInline):
    model = ReleaseCredit
    extra = 0


class ReleaseTrackInline(admin.TabularInline):
    model = ReleaseTrack
    extra = 0
    autocomplete_fields = ("track",)


@admin.register(CanonicalRelease)
class CanonicalReleaseAdmin(admin.ModelAdmin):
    list_display = ("title", "release_type", "edition", "release_date", "state")
    list_filter = ("release_type", "edition", "state")
    search_fields = ("title",)
    inlines = (ReleaseCreditInline, ReleaseTrackInline)
    readonly_fields = ("identity_key", "created_at", "updated_at")


class TrackCreditInline(admin.TabularInline):
    model = TrackCredit
    extra = 0


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ("official_title", "edition", "duration_seconds", "canonical_id")
    list_filter = ("edition",)
    search_fields = ("official_title", "normalized_title", "canonical_id")
    inlines = (TrackCreditInline,)
    readonly_fields = ("canonical_id", "normalized_title", "identity_key", "created_at", "updated_at")


@admin.register(SourceMatch)
class SourceMatchAdmin(admin.ModelAdmin):
    list_display = ("source_item", "release", "track", "confidence", "matching_method", "state", "decided_by", "decided_at")
    list_filter = ("state", "matching_method")
    search_fields = ("source_item__title", "source_item__native_item_id", "release__title", "track__official_title")
    readonly_fields = tuple(field.name for field in SourceMatch._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ReviewItem)
class ReviewItemAdmin(admin.ModelAdmin):
    list_display = ("source_item", "category", "state", "reason", "actor", "reviewed_at", "created_at")
    list_filter = ("category", "state", "source_item__platform")
    date_hierarchy = "created_at"
    search_fields = ("source_item__title", "source_item__native_item_id", "reason", "resolution", "source_match__release__title", "source_match__track__official_title")
    readonly_fields = ("source_item", "source_match", "category", "reason", "evidence", "state", "actor", "reviewed_at", "created_at", "updated_at", "admin_action")
    fields = (*readonly_fields, "resolved_release", "resolved_track", "resolution")
    actions = ("approve_selected", "reject_selected", "correct_selected", "requeue_selected")

    def _apply(self, request, queryset, action):
        changed = 0
        for review in queryset.select_related("source_match", "source_item"):
            try:
                before = {"state": review.state, "action": review.admin_action}
                resolve_review(
                    review,
                    action,
                    actor=request.user,
                    release=review.resolved_release,
                    track=review.resolved_track,
                    resolution=review.resolution,
                )
                review.refresh_from_db()
                audit(request.user, f"review_{action}", review, before, {"state": review.state, "action": review.admin_action})
                changed += 1
            except (ValueError, ValidationError) as exc:
                self.message_user(request, f"Review {review.pk}: {exc}", level=messages.WARNING)
        self.message_user(request, f"Applied {action} to {changed} review item(s).", level=messages.SUCCESS)

    @admin.action(description="Approve selected reviews")
    def approve_selected(self, request, queryset):
        self._apply(request, queryset, "approve")

    @admin.action(description="Reject selected reviews")
    def reject_selected(self, request, queryset):
        self._apply(request, queryset, "reject")

    @admin.action(description="Correct selected reviews using resolved release/track fields")
    def correct_selected(self, request, queryset):
        self._apply(request, queryset, "correct")

    @admin.action(description="Explicitly requeue selected reviews for human review")
    def requeue_selected(self, request, queryset):
        self._apply(request, queryset, "requeue")

    def save_model(self, request, obj, form, change):
        if change and obj.resolved_track_id and obj.resolved_release_id:
            if not obj.resolved_release.release_tracks.filter(track=obj.resolved_track).exists():
                raise ValidationError("Resolved track must belong to the selected release")
        super().save_model(request, obj, form, change)


@admin.register(ProcessingQueueItem)
class ProcessingQueueItemAdmin(admin.ModelAdmin):
    list_display = ("release", "track", "state", "due_at", "attempt_count", "last_error")
    list_filter = ("state",)
    search_fields = ("release__title", "track__official_title", "last_error")
    readonly_fields = tuple(field.name for field in ProcessingQueueItem._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(IdentityAuditEvent)
class IdentityAuditEventAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "action", "actor", "review_item", "source_item")
    list_filter = ("action",)
    readonly_fields = tuple(field.name for field in IdentityAuditEvent._meta.fields if field.name != "detail") + ("safe_detail",)

    @admin.display(description="Redacted event detail")
    def safe_detail(self, event):
        return safe_audit_json(event.detail)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
