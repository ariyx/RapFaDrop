from django.core.management.base import BaseCommand
from django.db import transaction

from sources.models import Artist, ArtistSource, SourceAuditEvent


SEEDS = [
    ("Hossein Tiem", "2ZgLpNVB2qQTifvz3l8xIY", "justiem"),
    ("Hesam Tiem", "6XsyaCX2jJLaS82vJoiiWi", "hesamtiem"),
    ("Amin Tijay", "3JS9sHeI06RtolBR5s5O0L", "amintijayy"),
    ("Mamazi", "4L42EENVSu2ZE8cwhVVeh8", "mamazioma"),
    ("Sajad Shahi", "3VzZOmXc8pZRfNxoiliE1A", "sajadshahi"),
    ("Sinazza", "2su0Z5gmtSRUreY11ocP8M", "sinazza"),
    ("Hoomaan", "6UJS43T8NPhmWmmpFY0hzP", "hoomaanxx"),
    ("Vinak", "1sKlyO3CCEvjeTN6Uck39S", "elvinako"),
    ("Dorcci", "6jj9lOTeZC28LkPoXK9hiT", "dorcci"),
    ("Hiphopologist", "45YMrIBH74j8e2wNlRSSdK", "hiphopologistsoroush"),
    ("Chvrsi", "7Hj58arwOvp6exTny9r5Ie", "chvrsi"),
    ("Poori", "5uEEhLt2ETeApnvs40MOxk", "godpoori"),
    ("Arta", "6gPKjPIXbBBnuLyLEq79Sz", "arta-mir"),
    ("Koorosh Wantons", "1UjD9VWeqDDlDSvNlnFTdl", "koorowsh420"),
    ("Canis", "6OPdGHW0QD6WknWX2tlzJm", "icanisofficial"),
    ("Sijal", "5F0BGBdSL945Bzxrq8aGbn", "sijalofficial"),
    ("Behzad Leito", "4zNEj5bkHE0kNSpfIwgdvu", "bezilei"),
    ("Sepehr Khalse", "2SFwcduI9cdZsG6UxnBm3C", "Khal3music"),
    ("Shayea", "3QNGoF6VzVNnkpjJDT3NHq", "shayeaofficial"),
    ("Fadaei", "5aWL79DpD45MzDMwCTZqsN", None),
    ("Sina Sae", "5er043agmHdVZkWTxL0Lpk", "sinasae"),
    ("Hichkas", "2X90kCLyxyPeJ5nynJGbvT", "hichkasofficial"),
    ("Yas", "7b8pXheEOc28fyFJnQzqmL", "yastunes"),
    ("Reza Pishro", "0u4qrFczDmAsJesHPgbnru", "pishromusic"),
    ("Ho3ein", "5vVveQB8n4kETe67waTS3t", None),
    ("Tohi", "7pBXdJN9S9N9nNifjPixET", "tohi"),
    ("Erfan", "1yPzb9mqugowOfUs2vIOgL", "erfanpaydar"),
    ("Amir Tataloo", "5CEosSs2y4M9THNGI6mej8", None),
    ("Sohrab Mj", "2B4DnBz9uzJN5nPgLEHCt7", "mjsohrab"),
    ("Mehrad Hidden", "0jCVTRvQkILbJvpviTpvd1", "mehradhiddenofficial"),
]


class Command(BaseCommand):
    help = "Import the approved 30 artists and disabled, unverified candidate profiles."

    @transaction.atomic
    def handle(self, *args, **options):
        created_artists = created_sources = 0
        for name, spotify_id, soundcloud_slug in SEEDS:
            artist, created = Artist.objects.get_or_create(official_name=name)
            created_artists += created
            defaults = {"native_profile_id": spotify_id, "canonical_url": f"https://open.spotify.com/artist/{spotify_id}"}
            _, created = ArtistSource.objects.get_or_create(artist=artist, platform=ArtistSource.Platform.SPOTIFY, defaults=defaults)
            created_sources += created
            if soundcloud_slug:
                _, created = ArtistSource.objects.get_or_create(
                    artist=artist,
                    platform=ArtistSource.Platform.SOUNDCLOUD,
                    defaults={"canonical_url": f"https://soundcloud.com/{soundcloud_slug}"},
                )
                created_sources += created
        SourceAuditEvent.objects.create(event_type="seed_imported", detail={"artists_created": created_artists, "sources_created": created_sources, "seed_artists": len(SEEDS)})
        self.stdout.write(self.style.SUCCESS(f"Seed verified: {Artist.objects.count()} artists; {ArtistSource.objects.count()} sources ({created_artists} and {created_sources} created this run)."))
