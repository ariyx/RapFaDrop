from django.core.management.base import BaseCommand, CommandError

from sources.adapters import SourceUnavailable
from sources.models import ArtistSource
from sources.services import baseline_source


class Command(BaseCommand):
    help = "Fetch and store an enabled, verified source snapshot without publishing it."

    def add_arguments(self, parser):
        parser.add_argument("source_id", type=int)

    def handle(self, *args, **options):
        try:
            source = ArtistSource.objects.select_related("artist").get(pk=options["source_id"])
        except ArtistSource.DoesNotExist as exc:
            raise CommandError("Source not found") from exc
        if not source.artist.enabled or not source.enabled or source.verification != ArtistSource.Verification.VERIFIED:
            raise CommandError("Baseline requires an enabled artist and enabled, verified source")
        if source.platform != ArtistSource.Platform.SOUNDCLOUD:
            raise CommandError("Spotify release baselining is unavailable until a bounded release method is proven")
        try:
            run = baseline_source(source)
        except SourceUnavailable as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Baseline {run.status}: {run.item_count} source items; no publication work created."))
