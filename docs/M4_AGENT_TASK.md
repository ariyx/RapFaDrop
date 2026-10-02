# M4 coding-agent task — Telegram publication and captions

Read `AGENTS.md`, `docs/STATUS.md`, `docs/PRODUCT_SPEC.md`, `docs/IMPLEMENTATION.md`, `docs/M3_AGENT_TASK.md`, and completed M0–M3 reports before changing code. Add this file as `docs/M4_AGENT_TASK.md` before implementation.

## Goal

Implement M4 only: durable Telegram publication orchestration, safe conditional captions, in-place upgrades, ordered album/EP delivery, retries, and test-channel integration capability.

Do not send to `@RapFaDrop`. Do not deploy to the server. Do not build the full administrator product from M5.

## Preconditions and safety

- M3 `ready` media candidates are the only audio files eligible for sending.
- Telegram credentials and a test-channel chat ID are local configuration only. If they are unavailable, fake gateway tests still run and the live integration gate remains open.
- The production channel ID/username must be blocked by an explicit configuration safeguard in development/test modes. Refuse a send if the configured target is the production channel without an explicit later production mode.
- Never log bot tokens, signed URLs, local media bytes, or Telegram request authorization headers.

## Required durable publication state

Add the smallest migrations/domain services for a `Publication` and `PublicationAttempt` model linked to the M2 canonical item and M3 prepared candidate. Include:

- target channel, kind (`single_audio`, `album_intro`, `album_track_audio`, `edition`), durable uniqueness key, Telegram message ID/URL, caption version, state, timestamps, and error state
- pending send attempt before calling Telegram, response facts afterward, retry due time, reconciliation state, and audit references
- upgrade relation from a prior published message to a better prepared candidate
- album session/cursor data sufficient to preserve order and resume a failed track

Use PostgreSQL constraints and transactions. Celery retry or two workers must not create a second post for one publication identity. Redis locks can help scheduling but are not the durable source of truth.

## Telegram gateway

Define a narrow replaceable gateway around the Bot API. It needs structured operations for:

- send audio with cover/caption
- send album cover/introduction
- edit a published message's audio/caption where Telegram supports it
- send a correction reply
- delete a correction reply
- send an admin notification to a configured review destination

Provide a deterministic fake gateway for tests. Keep a real gateway opt-in through local configuration. Do not use a user account/session automation path.

When a request may have succeeded remotely but the worker loses the response, mark the attempt `uncertain` and stop blind resend. Reconcile with a proven test-channel strategy or create an admin-visible reconciliation record. A failed media edit must never silently send a second replacement post.

## Caption rendering

Create a versioned, configurable template representation and a renderer that emits Telegram-safe entities or escaped supported markup. Remote/source strings are untrusted input. Test rendered output, not only source templates.

Default independent single caption:

```text
DROP                         [bold]

Music Video                  [official URL, optional]
Spotify / SoundCloud         [available labels only]
Album                        [channel album-introduction URL, optional]
Original                     [original-track channel URL, optional]

t.me/RapFaDrop
```

Default album/EP track caption:

```text
LP DROP / EP DROP            [bold; configurable/removable]

Music Video                  [optional]
Spotify / SoundCloud         [available labels only]
Album                        [this album introduction URL]
Original                     [optional]

t.me/RapFaDrop
```

Default LP/EP introduction caption:

```text
TITLE                         [title only, bold]
LP · Artist One × Artist Two
feat. Guest One · Guest Two   [guest names only, italic]

پیش‌تر از این آلبوم منتشر شده:
› Earlier Single One
› Earlier Single Two

Original Album                [optional linked row]
@RapFaDrop
```

Rules:

1. The small prior-single marker is **`›`**. Do not use `•`.
2. Show a row only when its data exists. If just Spotify or SoundCloud exists, show only that label, with no slash.
3. Hide the complete `feat.` and prior-singles blocks when empty.
4. Use official title and artist display values. Channel attribution belongs only in configured template/tag fields.
5. Link prior singles, album, original track, and original album to stored channel publication URLs.
6. Preserve `DROP` on an earlier single when it later gains an Album link.
7. If Telegram's actual caption limit would be exceeded, keep the introduction concise and produce a safe following text post only for overflow prior-single links. Record that post as part of the album session.
8. Store template version on every publication so later edits do not rewrite historical output unexpectedly.

## Single workflow and upgrade

Publish a single only after identity is confident and M3 has a ready candidate. Reserve the publication in a transaction, create the attempt, send once, then persist message ID/URL immediately.

A better or correctly tagged candidate may replace audio in the same message only through a tested gateway edit. After a successful upgrade, send a configurable correction reply to the original message and schedule deletion with a default of 10 minutes. Preserve the original publication URL/message ID. On edit failure, retry/notify; do not create a new audio post.

When a single later belongs to an LP/EP, the album introduction links to it and its existing caption gains an Album link through a safe edit.

## Album/EP workflow

1. Require a confidently typed LP/EP and pre-stage every as-yet-unpublished track with a ready M3 candidate before any intro send.
2. Existing earlier single publications are linked in the intro and skipped as album audio.
3. Under a durable per-channel album lock/session, send official cover + introduction first, then remaining audio tracks sequentially in original source order. Album tracks do not reply to the introduction.
4. Continue discovery/preparation while the block sends. Hold general publication sends only during this short ordered output block.
5. If track N fails, retry it and notify the review destination. After 15 minutes unresolved, release the general publication queue, keep an exact cursor at N, and resume the album later from N. Never resend confirmed intro or earlier tracks.
6. A track officially added after the album intro is a later independent track post with Album link; do not rewrite old ordering.

## Editions and late links

For a distinct confirmed instrumental, deluxe, or rerelease, publish its own audio through the same state machine and caption it with `Original` or `Original Album` when a stored original publication exists. Do not add a duplicate file post for an identical work.

When verified music-video or platform links appear later, edit the prior caption in place using the stored template/publication relation. Capture every edit attempt and failure.

## Required tests

Use the fake gateway for normal automated tests. Cover at least:

1. Conditional single and album captions, escaping, and entity/markup correctness; include Persian, Latin, special characters, no-feature, no-video, one-platform, and overflow cases.
2. Default album intro uses `›`, title-only bold, and guest-only italics.
3. Duplicate/concurrent publication requests create one Telegram send and one durable publication.
4. A simulated uncertain send does not blind-resend.
5. Single upgrade keeps the same publication message ID, creates then deletes the correction reply on schedule, and records failed edits without duplicate audio.
6. Earlier single + later album links both directions and skips the repeated album audio.
7. Album pre-staging blocks introduction until all new required tracks are ready.
8. Album order, failure at track 3, retry, 15-minute release of the general queue, and resume cursor never resend prior tracks.
9. Late music-video/platform link edits the existing caption.
10. Distinct edition uses original linkage; identical work produces no second audio publication.
11. Production-channel safeguard rejects sends in test/development mode.
12. No test reaches a real Telegram endpoint unless an explicit integration-test setting is enabled.

## Optional live test-channel probe

If a bot token and isolated test-channel ID are supplied locally, add an opt-in command that sends a disposable test audio file, records its message ID, edits that same message, sends/deletes a correction reply, and records observed Bot API behavior and limits. It must refuse the production channel and must not run during normal tests. If credentials are absent, record the integration gate as not run.

## Delivery

- Update `docs/PRODUCT_SPEC.md` and `docs/IMPLEMENTATION.md` so every prior-single example and rule uses `›`, replacing any `•` variation.
- Update `docs/STATUS.md`.
- Add `docs/reports/M4_PUBLICATION.md` with tested state transitions, caption samples, fake-gateway results, optional live-test result, and open integration gates.
- Run Docker Compose, migrations, migration-drift check, Django check, full tests, health checks, and secret/media scans locally.
- Commit focused changes and push normally to `main`.
- Do not deploy or start M5.

## Completion report

```text
Implemented:
Local commit SHA and pushed branch:
Local checks (command → observed result):
Caption/template results:
Single upgrade and reconciliation results:
Album sequencing/resume results:
Test-channel probe result or exact blocker:
Documentation updated:
Open gates and proposed M5 scope:
```

Stop after M4 and await the owner's review.
