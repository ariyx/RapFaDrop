# M3 media acquisition, validation and preparation

Observed locally on 2026-10-02. This report covers M3 only; no deployment or M4 work occurred.

## Implementation and boundaries

- Added durable `MediaCandidate`, `MediaAttempt` and `MediaAuditEvent` records linked to M2 canonical track/release and source-match IDs. Candidate state, retry timing, provenance, validation facts, audio hash/size, artwork/tag results, and quality rank are persisted.
- Added an anonymous, bounded yt-dlp provider for SoundCloud tracks, configurable ordered selection through `RAPFADROP_MEDIA_PROVIDER_ORDER`, an explicit acquisition command, and a separate opt-in empirical probe. Acquisition is not scheduled. It requires a pending/retry M2 queue item with a high-confidence approved match. Spotify has no full-audio path and is routed to review without a download attempt.
- Persistent media storage is configurable and mounted as a named volume shared by Compose web/worker. Staging is private and removed after success or failure. Ready files remain immutable; duplicate hashes reuse prepared media.
- ffprobe requires an audio stream and measurable duration; it records SHA-256, size, duration, codec, sample rate, channels and measured bitrate. Defaults allow `max(5 seconds, 5%)` duration variance, route missing/materially mismatched expected duration to review, and reject recordings below 90% of expected length. Limits are configurable.
- Quality ranking uses observed file size/duration, stream properties and provenance confidence, not provider bitrate labels. The original validated audio is retained; tags are written to a separate prepared copy.
- Mutagen writes canonical title, credited artist(s), album, date and track/disc numbers for MP3/WAVE, MP4/M4A, FLAC, Ogg Vorbis and Ogg Opus. Configured channel tags map by format; unsupported MP4 fields are reported. Readback verifies core fields and embedded art. Fixture tests include Persian and Latin metadata.
- Official artwork evidence is restricted to HTTPS SoundCloud CDN URLs and query credentials are removed. Images are limited by configured size, JPEG/PNG type and dimensions, then embedded when supported. Authenticated admin uploads share the same validation, provenance, tagging, audit and state pipeline.
- No M3 code calls Telegram, posts media, enables sources, or starts a baseline.

## Empirical SoundCloud probe

The explicitly confirmed `probe_media_pipeline` command ran against the supplied public URL `https://soundcloud.com/sijalofficial/vaghti-raft` at `2026-10-02T12:30:34Z`. Tool versions were yt-dlp `2026.08.19`, Mutagen `1.48.1`, Pillow `12.3.0`, ffprobe/ffmpeg `7.1.5-0+deb13u1`.

The provider resolved SoundCloud item ID `2368809320`, title “Vaghti Raft”, uploader “Sijal”, expected duration 176.046 seconds and recorded official artwork evidence. The downloaded AAC/M4A was 3,552,597 bytes, SHA-256 `7b64edb0064e72ca075206889f2bc24dd5aeb49ba91145bef2c776d4453ec868`, measured duration 176.054 seconds, 44.1 kHz stereo, one audio stream and 161,432 bit/s measured bitrate. Duration differed by 0.008 seconds (within the configured 8.802-second tolerance). Validation was `valid` / `match`.

The prepared M4A embedded a validated 1080×1080 JPEG artwork (104,526 bytes). Title, artist, album/channel suffix, configured channel fields and artwork all passed format-aware readback. The report identified publisher, author URL, conductors and initial key as unsupported MP4 fields. Download, artwork and prepared files lived in a temporary directory and were removed (`temporary_bytes_deleted: true`). This is one observed sample, not a reliability or broad-coverage claim.

## Local verification

- `docker compose config --quiet`: passed.
- `docker compose build`: web, worker and beat images built.
- `docker compose up -d --force-recreate`: all services started.
- `python manage.py migrate --noinput`: no migrations pending; `migrate --check`: passed.
- `makemigrations --check --dry-run`: no changes detected.
- `python manage.py check`: no issues.
- `python manage.py test -v 1`: 44 tests passed, including generated audio fixtures, ordered provider selection, failure/retry and provenance preservation, duration/corruption/preview cases, observed-quality ranking, configured tag policy and MP3/M4A artwork readback, authenticated upload/audit, Spotify review-only behavior, cleanup, deduplication and concurrent requests.
- `docker compose ps`: all five services healthy. `GET /health/` returned `{"status":"ok","database":"ok"}`.
- `git diff --check`: passed. Repository review found no Telegram Bot API call in M3 and no media fixture/download artifact staged.

## Open gates

Only yt-dlp/SoundCloud is implemented; no independent fallback was tested. Spotify full audio remains unavailable. The supplied SoundCloud sample does not establish broad source coverage, quality, rights clearance or long-term availability. Operator confirmation of canonical metadata and artwork rights remains necessary. Production paths, backups, operational quotas, and all Telegram publication behavior are outside M3 and remain for later owner review.
