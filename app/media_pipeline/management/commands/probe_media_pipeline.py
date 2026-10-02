import json
import subprocess
import tempfile
import time
from pathlib import Path

import mutagen
import yt_dlp
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from PIL import __version__ as pillow_version

from media_pipeline.artwork import fetch_recorded_soundcloud_artwork
from media_pipeline.providers import PROVIDERS, ProviderError, redact_diagnostic
from media_pipeline.tagging import TaggingError, prepare_tagged_copy, validate_artwork
from media_pipeline.validation import compare_duration, probe_audio


class Command(BaseCommand):
    help = "Opt-in bounded SoundCloud acquisition, ffprobe, tag, and readback; temporary files are removed."

    def add_arguments(self, parser):
        parser.add_argument("url")
        parser.add_argument("--title", default="")
        parser.add_argument("--artist", default="")
        parser.add_argument("--timeout", type=int, default=180)
        parser.add_argument("--confirm-download", action="store_true", help="Confirm this command may temporarily download the supplied public SoundCloud track.")

    def handle(self, *args, **options):
        if not options["confirm_download"]:
            raise CommandError("This empirical probe downloads one temporary media file; pass --confirm-download explicitly.")
        timeout = max(15, min(int(options["timeout"]), 240))
        result = {
            "probe": "m3-media-acquisition-validation-preparation",
            "probe_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "provider": "yt-dlp",
            "tool_versions": {
                "yt_dlp": yt_dlp.version.__version__, "mutagen": mutagen.version_string,
                "pillow": pillow_version, "ffprobe": _tool_version("ffprobe"), "ffmpeg": _tool_version("ffmpeg"),
            },
            "source_url": options["url"].split("?", 1)[0].split("#", 1)[0],
            "observed": False,
        }
        provider = PROVIDERS["yt-dlp"]
        try:
            with tempfile.TemporaryDirectory(prefix="rapfadrop-m3-probe-") as temp:
                work = Path(temp)
                info = provider.probe(options["url"], timeout=timeout)
                result["provenance"] = {
                    "source_platform": "soundcloud",
                    "native_item_id": info.provider_item_id,
                    "provider_title": info.title,
                    "provider_uploader": info.uploader,
                    "provider_duration_seconds": info.duration_seconds,
                    "official_artwork_source_url_recorded": bool(info.artwork_source_url),
                }
                downloaded = provider.download(info, work / "download", timeout=timeout)
                facts = probe_audio(downloaded.path)
                comparison, validation = compare_duration(facts["duration_seconds"], info.duration_seconds)
                if validation != "valid":
                    raise TaggingError(f"Bounded empirical media probe did not pass duration policy: {comparison.get('status')}")
                artist = options["artist"].strip() or info.uploader
                title = options["title"].strip() or info.title
                artwork = None
                artwork_result = {"state": "not_provided"}
                if info.artwork_source_url:
                    try:
                        artwork = fetch_recorded_soundcloud_artwork(info.artwork_source_url, work / "artwork.jpg", timeout=min(timeout, 30))
                        artwork_result = {"state": "validated", **validate_artwork(artwork)}
                    except (ProviderError, TaggingError) as exc:
                        artwork = None
                        artwork_result = {"state": "unavailable_or_invalid", "redacted_error": redact_diagnostic(exc)}
                prepared = work / f"prepared{downloaded.path.suffix.lower()}"
                tag_result = prepare_tagged_copy(downloaded.path, prepared, {
                    "title": title,
                    "artists": [artist] if artist else [],
                    "album": title,
                    "track_number": 1,
                    "disc_number": 1,
                }, artwork_path=artwork)
                result.update({
                    "observed": True,
                    "validation": {"status": validation, "complete": True, "duration_comparison": comparison, "ffprobe": facts},
                    "tag_artwork_readback": tag_result,
                    "artwork_source_check": artwork_result,
                    "temporary_bytes_deleted": True,
                })
        except Exception as exc:
            result["error"] = {"type": type(exc).__name__, "message": redact_diagnostic(exc)}
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
        if not result["observed"]:
            raise CommandError("The bounded empirical M3 probe did not complete successfully.")


def _tool_version(executable):
    try:
        completed = subprocess.run([executable, "-version"], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    if completed.returncode:
        return "unavailable"
    return (completed.stdout.splitlines() or ["unknown"])[0][:200]
