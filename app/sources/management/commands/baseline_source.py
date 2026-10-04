from django.core.management.base import BaseCommand, CommandError

from sources.adapters import SourceUnavailable
from sources.models import ArtistSource
from sources.services import baseline_source


class Command(BaseCommand):
    help = "Fetch and store an enabled, verified source snapshot without publishing it."

    def add_arguments(self, parser):
        parser.add_argument("source_id", type=int)
        parser.add_argument("--while-disabled", action="store_true", help="Baseline a verified disabled source before activation; requires discovery-only isolation.")

    def handle(self, *args, **options):
        try:
            source = ArtistSource.objects.select_related("artist").get(pk=options["source_id"])
        except ArtistSource.DoesNotExist as exc:
            raise CommandError("Source not found") from exc
        if source.verification != ArtistSource.Verification.VERIFIED or (not options['while_disabled'] and (not source.artist.enabled or not source.enabled)):
            raise CommandError("Baseline requires an enabled artist and enabled, verified source")
        if not source.release_polling_available:
            raise CommandError("Release baselining is unavailable for this source configuration")
        try:
            run = baseline_source(source, allow_disabled=options['while_disabled'])
        except (SourceUnavailable, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Baseline {run.status}: {run.item_count} source items; no publication work created."))
