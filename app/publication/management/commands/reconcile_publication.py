from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from publication.models import PublicationAttempt
from publication.services import PublicationError, reconcile


class Command(BaseCommand):
    help = "Record an operator-observed Telegram outcome without any network call."

    def add_arguments(self, parser):
        parser.add_argument("--attempt-id", type=int, required=True)
        parser.add_argument("--actor-id", type=int, required=True)
        parser.add_argument("--decision", choices=("confirmed_success", "confirmed_not_delivered"), required=True)
        parser.add_argument("--evidence", required=True)
        parser.add_argument("--message-id", type=int)
        parser.add_argument("--chat-id")

    def handle(self, *args, **options):
        try:
            pub = reconcile(PublicationAttempt.objects.get(pk=options["attempt_id"]), actor=get_user_model().objects.get(pk=options["actor_id"]), decision=options["decision"], evidence=options["evidence"], message_id=options["message_id"], remote_chat_id=options["chat_id"])
        except (PublicationError, PublicationAttempt.DoesNotExist, get_user_model().DoesNotExist) as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(f"Publication {pub.pk}: {pub.state}")
