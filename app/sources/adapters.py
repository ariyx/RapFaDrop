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
        if not isinstance(profile, dict) or profile.get("entries") is None:
            raise SourceUnavailable("SoundCloud profile response lacks a complete entry list")
        entries = list(profile["entries"])
        if len(entries) >= options['playlistend'] or any(not entry for entry in entries):
            raise SourceUnavailable("SoundCloud profile response is truncated or reaches the 100-entry bound")
        items = [normalize_soundcloud_item(item) for item in entries]
        if len({item['native_item_id'] for item in items}) != len(items):
            raise SourceUnavailable("SoundCloud profile response repeats a native item ID")
        return items


class SpotifyAdapter:
    platform = "spotify"
    identity_capability = "SpotifyScraper artist identity; requires explicit verification"

    def __init__(self):
        self.last_probe = None

    def _call(self, method, *args):
        if settings.SPOTIFY_DISCOVERY_MODE != "spotifyscraper":
            raise SourceUnavailable(self.status())
        from .spotify_scraper import SpotifyScraperDiscovery
        adapter = SpotifyScraperDiscovery()
        try:
            return getattr(adapter, method)(*args)
        finally:
            if method == 'fetch_item' and self.last_probe and adapter.last_probe:
                self.last_probe = {key: self.last_probe[key] + adapter.last_probe[key]
                                   for key in ('requests', 'pages', 'elapsed_seconds')}
            else:
                self.last_probe = adapter.last_probe

    @staticmethod
    def status():
        mode = settings.SPOTIFY_DISCOVERY_MODE
        if mode == "spotifyscraper":
            return "SpotifyScraper 3.9.2 discovery enabled; individual sources still require identity verification and baseline"
        if mode == "unavailable":
            return "Unavailable: Spotify discovery is disabled by configuration"
        return "Unavailable: unsupported Spotify discovery mode; no adapter selected"

    def list_recent(self, source):
        return self._call('list_recent', source)

    def resolve_profile(self, source):
        return self._call('resolve_profile', source)

    def fetch_item(self, source, item):
        return self._call('fetch_item', source, item)


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
