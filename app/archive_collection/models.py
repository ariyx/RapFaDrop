from django.db import models
from django.core.exceptions import ValidationError


class Collection(models.Model):
    name = models.CharField(max_length=80, unique=True)
    target = models.CharField(max_length=100, default="-1004311149640")
    roster = models.JSONField(default=list)
    application_sha = models.CharField(max_length=40)
    paused = models.BooleanField(default=True)
    frozen_at = models.DateTimeField(null=True)
    verification = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            previous = type(self).objects.get(pk=self.pk)
            if previous.frozen_at and any(getattr(previous, field) != getattr(self, field)
                    for field in ("name", "target", "roster", "application_sha", "frozen_at")):
                raise ValidationError("Frozen collection identity and roster cannot be replaced")
        super().save(*args, **kwargs)


class ArtistSelection(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.PROTECT, related_name="selections")
    source = models.ForeignKey("sources.ArtistSource", on_delete=models.PROTECT)
    roster_position = models.PositiveSmallIntegerField()
    evidence = models.JSONField(default=dict)
    error = models.TextField(blank=True)
    observed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("collection", "source"), name="archive_artist_once")]


class Recording(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.PROTECT, related_name="recordings")
    spotify_id = models.CharField(max_length=22)
    metadata = models.JSONField(default=dict)
    order = models.PositiveIntegerField()
    state = models.CharField(max_length=24, default="pending")
    reason = models.TextField(blank=True)
    evidence = models.JSONField(default=dict)
    attempts = models.PositiveSmallIntegerField(default=0)
    retry_due_at = models.DateTimeField(null=True)
    candidate = models.ForeignKey("media_pipeline.MediaCandidate", null=True, on_delete=models.PROTECT)
    publication = models.ForeignKey("publication.Publication", null=True, on_delete=models.PROTECT, related_name="archive_recordings")
    track = models.ForeignKey("releases.Track", null=True, on_delete=models.PROTECT)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.pk and self.collection.frozen_at:
            previous = type(self).objects.get(pk=self.pk)
            if any(getattr(previous, field) != getattr(self, field)
                    for field in ("collection_id", "spotify_id", "metadata", "order")):
                raise ValidationError("Frozen recording selection/version metadata cannot be replaced")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ("order", "pk")
        constraints = [models.UniqueConstraint(fields=("collection", "spotify_id"), name="archive_recording_once")]


class Slot(models.Model):
    selection = models.ForeignKey(ArtistSelection, on_delete=models.PROTECT, related_name="slots")
    number = models.PositiveSmallIntegerField()
    popular_rank = models.PositiveSmallIntegerField()
    recording = models.ForeignKey(Recording, on_delete=models.PROTECT, related_name="slots")

    class Meta:
        constraints = [models.UniqueConstraint(fields=("selection", "number"), name="archive_slot_once"),
                       models.CheckConstraint(condition=models.Q(number__in=(1, 2)), name="archive_two_slots")]


class AcquisitionSource(models.Model):
    """Verified acquisition identity only. No polling flag, baseline or queue capability."""
    artist = models.ForeignKey('sources.Artist', on_delete=models.PROTECT)
    platform = models.CharField(max_length=20, choices=[('soundcloud', 'SoundCloud'), ('youtube', 'YouTube')])
    native_id = models.CharField(max_length=160)
    profile_url = models.URLField(max_length=500)
    evidence = models.JSONField(default=dict)
    verified_at = models.DateTimeField()
    catalog = models.JSONField(default=list)
    catalog_checked_at = models.DateTimeField(null=True)
    retry_due_at = models.DateTimeField(null=True)
    last_error = models.CharField(max_length=1000, blank=True)

    @property
    def canonical_url(self):
        return self.profile_url

    class Meta:
        constraints = [models.UniqueConstraint(fields=('artist', 'platform', 'native_id'), name='archive_acquisition_identity_once')]


class RecordingAlias(models.Model):
    recording = models.OneToOneField(Recording, on_delete=models.PROTECT, related_name='canonical_alias')
    canonical = models.ForeignKey(Recording, on_delete=models.PROTECT, related_name='aliases')
    evidence = models.JSONField(default=dict)
    reconciled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=~models.Q(recording=models.F('canonical')), name='archive_alias_not_self')]
