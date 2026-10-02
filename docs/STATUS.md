# Project status and handoff

Updated: 2026-10-02. This records observed local M0 implementation and verification. Check Git and the actual environment before relying on it.

## Current state

- Work began from clean `main` / `origin/main` at `dbad4e5519554b1939b89a2269d7cc9a44dcf4c2` (`docs: establish project baseline`). The delivery commit and server result are recorded after the normal push/deployment sequence.
- M0 now contains a Python 3.13/Django 5.2.17 foundation, PostgreSQL, Redis, non-root Celery worker/beat, database-backed `/health/`, pinned dependencies, placeholder-only `.env.example`, opt-in diagnostic commands and focused tests. No product release schema or Telegram publishing exists.
- Local Compose build/start, built-in migrations, Django check, focused tests and all five service health checks passed. The health endpoint returned `{"status":"ok","database":"ok"}`. Detailed provider evidence is in [`reports/M0_FEASIBILITY.md`](reports/M0_FEASIBILITY.md).
- SoundCloud is verified only for the supplied track/set. Spotify is partially verified for public oEmbed identity on three profiles; the sampled `spotipyFree` release path timed out, so recent-release coverage remains open. One `yt-dlp` SoundCloud download was completed, measured and deleted; no independent fallback was verified.
- No Telegram API call or production channel post occurred. Server deployment is not claimed until it is observed.

## M0 acceptance evidence

1. Passed locally: Compose config/build/start, five healthy services, migrations, Django check/tests and database health.
2. Passed for supplied examples: repeatable sanitized SoundCloud track/set output with IDs, metadata, ordering, album evidence and media variants.
3. Partial: public Spotify identity works for three samples without Premium; recent releases/pagination failed to return and remain an open gate.
4. Passed for one candidate: `yt-dlp` acquisition plus `ffprobe`; no fallback is claimed.
5. Secret/media hygiene and no-production-post checks remain part of the pre-push review; push and server results are recorded after they occur.

## Decisions, assumptions and gates

| Topic | Current rule or observation | Verification / remaining choice |
| --- | --- | --- |
| Artist list | Thirty selected artists and candidate Spotify/SoundCloud URLs are in `PRODUCT_SPEC.md`. | Verify identity and recent releases per profile before activation; three SoundCloud profiles are unconfirmed. |
| SoundCloud | The supplied Sijal track and set work through `yt-dlp 2026.08.19`; the set carries explicit album evidence. | Do not generalize from two URLs; measure profile coverage and sustainable polling in M1. |
| Spotify | oEmbed confirms profile identity without Premium; `spotipyFree` timed out for all three samples. | Resolve a bounded recent-release method before scheduling Spotify polling. No full audio is available from this evidence. |
| Audio providers | One SoundCloud candidate downloaded completely and measured as AAC ~160 kbps. | No independent fallback is verified. Test one only after demonstrating an independent failure path. |
| Source monitoring | SoundCloud and Spotify must remain independent. Initial interval hypotheses remain unverified. | Measure reliability, rate limits and release latency before selecting intervals. |
| Telegram | M0 contains no gateway or channel configuration. | Later live tests must use an isolated test channel; never use production for tests. |
| Admin and deployment | M0 provides Django's built-in schema and health only. | Full admin/domain schema, HTTPS, backup/restore and Telegram behavior belong to later milestones. |

## Next implementation task after owner review: M1

Do not begin M1 automatically. The proposed next slice is to resolve a bounded public Spotify recent-release method, then implement disabled/unverified source records and idempotent first baselines for the 30 seed profiles while keeping SoundCloud and Spotify failures isolated. Production Telegram publishing remains out of scope.

## Handoff record to maintain

After each milestone or material design change, update this file with the observed Git SHA, implemented scope, tests/probe outputs (or durable links to reports), unresolved failures, server result and exact next milestone. Keep planned work separate from observed results. Update `PRODUCT_SPEC.md` for a changed owner decision, `IMPLEMENTATION.md` for architecture/acceptance changes, and `DEPLOYMENT.md` for verified operational procedure changes.
