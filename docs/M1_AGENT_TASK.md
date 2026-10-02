# M1 coding-agent task — source discovery and baseline

Read `AGENTS.md`, `docs/STATUS.md`, `docs/PRODUCT_SPEC.md`,
`docs/IMPLEMENTATION.md`, `docs/M0_AGENT_TASK.md`, and the completed M0
feasibility report before changing code.

## Goal

Implement M1 only: durable artist/source configuration, safe source polling,
and idempotent historical baselining. Do not create releases for publication,
download media, or send Telegram messages.

## M0 facts that govern this task

- SoundCloud discovery was verified only for the supplied Sijal track and OCD
  album URLs.
- Spotify public oEmbed resolved profile identities for Sijal, Fadaei, and
  Ho3ein, but `spotipyFree` recent-release requests timed out.
- Spotify recent-release discovery, pagination, and reliable polling are
  unverified. Do not present Spotify as an active working feed.

## Required implementation

1. Add durable models and migrations for:
   - `Artist`
   - `ArtistSource`
   - `SourceItem`
   - minimal audit/baseline records needed for safe operations

2. Store:
   - official artist name, aliases, enabled state
   - platform, native profile ID, canonical profile URL, verification state
   - baseline time, last successful poll, next due poll, error/backoff state
   - stable platform item IDs, source metadata, source release time,
     first-observed time, and raw data sanitized for safe storage

3. Add the approved 30 artists and candidate source profiles from
   `PRODUCT_SPEC.md` as disabled and unverified seed data. Missing SoundCloud
   profiles must stay empty; do not substitute fan accounts.

4. Build source adapter interfaces that keep SoundCloud and Spotify separate.

5. Implement SoundCloud polling for enabled and verified sources:
   - poll only sources whose `next_poll_at` is due
   - store source items idempotently by `(platform, native_item_id)`
   - set a new due time after success
   - use source-specific exponential backoff after a failure
   - one source failure must not stop another source

6. Implement initial baselining:
   - on first activation, fetch and store the current source snapshot
   - mark baseline completion and timestamp
   - never queue, publish, download, or notify about historical items
   - safely resume after interruption without duplicates

7. Add a Spotify adapter shell using only M0-proven identity metadata.
   Keep Spotify release polling disabled or explicitly unavailable until a
   bounded recent-release method is proven. Expose its status clearly in the
   admin/data layer and logs.

8. Add a minimal admin interface or management commands for:
   - viewing artists and sources
   - enabling/disabling a source
   - recording source verification
   - triggering a manual baseline/poll for development
   - viewing source errors and baseline status

## Required tests

Add meaningful tests for:

- importing all 30 seed artists and candidate profiles
- no fan-account replacement for missing sources
- disabled/unverified sources are not polled
- duplicate platform item IDs create one `SourceItem`
- first baseline stores existing items without creating publication work
- interrupted baseline resumes idempotently
- a failing source backs off while another due source still succeeds
- Spotify recent-release polling remains unavailable until verified

Use fixtures/fakes for automated tests. Do not make provider network calls during
normal test discovery.

## Delivery rules

- Run development, Docker, migration, Django, and automated tests locally.
- Commit focused changes and push normally to `main`.
- Do not deploy to the server during M1; final deployment happens later.
- Do not start M2.
- Do not post to Telegram.
- Never commit credentials, cookies, downloaded audio, or `.env` values.
- Update `docs/STATUS.md`, `docs/IMPLEMENTATION.md` where observations change
  the design, and create `docs/reports/M1_DISCOVERY.md`.

## Completion report

Report:

- Implemented
- Local commit SHA and pushed branch
- Local checks and observed results
- Seed import and baseline results
- SoundCloud polling behavior
- Spotify capability and limitation
- Documentation updated
- Open gates and proposed M2 scope