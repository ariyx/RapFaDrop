# Project status and handoff

Updated: 2026-10-02. M1 is implemented and verified locally; the pushed implementation SHA is recorded below. No deployment was performed, per the M1 instruction.

## Current state

- Work began from clean `main` / `origin/main` at `ea8320b21fae97e2141e092ed76097187dbae257`, the M0 status handoff. M1 implementation/report commit `ea04651c8e61624d04d53d41323a60c19481c37e` and Persian-alias follow-up commit `5bf7aed9a4be40a98d3c25ead32e3eea8ffefc32` were pushed normally to `origin/main`; `git ls-remote origin refs/heads/main` confirmed the follow-up SHA. The untracked M1 task document is now included in Git.
- The M0 implementation commit is `0c4952d30fb5abd8f4c0718ca5c51eee7c37985b`; its provider and deployment observations remain in [`reports/M0_FEASIBILITY.md`](reports/M0_FEASIBILITY.md).
- M1 adds durable artist/source/item/baseline/audit records, disabled/unverified seed data, separate SoundCloud and Spotify adapters, scheduled due-only polling, idempotent history snapshots, per-source backoff, admin screens and operator commands. No release queue, media download, Telegram integration or publication exists.
- Local Compose build/start, migrations, migration drift check, Django check, all 17 automated tests, all five service health checks and `/health/` passed. Seed import observed 30 artists and 57 sources: 30 Spotify and 27 SoundCloud. Persian aliases from the UTF-8 product spec persist on all 30 artists and render in management/admin; the authenticated admin round-trip test passed. All sources remain disabled/unverified; missing SoundCloud sources remain blank for Fadaei, Ho3ein and Amir Tataloo. The local database has zero source items and zero baseline runs because no candidate was verified or activated.
- Baseline/poll behavior passed fake-backed tests: duplicate IDs persist once, interrupted writes roll back and retry, and a failing due source backs off without blocking a healthy source. Persian aliases from the UTF-8 product specification are seeded and tested through persistence, management output and the Django admin list. The admin identifies SoundCloud profile polling as implemented but empirically unprobed; Spotify release polling is explicitly unavailable.
- M1 did not run new provider probes because all profile candidates remain unverified. Existing M0 SoundCloud track/set evidence does not establish profile-feed coverage; Spotify's sampled release path timed out and oEmbed supplied identity only. Details and open gates are in [`reports/M1_DISCOVERY.md`](reports/M1_DISCOVERY.md).
- No server deployment, Telegram call or production channel post occurred for M1. Local Compose services were stopped after verification; the PostgreSQL volume was preserved.
- SoundCloud is verified only for the supplied track/set. Spotify is partially verified for public oEmbed identity on three profiles; the sampled `spotipyFree` release path timed out, so recent-release coverage remains open. One `yt-dlp` SoundCloud download was completed, measured and deleted; no independent fallback was verified.
- No Telegram API call or production channel post occurred. Server deployment could not begin: `ssh -o BatchMode=yes -o ConnectTimeout=10 root@91.107.178.12` returned `Permission denied (publickey,password)`. No server checkout, configuration, data or service was changed.

## M0 acceptance evidence

1. Passed locally: Compose config/build/start, five healthy services, migrations, Django check/tests and database health.
2. Passed for supplied examples: repeatable sanitized SoundCloud track/set output with IDs, metadata, ordering, album evidence and media variants.
3. Partial: public Spotify identity works for three samples without Premium; recent releases/pagination failed to return and remain an open gate.
4. Passed for one candidate: `yt-dlp` acquisition plus `ffprobe`; no fallback is claimed.
5. Passed locally/push: `.env` stayed ignored, only placeholders were committed, secret/media scans were clean, and `main` was pushed without force. Server verification is blocked by unavailable SSH authentication and is not marked passed.

## M1 acceptance evidence

1. Passed locally: Compose config/build/start, migrations and migration drift check, Django system check, 17 tests, five healthy services and the database-backed health response.
2. Seeded and observed: 30 artists, 57 disabled/unverified profile candidates (30 Spotify, 27 SoundCloud); no fan substitution for the three missing SoundCloud profiles.
3. Passed with fakes: initial baseline snapshots, idempotent item IDs, simulated interruption/retry, sanitized remote metadata, inactive-source skipping, source-specific exponential backoff and independent source outcomes.
4. Spotify: release polling remains unavailable; identity-only M0 evidence is partial.
5. No M1 source profile probes, deployment, Telegram API call or publication occurred.
6. UTF-8 verified: product-spec Persian aliases were read explicitly as UTF-8, seeded, read back from PostgreSQL and displayed by `source_status` and the authenticated admin list test. All seed alias fields are populated; owner-added aliases survive reseeding.

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

## Next milestone after owner review: M2 — identity and queue

M1 is complete. Before enabling any seed, verify its profile identity and recent official works; empirically test SoundCloud profile-feed coverage and resolve an explicitly bounded Spotify recent-release method. Keep Spotify unavailable until that gate passes. The proposed M2 scope is canonical release/track identity, cross-source matching, edition/album relationships, review states and a durable queue. Do not infer those behaviors from M1 source items; no M2 code has been started.

## Handoff record to maintain

After each milestone or material design change, update this file with the observed Git SHA, implemented scope, tests/probe outputs (or durable links to reports), unresolved failures, server result and exact next milestone. Keep planned work separate from observed results. Update `PRODUCT_SPEC.md` for a changed owner decision, `IMPLEMENTATION.md` for architecture/acceptance changes, and `DEPLOYMENT.md` for verified operational procedure changes.
