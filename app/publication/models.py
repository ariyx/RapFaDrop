from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class CaptionTemplate(models.Model):
    kind = models.CharField(max_length=24)
    version = models.PositiveIntegerField(default=1)
    config = models.JSONField(default=dict)
    enabled = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("kind", "version"), name="caption_kind_version_uniq")]

    def save(self, *args, **kwargs):
        if self.pk and self.publications.exists():
            old = type(self).objects.get(pk=self.pk)
            if (old.kind, old.version, old.config) != (self.kind, self.version, self.config):
                raise ValidationError("Referenced templates are immutable; create a new version.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.kind} v{self.version}"


class PublicationChannel(models.Model):
    target = models.CharField(max_length=100, unique=True)
    active_album = models.ForeignKey("AlbumSession", null=True, blank=True, on_delete=models.SET_NULL, related_name="channel_locks")
    in_flight = models.ForeignKey("PublicationAttempt", null=True, blank=True, on_delete=models.SET_NULL, related_name="channel_leases")
    lease_until = models.DateTimeField(null=True, blank=True)


class Publication(models.Model):
    class Kind(models.TextChoices):
        SINGLE = "single_audio", "Single audio"
        INTRO = "album_intro", "Album introduction"
        TRACK = "album_track_audio", "Album track audio"
        EDITION = "edition", "Edition audio"
        OVERFLOW = "overflow", "Prior-single overflow"
        CORRECTION = "correction", "Correction reply"
        NOTIFICATION = "notification", "Admin notification"

    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        SENDING = "sending", "Sending"
        PUBLISHED = "published", "Published"
        RETRY_WAIT = "retry_wait", "Retry wait"
        UNCERTAIN = "uncertain", "Reconciliation required"
        REVIEW = "review_required", "Review required"
        DELETED = "deleted", "Deleted"

    channel = models.ForeignKey(PublicationChannel, on_delete=models.PROTECT, related_name="publications")
    identity_key = models.CharField(max_length=160)
    kind = models.CharField(max_length=24, choices=Kind.choices)
    track = models.ForeignKey("releases.Track", null=True, blank=True, on_delete=models.PROTECT, related_name="publications")
    release = models.ForeignKey("releases.CanonicalRelease", null=True, blank=True, on_delete=models.PROTECT, related_name="publications")
    candidate = models.ForeignKey("media_pipeline.MediaCandidate", null=True, blank=True, on_delete=models.PROTECT, related_name="publications")
    original = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="linked_publications")
    album_session = models.ForeignKey("AlbumSession", null=True, blank=True, on_delete=models.PROTECT, related_name="publications")
    template = models.ForeignKey(CaptionTemplate, null=True, blank=True, on_delete=models.PROTECT, related_name="publications")
    caption_html = models.TextField(blank=True)
    context = models.JSONField(default=dict)
    state = models.CharField(max_length=16, choices=State.choices, default=State.PENDING)
    message_id = models.PositiveBigIntegerField(null=True, blank=True)
    message_url = models.CharField(max_length=300, blank=True)
    retry_due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    delete_due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_error = models.CharField(max_length=500, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("channel", "identity_key"), name="publication_identity_uniq"),
            models.UniqueConstraint(fields=("channel", "track"), condition=Q(track__isnull=False), name="publication_track_uniq"),
            models.UniqueConstraint(fields=("channel", "message_id"), condition=Q(message_id__isnull=False), name="publication_message_uniq"),
        ]


class PublicationAttempt(models.Model):
    class State(models.TextChoices):
        PENDING = "pending", "Pending response"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Definitely failed"
        UNCERTAIN = "uncertain", "Uncertain outcome"

    publication = models.ForeignKey(Publication, on_delete=models.PROTECT, related_name="attempts")
    operation = models.CharField(max_length=24)
    operation_key = models.CharField(max_length=100)
    state = models.CharField(max_length=12, choices=State.choices, default=State.PENDING)
    candidate = models.ForeignKey("media_pipeline.MediaCandidate", null=True, blank=True, on_delete=models.PROTECT, related_name="publication_attempts")
    previous_candidate = models.ForeignKey("media_pipeline.MediaCandidate", null=True, blank=True, on_delete=models.PROTECT, related_name="upgrade_attempts")
    payload = models.JSONField(default=dict)
    response = models.JSONField(default=dict)
    error = models.CharField(max_length=500, blank=True)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("publication",), condition=Q(state="pending"), name="publication_pending_attempt_uniq")]


class AlbumSession(models.Model):
    channel = models.ForeignKey(PublicationChannel, on_delete=models.PROTECT, related_name="album_sessions")
    release = models.ForeignKey("releases.CanonicalRelease", on_delete=models.PROTECT, related_name="album_sessions")
    intro = models.ForeignKey(Publication, null=True, blank=True, on_delete=models.PROTECT, related_name="introduced_sessions")
    entries = models.JSONField(default=list)
    overflow = models.JSONField(default=list)
    context = models.JSONField(default=dict)
    cursor = models.PositiveIntegerField(default=0)
    state = models.CharField(max_length=20, default="waiting_media")
    failed_since = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("channel", "release"), name="album_channel_release_uniq")]


class PublicationReconciliation(models.Model):
    attempt = models.OneToOneField(PublicationAttempt, on_delete=models.PROTECT, related_name="reconciliation")
    state = models.CharField(max_length=20, default="open")
    decision = models.CharField(max_length=24, blank=True)
    evidence = models.CharField(max_length=1000, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class PublicationAuditEvent(models.Model):
    publication = models.ForeignKey(Publication, on_delete=models.PROTECT, related_name="audit_events")
    attempt = models.ForeignKey(PublicationAttempt, null=True, blank=True, on_delete=models.PROTECT, related_name="audit_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    action = models.CharField(max_length=40)
    detail = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
