from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.utils import timezone

from sources.models import ArtistSource
from sources.services import poll_due_sources, poll_source


class Command(BaseCommand):
    help = "Poll due, enabled, verified sources; provider failures are isolated."

    def add_arguments(self, parser):
        parser.add_argument("--source-id", type=int, help="Poll one source instead of all due sources")
        parser.add_argument("--force", action="store_true", help="Make the selected eligible source due now")

    def handle(self, *args, **options):
        if options["force"] and not options["source_id"]:
            raise CommandError("--force requires --source-id")
        if options["source_id"]:
            try:
                source = ArtistSource.objects.select_related("artist").get(pk=options["source_id"])
            except ArtistSource.DoesNotExist as exc:
                raise CommandError("Source not found") from exc
            if not source.artist.enabled or not source.enabled or source.verification != ArtistSource.Verification.VERIFIED:
                raise CommandError("Manual poll requires an enabled artist and enabled, verified source")
            if options["force"]:
                source.next_poll_at = timezone.now()
                source.save(update_fields=("next_poll_at", "updated_at"))
            elif source.next_poll_at is not None and source.next_poll_at > timezone.now():
                raise CommandError("Source is not due; pass --force for an operator-requested development poll")
            result = poll_source(source)
            self.stdout.write(f"source={source.pk} platform={source.platform} result={result}")
            return
        results = poll_due_sources()
        for source_id, result in results.items():
            self.stdout.write(f"source={source_id} platform={ArtistSource.objects.get(pk=source_id).platform} result={result}")
        self.stdout.write(self.style.SUCCESS(f"Processed {len(results)} due source(s)."))
