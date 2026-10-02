from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

import yt_dlp
from django.conf import settings


class SourceUnavailable(RuntimeError):
    """Raised when a provider capability is not currently proven/available."""


class SoundCloudAdapter:
    platform = "soundcloud"

    def list_recent(self, source):
        if not source.canonical_url:
            raise ValueError("SoundCloud source has no canonical profile URL")
        options = {"quiet": True, "no_warnings": True, "skip_download": True,
                   "socket_timeout": 30, "extract_flat": False, "playlistend": 100}
        with yt_dlp.YoutubeDL(options) as ydl:
            profile = ydl.extract_info(source.canonical_url, download=False)
        entries = profile.get("entries") or []
        return [normalize_soundcloud_item(item) for item in entries if item]


class SpotifyAdapter:
    platform = "spotify"
    identity_capability = "public oEmbed identity only; sampled at M0"
    release_polling_available = False

    @staticmethod
    def status():
        mode = settings.SPOTIFY_DISCOVERY_MODE
        if mode != "unavailable":
            return "Unavailable: unsupported Spotify discovery mode; no adapter selected"
        return "Unavailable: public identity/embed subsets do not prove current release listing; authenticated API access unavailable"

    def list_recent(self, source):
        raise SourceUnavailable(self.status())


def _release_time(item):
    value = item.get("release_timestamp") or item.get("timestamp")
    if value:
        return datetime.fromtimestamp(value, tz=timezone.utc)
    for key in ("release_date", "upload_date"):
        value = item.get(key)
        if value:
            try:
                return datetime.strptime(value, "%Y%m%d").replace(tzinfo=timezone.utc)
            except ValueError:
                try:
                    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
    return None


def normalize_soundcloud_item(item):
    """Keep a metadata allowlist; never persist descriptions, tokens, or media URLs."""
    native_id = item.get("id")
    if native_id is None:
        raise ValueError("SoundCloud item did not include a stable native ID")
    item_url = item.get("webpage_url") or ""
    parts = urlsplit(item_url)
    if parts.scheme != "https" or parts.hostname not in {"soundcloud.com", "www.soundcloud.com"}:
        item_url = ""
    else:
        item_url = urlunsplit(("https", "soundcloud.com", parts.path.rstrip("/"), "", ""))
    safe = {key: item.get(key) for key in (
        "id", "title", "uploader", "uploader_id", "channel_id", "duration",
        "timestamp", "release_timestamp", "release_date", "upload_date", "album",
        "album_type", "track_number", "availability",
    ) if item.get(key) is not None}
    return {
        "native_item_id": str(native_id),
        "title": str(item.get("title") or "")[:500],
        "canonical_url": item_url,
        "source_release_at": _release_time(item),
        "metadata": {key: value for key, value in safe.items() if key not in {"id", "title"}},
        "sanitized_raw_data": safe,
    }
