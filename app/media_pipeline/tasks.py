"""Bounded acquisition of verified Spotify-bridged full-audio candidates."""

from celery import shared_task
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from .models import MediaCandidate
from .providers import PROVIDERS
from .services import retry_candidate


@shared_task(name="media_pipeline.tasks.process_spotify_bridge_media")
def process_spotify_bridge_media():
    if (not settings.SPOTIFY_MEDIA_BRIDGE_ENABLED or settings.PUBLICATION_WORKER_ENABLED or
            settings.TELEGRAM_LIVE_ENABLED or settings.TELEGRAM_MODE != "disabled"):
        return {"skipped": "bridge or publication guard"}
    now = timezone.now()
    candidates = list(MediaCandidate.objects.filter(
        provenance__has_key="spotify_bridge_release_id", provider__in=settings.MEDIA_PROVIDER_ORDER,
        state__in=(MediaCandidate.State.CANDIDATE, MediaCandidate.State.RETRY_WAIT),
        source_match__source_item__platform="soundcloud",
        source_match__source_item__source__verification="verified",
    ).filter(Q(retry_due_at__isnull=True) | Q(retry_due_at__lte=now)).order_by("created_at", "pk")[:2])
    results = {}
    for candidate in candidates:
        provider = PROVIDERS.get(candidate.provider)
        if provider is None or not provider.can_handle(candidate.source_match.source_item.canonical_url):
            results[candidate.pk] = "provider_unavailable"
            continue
        result = retry_candidate(candidate, provider=provider, now=now)
        results[candidate.pk] = result.state
    return results
