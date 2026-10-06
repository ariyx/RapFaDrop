from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class MediaCandidate(models.Model):
    class State(models.TextChoices):
        CANDIDATE = "candidate", "Candidate"
        DOWNLOADING = "downloading", "Downloading"
        DOWNLOADED = "downloaded", "Downloaded"
        INVALID = "invalid", "Invalid"
        REVIEW_REQUIRED = "review_required", "Review required"
        RETRY_WAIT = "retry_wait", "Retry wait"
        PREPARING = "preparing", "Preparing"
        READY = "ready", "Ready"

    class PreparationState(models.TextChoices):
        PENDING = "pending", "Pending"
        PREPARING = "preparing", "Preparing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    class ArtworkState(models.TextChoices):
        NOT_PROVIDED = "not_provided", "Not provided"
        AVAILABLE = "available", "Validated; pending embed"
        EMBEDDED = "embedded", "Embedded"
        UNSUPPORTED = "unsupported", "Unsupported for format"
        INVALID = "invalid", "Invalid artwork"

    track = models.ForeignKey("releases.Track", on_delete=models.PROTECT, related_name="media_candidates")
    release = models.ForeignKey("releases.CanonicalRelease", on_delete=models.PROTECT, related_name="media_candidates")
    source_match = models.ForeignKey("releases.SourceMatch", on_delete=models.PROTECT, related_name="media_candidates")
    provider = models.CharField(max_length=32)
    transport_identity = models.CharField(max_length=64, blank=True, default='')
    state = models.CharField(max_length=20, choices=State.choices, default=State.CANDIDATE, db_index=True)
    preparation_state = models.CharField(max_length=12, choices=PreparationState.choices, default=PreparationState.PENDING)
    artwork_state = models.CharField(max_length=16, choices=ArtworkState.choices, default=ArtworkState.NOT_PROVIDED)
    attempt_count = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    retry_due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_outcome = models.CharField(max_length=32, blank=True)
    last_error = models.CharField(max_length=1000, blank=True)
    candidate_path = models.CharField(max_length=1024, blank=True)
    prepared_path = models.CharField(max_length=1024, blank=True)
    artwork_path = models.CharField(max_length=1024, blank=True)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    file_size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    expected_duration_seconds = models.FloatField(null=True, blank=True)
    observed_facts = models.JSONField(default=dict, blank=True)
    duration_comparison = models.JSONField(default=dict, blank=True)
    validation_report = models.JSONField(default=dict, blank=True)
    preparation_report = models.JSONField(default=dict, blank=True)
    provenance = models.JSONField(default=dict, blank=True)
    quality_rank = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="media_candidates_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "pk")
        constraints = [
            models.UniqueConstraint(fields=("track", "source_match", "provider", "transport_identity"), condition=~models.Q(provider="manual"), name="media_candidate_identity_uniq"),
        ]
        indexes = [models.Index(fields=("track", "state"), name="media_cand_track_state_idx")]

    def clean(self):
        if self.source_match_id:
            if self.source_match.track_id != self.track_id or self.source_match.release_id != self.release_id:
                raise ValidationError("Media candidate identity must match its source match.")

    def __str__(self):
        return f"{self.track} via {self.provider} ({self.get_state_display()})"


class MediaAttempt(models.Model):
    class State(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        RETRY_WAIT = "retry_wait", "Retry wait"
        INVALID = "invalid", "Invalid"
        REVIEW_REQUIRED = "review_required", "Review required"

    candidate = models.ForeignKey(MediaCandidate, on_delete=models.CASCADE, related_name="attempts")
    provider = models.CharField(max_length=32)
    state = models.CharField(max_length=20, choices=State.choices, default=State.RUNNING)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(max_length=32, blank=True)
    error = models.CharField(max_length=1000, blank=True)
    evidence = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-started_at", "-pk")


class MediaAuditEvent(models.Model):
    candidate = models.ForeignKey(MediaCandidate, on_delete=models.CASCADE, related_name="audit_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=32)
    detail = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-occurred_at", "-pk")
