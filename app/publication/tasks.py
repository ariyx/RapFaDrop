from celery import shared_task
from django.conf import settings

from .gateway import TelegramGateway
from .services import run_due


@shared_task
def process_due_publications():
    if not settings.PUBLICATION_WORKER_ENABLED or not settings.TELEGRAM_LIVE_ENABLED:
        return "disabled"
    run_due(gateway=TelegramGateway())
    return "processed"
