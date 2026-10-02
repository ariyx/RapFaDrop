import json

from django.core.management.base import BaseCommand, CommandError

from diagnostics.probes import spotify_artist


class Command(BaseCommand):
    help = "Run an opt-in, read-only public Spotify metadata probe without login."

    def add_arguments(self, parser):
        parser.add_argument("artist_ids", nargs="+")
        parser.add_argument("--limit", type=int, default=5)
        parser.add_argument("--timeout", type=int, default=20)

    def handle(self, *args, **options):
        from SpotipyFree import Spotify

        client = Spotify()
        results = [spotify_artist(client, artist_id, options["limit"], options["timeout"]) for artist_id in options["artist_ids"]]
        output = {"adapter": "spotipyFree", "adapter_version": "1.9.14", "results": results}
        self.stdout.write(json.dumps(output, ensure_ascii=False, indent=2))
        if not all(item["observed"] for item in results):
            raise CommandError("One or more Spotify probes failed; see structured output.")
