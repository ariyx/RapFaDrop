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
        "audio_bitrate_bps": _integer(stream.get("bit_rate")),
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
    provenance = provenance or {}
    rate = int(facts.get("audio_bitrate_bps") or facts.get("measured_bitrate_bps") or 0)
    preferred = facts.get("codec_name") == "mp3" and 300000 <= rate <= 340000 and not provenance.get("transcoded_from_lossy")
    return {
        "delivery_tier": 2 if preferred else 1 if delivery_eligible(facts) else 0,
        "codec_name": facts.get("codec_name", ""),
        "audio_bitrate_bps": rate,
        "transcoded_from_lossy": bool(provenance.get("transcoded_from_lossy")),
        "measured_bitrate_bps": int(facts.get("measured_bitrate_bps") or 0),
        "sample_rate_hz": int(facts.get("sample_rate_hz") or 0),
        "channels": int(facts.get("channels") or 0),
        "provenance_confidence": int((provenance or {}).get("provenance_confidence", 0)),
        "ranking_basis": "Complete matched MP3 near 320k preferred unless known lossy transcode; compressed fallback. Nominal bitrate is not authenticity proof; cross-codec fidelity is not measured.",
    }


def delivery_eligible(facts):
    return facts.get("codec_name") in {"mp3", "aac"}


def quality_key(rank):
    # Codec preference is a delivery policy, not a claim of equivalent perceptual quality.
    return (rank.get("delivery_tier", 1), rank.get("audio_bitrate_bps", rank.get("measured_bitrate_bps", 0)), rank.get("provenance_confidence", 0))


def quality_improved(new, old):
    if new.get("transcoded_from_lossy"):
        return False
    if new.get("delivery_tier", 1) != old.get("delivery_tier", 1):
        return new.get("delivery_tier", 1) > old.get("delivery_tier", 1)
    if new.get("codec_name") != old.get("codec_name"):
        return False  # A numeric cross-codec bitrate comparison cannot prove an upgrade.
    return new.get("audio_bitrate_bps", new.get("measured_bitrate_bps", 0)) > old.get("audio_bitrate_bps", old.get("measured_bitrate_bps", 0))


def _number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _integer(value):
    number = _number(value)
    return int(number) if number is not None and number > 0 else None
