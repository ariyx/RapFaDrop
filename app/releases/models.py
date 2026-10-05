import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .normalization import normalize_text


class CanonicalRelease(models.Model):
    class ReleaseType(models.TextChoices):
        SINGLE = "single", "Single"
        LP = "lp", "LP"
        EP = "ep", "EP"

    class State(models.TextChoices):
        IDENTIFIED = "identified", "Identified"
        REVIEW_REQUIRED = "review_required", "Review required"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    title = models.CharField(max_length=500)
    release_type = models.CharField(max_length=12, choices=ReleaseType.choices)
    edition = models.CharField(max_length=32, default="original")
    release_date = models.DateField(null=True, blank=True)
    state = models.CharField(max_length=20, choices=State.choices, default=State.IDENTIFIED)
    identity_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    edition_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="editions")
    credited_artists = models.ManyToManyField("sources.Artist", through="ReleaseCredit", related_name="canonical_releases")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("title", "pk")

    def save(self, *args, **kwargs):
        self.title = str(self.title or "")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.get_release_type_display()})"


class Track(models.Model):
    canonical_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    official_title = models.CharField(max_length=500)
    normalized_title = models.CharField(max_length=500, db_index=True)
    identity_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    edition = models.CharField(max_length=32, default="original")
    edition_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="editions")
    credited_artists = models.ManyToManyField("sources.Artist", through="TrackCredit", related_name="canonical_tracks")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("official_title", "pk")

    def save(self, *args, **kwargs):
        if not self.normalized_title:
            self.normalized_title = normalize_text(self.official_title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.official_title


class ReleaseCredit(models.Model):
    release = models.ForeignKey(CanonicalRelease, on_delete=models.CASCADE, related_name="artist_credits")
    artist = models.ForeignKey("sources.Artist", on_delete=models.PROTECT, related_name="release_credits")
    position = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ("position", "pk")
        constraints = [models.UniqueConstraint(fields=("release", "artist"), name="release_artist_credit_uniq")]


class TrackCredit(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="artist_credits")
    artist = models.ForeignKey("sources.Artist", on_delete=models.PROTECT, related_name="track_credits")
    position = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ("position", "pk")
        constraints = [models.UniqueConstraint(fields=("track", "artist"), name="track_artist_credit_uniq")]


class ReleaseTrack(models.Model):
    release = models.ForeignKey(CanonicalRelease, on_delete=models.CASCADE, related_name="release_tracks")
    track = models.ForeignKey(Track, on_delete=models.PROTECT, related_name="release_memberships")
    position = models.PositiveSmallIntegerField()
    prior_single = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="album_links")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("position", "pk")
        constraints = [
            models.UniqueConstraint(fields=("release", "track"), name="release_track_pair_uniq"),
            models.UniqueConstraint(fields=("release", "position"), name="release_track_position_uniq"),
            models.CheckConstraint(condition=Q(prior_single__isnull=True) | ~Q(pk=models.F("prior_single_id")), name="release_track_not_own_prior"),
        ]


class SourceMatch(models.Model):
    class State(models.TextChoices):
        MATCHED = "matched", "Matched"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CORRECTED = "corrected", "Corrected"
        REVIEW_REQUIRED = "review_required", "Review required"

    source_item = models.OneToOneField("sources.SourceItem", on_delete=models.PROTECT, related_name="identity_match")
    release = models.ForeignKey(CanonicalRelease, null=True, blank=True, on_delete=models.PROTECT, related_name="source_matches")
    track = models.ForeignKey(Track, null=True, blank=True, on_delete=models.PROTECT, related_name="source_matches")
    confidence = models.PositiveSmallIntegerField(default=0)
    evidence = models.JSONField(default=dict, blank=True)
    matching_method = models.CharField(max_length=80)
    state = models.CharField(max_length=20, choices=State.choices)
    admin_decision = models.CharField(max_length=20, blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="identity_match_decisions")
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(track__isnull=True) | Q(release__isnull=False), name="source_match_track_has_release")]
        indexes = [models.Index(fields=("state", "confidence"), name="source_match_state_conf_idx")]


class ReviewItem(models.Model):
    class Category(models.TextChoices):
        LOW_CONFIDENCE = "low_confidence", "Low confidence"
        ARTIST_MISMATCH = "artist_mismatch", "Artist mismatch"
        POSSIBLE_DUPLICATE = "possible_duplicate", "Possible duplicate"
        EDITION = "edition", "Edition ambiguity"
        COLLECTION_TYPE = "collection_type", "Collection type"
        INVALID_SOURCE = "invalid_source", "Invalid source metadata"
        MANUAL = "manual", "Manual review"

    class State(models.TextChoices):
        OPEN = "open", "Open"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CORRECTED = "corrected", "Corrected"
        REQUEUED = "requeued", "Requeued for review"

    class AdminAction(models.TextChoices):
        NONE = "", "—"
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"
        CORRECT = "correct", "Correct"
        REQUEUE = "requeue", "Requeue for review"

    source_item = models.OneToOneField("sources.SourceItem", on_delete=models.PROTECT, related_name="review_item")
    source_match = models.ForeignKey(SourceMatch, null=True, blank=True, on_delete=models.PROTECT, related_name="reviews")
    category = models.CharField(max_length=24, choices=Category.choices)
    reason = models.CharField(max_length=500)
    evidence = models.JSONField(default=dict, blank=True)
    state = models.CharField(max_length=16, choices=State.choices, default=State.OPEN)
    resolution = models.CharField(max_length=1000, blank=True)
    resolved_release = models.ForeignKey(CanonicalRelease, null=True, blank=True, on_delete=models.PROTECT, related_name="review_resolutions")
    resolved_track = models.ForeignKey(Track, null=True, blank=True, on_delete=models.PROTECT, related_name="review_resolutions")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="release_review_decisions")
    admin_action = models.CharField(max_length=12, choices=AdminAction.choices, blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("state", "-created_at")
        indexes = [models.Index(fields=("state", "category"), name="review_state_category_idx")]
        constraints = [models.CheckConstraint(condition=Q(resolved_track__isnull=True) | Q(resolved_release__isnull=False), name="review_track_has_release")]

    def __str__(self):
        return f"{self.get_category_display()}: {self.source_item}"


class ProcessingQueueItem(models.Model):
    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        RETRY_WAIT = "retry_wait", "Retry wait"
        COMPLETE = "complete", "Complete"
        CANCELLED = "cancelled", "Cancelled"

    release = models.ForeignKey(CanonicalRelease, null=True, blank=True, on_delete=models.PROTECT, related_name="processing_queue_items")
    track = models.ForeignKey(Track, null=True, blank=True, on_delete=models.PROTECT, related_name="processing_queue_items")
    state = models.CharField(max_length=16, choices=State.choices, default=State.PENDING)
    due_at = models.DateTimeField()
    attempt_count = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("due_at", "pk")
        indexes = [models.Index(fields=("state", "due_at"), name="processing_queue_due_idx")]
        constraints = [
            models.CheckConstraint(condition=Q(release__isnull=False) | Q(track__isnull=False), name="queue_item_has_canonical_target"),
            models.UniqueConstraint(fields=("track",), condition=Q(track__isnull=False), name="queue_track_target_uniq"),
            models.UniqueConstraint(fields=("release",), condition=Q(release__isnull=False, track__isnull=True), name="queue_release_target_uniq"),
        ]


class IdentityAuditEvent(models.Model):
    review_item = models.ForeignKey(ReviewItem, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_events")
    source_match = models.ForeignKey(SourceMatch, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_events")
    source_item = models.ForeignKey("sources.SourceItem", null=True, blank=True, on_delete=models.SET_NULL, related_name="identity_audit_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=24)
    detail = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-occurred_at",)


class FreshDispatch(models.Model):
    """Durable eligibility manifest; broker messages cannot invent eligible work."""
    source_item = models.OneToOneField("sources.SourceItem", on_delete=models.PROTECT)
    disposition = models.CharField(max_length=20, default="review", db_index=True)
    reason = models.CharField(max_length=500)
    evidence = models.JSONField(default=dict)
    release = models.ForeignKey(CanonicalRelease, null=True, on_delete=models.PROTECT)
    due_at = models.DateTimeField(default=timezone.now)
    attempts = models.PositiveIntegerField(default=0)
    processing_state = models.CharField(max_length=20, default="pending", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class FreshTrack(models.Model):
    dispatch = models.ForeignKey(FreshDispatch, on_delete=models.PROTECT, related_name="tracks")
    track = models.ForeignKey(Track, on_delete=models.PROTECT)
    native_id = models.CharField(max_length=22)
    position = models.PositiveSmallIntegerField()
    metadata = models.JSONField(default=dict)
    evidence = models.JSONField(default=dict)
    candidate = models.ForeignKey("media_pipeline.MediaCandidate", null=True, on_delete=models.PROTECT)
    publication = models.ForeignKey("publication.Publication", null=True, on_delete=models.PROTECT)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def spotify_id(self):
        return self.native_id

    class Meta:
        constraints = [models.UniqueConstraint(fields=("dispatch", "position"), name="fresh_track_position_once")]


class FreshProviderBackoff(models.Model):
    platform = models.CharField(max_length=20, unique=True)
    due_at = models.DateTimeField()
    reason = models.CharField(max_length=500)


class FreshControl(models.Model):
    name = models.CharField(max_length=20, unique=True, default="production")
    paused = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
