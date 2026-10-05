from celery import shared_task
from django.conf import settings

from .gateway import TelegramGateway
from .services import run_due


@shared_task
def process_due_publications():
    if not settings.PUBLICATION_WORKER_ENABLED or not settings.TELEGRAM_LIVE_ENABLED:
        return "disabled"
    if settings.TELEGRAM_MODE == 'production':
        if not settings.FRESH_PIPELINE_ENABLED:
            return 'fresh dispatch disabled'
        from releases.fresh import publication_scope, is_paused
        if is_paused():
            return 'durably paused'
        pubs, sessions = publication_scope()
        run_due(gateway=TelegramGateway(), publication_ids=pubs, session_ids=sessions)
    else:
        run_due(gateway=TelegramGateway())
    return "processed"
