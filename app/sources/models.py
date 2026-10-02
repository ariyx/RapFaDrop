from django.conf import settings
from django.db import models


class Artist(models.Model):
    official_name = models.CharField(max_length=200, unique=True)
    aliases = models.JSONField(default=list, blank=True)
    enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("official_name",)

    def __str__(self):
        return self.official_name


class ArtistSource(models.Model):
    class Platform(models.TextChoices):
        SOUNDCLOUD = "soundcloud", "SoundCloud"
        SPOTIFY = "spotify", "Spotify"

    class Verification(models.TextChoices):
        UNVERIFIED = "unverified", "Unverified"
        VERIFIED = "verified", "Verified"
        UNAVAILABLE = "unavailable", "Unavailable"

    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="sources")
    platform = models.CharField(max_length=20, choices=Platform.choices)
    native_profile_id = models.CharField(max_length=160, blank=True)
    canonical_url = models.URLField(max_length=500, blank=True)
    enabled = models.BooleanField(default=False)
    verification = models.CharField(max_length=20, choices=Verification.choices, default=Verification.UNVERIFIED)
    baseline_started_at = models.DateTimeField(null=True, blank=True)
    baseline_completed_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    next_poll_at = models.DateTimeField(null=True, blank=True)
    consecutive_failures = models.PositiveIntegerField(default=0)
    last_error_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=1000, blank=True)
    poll_interval_seconds = models.PositiveIntegerField(default=90)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("artist__official_name", "platform")
        constraints = [models.UniqueConstraint(fields=("artist", "platform"), name="source_artist_platform_uniq")]
        indexes = [models.Index(fields=("platform", "enabled", "verification", "next_poll_at"), name="source_due_poll_idx")]

    def __str__(self):
        return f"{self.artist} — {self.platform}"

    @property
    def release_polling_available(self):
        return self.platform == self.Platform.SOUNDCLOUD


class SourceItem(models.Model):
    platform = models.CharField(max_length=20, choices=ArtistSource.Platform.choices)
    native_item_id = models.CharField(max_length=200)
    source = models.ForeignKey(ArtistSource, on_delete=models.PROTECT, related_name="items")
    title = models.CharField(max_length=500, blank=True)
    canonical_url = models.URLField(max_length=1000, blank=True)
    source_release_at = models.DateTimeField(null=True, blank=True)
    first_observed_at = models.DateTimeField()
    metadata = models.JSONField(default=dict, blank=True)
    sanitized_raw_data = models.JSONField(default=dict, blank=True)
    from_baseline = models.BooleanField(default=False)

    class Meta:
        ordering = ("-first_observed_at",)
        constraints = [models.UniqueConstraint(fields=("platform", "native_item_id"), name="source_item_platform_native_uniq")]

    def __str__(self):
        return f"{self.platform}:{self.native_item_id} {self.title}".strip()


class BaselineRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    source = models.ForeignKey(ArtistSource, on_delete=models.CASCADE, related_name="baseline_runs")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    item_count = models.PositiveIntegerField(default=0)
    error = models.CharField(max_length=1000, blank=True)

    class Meta:
        ordering = ("-started_at",)


class SourceAuditEvent(models.Model):
    source = models.ForeignKey(ArtistSource, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_events")
    artist = models.ForeignKey(Artist, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    event_type = models.CharField(max_length=40)
    detail = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-occurred_at",)
