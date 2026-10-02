# M3 coding-agent task — media acquisition, validation, and preparation

Read `AGENTS.md`, `docs/STATUS.md`, `docs/PRODUCT_SPEC.md`, `docs/IMPLEMENTATION.md`, `docs/M2_AGENT_TASK.md`, and the completed M0–M2 reports before changing code. Add this file as `docs/M3_AGENT_TASK.md` before implementation.

## Goal

Implement M3 only: acquire eligible audio candidates through replaceable providers, validate that they are complete playable recordings, prepare official metadata and artwork, and make media ready for a later publication step.

M3 does not send or edit Telegram messages, create channel posts, begin a production poll or baseline, or deploy to the server.

## Existing facts

- M0 observed that `yt-dlp` could acquire the supplied SoundCloud Sijal track. This one sample does not prove coverage or quality for all sources.
- Spotify has no verified recent-release polling or full-audio path. Do not treat a Spotify URL as a file source.
- M2 provides canonical tracks/releases, provenance, reviews, and idempotent future-work queue records. Reuse those IDs.

## Required media model and state

Add the smallest migrations and domain services for a durable `MediaCandidate` linked to a canonical track/release and source evidence. Record provider/source, attempt time and outcome, temporary file location outside Git, content hash and size, observed ffprobe facts, expected-duration comparison, validation/retry state, preparation/tag/artwork state, prepared-file path, provenance, and quality ranking.

Use explicit durable, idempotent states such as `candidate`, `downloading`, `downloaded`, `invalid`, `review_required`, `retry_wait`, `preparing`, and `ready`. A retry must not overwrite a validated candidate or lose its provenance.

## Acquisition rules

1. Define a narrow replaceable provider contract: capability check, probe, download, and structured result/error. Providers do not own canonical matching or publication state.
2. Implement `yt-dlp` first with bounded subprocess timeout, sanitized diagnostics, an explicit output directory, and no credentials/cookies in code, logs, reports, or Git.
3. Add ordered provider policy/configuration. A second provider may be registered as an unverified candidate. Call it an independent fallback only after a real test proves an independent failure path.
4. Request media only for a confidently identified M2 queue item or authenticated manual upload. Ambiguous identity stays in review.
5. On provider failure, retain the candidate record, schedule bounded exponential backoff, preserve error evidence, and allow a later provider/manual-upload path. Never create a link-only placeholder.
6. Clean failed/partial temporary files safely. Retain a ready candidate for M4; no media temp path may enter Git.

## Validation and quality

Validate downloaded and uploaded files with ffprobe. Require an audio stream and compare observed duration to expected source duration when available. Keep duration tolerance and completeness policy configurable, record measured facts, and route missing or materially conflicting evidence to review. Reject known previews, truncation, corruption, and audio-less files.

Preserve the best real source. Rank using observed properties and provenance, not advertised labels. Do not upsample or transcode low-quality audio to claim a quality upgrade.

## Metadata, artwork, and manual upload

1. Create a publishable copy with Mutagen or a format-aware equivalent while preserving the original validated candidate.
2. Write verified official title, main artist credits, release/album, track/disc number, release date, and official artwork when available. Do not replace official identity with the channel name.
3. Implement configurable `@RapFaDrop` channel-tag policy for documented fields. Map by format and record unsupported fields honestly.
4. Accept/fetch artwork only from recorded official source evidence; validate image type/size and embed it for supported formats.
5. Add authenticated admin manual upload for an identified item. It must follow the same hash, ffprobe, validation, artwork, tag, state, and audit pipeline. Restrict types/size via configuration.

## Required tests

Use fixtures/fakes and generated local test audio. Network downloads remain opt-in. Cover at least:

1. Provider failure records a retryable candidate and creates no post.
2. A valid candidate captures ffprobe facts and reaches `ready` after tagging.
3. Missing audio, corrupt file, preview/truncated duration, and material duration mismatch are rejected or reviewed.
4. Repeated/concurrent requests do not duplicate prepared media or queue work.
5. Quality ranking chooses a genuinely better source and rejects fake nominal bitrate upgrades.
6. Tag/artwork values survive format-aware readback; unsupported fields are recorded.
7. Persian and Latin title/artist text survives tagging and readback.
8. Manual admin upload uses the same pipeline and records actor/action.
9. Partial files are cleaned while ready candidates remain available.
10. No path invokes the Telegram Bot API.

## Empirical M3 probe

Provide an opt-in bounded command that runs acquisition, ffprobe, tagging, and readback on the supplied `Vaghti Raft` SoundCloud URL. Record tool versions, UTC time, provenance, measured audio facts, tag/readback outcomes, and redacted errors. Remove disposable test media afterward. It must not run in normal test discovery or publish anything.

## Delivery

- Update `docs/STATUS.md` and `docs/IMPLEMENTATION.md` with observed M3 facts.
- Add `docs/reports/M3_MEDIA.md` covering provider results, validation policy, tag/artwork readback, cleanup, and open gates.
- Run Docker Compose, migrations, migration-drift check, Django check, full tests, health checks, and secret/media scans locally.
- Commit focused changes and push normally to `main`.
- Do not deploy, enable a source, or start M4.

## Completion report

```text
Implemented:
Local commit SHA and pushed branch:
Local checks (command → observed result):
Provider and validation results:
Metadata/artwork readback results:
Manual-upload and cleanup results:
Documentation updated:
Open gates and proposed M4 scope:
```

Stop after M3 and await the owner's review.
