# Automatic new-release activation

Updated 2026-10-06, Tehran. Evidence snapshots: 2026-10-06T09:35:27Z
(13:05 Tehran), 10:00:49Z (13:30 Tehran), and final runtime/cleanup observations in
[safe audit evidence](data/fresh_release_activation_evidence.json).
The owner explicitly authorized production activation and catch-up publication;
the Popular collection did not need to finish first.

Tested, pushed and deployed application:
**`4226ecbc65b3def5e8b6dce32338a777b68d8e87`**.
Implementation commits `75fecf1`, `5e0a250`, `27fb202`, `4226ecb` are on main.
This handoff is a documentation-only follow-up; its commit does not require
application deployment. **229 application tests + nine backup tests**, migration,
system check, migration drift and deployment health passed on the exact final code
in a separate server PostgreSQL/Redis/media environment.

## Running configuration and preservation

All **83 approved artists / 83 verified enabled Spotify sources** remain covered.
The original **84 baselines, 4,133 source items, curated source fields and 54 archive
publications** were hash-compared: none deleted or modified. Discovery/derived
track facts increased the current source-item count to **4,152**. Four official
contributors were added disabled; total Artist rows are 87, without expanding the
approved discovery roster. Three generic identity reviews were resolved with
complete native-credit evidence; genuine ambiguity remains held. The original
caption rows were preserved; three immutable defaults were added by the existing
caption versioning path. No caption or metadata policy was changed.

Popular collection stays **paused**, with **83 artists / 166 slots / 155 native
recordings / 152 canonical identities**, **54 unique posts and 98 pending rows**.
Original selections, aliases, reviews and publication IDs remain durable.

Protected Compose order is internal, Spotify pilot, Spotify bridge, discovery-only,
then `/var/lib/rapfadrop-operations/fresh-production.compose.yaml`. Final runtime
roles and queue subscriptions were inspected:

| Role | Queue/schedule | Bridge/Fresh | Telegram mode/live/publication | Credentials |
| --- | --- | --- | --- | --- |
| web | Admin/health | ON | disabled/OFF/OFF | No provider session or music token |
| worker | `spotify-pilot` | ON | disabled/OFF/OFF | No music token |
| beat | Discovery tick 60s; fresh media 60s; publication 30s | ON | production/ON/ON | No music token |
| fresh-media | `fresh-media-v1`, solo concurrency 1 | ON | disabled/OFF/OFF | Owner YouTube cookie, read-only Deno |
| fresh-publication | `fresh-publication-v1`, solo concurrency 1 | ON | production/ON/ON | Private music bot file only |

All 83 source polling intervals remain **180 seconds**. Actual scheduler dispatch,
worker consumption, repeated complete polling and durable due-state progression
were observed. The fresh queues and Spotify queue were empty at the completion
snapshot. The unconsumed default `celery` queue still contains three backend-cleanup
envelopes; it was neither purged nor subscribed. Runtime memory limits are 256 MiB
metadata worker, 192 MiB beat, 384 MiB media and 256 MiB publisher, with CPU limits.
Health/database and daily backup timer pass; disk has approximately 11 GiB free.

Before sends, actual `getMe/getChat/getChatMember` verified **RapFaDropBot,
8697681226**, exact **`-1004311149640 / @RapFaDrop`**, channel type and administrator
posting permission. The gateway repeats these checks per mutation and permits
only durable fresh scope. The media worker cannot send, and the fresh publisher
cannot send the paused Popular backlog. Private worker cookies and the music token
are UID 1000, mode 0600; no secret enters Git or this audit. YouTube uses protected
owner authentication, Deno 2.5.0, yt-dlp 2026.8.19 and yt-dlp-ejs 0.8.0.

## Catch-up and actual results

Initial durable manifest: **3 eligible, 3,887 excluded, one review**. Exclusions are
3,882 historical baseline facts and five pre-baseline 2025 catalog additions
(Eycin: Motenaferam, Chi Migi, Chizi Namonde; Naaji: Az Inja, Tadriji).
Later real scheduled discovery added two eligible releases, making **5 eligible,
3,887 excluded, one review / 3,893 total**, without manufacturing a discovery.

| Release | Native Spotify release ID | Current result |
| --- | --- | --- |
| Amin Tijay — Pellezterari | `5DGYK44aTDyMJrka40TZ0S` | Complete LP; introduction **61**, ordered tracks **62–74** |
| Hesam Tiem — Joft 6 | `1CVZnb0I9ZPAavTxmu72tt` | Complete single, **60** |
| Mamazi — OGHDE | `40O11g61vfThnoSF8FYdsq` | Pending; no independently corroborated credited acquisition profile registered |
| Amir Tataloo — Mano Khoda Shoma Hame | `2Q9azs6CaUEkqZtTYYCTZl` | Real discovery at 2026-10-06T08:16:10.599655Z; pending complete matched audio |
| Masin — GHASAB KALAMAT | `2DPb4WL7ltHPaDmThDahsE` | Real scheduled discovery and complete automatic send, **75**, with full decode/tag/artwork/Telegram byte readback |
| Dalu — HAHAAA | `6IByq1FJu3hGv0CoU6qBVc` | Review: day-only release date overlaps baseline; freshness cannot be proved |

The Tataloo release's complete official response contains one **855.054-second**
track `5sYGAU7L6JgUrkfzy9J3Yx`, credited to Amir Tataloo and Hassan Baba and typed EP
upstream. Verified catalogs were bounded/cached at 150 SoundCloud and 50 YouTube
entries; a matching-title YouTube candidate `cmj7_tDeekQ` timed out at the existing
30-second probe bound. It was not accepted, downloaded, trimmed or published.
Both unavailable releases have durable manual-review candidates and staggered
exponential retry due states; neither blocks unrelated ready work. At the snapshot
there was no active shared provider-authentication backoff. A future shared access
challenge persists a provider-specific 15-minute hold and actionable admin alert,
without anonymous fallback. No claim of currently working Tataloo audio is made.

Pellezterari was observed **2026-10-05T08:32:20.316919Z**, official release day
2026-10-05, after its successful 2026-10-04 baseline. Its identity came from the
stored album release, not a guessed Yadegarit album ID. Complete ordered credits
identify Amin Tijay, Lil Deafo and !Leo on all tracks; Neemski is featured on a
subset. All 13 unpublished recordings were acquired, prepared and fully decoded
before the introduction. No prior matching published single existed for these
tracks; actual prior-single reuse was not exercised by this album, but remains
covered by focused tests. Official version text, including Old Version, is preserved.

| Position | Track | Native Spotify track ID | Production message |
| --- | --- | --- | --- |
| 1 | Yadegarit | `3yhTL64et9hrK0JjN5r811` | 62 |
| 2 | Nemitarsam | `7oT3uQejr7WCa8QIodyTpB` | 63 |
| 3 | Khastegi | `2HeRkvMYpmE09psRVzGyfP` | 64 |
| 4 | Naya Donbalam | `0Y04tdpbsP7HdS05iycSw6` | 65 |
| 5 | Nefrine13 | `40Bc6U3vxP4SacSlP1s6Jz` | 66 |
| 6 | Asemoon | `6rUIBLKYT21FJVnZxfrGLw` | 67 |
| 7 | Pelleha | `6LLPkollGzKWE6XElrC6DX` | 68 |
| 8 | Bad Trip | `6XxYODV3Kg5JZ8FVivAxzE` | 69 |
| 9 | Tanha Plan | `4Wc9tcoNbUJIDwthNDcY5z` | 70 |
| 10 | NRF | `35dxPxGmlANeeCQo77K46a` | 71 |
| 11 | Matarsak | `3sbVPy0q2iBPzMt3piLfic` | 72 |
| 12 | Ghalbam Ni - Old Version | `2nkwgxTa286hBolgT6hdTr` | 73 |
| 13 | Donya Vaysa | `0XBuOJQP4gWkfBjoJe8yDc` | 74 |

Joft 6 track `0zuVzvQy5TazHzkDNn2NV9` used the confirmed native artist identity
despite the provider spelling HesamTiem versus the curated Hesam Tiem name.
Actual source was `https://soundcloud.com/hesamtiem/joft6`; all album files came
from verified `soundcloud.com/amintijayy` recordings. Those **14 complete native AAC/M4A
files**, approximately **160 kb/s, 44.1 kHz stereo**, were sent with no audio
conversion and no claim of native Spotify audio or MP3 320 quality. Duration/version,
full FFmpeg decoding, actual eleven-field tag/artwork readback and **Telegram
byte/hash readback passed for all 14 files**. Per-file bytes/durations/provenance
are retained in safe evidence. Introduction cover, caption text and Telegram
entities are durable; single Drop and album LP Drop headings are bold/channel-linked,
and album-track Spotify/Album links point to confirmed introduction 61.

An additional **Masin — GHASAB KALAMAT**, Spotify track
`1UhTtkURtKqG2intH9Ll6P`, was genuinely observed at
**2026-10-06T09:49:10.616977Z** and automatically confirmed as message **75** at
**09:50:46.451580Z**: **95.835 seconds after recorded discovery**. This measures
application processing, not unknown Spotify release-to-detection latency.
Verified native SoundCloud source was `https://soundcloud.com/masinrap/ghasab-kalamat`.
Complete AAC 160 kb/s / 44.1 kHz stereo, 262.641s, full decode, all tags/artwork
and 5,323,166-byte Telegram hash readback passed. Provider probe took **3.899s**,
acquisition **5.108s**, preparation **0.227s**, successful gateway phase **5.417s**.

The initial fresh caption context omitted the acquisition URL for a Spotify-led
identity. Commit `4226ecb` adds the already-verified SoundCloud URL without changing
caption templates or policy, with a focused regression. Messages **60 and 75**
were corrected in place to `Drop / › Spotify · SoundCloud`; Telegram entities
confirm both links and the bold channel-linked heading. Audio and message IDs were
preserved, no new audio sent; replay of message 60's edit added zero attempts.
The acquisition/publication evidence above was obtained on `27fb202`; the final
caption fix, live edits and operational readback ran on exact tested/deployed `4226ecb`.

There are **16 new production posts / 15 audio + one introduction**, messages
**60–75**, and **70 total confirmed publications**, including the untouched 54
Popular posts. Album cursor is **13 / complete**. Each new publication has one
successful send attempt, zero duplicate sends and **zero uncertain outcomes**. Repeated
scheduler replays and completed-album refreshes added no posts. No live failed-send,
upgrade or 15-minute album-hold scenario occurred; those paths were verified with
focused simulated tests rather than fabricated production failures.

## Timings, observed defect and recovery

The real SDK supplies some track artist references with an empty `id` and a valid
`spotify:artist:...` URI. This initially held all three eligible releases before
acquisition. Production was durably paused, the adapter was fixed with a real SDK
fixture/conflicting-ID regression, the exact final SHA was tested/backed up/deployed,
and the three real responses were revalidated without lowering identity checks.
Metadata rechecks took **0.462s Pellezterari, 0.343s OGHDE, 0.261s Joft 6**.

For the initial 14 files, measured acquisition was **4.588–5.593s per file**; validation/tagging/preparation
**0.164–0.301s per file**. Successful gateway phases, including target checks,
upload and durable confirmation, were **1.316–62.145s per audio**, introduction
**0.506s**. They are measured using audit events attached to the successful attempt,
not injected `started_at/finished_at` values. Pure socket-upload time was not
separately instrumented. Joft 6 confirmed at **2026-10-05T21:42:42.454960Z**;
album introduction at **22:05:41.358367Z**, last track at **22:08:11.402789Z**
(2026-10-06 01:38:11 Tehran). Introduction-through-last-track took **150.044s**.

Observation-to-confirm catch-up timing was **17,637.603s** for Joft 6 and
**48,951.086s** through the album's last track. These include the disabled period,
code correction, scheduling and complete-album staging; **they are not live-release
detection latency**. Recent complete Spotify polling responses took **0.131–0.514s**
for 1–2 pages / 2–3 requests. A newly discovered Tataloo item was genuinely observed
after activation, but its first public release time and successful send are not
known, so no live end-to-end latency claim is made.

A controlled graceful stop/restart of both fresh workers preserved exact paused
dispatch, track, candidate/retry and published-message snapshots, then resumed with
the verified target. An initial temporary audit helper had a syntax error after
the graceful stop; it was corrected and recovery completed before the snapshot.
No app code or message history was affected. Daily backup service restarts also
left the overnight automatic pipeline operating. All source/baseline/frozen-record
preservation checks and final health passed.

Protected restore-verified recovery receipts, dedicated backup channel only:

| Recovery point | Restored tables | Backup-channel receipt IDs |
| --- | --- | --- |
| `rapfadrop-20261005T205253Z-3eca00c7.tar.age` before first deployment | 43 | 86 / 87 |
| `rapfadrop-20261005T205447Z-11e9f4e6.tar.age` before activation | 47 | 88 / 89 |
| `rapfadrop-20261005T205614Z-9cec74c7.tar.age` armed-paused configuration | 47 | 90 / 91 |
| `rapfadrop-20261005T212855Z-bda583c4.tar.age` before final adapter fix deployment | 47 | 92 / 93 |
| `rapfadrop-20261006T095420Z-3474138e.tar.age` before final caption-link fix deployment | 47 | 96 / 97 |

All five uploads completed; task cleanup did not delete any backup material or
backup-channel message. Configured daily local retention remains independent.
After evidence/readback, **45 confirmed media/artwork files / 106,177,668 bytes**
were removed. No pending media, production post, history, session or backup was
deleted. Disposable `rfd-fresh-check` DB/Redis/runner and two source/build directories
were removed without deleting production volumes. No cleanup blocker remains.

## Owner/server commands

Run over SSH; the owner's computer can be switched off. Server Docker services
continue independently and restart according to their protected configuration.

```sh
ssh root@91.107.178.12
python3 /opt/rapfadrop/ops/control_fresh.py status
python3 /opt/rapfadrop/ops/control_fresh.py pause
python3 /opt/rapfadrop/ops/control_fresh.py resume
docker logs --tail 30 rapfadrop-fresh-media-1
docker logs --tail 30 rapfadrop-fresh-publication-1
```

Pause preserves durable work/queues/history, leaves discovery running and does not
resume the Popular collection. Resume verifies bot/channel permissions. Current
handoff: **automatic new-release processing/publication running**, two acquisitions
pending with explicit blockers, one freshness review, Popular collection paused.
