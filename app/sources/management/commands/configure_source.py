from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from sources.models import ArtistSource, SourceAuditEvent


class Command(BaseCommand):
    help = "Enable/disable and verify/unverify one candidate source."

    def add_arguments(self, parser):
        parser.add_argument("source_id", type=int)
        parser.add_argument("--enable", action="store_true")
        parser.add_argument("--disable", action="store_true")
        parser.add_argument("--verify", action="store_true")
        parser.add_argument("--unverify", action="store_true")
        parser.add_argument("--native-profile-id")

    def handle(self, *args, **options):
        try:
            source = ArtistSource.objects.select_related("artist").get(pk=options["source_id"])
        except ArtistSource.DoesNotExist as exc:
            raise CommandError("Source not found") from exc
        if options["enable"] and options["disable"] or options["verify"] and options["unverify"]:
            raise CommandError("Choose at most one of each opposing option")
        changes = {}
        if options["enable"]:
            changes["enabled"] = True
            source.next_poll_at = timezone.now()
            if not source.artist.enabled:
                source.artist.enabled = True
                source.artist.save(update_fields=("enabled", "updated_at"))
        if options["disable"]:
            changes["enabled"] = False
        if options["verify"]:
            changes["verification"] = ArtistSource.Verification.VERIFIED
            source.next_poll_at = timezone.now()
        if options["unverify"]:
            changes["verification"] = ArtistSource.Verification.UNVERIFIED
        if options["native_profile_id"]:
            changes["native_profile_id"] = options["native_profile_id"]
        if not changes:
            raise CommandError("No changes requested")
        before = {key: getattr(source, key) for key in changes}
        for key, value in changes.items():
            setattr(source, key, value)
        source.save()
        SourceAuditEvent.objects.create(source=source, artist=source.artist, event_type="source_configured", detail={"before": {k: str(v) for k, v in before.items()}, "after": {k: str(v) for k, v in changes.items()}})
        self.stdout.write(self.style.SUCCESS(f"Updated source {source.pk}: enabled={source.enabled}, verification={source.verification}"))
