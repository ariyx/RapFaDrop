import json
import time

from django.core.management.base import BaseCommand, CommandError

from diagnostics.probes import ProbeTimeout
from diagnostics.spotify_public import METHODS, probe_method
from sources.management.commands.seed_sources import SEEDS


class Command(BaseCommand):
    help = "Opt-in, bounded public Spotify discovery experiment; no database writes or credentials."

    def add_arguments(self, parser):
        parser.add_argument("--artists", nargs="+", default=["Sijal", "Fadaei", "Ho3ein", "Yas", "Hichkas"])
        parser.add_argument("--rounds", type=int, choices=(1, 2), default=2)
        parser.add_argument("--timeout", type=int, default=12)

    def handle(self, *args, **options):
        seeds = {name: spotify_id for name, _, spotify_id, _ in SEEDS}
        if not 1 <= options["timeout"] <= 20 or len(options["artists"]) > 5 or any(name not in seeds for name in options["artists"]):
            raise CommandError("Use at most five seed artists and a 1–20 second request bound")
        for round_number in range(1, options["rounds"] + 1):
            for name in options["artists"]:
                for method in METHODS:
                    try:
                        with ProbeTimeout(options["timeout"] * 2 + 2):
                            result = probe_method(seeds[name], method, timeout=options["timeout"])
                    except TimeoutError:
                        result = {"artist_id": seeds[name], "method": method, "error": "overall method deadline exceeded", "items": []}
                    self.stdout.write(json.dumps({"artist": name, "round": round_number, **result}, ensure_ascii=False))
                    self.stdout.flush()
                    # Explicit manual samples, never automatic access-control retries.
                    time.sleep(1)
