from django.core.management.base import BaseCommand
from django.db import transaction

from sources.models import Artist, ArtistSource, SourceAuditEvent


SEEDS = [
    ("Hossein Tiem", "حسین تی‌ام", "2ZgLpNVB2qQTifvz3l8xIY", "justiem"),
    ("Hesam Tiem", "حسام تی‌ام", "6XsyaCX2jJLaS82vJoiiWi", "hesamtiem"),
    ("Amin Tijay", "امین تیجی", "3JS9sHeI06RtolBR5s5O0L", "amintijayy"),
    ("Mamazi", "ممزی", "4L42EENVSu2ZE8cwhVVeh8", "mamazioma"),
    ("Sajad Shahi", "سجاد شاهی", "3VzZOmXc8pZRfNxoiliE1A", "sajadshahi"),
    ("Sinazza", "سیناتزا", "2su0Z5gmtSRUreY11ocP8M", "sinazza"),
    ("Hoomaan", "هومان", "6UJS43T8NPhmWmmpFY0hzP", "hoomaanxx"),
    ("Vinak", "ویناک", "1sKlyO3CCEvjeTN6Uck39S", "elvinako"),
    ("Dorcci", "دورچی", "6jj9lOTeZC28LkPoXK9hiT", "dorcci"),
    ("Hiphopologist", "هیپ‌هاپولوژیست", "45YMrIBH74j8e2wNlRSSdK", "hiphopologistsoroush"),
    ("Chvrsi", "چرسی", "7Hj58arwOvp6exTny9r5Ie", "chvrsi"),
    ("Poori", "پوری", "5uEEhLt2ETeApnvs40MOxk", "godpoori"),
    ("Arta", "آرتا", "6gPKjPIXbBBnuLyLEq79Sz", "arta-mir"),
    ("Koorosh Wantons", "کوروش وانتونز", "1UjD9VWeqDDlDSvNlnFTdl", "koorowsh420"),
    ("Canis", "کنیس", "6OPdGHW0QD6WknWX2tlzJm", "icanisofficial"),
    ("Sijal", "سیجل", "5F0BGBdSL945Bzxrq8aGbn", "sijalofficial"),
    ("Behzad Leito", "بهزاد لیتو", "4zNEj5bkHE0kNSpfIwgdvu", "bezilei"),
    ("Sepehr Khalse", "سپهر خلسه", "2SFwcduI9cdZsG6UxnBm3C", "Khal3music"),
    ("Shayea", "شایع", "3QNGoF6VzVNnkpjJDT3NHq", "shayeaofficial"),
    ("Fadaei", "فدایی", "5aWL79DpD45MzDMwCTZqsN", None),
    ("Sina Sae", "سینا ساعی", "5er043agmHdVZkWTxL0Lpk", "sinasae"),
    ("Hichkas", "هیچ‌کس", "2X90kCLyxyPeJ5nynJGbvT", "hichkasofficial"),
    ("Yas", "یاس", "7b8pXheEOc28fyFJnQzqmL", "yastunes"),
    ("Reza Pishro", "رضا پیشرو", "0u4qrFczDmAsJesHPgbnru", "pishromusic"),
    ("Ho3ein", "حصین", "5vVveQB8n4kETe67waTS3t", None),
    ("Tohi", "حسین تهی", "7pBXdJN9S9N9nNifjPixET", "tohi"),
    ("Erfan", "عرفان", "1yPzb9mqugowOfUs2vIOgL", "erfanpaydar"),
    ("Amir Tataloo", "امیر تتلو", "5CEosSs2y4M9THNGI6mej8", None),
    ("Sohrab Mj", "سهراب ام‌جی", "2B4DnBz9uzJN5nPgLEHCt7", "mjsohrab"),
    ("Mehrad Hidden", "مهراد هیدن", "0jCVTRvQkILbJvpviTpvd1", "mehradhiddenofficial"),
]


class Command(BaseCommand):
    help = "Import the approved 30 artists and disabled, unverified candidate profiles."

    @transaction.atomic
    def handle(self, *args, **options):
        created_artists = created_sources = 0
        for name, persian_alias, spotify_id, soundcloud_slug in SEEDS:
            artist, created = Artist.objects.get_or_create(official_name=name)
            created_artists += created
            aliases = list(artist.aliases or [])
            if persian_alias not in aliases:
                aliases.append(persian_alias)
                artist.aliases = aliases
                artist.save(update_fields=("aliases", "updated_at"))
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
