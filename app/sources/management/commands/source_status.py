from django.core.management.base import BaseCommand

from sources.models import ArtistSource
from sources.adapters import SpotifyAdapter


class Command(BaseCommand):
    help = "List artist sources, verification, baseline, poll and error status."

    def handle(self, *args, **options):
        self.stdout.write(f"Spotify discovery: {SpotifyAdapter.status()}")
        for source in ArtistSource.objects.select_related("artist"):
            self.stdout.write(" | ".join((
                str(source.pk), source.artist.official_name, f"aliases={','.join(source.artist.aliases or [])}", source.platform,
                f"artist_enabled={source.artist.enabled}", f"source_enabled={source.enabled}", f"verification={source.verification}",
                f"baseline={source.baseline_completed_at or 'pending'}", f"next={source.next_poll_at or 'unscheduled'}",
                f"failures={source.consecutive_failures}", f"error={source.last_error or '-'}",
                f"release_polling={'implemented/profile-unprobed' if source.release_polling_available else 'unavailable/identity-only'}",
            )))
