import json

from django.core.management.base import BaseCommand, CommandError

from diagnostics.probes import probe_soundcloud


class Command(BaseCommand):
    help = "Run an opt-in, read-only SoundCloud metadata probe."

    def add_arguments(self, parser):
        parser.add_argument("urls", nargs="+")
        parser.add_argument("--timeout", type=int, default=45)

    def handle(self, *args, **options):
        results = [probe_soundcloud(url, options["timeout"]) for url in options["urls"]]
        self.stdout.write(json.dumps(results, ensure_ascii=False, indent=2))
        if not all(item["observed"] for item in results):
            raise CommandError("One or more SoundCloud probes failed; see structured output.")
