import uuid

from django.conf import settings
from django.db import models


class OperatorAuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    object_type = models.CharField(max_length=80)
    object_id = models.CharField(max_length=80, blank=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    correlation_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at", "-pk")


class OperatorActionRequest(models.Model):
    """Audited operator intent. M5 deliberately does not execute external work."""
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=40)
    source = models.ForeignKey("sources.ArtistSource", null=True, blank=True, on_delete=models.SET_NULL)
    state = models.CharField(max_length=24, default="queued_for_worker")
    correlation_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")


class OperatorSettings(models.Model):
    class NotificationMode(models.TextChoices):
        DISABLED = "disabled", "Disabled"
        TEST_ONLY = "test_only", "Test target only"

    version = models.PositiveIntegerField(default=1)
    tag_fields = models.JSONField(default=list)
    correction_delete_seconds = models.PositiveIntegerField(default=600)
    notification_mode = models.CharField(max_length=16, choices=NotificationMode.choices, default=NotificationMode.DISABLED)
    notification_target = models.CharField(max_length=100, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)
