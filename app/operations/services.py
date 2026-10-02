from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
import json
import re

from media_pipeline.providers import redact_diagnostic

from .models import OperatorActionRequest, OperatorAuditEvent

OPERATOR_GROUP = "RapFaDrop Operators"


def has_operator_access(user):
    return bool(user.is_authenticated and user.is_active and (user.is_superuser or (user.is_staff and user.groups.filter(name=OPERATOR_GROUP).exists())))


def configure_operator_group():
    group, _ = Group.objects.get_or_create(name=OPERATOR_GROUP)
    permissions = Permission.objects.filter(content_type__app_label__in=("sources", "releases", "media_pipeline", "publication", "operations")).exclude(codename__startswith="delete_")
    group.permissions.set(permissions)
    return group


@transaction.atomic
def audit(actor, action, obj, before=None, after=None):
    return OperatorAuditEvent.objects.create(
        actor=actor, action=action, object_type=obj._meta.label_lower,
        object_id=str(obj.pk or ""), before=before or {}, after=after or {},
    )


def request_source_action(actor, source, action):
    if action not in {"poll", "baseline"}:
        raise ValueError("Unsupported source action")
    if source.verification != "verified":
        raise ValueError("Verify the source before requesting manual work")
    if action == "baseline" and source.platform != "soundcloud":
        raise ValueError("Release baselining is currently available only for SoundCloud")
    if not source.enabled or not source.artist.enabled:
        raise ValueError("Enable the verified artist/source before queuing manual work")
    request = OperatorActionRequest.objects.create(actor=actor, source=source, action=action)
    audit(actor, f"source_{action}_requested", source, after={"request_id": request.pk, "state": request.state})
    return request


def active_correction_delete_seconds(default):
    from .models import OperatorSettings
    value = OperatorSettings.objects.filter(pk=1).values_list("correction_delete_seconds", flat=True).first()
    return value if value is not None else default


def active_media_tag_fields(default):
    from .models import OperatorSettings
    value = OperatorSettings.objects.filter(pk=1).values_list("tag_fields", flat=True).first()
    return frozenset(value) if value is not None else default


def safe_audit_json(value):
    hidden_keys = {"payload", "response", "raw", "raw_data", "sanitized_raw_data", "provenance", "candidate_path", "prepared_path", "artwork_path"}

    def clean(item):
        if isinstance(item, dict):
            return {key: ("[omitted]" if str(key).casefold() in hidden_keys else clean(child)) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [clean(child) for child in item]
        if isinstance(item, str):
            text = redact_diagnostic(item)
            return re.sub(r"(?:[A-Za-z]:\\[^\s]+|/(?:[^\s/]+/)*[^\s]*)", "[path omitted]", text)
        return item

    return json.dumps(clean(value or {}), ensure_ascii=False, sort_keys=True)
