import json

from django.core.management.base import BaseCommand, CommandError

from releases.models import ProcessingQueueItem

from media_pipeline.services import MediaRequestError, acquire_candidate


class Command(BaseCommand):
    help = "Acquire and validate media for one confidently identified M2 queue item."

    def add_arguments(self, parser):
        parser.add_argument("--queue-id", required=True, type=int)
        parser.add_argument("--provider", default=None, help="Provider name; defaults to the first registered provider in RAPFADROP_MEDIA_PROVIDER_ORDER.")

    def handle(self, *args, **options):
        try:
            queue = ProcessingQueueItem.objects.get(pk=options["queue_id"])
            candidate = acquire_candidate(queue, provider_name=options["provider"])
        except (ProcessingQueueItem.DoesNotExist, MediaRequestError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps({
            "candidate_id": candidate.pk,
            "track_id": candidate.track_id,
            "release_id": candidate.release_id,
            "provider": candidate.provider,
            "state": candidate.state,
            "attempt_count": candidate.attempt_count,
            "last_outcome": candidate.last_outcome,
            "retry_due_at": candidate.retry_due_at.isoformat() if candidate.retry_due_at else None,
            "error": candidate.last_error,
        }, ensure_ascii=False, indent=2))
