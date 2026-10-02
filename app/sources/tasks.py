from celery import shared_task

from .services import poll_due_sources


@shared_task(name="sources.tasks.poll_due_artist_sources")
def poll_due_artist_sources():
    return poll_due_sources()
