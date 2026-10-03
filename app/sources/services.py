from datetime import timedelta
import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .adapters import SoundCloudAdapter, SpotifyAdapter, SourceUnavailable
from .models import ArtistSource, BaselineRun, SourceAuditEvent, SourceItem

logger = logging.getLogger(__name__)


def adapter_for(platform):
    if platform == ArtistSource.Platform.SOUNDCLOUD:
        return SoundCloudAdapter()
    if platform == ArtistSource.Platform.SPOTIFY:
        return SpotifyAdapter()
    raise ValueError(f"Unsupported source platform: {platform}")


def _upsert_items(source, items, observed_at, from_baseline):
    count = 0
    for item in items:
        _, created = SourceItem.objects.get_or_create(
            platform=source.platform,
            native_item_id=item["native_item_id"],
            defaults={
                "source": source,
                "title": item.get("title", ""),
                "canonical_url": item.get("canonical_url", ""),
                "source_release_at": item.get("source_release_at"),
                "first_observed_at": observed_at,
                "metadata": item.get("metadata", {}),
                "sanitized_raw_data": item.get("sanitized_raw_data", {}),
                "from_baseline": from_baseline,
            },
        )
        count += int(created)
    return count


def baseline_source(source, adapter=None, now=None):
    """Snapshot history atomically. Repeating after a crash is safe by stable IDs."""
    if source.baseline_completed_at is not None:
        completed = BaselineRun.objects.filter(source=source, status=BaselineRun.Status.COMPLETE).order_by("-completed_at").first()
        if completed is None:
            raise ValueError("Completed baseline has no successful run record")
        return completed
    if not source.artist.enabled or not source.enabled or source.verification != ArtistSource.Verification.VERIFIED:
        raise ValueError("Baseline requires an enabled artist and enabled, verified source")
    if not source.release_polling_available:
        raise ValueError("Release baselining is unavailable for this platform")
    now = now or timezone.now()
    adapter = adapter or adapter_for(source.platform)
    try:
        # Provider integrity is checked before a baseline run or cursor is written.
        items = adapter.list_recent(source)
    except Exception as exc:
        record_source_failure(source, exc, now=now)
        raise
    run = BaselineRun.objects.filter(source=source, status=BaselineRun.Status.RUNNING).order_by("started_at").first()
    if run is None:
        run = BaselineRun.objects.create(source=source, started_at=now)
    source.baseline_started_at = now
    source.save(update_fields=("baseline_started_at", "updated_at"))
    SourceAuditEvent.objects.create(source=source, artist=source.artist, event_type="baseline_started")
    try:
        with transaction.atomic():
            created_count = _upsert_items(source, items, now, from_baseline=True)
            run.status = BaselineRun.Status.COMPLETE
            run.completed_at = now
            run.item_count = len(items)
            run.save(update_fields=("status", "completed_at", "item_count"))
            source.baseline_completed_at = now
            source.last_success_at = now
            source.next_poll_at = now + timedelta(seconds=source.poll_interval_seconds)
            source.consecutive_failures = 0
            source.last_error = ""
            source.last_error_at = None
            source.save(update_fields=("baseline_completed_at", "last_success_at", "next_poll_at", "consecutive_failures", "last_error", "last_error_at", "updated_at"))
            SourceAuditEvent.objects.create(source=source, artist=source.artist, event_type="baseline_completed", detail={"items": len(items), "created": created_count})
        return run
    except Exception as exc:
        run.status = BaselineRun.Status.FAILED
        run.error = f"{type(exc).__name__}: {exc}"[:1000]
        run.save(update_fields=("status", "error"))
        record_source_failure(source, exc, now=now)
        raise


def record_source_failure(source, error, now=None):
    now = now or timezone.now()
    source.consecutive_failures += 1
    delay = min(source.poll_interval_seconds * (2 ** (source.consecutive_failures - 1)), 21600)
    retry_after = getattr(error, "retry_after", None)
    if isinstance(retry_after, (int, float)) and 0 <= retry_after <= 86400:
        delay = max(delay, retry_after)
    source.last_error = f"{type(error).__name__}: {error}"[:1000]
    source.last_error_at = now
    source.next_poll_at = now + timedelta(seconds=delay)
    source.save(update_fields=("consecutive_failures", "last_error", "last_error_at", "next_poll_at", "updated_at"))
    SourceAuditEvent.objects.create(source=source, artist=source.artist, event_type="poll_failed", detail={"error_type": type(error).__name__, "error": str(error)[:500], "retry_seconds": delay})


def poll_source(source, adapter=None, now=None):
    now = now or timezone.now()
    if not source.enabled or source.verification != ArtistSource.Verification.VERIFIED:
        return "skipped"
    if not source.artist.enabled:
        return "skipped"
    if source.platform == ArtistSource.Platform.SPOTIFY and not source.release_polling_available:
        reason = SpotifyAdapter.status()
        logger.warning("Spotify discovery unavailable for source_id=%s; no provider request", source.pk)
        record_source_failure(source, SourceUnavailable(reason), now=now)
        SourceAuditEvent.objects.create(source=source, artist=source.artist, event_type="release_poll_unavailable", detail={"reason": reason})
        return "unavailable"
    if not source.release_polling_available:
        return "unavailable"
    adapter = adapter or adapter_for(source.platform)
    if source.baseline_completed_at is None:
        baseline_source(source, adapter=adapter, now=now)
        return "baselined"
    try:
        items = adapter.list_recent(source)
        new_ids = set()
        if source.platform == ArtistSource.Platform.SPOTIFY:
            observed_ids = {item["native_item_id"] for item in items}
            known_ids = set(SourceItem.objects.filter(platform=source.platform, native_item_id__in=observed_ids).values_list("native_item_id", flat=True))
            new_ids = observed_ids - known_ids
            if len(new_ids) > 10:
                raise ValueError("Spotify poll found more than ten unknown IDs; inspect possible regional catalog backfill")
            for item in items:
                if item["native_item_id"] in new_ids:
                    adapter.fetch_item(source, item)
        with transaction.atomic():
            _upsert_items(source, items, now, from_baseline=False)
            if new_ids:
                from releases.services import ingest_source_item
                for source_item in SourceItem.objects.filter(platform=source.platform, native_item_id__in=new_ids):
                    ingest_source_item(source_item, now=now)
            source.last_success_at = now
            source.next_poll_at = now + timedelta(seconds=source.poll_interval_seconds)
            source.consecutive_failures = 0
            source.last_error = ""
            source.last_error_at = None
            source.save(update_fields=("last_success_at", "next_poll_at", "consecutive_failures", "last_error", "last_error_at", "updated_at"))
            SourceAuditEvent.objects.create(source=source, artist=source.artist, event_type="poll_succeeded", detail={"items": len(items)})
        return "success"
    except Exception as exc:
        record_source_failure(source, exc, now=now)
        return "failed"


def poll_due_sources(now=None, adapters=None):
    now = now or timezone.now()
    results = {}
    sources = ArtistSource.objects.select_related("artist").filter(
        artist__enabled=True,
        enabled=True,
        verification=ArtistSource.Verification.VERIFIED,
    ).filter(Q(next_poll_at__isnull=True) | Q(next_poll_at__lte=now)).order_by("next_poll_at", "pk")
    for source in sources:
        # Each provider is isolated; one failed source cannot stop another.
        adapter = (adapters or {}).get(source.platform) or adapter_for(source.platform)
        try:
            results[source.pk] = poll_source(source, adapter=adapter, now=now)
        except Exception:
            # A baseline's error is recorded at source level; keep later sources moving.
            results[source.pk] = "failed"
    return results
