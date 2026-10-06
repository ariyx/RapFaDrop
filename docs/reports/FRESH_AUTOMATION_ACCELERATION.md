# Automatic fresh-release acceleration and roster-wide recording fallback

Generated **2026-10-06T15:39:45.731746+00:00**. Exact server-tested, pushed and deployed application
**`b430247332d00397d0a45a01c7695f3fd51a0492`**. Owner authorized automatic fresh publication for all 83 approved
artists and recording-level independent uploaders. RapRelease remains a benchmark;
no audio was obtained from it. Popular collection remains paused.

## Implemented and verified

All **83/83** verified enabled Spotify sources now have a staggered **45-second**
poll interval. Discovery scheduler tick is 10 seconds; commit-triggered media and
publication hints remove periodic-only handoff waits. Durable recovery uses
15-second media and 30-second publication ticks. Broker failure cannot invalidate
committed discovery. Review approval queues continuation once. Queue isolation,
album complete pre-staging/order/prior-single rules and uncertain-send holds remain.

Owner-enabled fresh fallback searches up to ten public SoundCloud recordings
within the existing six-probe budget. It applies to **every eligible fresh recording**,
including artists without a registered acquisition profile. Explicit full credits,
title/version, stable native recording/uploader identity and duration must match;
recheck identity and credits before downloading. Reject incomplete files, decode
the whole recording, and verify official artwork and eleven channel fields by
actual tag readback. Independent uploader status and pre-upload encoding remain
unverified. Unknown-source nominal 320 is never an automatic quality upgrade.
Archive policy stays unchanged. A YouTube hold permits SoundCloud lookup without
resetting the held attempt. New transport identities preserve failed candidates
and attempts instead of preventing alternative candidates in the database.

**250 application + nine backup tests passed**, migrations/system/drift checks
passed; health is `ok`. An initial candidate-identity regression exposed the old
one-provider constraint; distinct transport identities fix it. Incorrect test
expectation for a nonretryable credit mismatch was corrected; failed check commits
were not deployed. The intermediate tested `29dc4e6` ran with independent fallback
OFF before the final exact tested application replaced it.

## Observed server-side real media samples

Historical Spotify frozen-selection metadata was read without changing selections
or production rows. A disposable environment had no production DB/Redis credential,
Telegram token or production media volume. These are historical acquisition and
preparation measurements, **not live-release detection or Telegram end-to-end latency**.

| Recording / full credits | Spotify ID | Search/match s | Download s | Art/tags s | Total s | Complete duration s | Native bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Masire Dard / Emad Ghavidel | `6f8ginsFVrSDwG88elopa6` | 10.365 | 11.242 | 0.281 | 30.35 | 329.932336 | 6656623 |
| 33 / EpiCure + Ho3ein | `0GjX7igOYf7jzPtQHDss87` | 11.412 | 7.174 | 0.161 | 25.802 | 237.818776 | 4798221 |
| Bavelamko / Catchybeatz + TM Bax + Talk Down | `7wRd6TS0h8dpDBtzfjGdMw` | 11.22 | 6.902 | 0.105 | 25.733 | 232.942585 | 4699847 |

All three retained native SoundCloud **AAC/M4A 160,000 bit/s, 44.1 kHz, stereo**;
full FFmpeg decoding, complete duration (within five seconds), official art and
all tag readback checks passed. No local audio transcoding. This proves the
SoundCloud delivery source and observed quality, not the uploader's original
encoding. Two previously blocked recordings from different artists, **33** and
**Bavelamko**, now succeeded through recording lookup without activating a profile.
Upload timing is **not measured**; Telegram test/music message IDs are **none**.

A separate controlled **33** replay traversed real materialization, identity,
candidate creation, native re-probe/download, validation, tagging/artwork,
full decoding and durable READY state in isolated PostgreSQL **55433**:
identity 0.387 s, lookup 13.645 s,
media processing 16.905 s, total 32.432 s.
Native download 9.94 s; re-probe
6.488 s; validation/preparation
0.254 s. Replay added **zero**
attempts, candidate IDs or posts. This replay stopped before Telegram transport.
Existing live production single/album evidence remains recorded in the earlier
fresh activation and media repair reports; no new music post is claimed here.

Request accounting: 12 provider subprocesses and three artwork fetches for the
comparison; four provider subprocesses plus artwork for the full media replay.
Underlying yt-dlp HTTP requests were not instrumented; subprocess count is not
an HTTP request count. Registry verification used 110 bounded metadata operations
plus eight official-link pages. No bulk download or default intermediary fallback.

## Registry and polling preservation

Registered acquisition coverage increased **55 to 75 artists / 72 to 92 associated
profiles**. Twenty additions: Ali Ardavan (artist); Ali Geramy (artist); Amir Khalvat (artist); Armin Zareei (artist); Arown (artist); Bamdad (artist); Dalu (artist); Dariu$h (collaborator); Fadaei (collaborator); Hamid Sefat (artist); Heliyom (artist); Isam (artist); Maslak (artist); Mehyad (artist); Parsa (collaborator); Parsalip (artist); Safir (artist); Shapur (collaborator); Sina Mafee (artist); Tlkhoon (artist).
Four collaborator accounts cannot implicitly establish the monitored artist's
credit. Profile presence is separate from recording availability and discovery.
Native public account/catalog agreement and multiple independent own-work matches
were required; reposts were excluded.

The initial 45-second pilot observed **656 actual adapter HTTP requests** over
approximately 170 seconds, all 83 sources with three scheduled successes, no failed
polls or 403/429. After final deployment, all 83 again have three latest successful
scheduled outcomes, evidence timestamp **2026-10-06T15:39:45.731746+00:00**. Prior 83-source sweep:
202 requests, 21.767 summed provider seconds, maximum 2.682 seconds per probe.
No source provider retry hold was shortened or historical baseline reset.

Eight artists still lack an independently corroborated **profile**. The global
recording fallback is enabled for them; do not describe their entire catalogs as
acquired or ready. Exact profile blockers:

- **Arman Miladi:** arman-miladi native account: two own uploads, only one independent Spotify work match; alternate collaborator account also only one match. Profile identity not established.
- **Catchybeatz:** catchybeatz account has no own uploads; collaborator accounts supplied only one independently matched work each. Individual Bavelamko recording succeeded in isolated fallback; this does not verify a profile.
- **Ho3ein:** ho3ein guessed account returned a different display identity and zero own works; alternate account had one unmatched work. FarsiChart profile references a different Spotify artist ID; listed YouTube channel not activated. Individual 33 recording succeeded in isolated fallback.
- **Quf:** qufam has three own uploads but no independent checked Spotify catalog/LP match; bounded collaborator catalog provided no Quf matches. This is a corroboration limitation, not absence of albums.
- **Saman Wilson:** samanwilson native account has one own upload and one independent work match; another guessed group handle resolved to a different identity. Profile identity not established.
- **The Don:** thedonofficial resolved to Don with ten unrelated uploads and zero independent matches; thedonmusic had no own uploads.
- **XWHISKY:** xwhisky has no own uploads; each checked collaborator profile supplied only one independently matched work.
- **Zakhmi:** zakhmiofficial had one unmatched upload; zakhmi had no own uploads.

## Remaining concrete recording blocker and honest quality

**Mano Khoda Shoma Hame**, Spotify `5sYGAU7L6JgUrkfzy9J3Yx`, remains unposted
and visible for review. Official SoundCloud `2413995774` is DRM protected and
not bypassed. Owner-authenticated YouTube access returned a page-reload challenge;
a later bounded probe timed out. The supported client workaround did not resolve
access. Public search found an official new video `GdnlBtXCJDY` with corroborated
title/uploader, but successful audio acquisition through the protected session
has not been established. Source-specific timeout/backoff remains in force.

One separate public Spotsaver intermediary trial used AST-extracted selected
musicdl **2.14.0 / `e5c3bd51b518642c24027921e63f482865809b61`**, no shared key,
no default chain, no account/DRM bypass. Two bounded identical-file attempts used
five HTTP requests each: MP3 **320,000 bit/s**, 44.1 kHz stereo, **854.151825 s**,
**34,166,073 bytes**, complete FFmpeg decode; combined acquisition/inspection
10.802 and 10.027 seconds. The selected video ID is corroborated public metadata,
but the final response omitted resolved video identity and original encoding.
No direct Spotify or native 320 provenance, production approval or publication
is claimed. Safe evidence was attached to the existing review; file removed.

All-artist first-minute delivery and universal native 320 quality are **not proven**.
The system processes available matched complete audio automatically; source access,
upload availability, metadata lag and ambiguous recording evidence can still hold
an individual release. Queue intervals cannot establish release-to-detection latency.

## Deployment, configuration and cleanup

Protected predeployment backup **rapfadrop-20261006T153608Z-4a41bf98.tar.age**
was restored against **47 tables** and uploaded as backup messages **106/107**.
Exact migration includes transport identity hashes without deleting prior rows.
Rollback onto the earlier one-provider constraint requires the protected database
restore if multiple transport candidates exist. A private prior configuration copy
precedes the media-only `fresh-independent.compose.json` overlay; it contains no bot
credential. `RAPFADROP_FRESH_INDEPENDENT_UPLOADERS_ENABLED=true` is restricted to
fresh-media. Metadata/media roles cannot send; the isolated publisher retains the
verified bot **8697681226** and production target **-1004311149640**.

Final state **83 approved / 83 enabled verified sources / 84 baselines / 4,152
items / 71 confirmed message records / zero uncertain sends**. Fresh bridge,
media and scoped production publication **ON/unpaused**; Popular **paused**, frozen
155 recordings/166 slots preserved. Original artist/source/baseline/item/frozen
selection/alias/publication/caption hashes show no unplanned deletion or change;
the authorized 45-second source cadence was normalized for preservation comparison.

Removed **9** comparison media/art files,
**32630252 bytes**, and the intermediary file,
**34166073 bytes**. Isolated full-flow media, PostgreSQL,
Redis and volumes removed with the check environment; disposable build source
and unused raw upstream source removed. Media remaining: **zero**. Test Telegram
posts: **zero**, so deletion is not applicable. Production music and backup posts
deleted: **zero**. Protected sessions retained. Default `celery` queue's three
old maintenance envelopes remain untouched/unconsumed; production queues isolated.
Server health verified after cleanup; daily protected backup service preserved.

[83-row source/recording capability CSV](data/fresh_audio_source_coverage.csv),
[safe timing, preservation and runtime evidence](data/fresh_automation_acceleration_evidence.json).
