# RapFaDrop — implementation guide for coding agents

Status: **M2 identity, review, and inert processing-queue implementation; media processing and publication remain out of scope.**
Repository: `https://github.com/ariyx/RapFaDrop.git` (documentation-only at the checkpoint in [`STATUS.md`](STATUS.md); verify current Git state).
Product source of truth: [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md).  
Reference for documentation organization: `https://github.com/ariyx/flow`; reuse its separation of agent instructions, product decisions and milestone plans, not its technology or product rules.

## 1. Outcome and scope

Monitor an owner-managed allowlist of 30 Persian rap artists on SoundCloud and Spotify. Detect newly published official singles and album/EP releases quickly; obtain a complete playable audio file; preserve official identity; apply configurable `@RapFaDrop` tags; and post an audio message with conditional source links to the Telegram channel. Admins manage artists, release reviews, errors, file uploads and caption/tag templates from a private web panel. The future historical archive may use another channel; existing releases are baselined now but are not auto-posted to the new-release channel.

The exact initial artist names and candidate profile URLs are in `PRODUCT_SPEC.md`. Treat URLs as seed data requiring a last-releases identity check on import. Fadaei, Ho3ein and Amir Tataloo have no confirmed SoundCloud source in the seed; leave it empty rather than substituting a fan account. The owner has no Spotify Premium. An unofficial public-metadata adapter is an empirical candidate, not a guaranteed integration. Spotify is a discovery/metadata source, not the full-audio file source.

Success means a new release moves through discovery, identity verification, media validation, tagging and Telegram publication once, with recorded timing and an admin-visible explanation of failures. Speed is measured as separate discovery, acquisition, preparation, upload and end-to-end latencies. Polling targets are starting hypotheses, not service-level promises.

## 2. Accepted stack and deployment shape

| Layer | Initial choice | Responsibility |
| --- | --- | --- |
| Language and web | Python 3.13, Django 5.2 LTS, Django templates/admin | Private multi-admin panel, forms, settings, previews and HTTP endpoints |
| Durable data | PostgreSQL | Artist identities, snapshots, release relations, publication state, audit and retry records |
| Background work | Celery with Redis broker, one beat scheduler | Per-source polling, acquisition, album staging, Telegram publication and retries |
| Media | yt-dlp candidate, FFmpeg/ffprobe, Mutagen | Source probing, completeness/format checks, tagging and embedded art |
| Telegram | Bot API behind a small Python gateway | `sendAudio`, cover post, caption/media edits, replies, notifications and deletes |
| Server | Docker Compose, reverse proxy with HTTPS (Caddy candidate) | Web, worker, beat, PostgreSQL, Redis, temporary media volume |

The implementation should use one Django codebase with separate web/worker/beat processes. PostgreSQL is authoritative; Redis is not the source of truth for whether a release has been published. Keep the Telegram gateway and source/downloader adapters small and replaceable. A downloader wrapper using the same failed extractor is not an independent fallback.

Suggested initial layout after milestone 0:

```text
AGENTS.md
README.md
docs/PRODUCT_SPEC.md
docs/IMPLEMENTATION.md
compose.yaml
.env.example
app/manage.py
app/config/
app/releases/           # identities, relationships, state and deduplication
app/sources/            # SoundCloud and Spotify metadata adapters
app/media_pipeline/     # acquisition, probes, tagging, cover handling
app/publication/        # Telegram gateway, caption rendering, album sequencer
app/control_panel/      # admin views, template preview and reviews
tests/
```

This is a target layout, not a demand to create empty packages ahead of their milestone. Images, downloaded media, tokens and production database dumps are never committed.

## 3. Durable data and identity

Design migrations in the milestone that first uses each entity. Initial conceptual entities:

| Entity | Key fields / uniqueness | Purpose |
| --- | --- | --- |
| `Artist` | Display name, aliases, enabled state | Canonical artist selected by owner |
| `ArtistSource` | Artist, platform, native profile ID, URL, verified state, baseline/next poll timestamps | Independent source configuration and backoff |
| `SourceItem` | Unique `(platform, native item ID)`, raw metadata, first-seen/release times, source URL | Stable input fact and replay protection |
| `Release` | Canonical title, type (single/LP/EP), edition, artists, official date, review state | One conceptual release across platforms |
| `Track` + `ReleaseTrack` | Canonical track, official title, artists, order and optional prior-single relation | Link an earlier single to a later album without reuploading it |
| `SourceMatch` | Release/track to source item, confidence, evidence, admin decision | Transparent identity resolution |
| `MediaCandidate` | Origin, actual codec/bit rate/duration, hash, validation/tag state, temporary location | Candidate file and upgrade decision |
| `Publication` | Unique channel + canonical track/edition or album introduction; Telegram message ID, URL, state | Durable output identity per channel |
| `Attempt` / `Review` / `AuditEvent` | Error, time, retry schedule, actor and decision | Recovery, admin review and observability |
| `TemplateSetting` | Kind, version, text, conditional variables, enabled state | Editable captions and metadata settings |

Use source IDs for exact matches first, then artist/title normalization, duration, release relation and evidence to rank candidates. Do not auto-merge a same-name remix, live take, instrumental or deluxe edition. Exact duplicate audio with a different release label does not create another file post. Reserve a publication identity in a database transaction before queueing a send. Celery's at-least-once delivery must not create duplicate posts.

### Initial baseline

Import the allowlist as disabled/unverified source records, check that each profile's recent works belong to the expected artist, then activate it. On first poll, persist the source snapshot and baseline time without queueing historical output. A partially completed baseline must resume idempotently after restart. A newly discovered item with an old release date or uncertain first-seen status goes to review, not automatic publication. Preserve historical source facts for a possible separate archive channel.

## 4. Polling and media adapters

- Poll SoundCloud and Spotify independently. Starting intervals for testing: SoundCloud about 1–2 minutes and Spotify about 2–5 minutes, staggered per artist. The scheduler checks due `ArtistSource` rows; adaptive next-poll timestamps and per-source backoff live in PostgreSQL. Respect rate limits and `Retry-After` when provided. A failing Spotify adapter does not block SoundCloud.
- Define a metadata adapter contract: `resolve_profile`, `list_recent`, `fetch_item`, `fetch_album_tracks`, returning stable native IDs, provenance and raw payload. Implement normalised values separately so the source can be debugged when markup changes.
- Begin with actual probes of the owner's SoundCloud samples: `https://soundcloud.com/sijalofficial/vaghti-raft` and `https://soundcloud.com/sijalofficial/sets/ocd`. Test Spotify public metadata access without Premium against several seeded profiles. Record actual capabilities, request count, rate limits and failure modes before committing to an adapter.
- Define a separate media-provider contract: `can_handle`, `probe`, `download`, `verify`. Try SoundCloud/yt-dlp where usable; for Spotify-only discovery, search for an official corresponding full recording and compare title, artist, duration and provenance. Never treat a Spotify URL as proof that another audio file is the same work. YouTube can be an acquisition candidate or music-video link, not the initial independent release feed.
- Keep an ordered fallback policy. A second provider counts as fallback only if its relevant failure path is independent. If all providers fail, retain the item in the queue, retry with increasing delay, alert an admin and permit a manual full-file upload through the same verification/tagging pipeline. Never publish a link-only placeholder.
- Use ffprobe for observed duration/codec/bit rate. Reject missing, truncated or preview audio. Preserve the best real available quality; do not upsample a low-quality source to claim higher quality. Keep acquisition and format handling configurable after real tests.
- Use Mutagen to write official title/artist and owner-configured channel fields, plus official cover when available. The product spec lists desired fields, including unusual credits fields; test mappings by output format before claiming that Telegram displays them. Do not overwrite verified official credits with a channel name silently.

## 5. Release and publication state machine

An item flows through `observed → identified → media_pending → media_ready → queued → publishing → published`. Any uncertain match or album type enters `review_required`; recoverable failures enter `retry_wait` with a due time; terminal failures remain visible for manual action. A published item may enter `upgrade_pending → published` after a better file or new link is found. Track all transitions with cause, attempt and timestamps. A state name can change in code, but the transitions and operator meaning must remain explicit.

### Single

Publish a single as soon as a complete, verified playable audio file is available. A provisional single may lack final tags or optimal quality, but its official title/artist and identity must be correct. Prepare a better file and replace media in the *same* Telegram message; send a reply announcing the correction and remove that reply after the configurable default of 10 minutes. On edit failure, alert/retry; do not automatically send a duplicate new message.

If the same track later appears on an LP/EP, retain the single publication, skip its album audio upload, include a link to the prior single in the album introduction, and add the album introduction link to the single's caption. Keep its `DROP` header. A new track added after the album is already published is a new post with an album link; do not rewrite the earlier album introduction solely because its source track list changed.

### Album/EP

Classify a SoundCloud set as LP, EP or ordinary playlist. Uncertain type awaits admin review; unrelated singles keep moving. Before the first album introduction post, acquire, verify and tag **all tracks that still need publication**. Previously published singles are linked and skipped. Post official cover + introduction, then each prepared audio track in the original order. Hold other publication sends only during this short output block; discovery and preparation continue.

If Telegram fails on track 3 after tracks 1–2 succeeded, retry track 3 and notify admins. After 15 minutes unresolved, release the general publication queue and persist a resumable cursor at track 3. Resume the album from that track in order when feasible. Never resend tracks 1–2. The album block may lose visual continuity in this exceptional case.

### Editions and duplicates

For an official distinct instrumental, deluxe or rerelease, preserve its official title and post its audio if it is substantively a different file/version. Link `Original` to the existing original-track publication or `Original Album` to the original album introduction if available. Do not post byte-for-byte or clearly identical reissues as another audio file. Ambiguous version comparison requires admin review.

### Telegram uncertainty and idempotency

Bot API calls can succeed remotely while a worker times out before saving the returned message ID. Persist a pending attempt before sending; on ambiguous outcomes, stop blind automatic resend and reconcile using an admin-visible record or a reliable lookup strategy proven in the test channel. Database uniqueness, publication state and per-channel album lock prevent two workers from sending the same canonical item. Store the returned Telegram message ID/URL immediately after success. A temporary-file cleanup waits for confirmed publication or a safe retry decision.

## 6. Captions, templates and metadata

Render dynamic links as Telegram-safe entities (or escaped supported markup). Treat artist titles and other remote strings as untrusted input. Preview the *rendered* conditional output in the panel, including bold/italic/link formatting and omitted separators. The approved defaults are:

```text
Single audio:            DROP (bold)
                         [Music Video]
                         [Spotify / SoundCloud]
                         [Album]
                         [Original]
                         t.me/RapFaDrop

Album track audio:       LP DROP / EP DROP (bold, editable/removable)
                         [Music Video]
                         [Spotify / SoundCloud]
                         Album (linked to introduction)
                         [Original]
                         t.me/RapFaDrop

Album cover post:        REFIGH (bold; example official title)
                         LP · Reza Pishro × Tohi
                         feat. Ali Owj · Big Shaggy · Nassim (names italic only)
                         [پیش‌تر از این آلبوم منتشر شده:]
                         [• CD]
                         [• Raghse Andam 3]
                         [Original Album]
                         @RapFaDrop
```

Square brackets here mean conditional rows, not literal output. `Music Video` requires an official video URL. Spotify and SoundCloud are each included only with that track's URL; omit the slash when only one exists. `Album` appears on an earlier single only after the introduction exists. `feat.` and the prior-singles section vanish as whole blocks when empty. The previous-single labels are linked to channel messages and use the `•` symbol from the owner's latest edited template. The album name is bold; only guest names after `feat.` are italic. When a caption exceeds Telegram's effective limit, keep the introduction concise and put overflow links in a following text post. No inline buttons are required in the first release.

The initial template variables are `title`, `artists`, `features`, `release_type`, `music_video_url`, `spotify_url`, `soundcloud_url`, `album_post_url`, `previous_singles`, `original_track_post_url`, `original_album_post_url`, and `channel`. Text order, optional sections, tag fields and the correction reply timeout must be editable from the panel. Store safe template versions; don't execute arbitrary Python or unrestricted user template code.

## 7. Admin panel and operations

Provide separate password accounts with equal access; another admin can reset an account with an audit event. Cover artist/source verification, enable/disable, template and metadata settings/preview, release queue, error details, manual audio upload, suspicious-item approve/reject/correct, publication links and basic latency metrics. Admin notifications in Telegram show a reason and route to an authenticated decision; one pending review must not stop unrelated releases.

Compose services: `web`, `worker`, `beat`, `postgres`, `redis`, and a TLS reverse proxy. Use separate worker queues/concurrency for polling/media and ordered publication; do not depend on Redis locks as the only durable record. Provide a health endpoint and a database migration command. Secrets are environment-provided and excluded from the repository; include only placeholder keys in `.env.example`. Persist PostgreSQL data and protect the private web panel with HTTPS. Temporary audio is deleted only after safe completion. Document a tested database backup/restore procedure before production deployment.

## 8. Milestones and acceptance evidence

Deliver one milestone at a time. Each milestone ends with commands/results, a short observed demo, and documented limits. Do not use a fabricated happy-path test as proof of a live provider.

| ID | Deliverable | Acceptance evidence |
| --- | --- | --- |
| M0 — repository and feasibility | Clone and verify `origin`, add docs and Dockerized Django/PostgreSQL/Redis/Celery skeleton, `.env.example`, isolated test setup, probe the given SoundCloud single/set and Spotify public metadata | `docker compose up` starts healthy services; real probe output records IDs, track order, audio options and errors; no production posting |
| M1 — source discovery | Seed 30 artists and disabled/unverified candidate profiles; provide explicit verification, activation, baseline, per-source adapters and scheduled polling | Fake-backed tests show first baselines create source facts only, repeated IDs deduplicate, disabled/unverified sources are skipped, and one source failure does not stall another |
| M2 — identity and queue | Canonical releases/tracks, cross-source matching, edition/album relation, admin review and backoff | Single-before-album and ambiguous-match scenarios reach the expected states without double publication |
| M3 — media | Full-file checks, candidate fallback, quality comparison, tags/cover, manual upload | Real samples play with correct fields; a failed download leaves a visible queued item and never posts a link-only message |
| M4 — Telegram publication | Caption renderer, in-place upgrades, cover/ordered album block, retries, notifications and delayed reply deletion | Test channel demonstrates same message ID after edit, linked prior singles, album resume at a failed track and no duplicate resend |
| M5 — administration | Accounts, panel flows, configuration preview, approvals, logs and metrics | Two separate admins can perform and audit decisions; manual upload follows the normal media/publication flow |
| M6 — server readiness | Compose configuration, HTTPS, backups, health and failure recovery | Restart/retry scenarios preserve database state and message IDs; measured discovery-to-publication timings guide interval tuning |

### First coding-agent task (M0 slice)

1. Inspect the clone and remote. State what exists; do not pretend code or tests already exist. Check the current handoff in `STATUS.md`.
2. Create the smallest Dockerized Django foundation with PostgreSQL, Redis, worker and beat; provide `README.md`, `.env.example`, health endpoint and reproducible setup commands. Do not implement the full product during scaffolding.
3. Build read-only diagnostic probes for the supplied SoundCloud track and set, and for a small sample of seeded Spotify artist pages using candidate public-metadata methods. Record errors and actual metadata/audio options without posting to `@RapFaDrop`.
4. Add meaningful checks for service boot and probe parsing where feasible. Report which Spotify features work without Premium and which media providers are actually independent. Update the implementation guide from observations.

Credentials, channel admin privileges, host/domain and any test-channel details are supplied later by the owner through secure local configuration. Do not invent or commit values. Live Telegram publication, edition matching and full admin UI belong to later milestones.

## 9. Decisions that require empirical validation

- Spotify metadata completeness and request stability without Premium; choose the working adapter only after probing actual seeded profiles.
- SoundCloud download options and the behavior of `yt-dlp`/an independent fallback on the owner's examples.
- Telegram file/caption limits, embedded tags/artwork rendering, `editMessageMedia` behavior for an audio message, and the reconciliation path after an ambiguous send.
- True source quality and whether quick tagging is fast enough to avoid a provisional single upload in most cases.
- Sustainable polling intervals and end-to-end delay for 30 initial artists under rate limits.

Record findings as observed data and adjust implementation choices; keep accepted product behavior intact unless the owner decides otherwise.

## 10. M0 observed adapter findings

The 2026-10-02 local M0 probes are recorded in [`reports/M0_FEASIBILITY.md`](reports/M0_FEASIBILITY.md). On the supplied SoundCloud examples, `yt-dlp 2026.08.19` resolved stable native IDs, explicit album evidence and ordered tracks, and acquired one complete AAC candidate measured by `ffprobe`. That evidence supports keeping `yt-dlp` as the first SoundCloud candidate, but does not establish a fallback or broad profile coverage.

`spotipyFree 1.9.14` required an undeclared `websockets` dependency and then timed out on the three sampled artist/release requests. Spotify oEmbed independently confirmed public profile identity without login for Sijal, Fadaei and Ho3ein, but exposed no recent releases or pagination. Keep the Spotify release adapter gate open for M1; do not schedule this experimental method or represent oEmbed as release monitoring.

## 11. M1 source implementation and observed limits

The `app/sources/` Django app owns the M1 `Artist`, `ArtistSource`, `SourceItem`, `BaselineRun` and `SourceAuditEvent` records. The seed command imports 30 artists, 30 candidate Spotify profiles and 27 candidate SoundCloud profiles. Everything starts disabled and unverified. Fadaei, Ho3ein and Amir Tataloo have no SoundCloud row; no collaborator or fan account is substituted. Candidate Spotify IDs are stored as profile identity metadata, not proof that a release feed works. The Persian aliases in `PRODUCT_SPEC.md` are valid UTF-8; the earlier apparent mojibake was PowerShell's default output decoding. The seed imports those Persian aliases, and repeat imports preserve owner-added aliases.

Only sources belonging to enabled artists and themselves enabled, verified, and due are considered by the scheduler. The default interval is 90 seconds per source. SoundCloud metadata polling uses a separate `yt-dlp` adapter and persists stable native item IDs, release/first-observed times and an allowlisted metadata payload; descriptions, formats, signed media URLs and arbitrary remote fields are excluded. The implementation currently reads a bounded latest-profile window of up to 100 items per request. A first poll baselines instead of treating historical items as new work. Database uniqueness on `(platform, native_item_id)`, transaction-scoped snapshot writes, and reuse of an interrupted running baseline make retries idempotent. A per-source exponential retry delay starts at that source's interval and caps at six hours.

The scheduled Celery task checks due records each minute; management commands and Django admin expose status, configuration/audit, manual baseline, due polling, and an explicitly forced single-source development poll. Manual baseline/poll requires enabled and verified configuration. No release/publication queue, media download, Telegram integration, or publication side effect is implemented in M1. Spotify's adapter exposes identity-only capability and raises an explicit unavailable result for release polling; it is not called as a Spotify release feed.

M1 automated tests use fakes and do not make provider calls. The local development database contains 30 artists and 57 candidate source records after the seed command; all are disabled/unverified, with zero source items and zero baseline runs. Test evidence covers deduplication, interruption/retry, sanitization, skipped inactive sources, per-source failure isolation, and Persian alias persistence/display through the model, seed command, status command and admin list. No new live profile probes were run in M1 because every candidate remains unverified. The prior M0 track/set and Spotify oEmbed observations remain in [`reports/M0_FEASIBILITY.md`](reports/M0_FEASIBILITY.md); they do not prove candidate SoundCloud profile coverage or Spotify release polling. Full observed check output and remaining gates are in [`reports/M1_DISCOVERY.md`](reports/M1_DISCOVERY.md).

## 12. M2 identity and review implementation

The `app/releases/` app owns canonical releases/tracks, ordered release membership, prior-single links, source matches, review items, audit events, and an inert processing queue. `ingest_source_item()` accepts only an existing `SourceItem`; it uses a transaction and row lock, preserves source provenance/display values, applies comparison-only Unicode normalization, and returns a stable match/review/duplicate/queued outcome. PostgreSQL uniqueness and consistency constraints protect source identity decisions, album ordering, credited artists, and one future queue item per canonical track.

Matching is intentionally explainable and conservative: verified artist identity plus normalized title and duration agreement can deduplicate cross-platform representations; artist/uploader disagreement, materially conflicting or missing duration, date conflicts, unclear collection type, and remix/live/instrumental/deluxe/rerelease markers route to review. A single later present on an LP/EP keeps the same canonical track and links its album membership to the prior single without duplicating future track work. Review actions are available to authenticated Django admins and record actor/decision/time. Queue retry state uses bounded exponential delay only; M2 adds no media task or publication side effect.

M2 fixture tests cover duplicate/replay and concurrent ingestion, SoundCloud/Spotify identity reuse, different artists, Persian/Latin comparisons without display mutation, edition separation, single-to-album order/linkage, uncertain cases, audited admin decisions, and retry scheduling. No provider calls, source activation, baseline, media processing, Telegram calls, or deployment occurred. The local seeded source records remain disabled/unverified. Detailed observed evidence and remaining calibration/provider gates are recorded in [`reports/M2_IDENTITY.md`](reports/M2_IDENTITY.md).

## 13. M3 media acquisition and preparation

The `app/media_pipeline/` app adds durable candidates, per-attempt outcomes, and audit events linked to M2's canonical track/release and source match. Candidate media and prepared copies live under the configured `MEDIA_ROOT`, shared by Compose web and worker through a named volume. Acquisition is an explicit management/admin action for a pending, confidently matched queue item; no scheduler invokes it. `RAPFADROP_MEDIA_PROVIDER_ORDER` chooses the first registered provider. `yt-dlp` is the only implemented full-audio provider and accepts anonymous SoundCloud track URLs. Unsupported sources, including Spotify, remain visible in review without a download attempt. There is no independent fallback claim.

Acquisition writes into bounded, private staging, rejects path escapes and oversized files, and removes partial work. ffprobe requires a measurable audio stream and records hash, size, duration, codec, sample rate, channels and measured bitrate. Duration tolerance and truncation ratio are configurable; missing expected duration routes to review, a recording shorter than 90% is rejected by default, and material differences beyond `max(5 seconds, 5%)` are reviewed. Quality ranking uses measured file-size/duration, observed stream properties and match confidence, never provider-advertised bitrate. Valid source audio is preserved; a separate immutable prepared copy receives official canonical title/artist/release metadata and format-aware Mutagen tags. Configured channel fields are applied by supported format and unsupported mappings are reported. Official SoundCloud artwork is fetched only from recorded `.sndcdn.com` evidence, size/type/dimensions checked, and embedded where supported. Authenticated manual uploads use the same validation, state, audit and tag pipeline.

Observed M3 evidence, the disposable SoundCloud probe measurements and local verification results are in [`reports/M3_MEDIA.md`](reports/M3_MEDIA.md). The local fixture suite passed 43 tests, including format readback, Persian/Latin metadata, upload audit, retries, Spotify review-only handling and concurrent candidate requests. The sole live media probe was explicitly invoked for the supplied Sijal track; it does not establish provider coverage beyond that sample. No source was activated, production baseline run, Telegram API call, publication, deployment, or M4 behavior occurred.
