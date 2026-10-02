# M0 coding-agent task — foundation and feasibility

This is the first implementation task. Start it only after importing this documentation into the current repository and checking its actual Git state. Read root `AGENTS.md`, `docs/AGENTS.md`, `docs/STATUS.md`, `docs/PRODUCT_SPEC.md`, `docs/IMPLEMENTATION.md` and `docs/DEPLOYMENT.md` before coding. The product specification governs behavior; this file narrows the first implementation slice.

## Copyable task

> Implement RapFaDrop milestone M0 in the local Git repository. Begin by reporting the branch, HEAD, remote and working-tree status. Create a minimal, runnable, Docker Compose based Python 3.13/Django 5.2 foundation with PostgreSQL, Redis, a Celery worker and beat, an HTTP health endpoint, documented startup commands, pinned compatible dependencies and `.env.example` containing placeholders only. Keep source and media-provider probes read-only and independent from the web startup path. Probe the supplied SoundCloud single and set and a small representative selection of the seeded Spotify profiles without Premium. Report actual IDs, metadata, album order, media options, access failures and rate-limit observations. Test `yt-dlp` as a candidate; describe an independent downloader fallback only if demonstrated by a separate failure-path test. Add focused automated checks for the code written, run the applicable Docker and Django smoke checks locally, and record observed outputs. Make changes locally, commit and push a normal non-force update, then verify that exact SHA on the owner's server using `docs/DEPLOYMENT.md` if secure SSH access and safe configuration are available. Do not post to the production Telegram channel, implement later milestones, claim an unrun probe passed, copy secrets into Git, or edit source on the server. Update `docs/STATUS.md` and any design document affected by observed results. End with the completion report described below.

## Deliverables

| Area | Minimum concrete result | Excluded from M0 |
| --- | --- | --- |
| Application | Django project, database connection, migrations, HTTP health route with an explicit database check or a separately named liveness route | Full artist/track schema, matching and queue state machine |
| Compose | `web`, `worker`, `beat`, `postgres`, `redis`; persistent database volume; bounded restart behavior; clear startup and shutdown instructions | Production channel publishing, permanent downloaded-audio archive |
| Configuration | `.env.example` with required variable names and safe placeholders, `.gitignore`, dependency lock/pins, no real credentials | Committed `.env`, credentials, cookies or server media |
| SoundCloud probe | Repeatable CLI command for the two URLs below, structured summary with source/native IDs, ownership evidence, timestamps, track order, and available audio variants/errors | Polling all thirty artists or treating a set as an LP without evidence |
| Spotify probe | Repeatable read-only command against a small set of seed profiles, observed recent item IDs/type/dates and any pagination/rate-limit/error behavior | Claiming Spotify full audio or guaranteed public metadata access |
| Media feasibility | A candidate `yt-dlp`/ffprobe diagnostic that records real codec, duration and bit rate when acquisition succeeds, or a concrete failure | Default publication, fabricated quality or a claimed untested fallback |
| Verification | Relevant parsing/configuration tests, Django check, Compose startup, health response, no unexpected posts | Large test suite that only repeats scaffolding |
| Operations | README setup, exact SHA, local and optional server results, updated status | SSH password in prompt/command, server-only code edits |

The supplied SoundCloud examples are `https://soundcloud.com/sijalofficial/vaghti-raft` and `https://soundcloud.com/sijalofficial/sets/ocd`. Select Spotify profiles from the seed table in `PRODUCT_SPEC.md`, including at least one artist without a confirmed SoundCloud profile if the public metadata method permits it. Distinguish source-reported release time, upload time, first observed time and probe time when those values exist; record missing values explicitly. Strip share-tracking query parameters for stable identity while preserving the original source ID and URL provenance.

## Probe and reporting rules

1. Make probes opt-in commands, not automatic network calls during `docker compose up`, migrations or test discovery. Give them bounded timeouts and enough error context to diagnose HTTP, authentication, parsing and extractor failures. Do not add a workaround that bypasses access controls.
2. Print or save a redacted machine-readable result plus a human summary. Record tool versions, probe timestamp in UTC, source URL, whether the response was observed or inferred, fields that are unavailable, and elapsed time. Avoid storing cookies, authorization headers, signed media URLs or full raw payloads in committed reports.
3. For a SoundCloud set, preserve native order and record the evidence used to label it LP, EP or playlist. If classification is uncertain, state it; M2 will decide review behavior. For Spotify, report independent success/failure from SoundCloud.
4. For an audio candidate, measure actual duration/codec/bit rate with ffprobe after a complete download when authorized and feasible. A metadata-only probe is useful but is not proof of complete playable audio. Keep temporary media out of Git and delete it after testing.
5. Record every failed command with exit code and a concise redacted error. An external access failure can leave a feasibility gate open while the infrastructure slice succeeds; do not silently substitute mock output for live evidence.
6. Only a provider whose relevant failure path is independent of the first provider can be called a fallback. If independence cannot yet be demonstrated, record it as an unverified candidate and defer provider selection.

## Acceptance and stop point

M0 infrastructure passes when the documented fresh setup boots the requested services, health and Django checks run, tests for implemented code pass, and secrets stay out of the commit. M0 feasibility passes per source only when repeatable live output demonstrates the stated fields; record each provider as `verified`, `partially verified`, `failed` or `not run`, with evidence. A blocked external source does not justify claiming the entire product works. No live publication is required or permitted in M0.

Check current remote and working tree again before pushing. Preserve unrelated local changes. Push with a normal fast-forward update to the established branch; if authentication or a concurrent update prevents it, retain a local commit and report the exact blocker. Deploy only the pushed SHA, with existing server data preserved and backup checks from `DEPLOYMENT.md`. If access is unavailable, finish local work and identify the blocker precisely. Do not mark server verification complete without observing it.

End the task with:

```text
Implemented:
Local commit SHA and pushed branch:
Local checks (command → observed result):
SoundCloud track/set findings (including limits):
Spotify profile findings (including limits):
Audio candidate/fallback findings:
Server deployed SHA and checks, or exact blocker:
Documentation updated:
Open gates and next proposed M1 slice:
```

Update `STATUS.md` with actual findings and durable links to any safe report. Stop at M0 and present the outcome for the owner's review before implementing M1.
