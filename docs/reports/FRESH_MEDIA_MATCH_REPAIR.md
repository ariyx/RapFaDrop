# Fresh-media matching repair

Observed 2026-10-06, Tehran. Safe readback evidence generated at
2026-10-06T10:34:27.832464Z; replay/cleanup at 10:44:06.613337Z.
Exact tested, pushed and deployed application:
`741f4b1ba82bd17f9582c5b1d6a9122a467cae17`.
[Safe evidence](data/fresh_media_match_repair_evidence.json).

## Correction and observed publication

The shared acquisition matcher cached both official catalogs and negative searches
for six hours. This could hide a newly uploaded official recording after an earlier
miss. Fresh dispatch now expires both caches at the existing source polling
interval (currently 180 seconds). The archive default remains six hours. Catalog
bounds, six-probe budget, provider backoff and durable dispatch retry schedules are
unchanged; this is not a guarantee of first-minute detection or immediate retry.

Mamazi's owner-approved curated SoundCloud profile `mamazioma` returned verified
native user `693001748`. Its distinctive OGHDE, SHU NUDE, Tomford 2 and Beautiful Cry
releases independently matched the monitored official Spotify catalog. The public
artist Telegram identity also corroborated the Mamazimanam identity. Its old Spotify/
SoundCloud shortlinks are expired: no successful direct crosslink resolution is
claimed. This evidence registered acquisition-only profile **64**, without changing
the curated discovery source or any baseline. Existing eligible dispatch **3886**
was made due once; the ordinary locked worker and publication scheduler handled it.

**OGHDE / Mamazi was published as [production message 76](https://t.me/RapFaDrop/76)**
at 2026-10-06T10:32:51.759028Z (14:02:51 Tehran). Native Spotify track
`4kt1vCDayf3LcmuI8ehcni`, release `40O11g61vfThnoSF8FYdsq`, matched SoundCloud
track `2413259331`, [official recording](https://soundcloud.com/mamazioma/oghde).
Uploader, title/version, complete credits and duration matched. The complete native
AAC/M4A is **144.056599 s**, **160,016 audio bps**, **44,100 Hz**, **two channels**;
2,907,088 source bytes, 2,935,212 prepared/delivered bytes. No audio conversion.
Full FFmpeg decoding, official artwork, actual eleven channel fields and tag
readback passed. Delivered SHA256 matched the retained prepared file. Caption
uses the existing linked bold Drop heading and Spotify/SoundCloud link row.

| Measured stage | Seconds |
| --- | ---: |
| Bounded official catalog fetch, 50 entries | 4.001 |
| Media pipeline native identity probe | 3.311 |
| Complete acquisition | 4.382 |
| Validation and preparation | 0.211 |
| Successful upload including target checks | 1.790 |
| Acquisition source registration/rearm to confirmed publication | 54.008 |

The historical discovery preceded this repair. No live release-to-detection timing
was measured. The matching probe preceding the pipeline probe has no separate
timing field; it is not folded into an invented acquisition or discovery time.
The successful dispatch used one bounded catalog and one matcher probe, then the
existing pipeline's re-probe and one download; downloader internal HTTP counts were
not instrumented. Preliminary checks were bounded to 5 Mamazi/15 Tataloo catalog
entries and individual probes. No bulk acquisition or Popular collection resume.

## Remaining exception and RapRelease

**Mano Khoda Shoma Hame / Amir Tataloo, Hassan Baba remains unposted**: expected
855.054 s, Spotify `5sYGAU7L6JgUrkfzy9J3Yx`. The existing verified official
SoundCloud user `52167935` now lists native recording `2413995774`, but its probe
returned **This video is DRM protected**. That path stopped, without bypass; its
stable URL is recorded as unavailable so automatic matching skips repeated probes.
The bounded owner-authenticated official YouTube candidate `cmj7_tDeekQ` ended
after **47.291 s** with **The page needs to be reloaded**. No complete matched file,
quality, collaborator proof or accepted version was established for that candidate.
The explicit reasons are retained in fresh-track evidence and the manual-review
candidate; its retry schedule is preserved, introduction withheld, no link-only post.
HAHAAA's separate baseline-day freshness ambiguity remains untouched.

The server fetched https://t.me/s/RapRelease, but received a channel landing page
without message history/audio. No claim about that channel's first-minute performance
or acquisition method is verified. No Telegram user session was provisioned to read
its unavailable history, and no aggregator recording was copied. A directly
accessible full recording or owner-supplied message link is a potential next clue;
it still needs complete recording/version and credit validation.

## Verification, preservation and cleanup

All work requiring network or Docker ran on the server. Separate PostgreSQL/Redis/
runner/media environment: **231 application tests + nine backup tests**, migrations,
system check and migration drift passed. New regression checks exercise delayed
official uploads, negative-search expiry, archive-cache preservation, provider
backoff and passing the actual source interval from fresh dispatch.

Protected predeployment backup `rapfadrop-20261006T103020Z-577694ff.tar.age`
restored **47 tables** and uploaded completely as dedicated backup messages **98/99**.
Exact-SHA deployment and final health both passed. No new runtime overlay, cookie,
bot, polling interval or caption/metadata policy was introduced.

**83 verified enabled Spotify sources, 84 baselines**, original source items,
curated source fields, Popular collection and historical publications passed the
existing hash preservation checks with no deletion or modification. Popular stays
paused with **155 native recordings / 166 slots**, 54 original posts. Fresh bridge,
media and scoped production publication remain ON. There are **71 publication
records**, including the new OGHDE post; zero uncertain sends. Completed OGHDE replay
added **zero attempts**, preserved message 76, and did not re-download or resend.

Three confirmed disposable media/artwork files totaling **5,865,720 bytes** were
removed after byte readback. The isolated test containers/database/Redis and temporary
exact-build source directory were removed. Production posts, volumes, protected
sessions, encrypted backups and audit records were retained. The remaining blocker
does not hold other artists' verified releases. Next work is acquisition of a
confidently matched, accessible full Tataloo recording; no completion is claimed for it.
