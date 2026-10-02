# M2 coding-agent task â€” identity, deduplication, and review queue

Read `AGENTS.md`, `docs/STATUS.md`, `docs/PRODUCT_SPEC.md`,
`docs/IMPLEMENTATION.md`, the completed M0/M1 reports, and
`docs/M1_AGENT_TASK.md` before changing code. Add this file to the repository
as `docs/M2_AGENT_TASK.md` before implementation.

## Goal

Implement M2 only: convert independently observed source items into durable
canonical releases and tracks, prevent duplicate publication work, represent
single-to-album and edition relationships, and route uncertainty to an
admin-visible review queue.

No downloader, file processing, Telegram Bot API call, live release
publication, source activation, real baseline, or server deployment belongs to
this milestone.

## Existing facts that govern this task

- M1 has 30 artists and 57 candidate sources, all disabled and unverified.
- SoundCloud is the only source with limited empirical discovery evidence.
- Spotify recent-release discovery is unavailable. Its source items may still
  be created by tests or future adapters; the identity model must not assume a
  working Spotify poller.
- Source items are durable facts. Preserve their platform/native IDs and do
  not rewrite raw source provenance during matching.

## Required models and state

Add migrations and a clear Django-domain API for the smallest durable model
needed for these concepts:

| Concept | Required behavior |
| --- | --- |
| Canonical release | Stores official title, type (`single`, `lp`, `ep`), edition, official release date, status, and credited artists. One release can have many source matches. |
| Canonical track | Stores official title, artist credits, normalized comparison values, and stable identity where available. A track can exist outside an album. |
| Release track | Associates a track with a release, preserves original order, and permits a prior single relation. |
| Source match | Links a `SourceItem` to a release and optionally a track, carries confidence, evidence, matching method, state, and admin decision. |
| Review item | Captures an uncertain identity, possible duplicate, uncertain album/playlist type, or edition ambiguity; keeps reason/evidence, resolution, actor, and timestamps. |
| Processing queue item | Represents future work without sending anything. It must be idempotent, linked to a canonical item, include a due time and retry/error information, and have an explicit state. |

Use PostgreSQL constraints, transactions, and explicit uniqueness rules. A
Celery retry or two source adapters seeing the same work must create at most
one canonical publication candidate. Do not use Redis as the source of truth.

## Matching rules

Implement a deterministic matching service. Keep it small, explainable, and
covered by tests.

1. Exact platform/native IDs and an existing approved `SourceMatch` win.
2. For cross-platform candidates, compare normalized official title, credited
   artists/aliases, duration when available, release date, collection context,
   and edition markers.
3. Normalize only for comparison. Preserve official source spelling in output
   fields. Normalization must safely handle Persian and Latin aliases,
   whitespace, punctuation, case, zero-width characters, and common feature
   separators. It must never erase the source value.
4. Auto-match only high-confidence, non-conflicting cases. A mismatch in main
   artist, a remix/live/version marker, materially different duration, a
   possible existing publication candidate, or ambiguous LP/EP/playlist type
   creates a review item.
5. An approved match is durable and auditable. A rejected match must not be
   silently proposed again unless new evidence or an explicit re-review action
   exists.
6. Do not auto-merge remixes, live performances, instrumentals, deluxe
   editions, rereleases, or same-title works from different artists.

## Required workflows

### Source item ingestion

Provide a service or task that consumes an already-stored `SourceItem` and
produces one of: `matched`, `review_required`, `ignored_duplicate`, or
`queued`. It must be safe to run repeatedly and safe after an interrupted
transaction.

### Single before album

When a later LP/EP contains an already-canonical single track, link the album
track to the existing canonical track and record the prior-single relation.
Do not create a second canonical track or a second future publication queue
item. M4 will later turn this relationship into channel links.

### Editions

Represent an official instrumental, deluxe, or rerelease as a distinct edition
when evidence shows it is a distinct version. Link it to an original canonical
track or release when known. Send unclear cases to review. Do not decide media
byte equality in M2.

### Admin review

Add authenticated Django admin/panel support sufficient to list, inspect,
approve, reject, correct, and requeue review items. Record actor and decision.
Approval must be idempotent. One open review must not block unrelated source
items.

### Queue and retry

Create queue records only for a confidently identified canonical item that
would need later processing. Do not start media work. A recoverable matching
or processing error uses a due time with bounded exponential backoff; a review
item is not retried as an automatic match loop.

## Required tests

Use fixtures/fakes. Network calls must remain opt-in and excluded from normal
test discovery. Add meaningful tests for at least:

1. Exact duplicate source ingestion is idempotent.
2. A high-confidence SoundCloud/Spotify representation becomes one canonical
   track/release and one future queue item.
3. Different artists with the same title do not auto-match.
4. Persian/Latin artist aliases and official display text survive normalization
and persistence without corrupting either value.
5. Remix, live, instrumental, deluxe, and rerelease candidates do not merge
with an original automatically.
6. A previously observed single becomes the same album track later, with a
prior-single relation and no duplicate future work.
7. Ambiguous album/playlist type and low-confidence matches create review
items, and unrelated candidates continue.
8. Approve/reject/correct review actions are audited and idempotent.
9. A retried task and concurrent ingestion attempt do not create duplicates.
10. Queue retry/backoff updates due time and leaves publication/media work
unstarted.

## Documentation and delivery

- Update `docs/IMPLEMENTATION.md` and `docs/STATUS.md` with observed M2 work.
- Add `docs/reports/M2_IDENTITY.md` containing the data invariants, matching
  thresholds/rules, fixtures used, test results, and remaining empirical gaps.
- Run Docker Compose, migrations, migration-drift check, Django check, full
  automated tests, health checks, and secret/media scans locally.
- Commit focused changes and push normally to `main`.
- Do not deploy to the server during M2. Do not start M3.

## Completion report

Report:

```text
Implemented:
Local commit SHA and pushed branch:
Local checks (command â†’ observed result):
Identity and deduplication fixture results:
Single-before-album and edition results:
Review and queue results:
Documentation updated:
Open gates and proposed M3 scope:
```

Stop after M2 and await the owner's review.