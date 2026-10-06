# Fresh-release speed and acquisition coverage correction

Owner clarification: RapRelease is a benchmark for the application's speed and
coverage, **not a request to copy its audio**. The forward-download investigation
stopped; no audio was downloaded, posted or substituted. Its disposable reader,
file locator and dependencies were removed. No owner API credentials or session
were requested or created. The owner also clarified that perfectly certain official
origin is not required; provenance and uncertainty must still be stated honestly,
with complete playable recordings and correct work/version/deduplication handling.

Observed final state **2026-10-06T11:17:01.103270Z (14:47 Tehran)**.
Exact tested/pushed/deployed application
**`5823944e08a840739e9f10e5b75236d4c082231a`**.
[Every artist's coverage and remaining blocker](data/fresh_audio_source_coverage.csv),
[safe evidence](data/fresh_speed_repair_evidence.json).

## Implemented and verified

The prior missing-file retry incorrectly used exponential processing-failure
backoff, reaching **15,360 seconds (4 h 16 min)**. Thus a subsequently available
recording could remain unseen even after the earlier six-hour catalog-cache fix.
Normal missing-file retry now caps at the source cadence, currently **180 seconds**.
Successful staging still uses 60 seconds. Candidate-specific retry holds, provider
backoff and unexpected-error exponential backoff remain intact; faster scheduling
does not override them. Existing Tataloo dispatch 3892's 12:36:59Z hold was advanced
once to 11:15:12Z after the protected backup. Its observed next retry is 11:19:02Z,
after a real bounded retry, rather than another multi-hour delay. It remains unposted.

The authoritative acquisition audit found **47 of 83 artists** had registered audio
profiles before this repair, despite all 83 having verified Spotify discovery.
Eight previously curated SoundCloud seeds were checked with native public profile
responses and one ten-entry catalog each. Multiple own-upload titles corroborated
the existing independent Spotify catalog; reposts were excluded from this evidence.
No audio was acquired for these checks, no discovery source enabled and no baseline
created/reset. Acquisition-only profiles **65–72** were registered:

| Artist | Native SoundCloud user | Own catalog corroborations |
| --- | --- | ---: |
| Amir Ribar | 390602913 | 8 |
| Daniyal | 1012712815 | 8 |
| Hoomaan | 1077202399 | 6 |
| Koorosh Wantons | 965886115 | 2, plus verified native badge |
| Poori | 562526439 | 10 |
| Sina Sae | 998861116 | 7 |
| Sinazza | 353838752 | 5 |
| Sohrab Mj | 1191957625 | 5 |

Badges are additional identity evidence, not an audio-quality guarantee. These
profiles do not prove availability of every full recording. Ordinary acquisition
still checks the actual native uploader, recording title/version, complete credits,
duration, file facts, tags/artwork and full decoding before its durable publication.

**232 application tests + nine backup tests**, migrations, system check and drift
passed in the isolated server environment. A regression verifies a ninth failed
match cannot cause hours of waiting while the independent 15-minute provider hold
remains intact. Exact deployment and final application/database health passed.
Predeployment encrypted backup `rapfadrop-20261006T110800Z-f3bdbeaf.tar.age`
restored **47 tables**, uploaded completely as dedicated backup messages **100/101**.
Disposable test DB/Redis/runner and exact-build source were removed.

## Remaining coverage and latency limitations

Current **55 artists / 72 acquisition profiles**; **28 artists remain uncovered**.
For every following artist, the exact current registry blocker is **no curated or
corroborated acquisition profile registered**. This does not claim there is no public
recording or profile anywhere; a broader verified provider search remains unfinished.
The CSV explicitly records every artist and this distinction:

Ali Ardavan, Ali Geramy, Amir Khalvat, Arman Miladi, Armin Zareei, Arown, Bamdad,
Catchybeatz, Dalu, Dariu$h, Fadaei, Hamid Sefat, Heliyom, Ho3ein, Isam, Maslak,
Mehyad, Parsa, Parsalip, Quf, Safir, Saman Wilson, Shapur, Sina Mafee, The Don,
Tlkhoon, XWHISKY, Zakhmi.

Discovery remains **83 verified enabled Spotify sources**, existing **180-second
source intervals**, 60-second dispatch and 30-second publication recovery ticks.
All 83 sources have three latest successful polling outcomes. Source polling,
provider catalog freshness, audio availability, download/preparation and queue
ticks each affect total time. **First-minute publication for all artists is not
implemented or measured**, and registration of a profile is not completion of a
full audio path. RapRelease's full acquisition method and actual release-to-post
latency were not established by its restricted public preview/forward metadata.

Tataloo's complete accessible acquisition is still blocked by its SoundCloud DRM
response and the authenticated YouTube page-reload failure; source registration
and retry scheduling do not resolve that access problem. HAHAAA retains its separate
baseline-day freshness review. No incomplete file or link-only post was sent.

## Preservation and next work

**83 approved artists / 83 active verified discovery sources / 84 baselines / 4,152
source items** preserved. Original curated fields, records, frozen selections and
publications passed hash preservation with no deletion/modification. Popular remains
paused, **155 native recordings / 166 slots**; **71 confirmed publication records**,
zero uncertain sends. Fresh bridge, media and scoped production publication remain
ON. This repair added no music posts and changed no caption, file-tagging, source
poll interval or runtime overlay policy. Production posts, volumes, protected owner
YouTube session and backups remain intact.

Next required work is verified acquisition coverage for the remaining 28 artists,
resolution of provider-access failures, and measured/staggered discovery and event
dispatch improvements before any claim of roster-wide first-minute performance.
