# Agent instructions for RapFaDrop

## Mission and authority

Build a reliable, self-hosted release monitor for the owner-managed Persian rap artist list. Publish verified audio to `@RapFaDrop` with the documented captions and metadata when the publication milestone is reached. The product decisions are in `docs/PRODUCT_SPEC.md`; implementation design and milestones are in `docs/IMPLEMENTATION.md`. M0 is authorized as a working baseline; later owner instructions supersede these files.

## Read before changing code

1. Read `docs/STATUS.md` and verify its checkpoint against the current repository; it records the observed handoff and the next task.
2. Read `docs/PRODUCT_SPEC.md` for product rules and the 30-artist seed list.
3. Read `docs/IMPLEMENTATION.md` for architecture, state transitions, milestones, tests and empirical gates; read `docs/DEPLOYMENT.md` before delivery or server verification.
4. Check the current repository and milestone before making a plan. Never assume the status file is newer than Git.
5. For the initial task, follow `docs/M0_AGENT_TASK.md` and record empirical results without inventing successful provider access.

## Working method

- Work in the milestone requested by the owner. Before a multi-file change, state the acceptance criteria and a short implementation plan. Report what changed, what was verified and what remains uncertain.
- The local docs-only clone has `origin` set to `https://github.com/ariyx/RapFaDrop.git`. Verify its current branch, remote and upstream state before coding or pushing. Do not claim that a local file is published upstream.
- Implement vertical slices with a visible result and a relevant test. Do not scaffold the entire product in one pass or silently proceed to the next milestone.
- Keep the status, product and implementation documents aligned with observed progress and changes to architecture or accepted behavior. Record deviations and the evidence that justified them.
- Use Python 3.13, Django 5.2 LTS, PostgreSQL, Redis, Celery, yt-dlp, FFmpeg, Mutagen and the Telegram Bot API as the initial stack. Docker Compose runs local and server services. Pin compatible versions when implementing, after checking current releases.
- Django owns the admin panel and product data. Celery workers own polling, media processing and publication tasks. PostgreSQL is authoritative for state; Redis carries transient work and locks. Keep source and downloader adapters independently replaceable.
- Do not add a separate frontend framework, microservices, additional brokers or a permanent media archive without a concrete requirement and a documented decision.

## Product invariants

- Only monitor enabled, verified sources in the allowlist. On first activation, baseline existing releases without posting them to the new-release channel.
- Never publish a link-only post or a short preview in place of complete audio. Ambiguous identity, match or duplicate status goes to admin review.
- Match one canonical work across platforms and editions. An earlier single is published when released; a later album links to its prior post and skips sending that audio again.
- Pre-stage and tag every as-yet-unpublished album track before publishing the cover post. Publish album tracks sequentially. If Telegram fails on a track, retry and notify admins; after 15 minutes release the general queue and resume the album from that track later.
- A verified independent single may be sent as an initial complete playable file and upgraded in the same Telegram message. Album-track pre-staging is stricter. Do not fabricate quality by transcoding a low-quality file to a higher nominal bit rate.
- Telegram message IDs and URLs are durable state. An uncertain send outcome must be reconciled before retrying to avoid duplicates. A failed edit must not silently create a new post.
- Caption rows appear only when their underlying URL or data exists. `DROP`, `LP DROP`, `EP DROP`, `Original`, `Original Album` and album introduction formatting follow the product spec and are editable in the admin panel.
- Keep source titles and artist names official. Channel tags go only into the configured metadata fields. Test actual file tags and Telegram presentation with real samples.

## Security and operations

- Never commit or log credentials, cookies, BotFather tokens, session files, private media or `.env` values. Provide `.env.example` with placeholder names only.
- Use separate admin accounts with equal privileges, password reset by another admin and an audit record. Protect the panel with HTTPS; keep PostgreSQL and Redis off the public internet.
- Store UTC timestamps and explicit source IDs. Use database constraints and transaction-safe publication state to make worker retries idempotent.
- Keep disposable media in a temporary volume, remove it after confirmed publication and retain the record of source, quality, attempt and Telegram message ID. Back up PostgreSQL and test restoration before deployment.

## Tests and completion report

- Test the behavior changed. The critical paths are baselining, cross-platform deduplication, single-before-album linkage, album staging/order/resume, incomplete-audio rejection, Telegram send reconciliation, in-place media edit, conditional captions, admin review and manual upload.
- Use fakes for unit tests and an isolated Telegram test channel for live integration. Never post tests to the production channel.
- At the end of each task, report: `Implemented`, `Verification`, `Documentation`, `Open questions`, and `Next milestone`. Distinguish observed behavior from planned behavior.
