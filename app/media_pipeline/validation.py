import hashlib
import json
import math
import subprocess
from pathlib import Path

from django.conf import settings


class MediaValidationError(ValueError):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size


def probe_audio(path, timeout=None):
    path = Path(path)
    if path.is_symlink():
        raise MediaValidationError("Candidate path is not a regular file")
    path = path.resolve(strict=True)
    if not path.is_file():
        raise MediaValidationError("Candidate path is not a regular file")
    if path.stat().st_size <= 0:
        raise MediaValidationError("Candidate file is empty")
    command = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=format_name,duration,bit_rate,size:stream=codec_type,codec_name,duration,bit_rate,sample_rate,channels",
        "-of", "json", str(path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout or settings.MEDIA_FFPROBE_TIMEOUT_SECONDS, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MediaValidationError(f"ffprobe failed: {type(exc).__name__}") from exc
    if result.returncode:
        raise MediaValidationError("ffprobe rejected the candidate as corrupt or unreadable")
    try:
        facts = json.loads(result.stdout)
    except (TypeError, ValueError) as exc:
        raise MediaValidationError("ffprobe returned invalid structured output") from exc
    streams = facts.get("streams") or []
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if not audio_streams:
        raise MediaValidationError("Candidate contains no audio stream")
    duration = _number((facts.get("format") or {}).get("duration"))
    if duration is None:
        duration = max((_number(stream.get("duration")) or 0 for stream in audio_streams), default=0) or None
    if duration is None or duration <= 0:
        raise MediaValidationError("Candidate has no measurable audio duration")
    file_hash, size = sha256_file(path)
    stream = audio_streams[0]
    measured_bitrate = int(round(size * 8 / duration))
    format_report = facts.get("format") or {}
    return {
        "sha256": file_hash,
        "file_size_bytes": size,
        "duration_seconds": duration,
        "format_name": str(format_report.get("format_name") or ""),
        "format_bitrate_bps": _integer(format_report.get("bit_rate")),
        "measured_bitrate_bps": measured_bitrate,
        "codec_name": str(stream.get("codec_name") or ""),
        "sample_rate_hz": _integer(stream.get("sample_rate")),
        "channels": _integer(stream.get("channels")),
        "audio_stream_count": len(audio_streams),
    }


def compare_duration(observed, expected):
    if expected is None or expected <= 0:
        return {"expected_seconds": expected, "observed_seconds": observed, "status": "missing_expected"}, "review_required"
    difference = observed - expected
    tolerance = max(settings.MEDIA_EXPECTED_DURATION_TOLERANCE_SECONDS, expected * 0.05)
    ratio = observed / expected
    report = {
        "expected_seconds": round(expected, 3),
        "observed_seconds": round(observed, 3),
        "difference_seconds": round(difference, 3),
        "tolerance_seconds": round(tolerance, 3),
        "observed_ratio": round(ratio, 4),
    }
    if ratio < settings.MEDIA_TRUNCATION_RATIO:
        report["status"] = "truncated_or_preview"
        return report, "invalid"
    if abs(difference) > tolerance:
        report["status"] = "material_mismatch"
        return report, "review_required"
    report["status"] = "match"
    return report, "valid"


def quality_rank(facts, provenance=None):
    # Actual measured bytes/duration take precedence over provider-advertised rates.
    return {
        "measured_bitrate_bps": int(facts.get("measured_bitrate_bps") or 0),
        "sample_rate_hz": int(facts.get("sample_rate_hz") or 0),
        "channels": int(facts.get("channels") or 0),
        "provenance_confidence": int((provenance or {}).get("provenance_confidence", 0)),
        "ranking_basis": "ffprobe file-size/duration and observed audio properties; advertised bitrate ignored",
    }


def _number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _integer(value):
    number = _number(value)
    return int(number) if number is not None and number > 0 else None
