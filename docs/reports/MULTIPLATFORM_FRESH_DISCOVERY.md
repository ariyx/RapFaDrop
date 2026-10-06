# Independent fresh discovery and owner-authorized Bache Mardom catch-up

Evidence date: **2026-10-06**. This closes the implementation gap identified in
[the preceding diagnosis](BACHE_MARDOM_DISCOVERY_GAP.md). It does not establish
exhaustive upstream coverage or guaranteed first-minute publication.

## Implemented behavior

Spotify remains a complete-catalog metadata discovery source for all83 approved
artists. Independent SoundCloud upload windows and public YouTube channel RSS
now feed the same durable identity, media and publication pipeline. Verified
acquisition profiles are reused without resetting ArtistSource records or their
historical baselines. Artists with no registered profile use a bounded public
SoundCloud search, explicitly distinguished from a verified artist account.

`FreshDiscoveryFeed` stores an independent watermark, observed native IDs,
per-feed schedules/errors and explicit catch-up authority. First polling records
a bounded head (20 SoundCloud uploads or the YouTube RSS window), not a complete
historical catalog. Historical uploads cannot enter publication merely because
they later reappear in that window. Exact upload time is checked before media.
Only the explicitly owner-authorized native2413998492 crosses the initial watermark.

Real platform/native identities and URLs are preserved. The existing verified
Spotify ArtistSource remains the artist authority FK; a feed SourceItem's actual
platform is SoundCloud/YouTube and its metadata identifies the independent feed.
No fabricated Spotify release or Spotify URL is inserted. Full structured guest
credits survive Unicode delimiter normalization. Unknown named guests are disabled
artist records with namespaced identities, not fabricated Spotify IDs. A shared
producer account cannot claim another approved artist's upload simply because
its feed was polled first; collaborator uploads require explicit artist evidence.

Metadata ambiguities create visible review records. Approval reuses the existing
fresh handoff; repeated approval does not enqueue a second continuation. Missing
complete audio remains visible and unposted. Exact-version/duration/credit checks,
full decoding, artwork/tag readback, durable publication identities, album staging
and uncertain-send reconciliation continue to apply. Public intermediary or
independent uploads are permitted under the owner's existing policy; original
registered sources are preferred. Official provenance is not a publication prerequisite.

The credential-free discovery worker consumes only `fresh-discovery-v1`, separate
from metadata, media and publication queues. Scheduling ticks every5 seconds;
each successful feed becomes due45 seconds later. Initially deployed batches are
bounded to6 feeds with two concurrent provider reads. A pushed, unverified
correction allows configured concurrency capped at4 and batches bounded to12.
Actual cycle time also depends on provider
response time and queue load; these settings are not measured release latency.
Provider failures/backoff remain isolated. Production publication authority stays
confined to the existing exact-target fresh publisher; Popular stays paused.

## Observed complete recording and publication

Owner-reported **Hiphopologist — Bache Mardom** was caught up from
https://soundcloud.com/hiphopologistsoroush/bachemardom, native track2413998492,
verified native uploader380097545. Complete track credits are **Hiphopologist,
Erfan, Sorry Bahar**. This is an explicitly authorized real release, not a test
post or an automatically manufactured historical discovery.

Published **2026-10-06T18:19:45.081619Z** to exact chat **-1004311149640**, verified
username **RapFaDrop**, message **[79](https://t.me/RapFaDrop/79)**. Durable
Publication74/FreshDispatch3896/FreshTrack20/MediaCandidate240 retain evidence.
The caption uses the owner-approved linked **Drop** heading and corresponding
SoundCloud link, with no invented Spotify link or title/artist caption rows.

Actual source: **AAC/M4A160,000 bit/s,44.1kHz stereo,332.64907 seconds**;
provider expected332.627 seconds. Source audio6,711,161 bytes; the tagged file
received by Telegram is7,303,607 bytes including1080x1080 embedded JPEG artwork.
Complete FFmpeg decode and actual title/artists/album suffix/channel-field/artwork
readback passed. This is not native Spotify audio, MP3320 or proof of a lossless
original master. No transcoding quality upgrade is claimed.

Readback **2026-10-06T18:22:16.441131Z** fetched the Telegram file and compared it
to the **prepared tagged file**, not the raw acquisition bytes. Byte count and
SHA256 matched. Scoped publication replay added **zero attempts/messages** and
the dispatcher subsequently recorded completion. Zero uncertain sends were observed.
Production acquisition5.254s, provider re-probe3.390s, validation/preparation0.423s;
Telegram byte-readback0.371s. Upload wall time is uninstrumented. Discovery-to-send
includes queue wait and is a historical catch-up, not live-release detection latency.

The prior isolated server replay reached READY in29.558s: discovery3.807s,
identity/provider metadata6.857s, media18.774s (acquisition9.802s and preparation0.516s).
No Telegram message was created by that isolated replay. Its observed source audio
and complete tags/artwork/decode were consistent with the actual authorized send.

After successful readback, three production temporary media/artwork files were
removed at **2026-10-06T18:27:34.648016Z**. The actual release post and durable
database/audit records were retained. No music post or backup message was deleted.

## Verification and limits

Application **2e13f38bcac6fe437ccf2751d7b082fd2a8bbe1c** passed **271 server application
tests in227.855s** and **10 backup tests**. Migration/system/drift checks passed.
The complete recording/publication above ran on **3f2720daa91da4ef534248957769e5a074ef23ad**;
later changes add visible review/approval continuation and shared-profile routing.
Encrypted predeployment backup `rapfadrop-20261006T183930Z-f65b86ac.tar.age`
restored48 tables and uploaded as backup messages120/121. Final runtime activation
and the partial scheduled observations follow below.

## Partial activation and unresolved correction

At **2026-10-06T18:49:35.585913Z**, protected independent discovery was enabled in
beat and a credential-free dedicated worker: **100 feeds,92 registered verified
profile feeds for75 artists plus8 bounded independent search feeds**. No baseline
reset or archived-collection resume occurred. The84 BaselineRun rows and frozen
collection/selection/recording/alias/slot hashes matched before and after activation.
The separate preconfiguration archive `rapfadrop-20261006T184609Z-1c8aa734.tar.age`
restored48 tables and was uploaded before configuration/DB mutations.
Isolated review approval was checked twice and woke continuation exactly once;
the fixture transaction rolled back, with no media/network/Telegram calls.

At **2026-10-06T18:53:20.219078Z**,83 Spotify sources had three latest successful
polls,37 independent feeds had completed their first watermark, and **none yet
had three successful polls**. Maximum independent success age265.252s; initially
observed six-feed/two-reader batches took about30s. This did not meet a fast
roster-wide cadence. Enabled feed counts are not successful-source coverage.

Real Alipasha RSS showed root channelId without the`UC` prefix, while the author
URI and every entry carried the registered canonical ID. The initially deployed
adapter rejected it and other YouTube feeds. Generic correction
**b2627b0ea71687e70a55063955aed978e8bf5683** checks root compatibility, exact author
URI and entry identities; marks Shorts for review; and exposes capped concurrency.
The candidate is pushed **but not verified/deployed**: its273-test server run logged
at least4 errors before repeated SSH/banner/health timeouts blocked retrieval of
tracebacks/final outcome. Offline exact-parser fixture checks passed without
network/database/media, but do not replace server checks. Error causes remain
unknown; do not invent a cause or claim the suite passed.

The detached `rfd-feed-rss-after-checks` operation is gated on a successful exact
deployment/verified backup and isolated live RSS/review checks. It must not be
bypassed. Its proposed4-reader/12-feed,512MiB/1CPU adjustment is **not confirmed
active**. The corrected scheduled monitor also awaits that result. Retrieve the
protected `rss-final/full-tests.log` first when SSH returns. Disposable check
DB/Redis/media are retained for that diagnosis; current runtime health after the
connection loss is unverified. Historical real release message79 remains retained.

Consequently **global autonomous first-minute/full-quality delivery is not proven
complete**. Spotify discovery and the initial independent worker were enabled;
the YouTube defect, failed candidate checks, remaining initial watermarks and
three-round/faster-cadence measurements are outstanding.
An archive created after the100-feed/eight-overlay configuration and its restore/
upload receipt also remain to be verified; the retained prechange archives provide
rollback evidence, not a demonstrated restore of the final activated configuration.

Automated tests cover watermarking/no historical jobs, exact native/uploader
identity, malformed native IDs, old reappearance, missing artwork/unknown feature
holds, full-width guest credits, shared collaborator routing, cross-platform
canonical reuse and replay. Existing application tests cover album pre-staging,
ordering/prior-single reuse/retry, reconciliation and conditional captions.
This rollout does **not** claim a new live album Telegram test or every possible
provider/version/restart scenario. Standalone uploads declaring album membership
remain held until complete album classification/staging is available.

Public independent search is bounded and relevance-ranked, not an exhaustive or
guaranteed fresh catalog. Artist uploads outside monitored profiles/search windows,
upstream outages/login challenges and unavailable complete recordings can still
delay or block delivery. Failed profiles must be reported individually; enabling
a flag or having83 Spotify sources does not prove every new recording is covered.
Native320 quality is only reportable when observed; complete160AAC is not converted
to nominal320 as a claimed quality improvement.
