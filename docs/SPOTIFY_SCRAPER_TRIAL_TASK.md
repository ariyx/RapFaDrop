# SpotifyScraper adapter trial task

Read `AGENTS.md`, `docs/STATUS.md`, `docs/SPOTIFY_DISCOVERY_TASK.md`, `docs/IMPLEMENTATION.md`, and `docs/reports/SPOTIFY_DISCOVERY.md` before changing code. Add this file as `docs/SPOTIFY_SCRAPER_TRIAL_TASK.md`.

## Goal

Evaluate and, only if evidence supports it, add `spotifyscraper` as a disabled-by-default public Spotify metadata adapter for artist discography discovery. It may create discovery facts only; it is never an audio provider.

## Scope

1. Pin a compatible `spotifyscraper` version and isolate it behind the existing Spotify adapter contract.
2. Do not use Spotify credentials, Premium, cookies, private endpoints, browser login, proxies, anti-bot workarounds, or user-account automation.
3. Keep the adapter disabled by default. Do not enable any ArtistSource, run a baseline, enqueue media/publication, send Telegram messages, or deploy.
4. Probe five seeded artists: Sijal, Fadaei, Ho3ein, and two others with different catalog sizes.
5. For each probe, record artist ID, returned release IDs, release type, title, release date/precision, URL, pagination/order behavior, request count, latency, and all failures.
6. Repeat a subset of probes to test stable IDs/order and bounded error handling.
7. Map only observed public fields into the existing source contract. Preserve raw provenance and never invent dates/types omitted by the package.
8. Respect source-specific backoff and keep SoundCloud/Spotify failures isolated.

## Adapter acceptance

The adapter can be proposed for a later controlled pilot only if it demonstrates all of:

- stable native artist/release IDs across repeated probes;
- recent release listing for the sampled artists, including pagination where needed;
- enough release date/type data to distinguish a new candidate from historical baseline material;
- bounded timeout/403/429/error handling;
- no credential/cookie requirement.

If any condition fails, keep it unavailable and record the failure. Do not replace the existing unavailable Spotify status with an assumed working adapter.

## Required tests

Add fixture/fake tests for:

- artist discography mapping, album/single/EP normalization, release ordering, and pagination;
- missing/partial release metadata;
- timeout, 403, 429, malformed payload, and isolated source backoff;
- stable ID/idempotent ingestion through the existing SourceItem path;
- disabled adapter/source producing no poll, media, queue, publication, or Telegram work;
- no credential, cookie, or sensitive diagnostic output.

Network probes must be opt-in and excluded from normal test discovery.

## Delivery

- Add `docs/reports/SPOTIFY_SCRAPER_TRIAL.md` with exact package version, methods, observed data, performance, errors, and adapter decision.
- Update `docs/STATUS.md` and `docs/IMPLEMENTATION.md`.
- Run local Docker, migrations, Django checks, full tests, health checks, and secret/media scans.
- Commit and push normally to `main`.
- Do not deploy or activate a source. Stop after reporting.
