import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from media_pipeline.models import MediaCandidate
from releases.models import CanonicalRelease
from publication.gateway import GatewayError, TelegramGateway
from publication.services import PublicationError, advance_album, prepare_album, publish_single


class Command(BaseCommand):
    help = "Explicitly publish a ready candidate or pre-staged album to the configured isolated test channel."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--candidate-id", type=int)
        group.add_argument("--album-id", type=int)
        parser.add_argument("--confirm-test-send", action="store_true")

    def handle(self, *args, **options):
        if not options["confirm_test_send"] or not settings.TELEGRAM_TEST_CHAT_ID:
            raise CommandError("Explicit confirmation and a local isolated test-channel ID are required")
        try:
            gateway = TelegramGateway()
            if options["candidate_id"]:
                result = publish_single(MediaCandidate.objects.get(pk=options["candidate_id"]), settings.TELEGRAM_TEST_CHAT_ID, gateway=gateway)
            else:
                session = prepare_album(CanonicalRelease.objects.get(pk=options["album_id"]), settings.TELEGRAM_TEST_CHAT_ID)
                result = advance_album(session, gateway=gateway)
        except (GatewayError, PublicationError, MediaCandidate.DoesNotExist, CanonicalRelease.DoesNotExist) as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(json.dumps({"record_id": result.pk, "state": result.state, "message_id": getattr(result, "message_id", None), "cursor": getattr(result, "cursor", None)}))
