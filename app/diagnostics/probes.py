import json
import signal
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import yt_dlp
import requests

TRACKING_KEYS = {"si", "utm_campaign", "utm_content", "utm_medium", "utm_source", "utm_term"}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class ProbeTimeout:
    def __init__(self, seconds):
        self.seconds = seconds

    def __enter__(self):
        def raise_timeout(signum, frame):
            raise TimeoutError(f"provider operation exceeded {self.seconds} seconds")

        self.previous_handler = signal.signal(signal.SIGALRM, raise_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, exc_type, exc_value, traceback):
        signal.alarm(0)
        signal.signal(signal.SIGALRM, self.previous_handler)


def stable_url(url):
    parts = urlsplit(url)
    query = urlencode([(key, value) for key, value in parse_qsl(parts.query) if key.lower() not in TRACKING_KEYS])
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), query, ""))


def clean_formats(formats):
    fields = ("format_id", "ext", "protocol", "acodec", "vcodec", "abr", "tbr", "filesize", "filesize_approx")
    return [{key: item.get(key) for key in fields if item.get(key) is not None} for item in formats or []]


def soundcloud_item(info, order=None):
    fields = (
        "id", "title", "uploader", "uploader_id", "channel", "channel_id",
        "duration", "timestamp", "upload_date", "release_timestamp", "release_date", "webpage_url",
        "album", "album_type", "track_number", "availability",
    )
    result = {key: info.get(key) for key in fields if info.get(key) is not None}
    description = info.get("description")
    result["description_present"] = bool(description)
    result["description_length"] = len(description or "")
    if "webpage_url" in result:
        result["webpage_url"] = stable_url(result["webpage_url"])
    if order is not None:
        result["order"] = order
    result["formats"] = clean_formats(info.get("formats"))
    return result


def classify_collection(info):
    evidence = {key: info.get(key) for key in ("title", "album", "album_type") if info.get(key)}
    evidence["description_present"] = bool(info.get("description"))
    evidence["description_length"] = len(info.get("description") or "")
    explicit = str(info.get("album_type") or "").lower()
    if explicit in {"album", "ep", "single"}:
        classification = "LP" if explicit == "album" else explicit.upper()
        confidence = "source-explicit"
    else:
        classification = "uncertain-playlist-or-release"
        confidence = "review-required"
    return {"classification": classification, "confidence": confidence, "evidence": evidence}


def probe_soundcloud(url, timeout=45):
    started = time.monotonic()
    probed_at = utc_now()
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "socket_timeout": timeout,
        "extract_flat": False,
        "playlistend": 100,
    }
    result = {
        "probe": "soundcloud",
        "probe_time_utc": probed_at,
        "first_observed_time_utc": probed_at,
        "source_url": url,
        "stable_source_url": stable_url(url),
        "tool_versions": {"yt_dlp": yt_dlp.version.__version__},
        "observed": False,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
        entries = list(info.get("entries") or [])
        if entries:
            result.update({
                "observed": True,
                "kind": "set",
                "native_id": info.get("id"),
                "title": info.get("title"),
                "owner": info.get("uploader") or info.get("channel"),
                "track_count": len(entries),
                "classification": classify_collection(info),
                "tracks": [soundcloud_item(item, index) for index, item in enumerate(entries, 1)],
            })
        else:
            result.update({"observed": True, "kind": "track", "item": soundcloud_item(info)})
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)[:500]}
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result


def spotify_artist(client, artist_id, limit=5, timeout=20):
    started = time.monotonic()
    probed_at = utc_now()
    result = {
        "probe": "spotify",
        "probe_time_utc": probed_at,
        "first_observed_time_utc": probed_at,
        "artist_id": artist_id,
        "source_url": f"https://open.spotify.com/artist/{artist_id}",
        "observed": False,
    }
    try:
        with ProbeTimeout(timeout):
            artist = client.artist(artist_id)
        with ProbeTimeout(timeout):
            albums_response = client.artist_albums(artist_id, include_groups="album,single,compilation", limit=limit)
        items = albums_response.get("items", albums_response if isinstance(albums_response, list) else [])
        albums = []
        for album in list(items or [])[:limit]:
            albums.append({key: album.get(key) for key in ("id", "name", "album_type", "release_date", "release_date_precision", "total_tracks") if album.get(key) is not None})
        result.update({
            "observed": True,
            "verification_status": "verified",
            "method": "spotipyFree",
            "artist": {key: artist.get(key) for key in ("id", "name", "genres", "popularity") if artist.get(key) is not None},
            "recent_releases": albums,
            "pagination": {key: albums_response.get(key) for key in ("limit", "offset", "next", "previous", "total") if isinstance(albums_response, dict) and albums_response.get(key) is not None},
            "capabilities": {"public_metadata": True, "premium_required": False, "full_audio": False},
        })
    except Exception as exc:
        result["adapter_error"] = {"type": type(exc).__name__, "message": str(exc)[:500]}
        try:
            response = requests.get(
                "https://open.spotify.com/oembed",
                params={"url": result["source_url"]},
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            result.update({
                "observed": True,
                "verification_status": "partially-verified",
                "method": "spotify-oembed",
                "artist": {"id": artist_id, "name": payload.get("title")},
                "recent_releases": [],
                "pagination": {},
                "rate_limit": {
                    key: response.headers.get(key)
                    for key in ("Retry-After", "X-RateLimit-Limit", "X-RateLimit-Remaining")
                    if response.headers.get(key) is not None
                },
                "capabilities": {
                    "public_profile_identity": True,
                    "recent_releases": False,
                    "pagination": False,
                    "premium_required": False,
                    "full_audio": False,
                },
            })
        except Exception as fallback_exc:
            result["oembed_error"] = {"type": type(fallback_exc).__name__, "message": str(fallback_exc)[:500]}
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result


def acquire_and_ffprobe(url, timeout=180):
    started = time.monotonic()
    result = {
        "probe": "media-acquisition",
        "probe_time_utc": utc_now(),
        "source_url": stable_url(url),
        "provider": "yt-dlp",
        "tool_versions": {"yt_dlp": yt_dlp.version.__version__},
        "observed": False,
    }
    try:
        with tempfile.TemporaryDirectory(prefix="rapfadrop-probe-") as directory:
            template = str(Path(directory) / "candidate.%(ext)s")
            options = {"quiet": True, "no_warnings": True, "noprogress": True, "outtmpl": template, "socket_timeout": 45, "noplaylist": True}
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                path = Path(ydl.prepare_filename(info))
            command = ["ffprobe", "-v", "error", "-show_entries", "format=duration,bit_rate,size:stream=codec_type,codec_name,bit_rate,sample_rate,channels", "-of", "json", str(path)]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=True)
            result.update({
                "observed": True,
                "complete_download": True,
                "native_id": info.get("id"),
                "title": info.get("title"),
                "ffprobe": json.loads(completed.stdout),
                "temporary_file_deleted": True,
            })
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)[:500]}
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result
