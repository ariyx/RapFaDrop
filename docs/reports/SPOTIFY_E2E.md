# Server-only isolated Spotify to Telegram verification

Observed 2026-10-04 UTC. Final tested and deployed application: **`26afd28da5e20bbca37975b5a4512ea871dd6f72`**. Starting deployment: `0214e6dff71b3ac223bd4deddbe07ccd8ae13402`. Production publication remained OFF throughout. This was a controlled historical replay, **not a measurement of live-release detection latency**.

## Isolation and safety

All final acquisition, validation, tests and Telegram requests ran on the server. Initial preflight found 18 GiB available disk and 982 MiB available RAM out of 3819 MiB. The disposable Compose project `rapfadrop-e2e-server` had its own PostgreSQL database/volume (loopback port 55433), Redis instance (56380), queue `isolated-e2e`, media volume mounted at `/isolated-media`, runner and worker. Production database/Redis ports are 55432/56379. No production volume, Docker socket or production credential was mounted. The worker consumed only the isolated queue and had no Telegram token.

Runner/worker limits were 384 MiB and 0.5 CPU each; PostgreSQL 160 MiB/0.25 CPU; Redis 64 MiB/0.15 CPU with a 16 MiB cache ceiling. Publication switches defaulted disabled. Sending used process-scoped Django overrides and a fresh Telegram `getChat` guard before each mutation. The exact verified destination was **`-1004475982526`, `@RapFaDropTest`, type channel**; the production target was empty. Channel branding inside captions/tags did not determine the destination. No send targeted `@RapFaDrop`.

An earlier local attempt was abandoned when the owner requested server-only execution. Its timed-out send had no message ID; the owner explicitly confirmed no post was visible. It was not blindly resent. The old local disposable project was removed. Local acquisition is excluded from the results below.

## Real flow and observed gates

Live Spotify profile identity and complete discography validation returned Sijal artist `5F0BGBdSL945Bzxrq8aGbn`, 89 releases over two complete pages. Live details validated the complete single and album track lists. The replay cached these actual validated provider models and excluded only the selected releases from the **isolated** baseline. It then used the real discovery adapter, `poll_source`, unseen-ID ingestion, canonical identity/deduplication, review approval, media selection, acquisition, preparation and publication code. Historical dates were retained, so operator review was required rather than pretending these were recent discoveries.

Samples: “Vaghti Raft” (Spotify album `7pN6sS1AbnNa4pviSz3u8c`), “Dele Man” (`2Aq5hdtkqmRvrSuQtIBdyS`) and the nine-track LP “OCD” (`2yHJfINmVWOpGLymx3JxaW`). Real full recordings came from [Sijal's Vaghti Raft](https://soundcloud.com/sijalofficial/vaghti-raft) and [OCD set](https://soundcloud.com/sijalofficial/sets/ocd), stable uploader `801842584`. Title guest suffixes and prior-single release-date differences were explicitly reviewed as cross-platform corrections. Approval replays created no additional processing jobs.

Ten distinct recordings were acquired, including Dele Man once as the prior single. FFprobe and full FFmpeg decode verified playable complete audio before publication. Mutagen readback checked actual official titles, all artist credits, album names, configured channel fields and embedded artwork. A comments-only channel-tag configuration was also checked on a real prepared copy. Telegram `getFile` readback of all ten audio files matched uploaded bytes exactly and passed full decode and embedded metadata/artwork verification. Embedded cover bytes matched the official cover files.

The album could not send an introduction until all media was ready. It sent its official cover/introduction followed by the eight remaining tracks in order. Dele Man was linked as an earlier single, skipped as a new audio post and edited to include the album URL. All eight album-track captions included the introduction URL after the fix. Missing video/original rows were omitted; Spotify/SoundCloud links, DROP/LP DROP labels and guest introduction formatting were checked against actual Telegram responses and durable records.

A controlled provider probe changed the observed native ID to an explicit mismatch. The real candidate-processing path rejected it before download, retained `REVIEW_REQUIRED` with `provider_identity_mismatch`, exposed it in the review/admin queryset, and refused publication. Unsupported manual candidates also stayed visible pending complete audio. No link-only fallback was sent.

A definite **pre-send** error was injected for “2 Ace”; no Telegram call occurred for that failed attempt. The durable album cursor remained at the failed track with retry state. Runner/worker restart and a fresh-process retry resumed there, preserving the already confirmed cover and first track. Media worker restart was also exercised. Subsequent discovery, identity, approval, media and publication replays left counts unchanged: ten queue entries, 21 candidates, 11 media attempts and 13 publication attempts before cleanup; only eleven successful sends. This verifies definite-failure recovery. A genuinely uncertain live send was not deliberately induced; reconciliation remains covered by the automated suite.

## Defects, deployment and checks

Commit `d9ba58718a21880bf06fe18063197b16d5df787c` fixed missing official collaborator credits, selection of unsupported older matches ahead of supported candidates, and rejection of provider-probed SoundCloud identity mismatches before download. Contributor records are disabled; the fixes do not enable additional sources. Relevant checks and the full 134-test suite passed before deployment.

The first server Telegram run revealed a fourth defect: the first album track used the cached, previously unsent introduction object, omitting its Album link. Commit `26afd28da5e20bbca37975b5a4512ea871dd6f72` refreshes the session introduction immediately after its confirmed send. A regression checks both actual send payloads and durable captions. Changes were made in the normal checkout, committed and pushed normally; exact tested SHAs were deployed. The complete final **135-test server suite passed in 111.389 seconds**, with Django checks and no migration drift; **35 focused publication tests passed in 17.808 seconds** after deployment using a separate temporary media root.

Each deployment used the documented protected backup/checksum/list/restore procedure before changing application services. All 37 public-table row-content digests matched the disposable restore; restore databases were dropped. Retained root-only backups:

| Before deployment | Archive | Bytes | Restored content digest |
| --- | --- | ---: | --- |
| d9ba587 | `/var/backups/rapfadrop/pre_spotify_e2e_20261004.dump` | 197518 | `8873e3e76ad0c08f95b023489e929a2144f89bd65eaf181a22c3ba81d2d44d87` |
| 26afd28 | `/var/backups/rapfadrop/pre_spotify_albumcaption_20261004.dump` | 198140 | `3242c2fc96277bccb42881c5e68a8790849485c7f4cb724cd973568d87f28f30` |

Production beat and workers were briefly stopped for consistent backup and application services recreated afterward; PostgreSQL/Redis volumes were preserved. No firewall, Nginx or production overlay change was needed. An initial focused concurrency test used an isolated database but inherited the production media mount and generated two synthetic 30-second test files. Their exact paths were identified and deleted after verifying no production references; production media returned to zero files. All subsequent focused checks used a separate media root.

## Timings, requests and quality

Timings are measured on the **final server run**. Provider metadata/probe/download figures are separate from the controlled discovery replay and Telegram readback. Preparation below measures tag/copy work only; cover fetching and complete-audio decode validation are additional operations included in end-to-end elapsed time.

| Stage | Observed time | Scope |
| --- | ---: | --- |
| Spotify identity | 0.612 s | 2 HTTP invocations |
| Complete Spotify discography | 0.464 s | 2 pages, 3 HTTP invocations; transport 0.444 s |
| Selected Spotify details | 1.488 / 0.362 / 0.449 s | 2 HTTP invocations each |
| Controlled unseen-ID discovery replay | 0.383 s | Cached validated responses through real application ingestion |
| SoundCloud single / set metadata | 3.726 / 10.999 s | 8 / 60 HTTP invocations |
| Acquisition: ten native probes | 41.923 s summed | 3.855–4.895 s each |
| Acquisition: ten complete downloads | 56.399 s summed | 4.865–6.111 s each |
| Preparation: ten tag/copy operations | 0.351 s summed | 0.017–0.066 s each |
| Upload: ten audio + one cover send | 78.265 s summed | 1.073–61.605 s per send; excludes getChat/readback |
| Single end-to-end: Vaghti Raft | 144.504 s | Replay observation to confirmation and readback |
| Prior-single end-to-end: Dele Man | 228.062 s | Same definition |
| Complete OCD album end-to-end | 602.057 s | Includes review/acquisition, safety guards, restart/retry and readback |

Final replay observation began `2026-10-04T09:30:20.944249Z`. Album elapsed time from acquisition start was 590.944 s. These figures do not establish live-release polling latency. Some Telegram operations took approximately 60 seconds; no network cause was established.

Measured request volume: Spotify 11, SoundCloud metadata 68, instrumented yt-dlp probe/download HTTP entry calls 373, artwork requests 10: **462 counted HTTP invocations**. The additional controlled mismatch probe and Telegram calls are outside that count. This is instrumented application/provider request volume, not an exact packet count including every internal retry.

The ten original files totaled **38,047,154 bytes**, AAC/M4A, **44.1 kHz stereo**, durations **139.900227–236.982857 s**, measured bitrate **161408–161432 bit/s** (approximately 160 kb/s audio with container overhead). No bitrate upconversion was performed. Larger prepared-file bitrate reflects embedded JPEG/tag bytes, not improved audio quality.

## Message evidence and disposal

The first server run at d9ba587 produced message IDs **21–31**; all eleven were deleted. The successful repeat at 26afd28 produced:

| Message ID | Content | Cleanup |
| ---: | --- | --- |
| 32 | Vaghti Raft | Deleted |
| 33 | Dele Man prior single | Deleted |
| 34 | OCD cover/introduction | Deleted |
| 35 | Hichki Mese Man | Deleted |
| 36 | 2 Ace | Deleted |
| 37 | Bekhatere To | Deleted |
| 38 | Kabol | Deleted |
| 39 | Seda | Deleted |
| 40 | Eshghe Alaki | Deleted |
| 41 | Greece | Deleted |
| 42 | Azadi | Deleted |

Durable message IDs, attempts, captions and file-quality evidence were exported as safe audit details before database disposal. Final summary records eleven `deleted` publications, ten byte-matched Telegram readbacks and zero remaining test media files. Compose containers, both disposable PostgreSQL/media volumes, isolated Redis/queue and protected temporary token environment were removed. Safe summaries are retained under root-only `/var/lib/rapfadrop-operations/e2e-20261004/`; no downloaded audio, tokens or database dump from the test is retained there.

## Production outcome and limits

After deployment and cleanup: healthy web/database; clean deployed application SHA 26afd28; five verified/enabled Spotify sources at 180 seconds: Sijal 31, Fadaei 39, Hichkas 42, Yas 44 and Ho3ein 48. **177 historical Spotify IDs, zero new IDs**, and zero production reviews, processing jobs, media candidates/attempts, publications/attempts or media files. Stable SourceItem digest `bad43929b7c93f9a77d61a9a4a3feafc130de248898784ffad2031950828b7d4` and baseline digest `c7d071ba1adc750ce13e93bb6dd3d06e3fa2c4d2a2eec464191ddbd677461639` were unchanged. Pilot/media queues were empty; the pre-existing unconsumed default-queue housekeeping envelope was left untouched.

The protected Spotify-to-media bridge remains **ON**. Telegram mode remains **disabled**, Telegram live flag **false**, publication-worker flag **false**, with no production bot token. Manage production with all three Compose files in order: `compose.internal.yaml`, `spotify-pilot.compose.yaml`, `spotify-bridge.compose.yaml` (the latter two under `/var/lib/rapfadrop-operations/`).

The bounded reviewed single/LP full path passed; the mismatched candidate correctly remained blocked for review. There was no missing-complete-recording blocker for these samples. Automatic recent-release matching without review, live detection latency, live uncertain-send reconciliation, and a separate EP Telegram run were not measured. Production publication activation is a separate owner decision; this task stops before activation.
