from celery import shared_task
from .fresh import process_due


@shared_task(name="releases.tasks.process_fresh_releases")
def process_fresh_releases():
    return process_due()
