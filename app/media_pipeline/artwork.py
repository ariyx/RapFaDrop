from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from django.conf import settings

from .providers import ProviderError


def fetch_recorded_soundcloud_artwork(source_url, destination, timeout=20):
    """Fetch only yt-dlp-recorded SoundCloud CDN artwork; never follow arbitrary URLs."""
    return _fetch_recorded_artwork(source_url, destination, timeout, spotify=False)


def fetch_recorded_spotify_artwork(source_url, destination, timeout=20):
    """Fetch a frozen official album cover only from Spotify's pinned image CDN."""
    return _fetch_recorded_artwork(source_url, destination, timeout, spotify=True)


def _fetch_recorded_artwork(source_url, destination, timeout, *, spotify):
    current = source_url
    session = requests.Session()
    session.trust_env = True
    try:
        for _ in range(4):
            parts = urlsplit(current)
            allowed = (parts.hostname == "i.scdn.co" and parts.path.startswith("/image/")) if spotify else (parts.hostname and parts.hostname.endswith(".sndcdn.com"))
            if parts.scheme != "https" or not allowed or parts.username or parts.password or parts.port not in {None, 443}:
                raise ProviderError("Recorded artwork URL is outside the approved provider CDN", retryable=False)
            response = session.get(current, timeout=timeout, stream=True, allow_redirects=False)
            if response.is_redirect:
                next_url = urljoin(current, response.headers.get("Location", ""))
                response.close()
                current = next_url
                continue
            response.raise_for_status()
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > settings.MEDIA_MAX_ARTWORK_BYTES:
                response.close()
                raise ProviderError("Artwork exceeds the configured size limit", retryable=False)
            target = Path(destination)
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            size = 0
            with target.open("xb") as output:
                for chunk in response.iter_content(64 * 1024):
                    size += len(chunk)
                    if size > settings.MEDIA_MAX_ARTWORK_BYTES:
                        raise ProviderError("Artwork exceeds the configured size limit", retryable=False)
                    output.write(chunk)
            response.close()
            target.chmod(0o600)
            return target
        raise ProviderError("Artwork provider redirected too many times", retryable=False)
    except (requests.RequestException, OSError, ValueError) as exc:
        raise ProviderError(f"Artwork fetch failed: {type(exc).__name__}") from exc
    finally:
        session.close()
