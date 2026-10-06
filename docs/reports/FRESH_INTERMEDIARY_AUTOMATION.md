# Fresh intermediary automation and owner-approved publication

Generated **2026-10-06T16:38:08.273316+00:00**. Exact server-tested, pushed and deployed application
**`7bf07060c4ddcf7496c8ffe369420505d13242e6`**; **259 application + nine backup tests** passed, migrations/system/drift
checks passed. Documentation commit may be newer than the running application.
[Safe evidence](data/fresh_intermediary_automation_evidence.json),
[83-artist coverage](data/fresh_audio_source_coverage.csv).

## Owner policy and implemented behavior

The owner explicitly requested publication of the complete intermediary sample
and automatic handling of similar future recordings, then clarified that original
sources have priority and 100% original provenance is unnecessary. This supersedes
the earlier hold for unknown intermediary encoding/output binding. Work/version,
full credits, stable selection, complete duration, full decode, official artwork,
actual tags, deduplication and uncertain-send reconciliation remain required.
No access-control/DRM/entitlement bypass or third-party shared credential was used.

The normal fresh acquisition finder runs first: registered SoundCloud/YouTube and
the previously owner-enabled independent recording lookup. If no usable match is
available, **all 83 artists** can use the public Spotsaver path. A held provider
does not freeze healthy alternative providers. Shared authentication/network/429
failures hold only that provider for 15 minutes; bounded negative lookup cache is
60 seconds. Failed candidates/attempts remain intact and visible for review.
Archive/frozen selections are unchanged; Popular remains paused.

`RAPFADROP_FRESH_SPOTSAVER_ENABLED=true` is enabled only on the protected media
overlay. The media worker has no bot credential and all Telegram switches OFF.
The scoped publisher retains production/live/publication ON, with independently
verified bot **8697681226**, chat **-1004311149640**, username **RapFaDrop** and
posting permission. Fresh bridge is ON/unpaused; no historical catalog backfill.
The service runs on the server and does not depend on the owner's computer.

## Selected intermediary and actual server measurements

Implemented only the inspected public Spotsaver method from **musicdl 2.14.0,
`e5c3bd51b518642c24027921e63f482865809b61`**, not its package/default provider chain.
No embedded API credentials are used. Public frontend headers and anonymous
ephemeral response cookies are preserved in memory; no owner Spotify/YouTube
session is supplied to this intermediary. Hosts, HTTPS, redirects, byte/request
budgets and timeouts are bounded. Binary URLs/cookies are not persisted.

| Recording | Spotify ID | Result | Lookup seconds |
| --- | --- | --- | ---: |
| Masire Dard | `6f8ginsFVrSDwG88elopa6` | Metadata only matched; no download | 5.373 |
| 33 | `0GjX7igOYf7jzPtQHDss87` | Intermediary public video recording/version mismatch | 5.527 |
| Bavelamko | `7wRd6TS0h8dpDBtzfjGdMw` | Metadata only matched; no download | 1.705 |
| Mano Khoda Shoma Hame | `5sYGAU7L6JgUrkfzy9J3Yx` | Full recording passed | 0.748 |

The comparison performed **15 recorded HTTP requests**: three metadata/video
requests for each sample, plus three download/redirect requests for Tataloo.
Masire Dard and Bavelamko establish metadata matching only; they were not downloaded
again. **33 remains rejected on the intermediary path for public video
recording/version mismatch**; its earlier complete SoundCloud acquisition remains
separate successful evidence. This is not a claim of failure across all providers.
The first adapter trial without inspected frontend headers received HTTP403 on
the first sample and stopped. The corrected public protocol succeeded; no login
challenge was bypassed and no shared failure was repeated for every artist.

Tataloo + Hassan Baba, **Mano Khoda Shoma Hame**, track
`5sYGAU7L6JgUrkfzy9J3Yx`, expected **855.054 s**, selected corroborated public
video `GdnlBtXCJDY`. Actual **MP3, 320,000 bit/s, 44.1 kHz, stereo,
854.151825 s, 34,166,073 bytes**, SHA256
`8d2d792dbed2928d3fc0e853d8eaf8038227739825781cc84a30c88bad65274c`.
Provider domains: **spotsaver.net**, **www.youtube.com** (metadata only),
**yt1s-worker-6.dlsrv.online** (binary transport; earlier approved sample used worker2).
Corrected adapter lookup **0.748 s**, acquisition **4.029 s**, separate full
FFmpeg decode **7.913 s**, total **13.197 s**. No local audio conversion.
Intermediary conversion, original encoding and final binary/video binding remain
unreported. The owner accepts this uncertainty. **Not direct Spotify audio or
proven native MP3 320**, and never counted as a quality upgrade.

## Normal isolated application flow and live approved post

Controlled historical replay in disposable PostgreSQL **55433**, separate Redis
and media volume, Telegram disabled/no credential: real materialization/identity,
intermediary lookup, candidate creation, identity recheck, download, full-file
validation, official artwork/tag preparation and durable READY all passed.
Identity **0.335 s**, lookup **0.362 s**,
normal media processing **5.356 s**, download
**4.288 s**, provider recheck
**0.283 s**, recorded validation/preparation
**0.546 s**, total READY
**9.771 s**. The preparation timer covers its recorded section,
not every later decode/readiness check. Recheck/download recorded six requests;
initial lookup adds three, plus official artwork fetch. All actual tag fields and
embedded artwork read back correctly. READY replay added **zero attempts/posts**.
No discovery or upload latency was measured in this replay.

Before automatic integration, the specifically owner-approved exact sample was
prepared through the shared validation/tagging flow as candidate **234**:
preparation **6.349 s**, complete decode/artwork/tag readback passed. Earlier
bounded acquisition/inspection **9.346 s**, five HTTP requests. A root-run
operational helper initially created UID0 files; only this candidate's files and
track directory were corrected to UID1000. Normal media workers already run UID1000.

The existing scoped album publisher then sent **cover/introduction 77** and
**audio 78** in order, at **2026-10-06T15:58:14.842326Z** durable scheduler time:
[introduction](https://t.me/RapFaDrop/77), [audio](https://t.me/RapFaDrop/78).
Existing official release classification was preserved; this one-track EP does
not demonstrate a multi-track album trial. Audio caption remained **EP Drop**,
Spotify then Album link; Telegram returned matching entities/performer/title,
duration **854 s**, **34,250,263 tagged bytes**. Durable publication IDs **72/73**,
album session **2** completed, cursor **1**. Exact deployment restarted workers;
normal scoped replay after restart added **zero attempts/messages**.

**Upload wall-clock duration is unmeasured**: the existing attempt records one
scheduler timestamp for both start and finish, so subtracting them would be
misleading. Telegram audio byte readback remains **blocked by hosted Bot API's
20 MB file limit**. Full original/prepared local decode and tag/art readback plus
durable Telegram response passed; do not describe hosted byte comparison as passed.
These bounded historical replays are not measured live-release detection latency.

## Preservation, backup, cleanup and remaining limits

Final: **83 approved / 83 verified enabled Spotify sources**, all with three
latest successful scheduled polls, staggered **45 s** cadence; **75/83** associated
acquisition profiles, **92 rows**. **84 baseline runs / 4,152 SourceItems**,
**73 confirmed message records / zero uncertain sends**. Popular stays paused,
**155 frozen recordings / 166 slots**; no collection resume or historic backfill.
Independent public recording and intermediary fallback apply even where a verified
artist profile is absent; availability is checked per recording.

Encrypted pre-mutation backup **108/109**, intermediate deployment **110/111**,
final exact pre-deployment **112/113**, final enabled-configuration **114/115**;
all restored **47 tables** and uploaded. Only the media overlay was added.
Recovery config was also corrected to include both independent and intermediary
overlays in `protected_files`, since `compose_files` alone does not archive them.
Critical artist/baseline/item/archive/registry/caption/publication table hashes
matched the exact pre-deployment snapshot. Existing source IDs/curated fields,
baselines, historical IDs, schedules, captions and old publications were preserved.
Daily backup timer and protected owner sessions remain.

Removed **2 disposable binary files /
68332146 bytes**, upstream raw source, build source
and isolated database/Redis/media volumes. Removed only the confirmed candidate234
temporary source/prepared/artwork files (**3 files /
68464861 bytes**), retaining safe facts/provenance/durable IDs.
No production music post or backup message was deleted; unrelated media untouched.
Production health/database **ok**. Only isolated queues are consumed; three dormant
default `celery` envelopes are preserved.

Automatic fallback is enabled for every approved artist, with original-source
priority. This does not guarantee every upstream recording is available, native
320 quality, or publication in the first minute. Explicit wrong/missing/partial
recordings remain review-visible and unposted; public provider failures retain
isolated backoff. Future live-release latency remains unmeasured. No DRM path,
bulk intermediary collection resume or further account setup was enabled.
