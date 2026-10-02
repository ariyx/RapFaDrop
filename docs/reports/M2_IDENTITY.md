# M2 identity, deduplication, review, and queue report

Observed locally on 2026-10-02. This report covers M2 only. No server deployment, live provider request, source activation, baseline run, media processing, Telegram API call, or M3 implementation occurred.

## Implemented

- Added the `releases` Django app and PostgreSQL migration for canonical releases/tracks, ordered release membership and prior-single relationships, source matches, review items, an inert future-work queue, credits, and identity audit events.
- `ingest_source_item()` processes only an already persisted `SourceItem`. It locks that source row, is transaction-safe/idempotent, records deterministic evidence and a matching method, and returns `matched`, `review_required`, `ignored_duplicate`, or `queued`. It does not poll, download, process, or publish anything.
- Identity keys are scoped to the verified artist record, normalized title, release type, and edition. Normalization is comparison-only: NFKC/casefold, Arabic/Persian character equivalents, half-space/whitespace, punctuation, zero-width marks, and common feature separators are handled without changing source or official display strings.
- A verified initial work is queued once. A later high-confidence cross-platform match reuses the same canonical track/release. Same-title works from different artists remain separate. Missing/uncertain duration, material duration conflict, conflicting single release dates, uploader mismatch, unknown collection type, playlist ambiguity, and edition markers route to review. Edition markers create distinct candidates and link to an original when unambiguous; they are never silently merged.
- A later LP/EP reuses an existing single track, preserves track order and points to the prior single membership. The unique queue constraint prevents a second future track job.
- Authenticated Django admin lists and inspects canonical identities, matches, queue entries, audit events, and reviews. Review actions approve, reject, correct, or explicitly requeue with actor/time/audit data. Approval is idempotent. Queue retries update a due time using bounded exponential backoff; no worker/media/publication task was added.

## Invariants and conservative rules

- Source items and their platform/native IDs and sanitized provenance remain immutable inputs to matching.
- `SourceMatch.source_item` and `ReviewItem.source_item` are unique; one source fact cannot acquire parallel matching/review decisions.
- Database constraints protect credited-artist pairs, one source match/review per source item, valid track-to-release associations, release order, queue target and one queue item per canonical track.
- Cross-platform auto-match requires the same canonical artist, equal normalized title, a conclusive duration within `max(5 seconds, 5%)`, and no conflicting single release date more than 180 days apart. This narrow deterministic rule is deliberately conservative; unavailable or inconclusive evidence routes to review.
- A first item from an enabled, verified source attached to an enabled artist is treated as its own canonical candidate; this is not empirical proof that the provider's uploader or catalog is correct. Live source activation is outside M2.
- Release/edition classification is limited to explicit source metadata and named title markers (`remix`, `live`, `instrumental`, `deluxe`, rerelease/remaster). Multiple markers and unclear collection types require review.
- Rejected matches return `ignored_duplicate`; only an explicit requeue action reopens the existing review. Review candidates are not put in the future-work queue until approved/corrected.

## Fixture coverage

All new identity tests use local PostgreSQL fixtures and fake persisted SoundCloud/Spotify `SourceItem` rows; they make no network calls. Coverage includes replay idempotence, cross-platform normalization, same-title/different-artist isolation, uploader and date conflicts, Persian names, all five edition categories, single-before-album linkage, ambiguous playlist and missing-duration review, unrelated-work progress, audited service decisions, authenticated admin inspection/approval, bounded retry times, and concurrent row-locked ingestion. The concurrent test is enabled on PostgreSQL and skipped on other backends.

## Observed local verification

Final clean verification on the M2 worktree:

- `docker compose config --quiet`: passed.
- `docker compose build`: passed for web, worker, and beat.
- `docker compose up -d`: passed; PostgreSQL, Redis, web, worker, and beat reported healthy.
- `python manage.py migrate --noinput`: passed; `python manage.py migrate --check`: passed; `python manage.py makemigrations --check --dry-run`: no changes detected.
- `python manage.py check`: no issues.
- `python manage.py test`: 29 tests passed, including the PostgreSQL concurrency test and authenticated admin review test. Tests use fakes/fixtures; no external source adapter was called.
- `GET /health/`: passed with `{"status":"ok","database":"ok"}`.
- `git diff --check`: passed. Tracked/untracked changes contain source/docs only; no `.env`, credentials, downloaded audio, or media artifact is included.

The local dev database retained its M1 state: the 30 artists and 57 candidate sources remain disabled/unverified, with zero `SourceItem` rows and zero baseline runs. Identity fixtures were isolated in Django's test database. No seeding, activation, or baseline command was run for M2.

## Remaining gates / proposed next milestone

Matching thresholds are initial deterministic policy, not statistically calibrated identity confidence. Live SoundCloud artist/profile coverage and Spotify recent-release discovery remain unproven from M0/M1; no new probes were made here. Human correction tooling is Django admin rather than a custom panel. M3 can be considered only after owner review of this M2 checkpoint; it is not started by this report. Media acquisition, Telegram publication, server deployment, and production rollout remain out of scope.
