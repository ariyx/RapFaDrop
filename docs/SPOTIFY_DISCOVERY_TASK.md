# Spotify discovery feasibility task

Read `AGENTS.md`, `docs/STATUS.md`, `docs/IMPLEMENTATION.md`, the M0 feasibility report, and M6 operations report before changing code. Add this file as `docs/SPOTIFY_DISCOVERY_TASK.md`.

## Goal

Determine whether Spotify can be a reliable, no-Premium discovery source for newly released items. SoundCloud and Spotify must remain parallel first-observation sources; neither is globally primary.

Spotify is discovery/metadata only in this project. Do not use Spotify as an audio source.

## Scope

1. Do not activate any additional source, run a baseline, enqueue media/publication work, send Telegram messages, or deploy production changes.
2. Test bounded public metadata approaches on at least five seeded artists: Sijal, Fadaei, Ho3ein, and two others. Include a recent release if public data permits.
3. For each method, record native artist/release IDs, title/type, release date, URL, page/order/pagination behavior, observed latency, HTTP status/rate-limit behavior, and failures.
4. Distinguish oEmbed identity resolution from actual recent-release listing. A successful artist identity lookup is not proof of release discovery.
5. Use no Spotify Premium account and do not commit client IDs, client secrets, browser cookies, access tokens, or captured signed URLs.
6. Do not bypass access controls. If a method needs unavailable authenticated access, mark it unavailable.
7. Select an adapter only if it can repeatedly list current artist releases with stable IDs and bounded failure behavior. Otherwise retain Spotify as disabled/unavailable and document the evidence.

## Required implementation safeguards

- Keep SoundCloud and Spotify adapter failures isolated.
- Add configuration/status that makes an unavailable Spotify adapter visible in the panel and logs.
- Do not mark a source verified or enabled merely because a public page opened.
- Add tests using fixtures/fakes for Spotify result parsing, pagination/order, 403/429/timeout behavior, and source-isolated backoff.
- Add a regression test that beat/poll scheduling cannot create publication envelopes when publication is disabled. The M6 pilot's initial beat override must not recur.

## Documentation and delivery

- Add `docs/reports/SPOTIFY_DISCOVERY.md` with methods tested, observed evidence, limitations, adapter decision, and next action.
- Update `docs/STATUS.md` and `docs/IMPLEMENTATION.md` with the parallel-source policy and observed Spotify result.
- Run local Docker, migrations, Django checks, full tests, health checks, and secret/media scans.
- Commit and push normally to `main`.
- Stop after reporting. Do not deploy or activate sources.
