import json
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from PIL import Image

from media_pipeline.models import MediaCandidate
from media_pipeline.services import process_manual_upload
from publication.gateway import GatewayError, TelegramGateway, guard_target
from publication.models import Publication
from publication.services import PublicationError, perform, publish_single, upgrade_single
from releases.models import CanonicalRelease, ReleaseCredit, ReleaseTrack, SourceMatch, Track, TrackCredit
from sources.models import Artist, ArtistSource, SourceItem


class Command(BaseCommand):
    help = "Opt-in disposable generated audio send/edit/reply/delete in an isolated test channel; credentials are never printed."

    def add_arguments(self, parser):
        parser.add_argument("--configuration-status", action="store_true")
        parser.add_argument("--confirm-test-send", action="store_true")

    def handle(self, *args, **options):
        configured = {
            "live_enabled": settings.TELEGRAM_LIVE_ENABLED,
            "test_mode": settings.TELEGRAM_MODE == "test",
            "bot_token_configured": bool(settings.TELEGRAM_BOT_TOKEN),
            "isolated_test_target_configured": bool(settings.TELEGRAM_TEST_CHAT_ID),
        }
        if options["configuration_status"]:
            self.stdout.write(json.dumps({"configuration": configured, "live_probe": "not_run"}))
            return
        if not options["confirm_test_send"] or not all(configured.values()):
            raise CommandError("Probe requires explicit confirmation, enabled test mode, local bot credentials and an isolated test target")
        target = guard_target(settings.TELEGRAM_TEST_CHAT_ID)
        gateway = TelegramGateway()
        # Resolve username/numeric aliases before creating synthetic fixture state.
        gateway._guard_live(target)
        root = Path(settings.MEDIA_ROOT).resolve()
        root.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix="m4-telegram-probe-", dir=root)).resolve()
        candidates = []
        result = {"time_utc": timezone.now().isoformat(), "configuration": configured, "live_probe": "started", "synthetic_fixture": True}
        try:
            actor, _ = get_user_model().objects.get_or_create(username="m4-integration-fixture", defaults={"is_staff": True, "is_active": False})
            artist, _ = Artist.objects.get_or_create(official_name="M4 generated test fixture")
            source, _ = ArtistSource.objects.get_or_create(artist=artist, platform="soundcloud", defaults={"native_profile_id": "synthetic-not-a-provider-profile", "canonical_url": "https://example.invalid/m4-generated-fixture"})
            release = CanonicalRelease.objects.create(title="M4 generated audio probe", release_type="single", state="approved")
            track = Track.objects.create(official_title="M4 generated audio probe", duration_seconds=2)
            TrackCredit.objects.create(track=track, artist=artist)
            ReleaseCredit.objects.create(release=release, artist=artist)
            ReleaseTrack.objects.create(release=release, track=track, position=1)
            item = SourceItem.objects.create(platform="soundcloud", native_item_id="synthetic-m4-"+uuid.uuid4().hex, source=source, title=track.official_title, canonical_url="https://example.invalid/m4-generated-fixture", metadata={"duration": 2, "synthetic_fixture": True}, first_observed_at=timezone.now())
            match = SourceMatch.objects.create(source_item=item, track=track, release=release, confidence=100, state="approved", matching_method="explicit-generated-integration-fixture", evidence={"synthetic_fixture": True, "not_provider_evidence": True})
            cover = work / "generated-cover.jpg"
            Image.new("RGB", (500, 500), (30, 90, 150)).save(cover)
            for bitrate in (64, 192):
                audio = work / f"generated-{bitrate}.mp3"
                subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=500:duration=2", "-c:a", "libmp3lame", "-b:a", f"{bitrate}k", "-y", str(audio)], check=True, timeout=30)
                candidate = MediaCandidate.objects.create(track=track, release=release, source_match=match, provider="manual", expected_duration_seconds=2, provenance={"synthetic_fixture": True})
                with audio.open("rb") as audio_stream, cover.open("rb") as art_stream:
                    candidate = process_manual_upload(candidate, File(audio_stream, name=audio.name), actor=actor, artwork_upload=File(art_stream, name=cover.name), artwork_source_url="https://example.invalid/m4-generated-cover")
                if candidate.state != "ready":
                    raise PublicationError("Generated probe candidate did not pass the M3 pipeline")
                candidates.append(candidate)
            pub = publish_single(candidates[0], target, gateway=gateway)
            if pub.state != "published":
                raise PublicationError("Initial probe send was not confirmed; inspect recorded state")
            original_id = pub.message_id
            pub = upgrade_single(pub, candidates[1], gateway=gateway)
            if pub.state != "published" or pub.message_id != original_id:
                raise PublicationError("Probe edit did not confirm the same message ID")
            reply = Publication.objects.get(original=pub, kind="correction")
            if reply.state != "published":
                raise PublicationError("Correction reply was not confirmed")
            reply = perform(reply, "delete", "probe-cleanup", {}, gateway=gateway)
            pub = perform(pub, "delete", "probe-cleanup", {}, gateway=gateway)
            if reply.state != "deleted" or pub.state != "deleted":
                raise PublicationError("Probe message cleanup was not confirmed")
            result.update({"live_probe": "passed", "message_id": original_id, "same_message_after_edit": True, "correction_message_id": reply.message_id, "correction_deleted": True, "test_audio_post_deleted": True, "publication_id": pub.pk})
            for candidate in candidates:
                directory = Path(candidate.candidate_path).resolve().parent
                if directory.is_relative_to(root) and directory.name == f"candidate-{candidate.pk}" and directory.parent.name == f"track-{candidate.track_id}":
                    shutil.rmtree(directory)
                candidate.state, candidate.preparation_state, candidate.last_outcome = "review_required", "failed", "probe_cleanup"
                candidate.candidate_path = candidate.prepared_path = candidate.artwork_path = ""
                candidate.save()
            result["temporary_media_deleted"] = True
        except (GatewayError, PublicationError, OSError, subprocess.SubprocessError):
            result.update({"live_probe": "incomplete", "error": "Inspect durable publication attempts; no automatic resend was performed", "retained_for_reconciliation": True})
        finally:
            if work.is_relative_to(root) and work.name.startswith("m4-telegram-probe-"):
                shutil.rmtree(work)
        self.stdout.write(json.dumps(result, indent=2))
        if result["live_probe"] != "passed":
            raise CommandError("Live probe did not fully complete; inspect its durable state before retrying")
