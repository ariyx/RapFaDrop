# Popular-track acquisition continuation

Generated 2026-10-05; final database evidence at **2026-10-05T10:17:40.530090Z**;
current CSV timestamps are in each row. Application tested, pushed and deployed:
**`2c8de05810e06fa577afa17fa9c07ce2c34a5133`**. Documentation commits after that SHA
do not require another deployment. This continues `initial-popular-20261004`.

The bounded server pass completed successfully at 10:16:48 UTC. It published one
new recording, reconciled two alternate Spotify identities without resending,
and left 110 uncertain/unavailable selections pending. This is partial collection
coverage, not completion for all artists and not live-release detection evidence.

## Outcome and evidence

| Measure | Before | After |
| --- | ---: | ---: |
| Frozen artists / slots / Spotify native rows | 83 / 166 / 155 | unchanged |
| Canonical identities after evidenced aliases | 154 | 152 |
| Native rows satisfied / unique production messages | 42 / 41 | 45 / 42 |
| Pending native rows | 113 | 110 |
| Acquisition identities: SoundCloud / YouTube | 32 / 30 | 33 / 30 |

**51/166 artist slots** now have a confirmed publication. Twelve artists have both
slots, 27 have one, and 44 have neither. Shared credits and aliases explain why
slot, native-row and unique-message counts differ. Three aliases exist in total,
including the previously reconciled Be Mula.

New **Taghsire Mane**, Spotify `4dg45KS6u6MmE0rpiiuASt`, is production
[message 47](https://t.me/RapFaDrop/47). Independently verified native SoundCloud
uploader `951055312` (`https://soundcloud.com/justiem`) was added for Hossein Tiem
as acquisition source 63. The already verified native YouTube channel
`UCOIr1MHUDZ2-3styyCGFcyg` explicitly links this profile and Spotify artist
`2ZgLpNVB2qQTifvz3l8xIY`; a fresh complete track probe confirms the uploader.
Both Tiem and Shayan Yo credits were checked. A repost in another artist's catalog
was not used as uploader ownership proof. This acquisition record does not enable
SoundCloud discovery; the existing artist/source record and flags are preserved.

Mituni Mage (`6zctI4eibSmLYcdCm3WNjb`) now reuses [message 20](https://t.me/RapFaDrop/20)
through canonical `2Ty7bGT5io8tYoW8is7OeD`. Highway (`4SkeTCe5fvWK7GLptQyM8a`)
reuses [message 26](https://t.me/RapFaDrop/26), canonical `0xJGuS0MYvyvzZnarcvhm8`.
These merges used the same official native recording, all credits, version and
duration, and an existing confirmed source binding. They are not title-only merges.
All 41 old publication rows, candidates, captions and message IDs are unchanged;
resuming the collection produced only one successful new `send_audio` attempt
(106), no failed/uncertain sends, no upgrades, and no duplicate old posts.
No independently validated better recording was established for existing posts.

## Real provider checks, quality and timing

All network/acquisition/checks ran on the server. Before production use, the
existing application image ran in a separate read-only container with no production
DB, queue, credentials or media mounts: 384 MiB, 0.5 CPU, 64 PIDs, 180 MiB tmpfs.
Preflight found about 12 GiB disk free and 871 MiB available memory.

| Check | Actual result |
| --- | --- |
| YouTube `-otaF5BEt30` on verified Tiem channel | Login/bot challenge after 3.973 s; no audio acquired, no bypass |
| SoundCloud native track `2367906905` | Full AAC/M4A 160,000 audio bps, stereo 44,100 Hz; 203.035283 s vs Spotify 203.011 s; 4,096,545 bytes; full FFmpeg decode passed; isolated acquisition/check 11.715 s |
| Production message 47 | Same native AAC preserved; delivered 4,121,770 bytes, 160,000 audio bps, same duration/rate/channels; artwork/tags explain container overhead; no transcoding |

Production timings, in seconds: matching catalogs **2.561 + 2.552**;
pipeline provider probe **2.650**; audio acquisition **4.031**;
validation/preparation **0.152**; total media work **15.827**;
upload operation including serialized send/readback **61.847**;
total processing **77.674**. Substeps do not exhaust total media work, which
includes matching, artwork and other pipeline overhead. No fresh Spotify discovery
was run: frozen historical selection evidence is retained in the CSV. These numbers
are processing timings for a historical collection, not live discovery latency.

Full decode passed. Actual embedded tags read back all eleven owner fields,
preserving official title/credits/album/numbering and embedding the official JPEG
cover. Delivered byte/hash readback from Telegram matched the prepared file.
Actual response entities confirm **Fave** bold and linked to the channel, followed
by `› Spotify · SoundCloud`; no artist/title caption lines or YouTube caption link.
Caption templates and album introduction markers were not changed.

Recorded bounded-pass evidence: **111 acquisition attempts**, **40 catalog
extractor invocations** (107.977 s summed), **39 newly cached successful searches**,
**six recorded matching probes**, one production audio download. In addition, the
isolated viability check made two track probes and one SoundCloud download, and
seven existing verified YouTube channel about pages were inspected for crosslinks.
These are application/extractor counts, not a measured HTTP request count; yt-dlp
can issue multiple HTTP requests, and unsuccessful searches are not counted as
cache entries. Catalogs cap at 50, with at most one SoundCloud expansion to 150;
search caps are 20 SoundCloud / ten YouTube; matching probes cap at six per recording.
Requests were serialized/bounded, with cached bindings and source-level backoff.

## Remaining blockers

**47 native rows** lack an independently corroborated profile for a credited artist.
About-page checks for Dorcci, Reza Pishro, Shayea, Yas, Hichkas and Sajad Shahi did
not establish the exact candidate SoundCloud crosslink. Candidate names alone,
mixed artist catalogs and absent links cannot authorize a source. This does not
prove those recordings are unavailable; corroborated official links or matched
manual files remain possible.

**63 native rows** have no confident complete match in the bounded verified lookup,
with the shared YouTube login challenge also recorded. The run hit the challenge on
`MjXvzV3D-bM`, stopped further YouTube probes for that pass, retained 15-minute
provider backoff and continued SoundCloud. This is not 63 individual failed YouTube
downloads. A legitimate authorized session that passes normal access checks would
be needed for further YouTube viability testing; no cookies or challenge bypass
were attempted. Native YouTube audio, format selection and successful upload
therefore remain unobserved on this server in this task.

Specific retained match evidence includes **Tuning**: candidate `2112111855` is
duration compatible, but not all selected collaborator credits are corroborated;
and **Babre Zakhmi**: candidate `2340158609` is only **30 seconds** versus 195.082 s
selected, rejected despite matching artist/title. KOBRA11's video candidate cannot
establish the selected recording/mix while its full probe is access-blocked;
compatible catalog duration alone is insufficient. No
preview, ambiguous mix, intermediary file or link-only post was published.
Per-recording reasons, lookup evidence, retry timestamps and pending statuses are
in the current CSV; catalog limits are not a claim of global absence.

## Implementation and verification

The focused change adds bounded catalog expansion/cached verified-channel search,
full collaborator checks, and provider failure isolation. It preserves exact
native uploader/channel/version/duration checks and refuses duration-compatible
music-video ambiguity. It reuses the existing yt-dlp/media/tagging/gateway pipeline;
no new dependency or Spotify/intermediary downloader was integrated.

Eight new focused regressions passed. The exact pushed application passed
**208 full application tests + eight backup tests**, Django checks, migrations and
drift checks on the isolated server stack. Tests cover collaborator/token-boundary
matches, incorrect recordings, catalog bounds/cache, shared authentication failure
isolation and music-video review, alongside existing identity/reconciliation,
quality/provenance, retry/restart and publication-capability tests. Passing these
tests does not imply YouTube's real access blocker is resolved.

Protected predeploy backup `rapfadrop-20261005T100713Z-0af0486e.tar.age` is
1,434,136 bytes, restored all **43 tables**, and uploaded as backup-channel messages
**82/83** before deployment. Backup locking serialized deployment and this pass.
Original roster, metadata/order, all 166 slots, 83 selection records, 131 source
identities/flags/baselines, 84 baseline runs, 4,125 existing items, two reviews and
caption templates compared unchanged against the protected before snapshot.
There are now 4,126 items: one new acquired SoundCloud recording. There are zero
downstream jobs. Polling timestamps continue to change normally.

Final production health is OK; **83 active verified Spotify sources**, discovery
mode `spotifyscraper`, discovery-only worker and beat remain running. Bridge OFF,
Telegram mode `disabled`, live publication OFF and publication worker OFF.
The collection-only gateway separately verified bot `8697681226` / `RapFaDropBot`,
exact channel `-1004311149640` / `RapFaDrop`, administrator and posting permission
before its authorized collection send. No general media worker is installed.

Collection **paused**; the one-shot acquisition service finished successfully and
is inactive, as are previous continuation/caption services. Daily protected backup
timer remains enabled. Removed **99 confirmed disposable media/artwork files**,
the isolated database/Redis/runner and the probe/exact-test directories. Three
alias rows were skipped by the cleanup command because they have no independent
readback; their shared canonical files were eligible under the original confirmed
records. Production music and backup messages were not deleted. Safe audit details
remain; private snapshots/configuration stay protected outside Git.

## Safe operating commands

Run on the server, preserving protected configuration and without enabling future
publication. Resume is not a new selection or baseline. The existing durable due
times/source caches/backoff remain in effect; never reset them or blindly retry an
uncertain send. Reconcile any uncertain send against observed channel delivery first.

```sh
C=/var/lib/rapfadrop-operations/popular-collection.compose.yaml
docker compose -p rapfadrop-popular -f "$C" run --rm -T collection popular_collection status
docker compose -p rapfadrop-popular -f "$C" run --rm -T collection popular_collection pause
```

For an explicitly authorized retry after resolving evidence/access, first make and
restore-check/upload a fresh recovery point using `ops/BACKUP_RESTORE.md`. Then:

```sh
(
  exec 9>/var/backups/rapfadrop/encrypted/.lock
  flock -n 9 || exit 1
  C=/var/lib/rapfadrop-operations/popular-collection.compose.yaml
  pause_collection() { docker compose -p rapfadrop-popular -f "$C" run --rm -T collection popular_collection pause; }
  trap pause_collection EXIT
  docker compose -p rapfadrop-popular -f "$C" run --rm -T collection popular_collection repair-links &&
  docker compose -p rapfadrop-popular -f "$C" run --rm -T collection popular_collection resume &&
  docker compose -p rapfadrop-popular -f "$C" run --rm -T collection popular_collection verify --credentials /var/lib/rapfadrop-operations/popular-collection.json &&
  docker compose -p rapfadrop-popular -f "$C" run --rm -T collection popular_collection run --limit 166 --credentials /var/lib/rapfadrop-operations/popular-collection.json
)
```

[Current 166-slot CSV](data/popular_track_selections.csv),
[current 155-native-row publication CSV](data/popular_track_publications.csv),
[safe evidence and receipt](data/popular_acquisition_evidence.json).
The initial report below remains historical. Stop before automatic future-release
activation; unresolved direct Spotify audio is a separate task.
