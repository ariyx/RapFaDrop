# Project status and handoff

Updated: 2026-10-02. This is a documentation checkpoint, not evidence of a running service. Check Git and the actual environment before relying on this date or status.

## Current state

- The observed `origin/main` at this checkpoint is `c39c40a` (`docs: add deployment and verification runbook`). It contains `AGENTS.md`, `README.md`, and the four documents under `docs/`; it contains no application, Compose configuration, migration, or test code.
- No Docker boot, SoundCloud/Spotify probe, Telegram test, or server deployment has been observed in this documentation pass. All M0–M6 implementation and empirical gates remain open.
- The product rules in `PRODUCT_SPEC.md` and the design in `IMPLEMENTATION.md` are the M0 working baseline. The owner requested complete documentation followed by M0. Later implementation choices still require empirical validation. A later owner instruction overrides a document.
- The server has been identified by the owner, but no server access or deployment is claimed. Never store server credentials or a bot token in Git or a prompt.

## Next implementation task: M0

Implement only the M0 foundation and read-only feasibility probes in [`M0_AGENT_TASK.md`](M0_AGENT_TASK.md) and `IMPLEMENTATION.md`. Start with `git status`, current branch/remote/SHA, and all documents linked by the root `AGENTS.md`. Work locally, commit and push the verified changes, then follow `DEPLOYMENT.md` for server verification if SSH authentication and safe configuration are available. Use an isolated Telegram test channel for later publication tests; M0 does not send Telegram messages.

M0 is complete when the following **observed** evidence is recorded in a milestone report, with the exact commit SHA:

1. `docker compose config --quiet` and `docker compose up --build -d` succeed; web, worker, beat, PostgreSQL and Redis are running. Django health and check commands succeed. Record actual commands, outputs and environment limits.
2. A repeatable read-only probe of the supplied SoundCloud track and set reports native IDs, title/artist, set classification evidence, original track order, available metadata and media options, with concrete errors where access fails. The probe must not post to Telegram.
3. A read-only public Spotify probe against a small set of the seeded artist profiles reports what can and cannot be fetched without Premium, native IDs, recent releases, pagination or rate-limit behavior where observed, and failure cases. Do not claim a full 30-artist monitoring capability from a few probes.
4. At least one candidate media acquisition method is assessed with real output or a recorded failure. A second method is described as an independent fallback only when its relevant failure path has actually been tested. No unverified downloader is described as working.
5. `.env.example` contains placeholder names only; no secret, media file or production data is committed. No production channel post occurs. The local commit is pushed normally; if a server step is blocked, record the exact blocker rather than marking it passed.

The detailed milestones and behavior acceptance criteria remain in `IMPLEMENTATION.md`. Avoid advancing to M1 automatically after M0; report observations and propose the next slice to the owner.

## Decisions, assumptions and gates

| Topic | Current rule or assumption | Verification / remaining choice |
| --- | --- | --- |
| Artist list | Thirty selected artists and candidate Spotify/SoundCloud URLs are in `PRODUCT_SPEC.md`. | Verify identity and recent releases per profile before activation; three SoundCloud profiles are unconfirmed. |
| Source monitoring | SoundCloud and Spotify poll independently. Initial interval hypotheses: roughly 1–2 and 2–5 minutes respectively. | Measure reliability, rate limits and release latency; tune intervals from observations. |
| Spotify | Public metadata is a discovery candidate; the owner has no Premium. | Probe actual coverage and stability; no promise of free access or full audio. |
| Audio providers | `yt-dlp` is an initial candidate; use a separately failing provider only after real testing. | Record true quality, complete audio and failure modes for each provider. |
| Single speed | A verified complete single may publish before final tags/quality, then replace media in its original message. | Test Telegram edit behavior, actual upload latency, metadata rendering and uncertain sends in an isolated channel. |
| Album block | Prepare and tag all new tracks before cover post; post in order. A 15-minute unresolved Telegram failure unlocks general sends and preserves a resume cursor. | Test order, failure recovery, message persistence and retry deduplication. |
| Captions and tags | Conditional default templates, `•` for prior singles in the owner's edited album example, official title/artist, configurable `@RapFaDrop` fields. | Verify rendered Telegram entities, captions, file tags, collisions with official credits and panel previews. |
| Admin and deployment | Separate equal-privilege accounts; HTTPS private panel; Docker Compose on owner's server. | Supply private configuration locally, test recovery/backup, health and test-channel permissions in their milestones. |

## Handoff record to maintain

After each milestone or material design change, update this file with the **observed** Git SHA, implemented scope, tests/probe outputs (or durable links to reports), unresolved failures, and exact next milestone. Keep planned work separate from observed results. Update `PRODUCT_SPEC.md` for a changed owner decision, `IMPLEMENTATION.md` for architecture/acceptance changes, and `DEPLOYMENT.md` for verified operational procedure changes. The milestone report format is in `DEPLOYMENT.md`.
