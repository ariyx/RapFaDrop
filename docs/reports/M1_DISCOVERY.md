# M1 source discovery and baseline report

Observed locally on 2026-10-02. No server deployment, provider profile probe, Telegram API call, publication, media download, or M2 implementation occurred during M1.

## Implemented

- Django `sources` app with `Artist`, `ArtistSource`, `SourceItem`, `BaselineRun`, and `SourceAuditEvent`; database uniqueness protects artist/platform pairs and source item `(platform, native_item_id)` identity.
- Idempotent `seed_sources` imports 30 approved artists, 30 Spotify profile candidates, and 27 SoundCloud candidates. All artist/source enable flags are false and verification is `unverified`. Fadaei, Ho3ein, and Amir Tataloo have no SoundCloud source rows; Mahdyar was not substituted.
- Artist aliases are stored in a JSON field and seeded from the Persian aliases in `PRODUCT_SPEC.md`. Explicit UTF-8 reading confirmed that the spec bytes/text are correct; the earlier apparent mojibake came from PowerShell's default output decoding. Reseeding preserves owner-added aliases.
- Separate SoundCloud and Spotify adapters. SoundCloud uses metadata-only `yt-dlp` profile extraction, currently bounded to the latest 100 entries per request. Persisted metadata is allowlisted and excludes descriptions, format lists, and signed/media URLs.
- Poll eligibility requires an enabled artist, enabled source, verified identity, and due timestamp. The first eligible poll baselines; subsequent polls upsert stable source IDs. Baseline writes are transactional, interrupted running runs are reused, and replay is idempotent. Per-source retry delay is exponential from that source's poll interval, capped at six hours; a failed source does not stop another.
- Celery Beat checks due sources every minute. Django admin and management commands expose status, source configuration/verification, baseline, due poll, and forced single-source development polling. No release/publication, download, or Telegram behavior exists.
- Spotify profile identity is informational only. Spotify release polling explicitly reports unavailable because M0's `spotipyFree` release requests timed out and oEmbed exposed no releases or pagination.

## Observed local results

- `docker compose config --quiet`: passed.
- Docker Compose image build: passed with the preconfigured local proxy routed through the Docker host; its value was not recorded.
- Compose startup: web, worker, beat, PostgreSQL, and Redis all reported healthy.
- `python manage.py migrate --noinput`: passed; `migrate --check`: passed; `makemigrations --check --dry-run`: no changes detected; `manage.py check`: no issues.
- `manage.py test`: 17 tests passed. Source polling tests use fakes and do not make provider calls. A dedicated Unicode regression test seeds `حسین تی‌ام`, reads it back from PostgreSQL, checks the management status output, and verifies the Persian alias appears in the authenticated Django admin artist list.
- `GET /health/`: `{"status":"ok","database":"ok"}`.
- Local dev reseed: 30 artists, 57 candidate sources, Persian aliases present on all 30 artists, 0 enabled artists, 0 enabled sources, 0 verified sources, 0 `SourceItem` rows, 0 baseline runs; missing SoundCloud list exactly `Fadaei`, `Ho3ein`, `Amir Tataloo`. The command was idempotent (0 artists/sources created) and filled aliases without removing existing owner-managed aliases.
- Observed PostgreSQL readback for Hossein Tiem preserved `حسین تی‌ام`; `source_status` printed the correct alias for both candidate sources. The authenticated admin changelist also rendered the exact alias in the automated test.
- Automated fixture baseline: duplicate platform/native IDs create one stored item; a simulated mid-write interruption rolls back and retry completes without duplicates. A failing due source received its own retry schedule while a healthy source succeeded.
- UTF-8 inspection: `Get-Content -Encoding UTF8 docs\PRODUCT_SPEC.md` displayed the source Persian names correctly; PowerShell's default `Get-Content` display was the misleading layer. Alias seed strings were copied from the explicit UTF-8 output.
- `git diff --check`: passed before delivery (final commit checks recorded in the completion handoff).

## Provider evidence and open gates

No new provider probes were made in M1: every seeded profile remains disabled/unverified, and regular tests intentionally use fakes. The prior read-only M0 evidence remains in [`M0_FEASIBILITY.md`](M0_FEASIBILITY.md): SoundCloud extraction succeeded for the supplied Sijal track and set, not for a candidate profile feed; Spotify oEmbed identified three sample profiles while `spotipyFree` release requests timed out. Therefore broad SoundCloud profile coverage, request/rate-limit behavior and Spotify release discovery remain unproven. Do not enable a seed until its profile identity and recent official works are verified.

Other open gates: the profile adapter is intentionally bounded to 100 recent entries per request; baseline completeness beyond that window is not claimed. The default 90-second per-source interval is a starting value, not a measured sustainable interval. Persian aliases round-trip correctly for the tested seed/model/admin path; the broader SoundCloud and Spotify provider gates remain open.

## Next milestone proposal (not started)

After owner review and source identity verification, M2 can add canonical releases/tracks, cross-source matching, album/edition relationships, review states and a durable work queue. Spotify remains gated unless a bounded recent-release method is first demonstrated. Media acquisition, Telegram publication, and production deployment were not part of this M1 task.
