"""Best-effort latency hints; durable rows and periodic tasks own recovery."""
from django.conf import settings
from django.db import transaction


def wake_media():
    if settings.FRESH_PIPELINE_ENABLED and settings.SPOTIFY_MEDIA_BRIDGE_ENABLED:
        from .tasks import process_fresh_releases
        transaction.on_commit(lambda: process_fresh_releases.apply_async(
            queue='fresh-media-v1', expires=60), robust=True)


def wake_publication():
    # Media workers deliberately have no Telegram credentials/live switches.
    # Only the isolated publication worker can authorize and perform a send.
    if settings.FRESH_PIPELINE_ENABLED and settings.SPOTIFY_MEDIA_BRIDGE_ENABLED:
        from publication.tasks import process_due_publications
        transaction.on_commit(lambda: process_due_publications.apply_async(
            queue='fresh-publication-v1', expires=60), robust=True)
