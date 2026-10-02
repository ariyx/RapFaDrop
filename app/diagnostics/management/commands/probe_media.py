import json

from django.core.management.base import BaseCommand, CommandError

from diagnostics.probes import acquire_and_ffprobe


class Command(BaseCommand):
    help = "Temporarily download one media candidate, inspect it with ffprobe, and delete it."

    def add_arguments(self, parser):
        parser.add_argument("url")
        parser.add_argument("--timeout", type=int, default=180)

    def handle(self, *args, **options):
        result = acquire_and_ffprobe(options["url"], options["timeout"])
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
        if not result["observed"]:
            raise CommandError("Media acquisition failed; see structured output.")
