import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings


_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_SECRET_RE = re.compile(r"(?i)(token|signature|sig|key|auth|policy)=([^&\s]+)")


def redact_diagnostic(value):
    value = _URL_RE.sub("[redacted-url]", str(value or ""))
    value = _SECRET_RE.sub(r"\1=[redacted]", value)
    return " ".join(value.split())[:1000]


@dataclass(frozen=True)
class ProviderProbe:
    provider: str
    source_url: str
    provider_item_id: str
    title: str
    duration_seconds: float | None
    uploader: str
    artwork_source_url: str = ""
    evidence: dict | None = None


@dataclass(frozen=True)
class DownloadResult:
    path: Path
    provider_item_id: str
    title: str
    duration_seconds: float | None
    uploader: str
    evidence: dict


class ProviderError(RuntimeError):
    def __init__(self, message, *, retryable=True, evidence=None):
        self.retryable = retryable
        self.evidence = evidence or {}
        super().__init__(redact_diagnostic(message))


class YtDlpProvider:
    """Anonymous, SoundCloud-only yt-dlp provider with bounded subprocess calls."""

    name = "yt-dlp"

    def can_handle(self, source_url):
        parts = urlsplit(source_url or "")
        return (
            parts.scheme == "https"
            and parts.hostname in {"soundcloud.com", "www.soundcloud.com"}
            and bool(parts.path.strip("/"))
            and "/sets/" not in parts.path
        )

    def _run(self, args, timeout):
        command = [sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-cookies", "--no-cache-dir", "--no-playlist", "--quiet", "--no-warnings", *args]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(f"yt-dlp operation timed out after {timeout} seconds") from exc
        except OSError as exc:
            raise ProviderError(f"yt-dlp could not start: {exc}") from exc
        if completed.returncode:
            diagnostics = redact_diagnostic(completed.stderr or completed.stdout or "provider exited unsuccessfully")
            raise ProviderError(f"yt-dlp failed ({completed.returncode}): {diagnostics}")
        return completed.stdout

    def probe(self, source_url, timeout=None):
        if not self.can_handle(source_url):
            raise ProviderError("yt-dlp M3 provider supports only SoundCloud track URLs", retryable=False)
        timeout = int(timeout or settings.MEDIA_DOWNLOAD_TIMEOUT_SECONDS)
        output = self._run(["--socket-timeout", str(min(timeout, 45)), "--skip-download", "--dump-single-json", "--", source_url], timeout)
        try:
            info = json.loads(output)
        except (TypeError, ValueError) as exc:
            raise ProviderError("yt-dlp returned unreadable probe data") from exc
        if info.get("_type") == "playlist" or info.get("entries"):
            raise ProviderError("Set/playlist acquisition is not enabled in M3", retryable=False)
        artwork_url = info.get("thumbnail") or ""
        artwork_parts = urlsplit(artwork_url)
        if not (artwork_parts.scheme == "https" and artwork_parts.hostname and artwork_parts.hostname.endswith(".sndcdn.com")):
            artwork_url = ""
        elif artwork_url:
            artwork_url = urlunsplit((artwork_parts.scheme, artwork_parts.netloc, artwork_parts.path, "", ""))
        return ProviderProbe(
            provider=self.name,
            source_url=source_url,
            provider_item_id=str(info.get("id") or ""),
            title=str(info.get("title") or "")[:500],
            duration_seconds=_positive_float(info.get("duration")),
            uploader=str(info.get("uploader") or info.get("channel") or "")[:300],
            artwork_source_url=artwork_url,
            evidence={"extractor": str(info.get("extractor_key") or "SoundCloud"), "format_count": len(info.get("formats") or [])},
        )

    def download(self, probe, destination, timeout=None):
        timeout = int(timeout or settings.MEDIA_DOWNLOAD_TIMEOUT_SECONDS)
        destination = Path(destination).resolve()
        destination.mkdir(parents=True, exist_ok=True, mode=0o700)
        max_mb = max(1, settings.MEDIA_MAX_UPLOAD_BYTES // (1024 * 1024))
        output_template = str(destination / "source.%(ext)s")
        args = [
            "--socket-timeout", str(min(timeout, 45)), "--retries", "1", "--fragment-retries", "1",
            "--max-filesize", f"{max_mb}M", "--format", "bestaudio/best", "--output", output_template,
            "--", probe.source_url,
        ]
        self._run(args, timeout)
        files = [path for path in destination.iterdir() if path.is_file() and not path.name.endswith((".part", ".ytdl"))]
        if len(files) != 1:
            raise ProviderError("yt-dlp did not produce exactly one candidate file")
        if files[0].is_symlink():
            raise ProviderError("yt-dlp output is a symbolic link", retryable=False)
        path = files[0].resolve()
        if path.parent != destination:
            raise ProviderError("yt-dlp output escaped its assigned temporary directory", retryable=False)
        if path.stat().st_size > settings.MEDIA_MAX_UPLOAD_BYTES:
            raise ProviderError("download exceeded the configured media size limit", retryable=False)
        return DownloadResult(path, probe.provider_item_id, probe.title, probe.duration_seconds, probe.uploader, probe.evidence or {})


def _positive_float(value):
    try:
        result = float(value)
        return result if result > 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


PROVIDERS = {YtDlpProvider.name: YtDlpProvider()}
