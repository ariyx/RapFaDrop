"""Opt-in metadata-only profile and discography probe; never writes models."""

import hashlib
import json
import time

from django.core.management.base import BaseCommand, CommandError

from releases.normalization import normalize_text
from sources.models import ArtistSource
from sources.spotify_scraper import SpotifyScraperDiscovery


NAMES = ("Sijal", "Fadaei", "Ho3ein", "Hichkas", "Yas")


class Command(BaseCommand):
    help = "Read-only bounded SpotifyScraper identity/discography probe for the five researched source records."

    def add_arguments(self, parser):
        parser.add_argument("--names", nargs="+", default=list(NAMES))
        parser.add_argument("--rounds", type=int, choices=(1, 2, 3), default=3)

    def handle(self, *args, **options):
        names = options["names"]
        if len(names) > 5 or len(set(names)) != len(names) or any(name not in NAMES for name in names):
            raise CommandError("Choose at most five distinct researched artist names")
        for name in names:
            source = ArtistSource.objects.select_related("artist").filter(platform="spotify", artist__official_name=name).first()
            if source is None:
                self.stdout.write(json.dumps({"artist": name, "error": "source record missing"}))
                continue
            adapter = SpotifyScraperDiscovery()
            try:
                identity = adapter.resolve_profile(source)
                accepted = {normalize_text(source.artist.official_name), *[normalize_text(alias) for alias in source.artist.aliases or []]}
                match = identity["id"] == source.native_profile_id and normalize_text(identity["name"]) in accepted
                self.stdout.write(json.dumps({"artist": name, "artist_id": source.native_profile_id,
                                              "identity_name": identity["name"], "identity_match": match,
                                              "identity_probe": adapter.last_probe}, ensure_ascii=False))
                self.stdout.flush()
                if not match:
                    continue
                previous = None
                for round_number in range(1, options["rounds"] + 1):
                    items = adapter.list_recent(source)
                    ids = [item["native_item_id"] for item in items]
                    digest = hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()
                    self.stdout.write(json.dumps({"artist": name, "artist_id": source.native_profile_id,
                                                  "round": round_number, "count": len(ids), "id_set_sha256": digest,
                                                  "same_ids_as_previous": None if previous is None else set(ids) == previous,
                                                  "first_release_id": ids[0] if ids else None,
                                                  "probe": adapter.last_probe}, ensure_ascii=False))
                    self.stdout.flush()
                    previous = set(ids)
                    time.sleep(2)
            except Exception as exc:
                self.stdout.write(json.dumps({"artist": name, "artist_id": source.native_profile_id,
                                              "error_type": type(exc).__name__, "error": str(exc),
                                              "probe": adapter.last_probe}, ensure_ascii=False))
                self.stdout.flush()
            time.sleep(2)
