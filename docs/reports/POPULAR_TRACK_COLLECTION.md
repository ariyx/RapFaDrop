# Popular-track archive collection

The latest bounded acquisition results, current coverage and remaining blockers
are in [POPULAR_TRACK_ACQUISITION.md](POPULAR_TRACK_ACQUISITION.md). The
[166-slot CSV](data/popular_track_selections.csv) and
[155-native-row CSV](data/popular_track_publications.csv) now reflect the
2026-10-05T12:13:16Z server observation: 50 unique messages, 53 satisfied native
rows, 102 pending; the authorized bounded server continuation is still running.
Original frozen selection timestamps remain unchanged. Final captions are described
in [FINAL_AUDIO_CAPTIONS.md](FINAL_AUDIO_CAPTIONS.md). The narrative below records
the initial nine-post outcome and original caption/search defaults; the collection
is continuing only this bounded pass; future-release publication stays OFF.

The owner authorizes only the initial two-slot Popular collection in production
`-1004311149640` (`@RapFaDrop`). Automatic future discovery publication stays OFF.

`archive_collection` records a frozen roster, one complete artist-specific Top
Tracks observation per artist, at most two slots, and unique stable Spotify track
identities. Shared tracks satisfy multiple slots without replacement selections.
The installed SpotifyScraper 3.9.2 adapter supplies `queryArtistOverview`; raw
credit URIs are retained because its parsed Top Tracks credits omit native artist
IDs. Album detail corroborates selected recording identity and numbering. This is
returned web-player Top Tracks ordering in an anonymous server session, not a
measurement of live discovery or a promise of identical ordering in every market.

A dedicated explicit CLI uses no Celery task or beat entry. Its production gateway
requires the exact frozen recording/candidate/publication/payload and durable
pending attempt, an unpaused collection, all ordinary music switches OFF, pinned
bot ID, exact channel ID/username and posting permission. Ordinary publication
paths retain their production block. Channel leases, definite-failure backoff and
uncertain-send reconciliation remain the existing application's mechanisms.

Acquisition uses bounded five-result SoundCloud metadata searches only when a
credited artist has a verified official profile. Exact title/version, credited
profile and duration must match before downloading. An unavailable file creates
an explicit archive metadata fact and review-required candidate for the existing
authenticated manual-upload workflow, without discovery ingestion, a historical
baseline change or a processing queue task. Unverified uploader/search identities
are not promoted to official sources. Complete files undergo duration validation,
tag/artwork readback and an entire FFmpeg decode. Official file metadata retains
complete Spotify credits. Owner-requested ARCHIVE captions contain only the bold
ARCHIVE heading, conditional platform/related links and footer; no historical DROP or
fabricated album/test-channel URL. Telegram success stores media file IDs as well
as message IDs; bounded getFile readback compares actual uploaded bytes. Confirmed
readback allows disposable media cleanup, never production-message deletion.

Server commands use the protected collection Compose file, not a general media
worker. Replace NAME only to deliberately create a separate collection; reruns of
the same name preserve observed selections, including explicit unresolved slots.

```sh
C=/var/lib/rapfadrop-operations/popular-collection.compose.yaml
docker compose -p rapfadrop-popular -f "$C" run --rm collection popular_collection status
docker compose -p rapfadrop-popular -f "$C" run --rm collection popular_collection pause
docker compose -p rapfadrop-popular -f "$C" run --rm collection popular_collection resume
flock -n /var/backups/rapfadrop/encrypted/.lock docker compose -p rapfadrop-popular -f "$C" run --rm collection popular_collection run --credentials /var/lib/rapfadrop-operations/popular-collection.json
docker compose -p rapfadrop-popular -f "$C" run --rm collection popular_collection export --output /collection-report
```

Freeze only after create/restore-check/upload of a recovery point and exact tested
SHA deployment. `freeze --sha SHA` starts paused. `resume` enables this explicit
collection only; no background retry service exists. Each invocation is bounded
to 166 unfinished recordings; definite acquisition errors back off 5 minutes to
6 hours. Failed/ambiguous audio remains visible; uncertain Telegram delivery
requires existing operator reconciliation. `pause` can stop further sends while
an active acquisition completes. Database advisory locking excludes concurrent
CLI dispatchers; channel serialization persists before every external mutation.

Final execution evidence and the complete 83-artist coverage table follow below.


## Owner caption and metadata correction (2026-10-04)

The owner replaced the earlier three-field policy with all eleven channel fields:
subtitle/comments/publisher/encoded_by/copyright/composers/conductors/initial_key
contain @RapFaDrop; album and album artist append ` | @RapFaDrop`; author_url is
https://t.me/RapFaDrop. MP3 uses ID3 frames; M4A uses native atoms plus UTF-8 iTunes
freeform SUBTITLE/PUBLISHER/CONDUCTOR/INITIALKEY/AUTHORURL atoms. Player display of freeform
atoms varies; actual file readback is required. Main title and track artists stay
official. Album introduction prior-single heading is now English:
`Previously released from this album:`.

Retagging creates a separate immutable prepared candidate from retained originals,
with complete decode and equal raw recording SHA, then edits the same stored
Telegram message through a durable edit_media attempt. It sends no correction or
replacement audio post. Restarts reuse the persisted candidate; uncertain edits
require reconciliation. A separate caption edit removes archive title/artist rows.

A real collection run exposed a stale-instance save clearing the reserved
Recording-to-Publication FK after successful sends. Publication/Attempt message IDs
survived. The fix reloads after reservation; repair-links only attaches exact
confirmed candidate/track/channel/archive bindings while paused and never sends.
Four existing confirmed messages (4-7) were repaired, caption-refreshed and
retagged in place before further collection sends. Official SoundCloud display
suffix matching now accepts only complete frozen Spotify credited names, preserving
version/duration/official-profile requirements; unknown guests/remixes stay blocked.

Selection SHA remains frozen at eb074f6e808836554ea474904473fc920bab039a, with 83
artists, 166 slots and 155 unique recordings. Exports distinguish that observation
SHA from the SHA performing the later preparation/publication. Final exact-SHA checks and execution evidence follow below.


The version-two channel policy writes the named M4A SUBTITLE freeform atom rather
than the podcast-description `desc` atom. Only an exact legacy channel description
is removed; genuine source descriptions remain intact. Policy versioning makes
same-message updates idempotent even when the eleven logical field names did not
change. The collection's prepared report records the policy version.

A later full-suite repeat exposed a test-fixture dependency after disposable Redis
had been removed: direct Celery broker assignment did not pin lazy Django broker
settings. The safety regression now also sets its subprocess REDIS_URL to memory://.
The two scheduler tests passed in 1.244 seconds without Redis, and the exact final
application subsequently passed the full 183 tests plus eight backup tests.

## Final server execution evidence
Generated **2026-10-04T19:59:02.703808+00:00**. Tested, pushed and deployed application: `c08738439737f928d696bed75923bcdaacca4181`. Frozen selection application: `eb074f6e808836554ea474904473fc920bab039a`; frozen at 2026-10-04 18:10:54.595358+00:00. This is historical Popular-track collection, not live-release detection latency. Documentation-only delivery does not redeploy the application.
**83 artists / 166 selected slots / 155 unique recordings; 9 unique production posts, 146 pending.** Ten artist slots are satisfied: two artists have both slots, six have one and 75 have none. No artist lacks a completed Popular selection; successful selection does not imply available audio. Shared collaborations have one canonical publication row and satisfy multiple artists without replacement tracks. All 155 recordings were attempted.
Exact production target and permissions were checked before mutation: `-1004311149640`, `@RapFaDrop`, bot `8697681226` / `@RapFaDropBot`, administrator with posting permission. These were owner-authorized archive posts, not integration-test posts.
Final message IDs: **4, 5, 6, 7, 9, 10, 11, 12, 13**. Nine send_audio, four edit_caption and ten edit_media attempts succeeded; no uncertain or failed publication attempt remains. Caption/tag changes edited the same messages and emitted no correction post.
Pending blockers (individual details are retained below and in both CSVs):
- 127: No verified official profile.
- 15: No confident full recording match.
- 1: Existing source identity belongs to another Spotify ID.
- 3: DRM-protected provider response.

The alternate Be Mula Spotify identity `7MayY1yz6a5FDx757hMn0x` matched SoundCloud recording `1390888048`, already bound to Spotify `22cRr8Qxt2Dy0lxAKcBJKl` and message 10. Its source identity was preserved; a second copy was not posted. Manual canonical/edition reconciliation is required. Missing profiles or bounded-search failures do not establish that no full recording exists elsewhere. DRM is not bypassed. No preview or link-only substitute was published.
### Published files and separately measured timings
All nine files came from verified credited official SoundCloud profiles via yt-dlp. Eight observed AAC streams were approximately 160 kb/s; Be Mula was approximately 96 kb/s. No nominal 320 kb/s transcode was fabricated. Full-duration matching and complete FFmpeg decoding passed. Official titles/credits, all eleven configured channel fields, album/album-artist suffixes and embedded artwork passed actual file readback. Telegram getFile readback matched uploaded bytes. M4A freeform tag display depends on the player; verified atom values are in the safe audit JSON.
`provider` in the publication CSV describes candidate allocation (manual for an immutable retagged version); `acquisition_provider` describes the original downloader from provenance. Retagging did not acquire new recordings.
Discovery used **490 instrumented metadata HTTP requests**, **135.849 s summed per-artist discovery time**, plus staggering. Each SoundCloud search was bounded to five entries and 45 seconds; downloads were limited to 50 MB with bounded retries. Nine successful acquisitions and ten policy-retag preparations were observed. Underlying yt-dlp HTTP subrequests were not instrumented, so no exact overall HTTP-request total is claimed.
Times below are seconds. Download and provider probe are acquisition subphases; media total includes original acquisition, validation/preparation and matching work. Preparation is the latest measured preparation (a policy retag for earlier posts). Upload is the initial audio send. Processing total is original media total plus initial upload; it excludes discovery, staggering, deployment interruptions, later edits and readback. A full collection wall-clock or live-release detection latency is not inferred from these sums. Retag-upload timing was not separately instrumented.
| Recording | Message | Codec / kb/s | Probe | Download | Latest preparation | Original media total | Initial upload | Original processing total | Source |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Bargard | 9 | aac / 160.0 | 2.783 | 3.903 | 0.295 | 8.221 | 62.226 | 70.447 | https://soundcloud.com/sijalofficial/bargard |
| Be Mula | 10 | aac / 96.0 | 2.651 | 3.731 | 0.144 | 12.059 | 2.587 | 14.645999999999999 | https://soundcloud.com/masinrap/bemola |
| Dashi | 11 | aac / 160.0 | 2.678 | 4.018 | 0.132 | 12.333 | 2.44 | 14.773 | https://soundcloud.com/shahinnajafimusic/dashi-shahin-najafi-erfan |
| LAMS | 4 | aac / 160.015 | 2.736 | 3.899 | 0.144 | 12.915 | 62.398 | 75.313 | https://soundcloud.com/bahramnouraei/lams |
| 209 | 5 | aac / 160.0 | 2.685 | 3.941 | 0.261 | 12.666 | 2.244 | 14.91 | https://soundcloud.com/shahinnajafimusic/209a |
| Masire Dard | 6 | aac / 160.0 | 2.679 | 4.595 | 0.353 | 12.765 | 2.811 | 15.576 | https://soundcloud.com/ghavidelemad/emad-ghavidel-masire-dard |
| Battle for Homs | 12 | aac / 160.0 | 2.74 | 11.41 | 0.158 | 19.589 | 129.095 | 148.684 | https://soundcloud.com/ghavidelemad/battle-for-homs |
| Azizam | 7 | aac / 160.0 | 2.815 | 3.906 | 0.142 | 12.069 | 2.262 | 14.331000000000001 | https://soundcloud.com/samiloww/azizam |
| Beri | 13 | aac / 160.0 | 2.62 | 4.016 | 0.167 | 13.213 | 2.18 | 15.392999999999999 | https://soundcloud.com/gdaal/beri |

### Preservation, retries and cleanup
Replay after process/deployment restarts kept the frozen 83/166/155 identities and original selection SHA. All nine stored message IDs were unchanged, with exactly one successful audio send per published recording and **zero duplicate posts**. The collection is **paused**; pending retry timestamps are durable but no automatic collection retry service exists. Resume/run requires an explicit operator invocation. Ordinary future publication, bridge and media worker remain OFF/absent. Metadata polling and the daily protected backup timer remain active.
All original 83 artist, 130 source, 3934 historical item, 84 baseline and one review rows passed preservation comparison; source polling timestamps were allowed to advance. Final snapshot: 83 active verified Spotify sources, 4092 total source items, 84 baselines, one review and zero downstream processing jobs. The 158 added items are scoped archive metadata facts, not baseline resets. All original historical IDs, including the original five-source/177-ID history, remain.
Confirmed readback preceded cleanup: **28 obsolete version files + 27 current media/artwork files removed (55 total)**, no shared candidate file retained by this cleanup. Durable candidates, provenance, attempts, IDs and reviews remain. **Zero production music messages deleted**. Disposable test database, Redis and media stack were removed; one-off collection containers exit with --rm. No production volume was removed. Seven temporary source/build directories were also removed; protected configs, audit logs, backup artifacts and production images remain. Final server had 13 GiB free disk and about 1001 MiB available memory; five production containers were running and web/database health passed.
Protected pre-deployment backup `rapfadrop-20261004T192413Z-289fc0ac.tar.age` passed isolated restore/upload before exact c087 deployment. Final post-collection backup `rapfadrop-20261004T200417Z-f89e92d8.tar.age` (870808 bytes, SHA256 `de70d793ab3b61a9dd19b7eb01fdeca4b8b4c73c4b4ad8d5af875e0289a5951d`) passed isolated 41-table restore at 20:04:41 UTC and uploaded as backup-channel messages **72/73**. Pre-c087 deployment backup messages were **70/71**. The final recovery point contains the paused collection and durable publication IDs, after disposable media cleanup. Backup messages belong only to the isolated backup channel, not the music channel. Protected environment changes were limited to the owner-requested eleven-field channel tag policy.
Final exact-SHA server checks: **183 application tests and eight backup tests**, Django system check, migrations and migration drift passed. Full tests used disposable server-side database/Redis; no local Docker or media downloads were needed. Real media readback passed for nine production files before cleanup. The English prior-single album heading is covered by caption tests; this collection does not claim a new album end-to-end run.
### Complete artist coverage and remaining review reasons
Each artist has exactly two frozen selections below. A shared post may satisfy several artist slots. Rank is the returned artist-specific Popular position; this is not an editorial replacement ranking.
| Artist | Slot 1 (Popular rank) | Outcome / exact blocker | Slot 2 (Popular rank) | Outcome / exact blocker |
| --- | --- | --- | --- | --- |
| Hossein Tiem | Taghsire Mane (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | KOBRA11 (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Hesam Tiem | West SidE (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Tuning (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Amin Tijay | Chikar Kardi Baam (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Love Dardesarsaaz (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Mamazi | YND (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | MARIO (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Sajad Shahi | Khastam (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | BAD FAAZ (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Sinazza | Alan Kojayi (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Rotation (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Hoomaan | Goor (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Khatere (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Vinak | Mituni Mage (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Bi Marefat (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Dorcci | Ghatle Amd (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | ADDI (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Hiphopologist | Bad Zaat (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Boz (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Chvrsi | Chera Rafti (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Keshidi Par (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Poori | Miad Az Man Bar (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | HELA (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Arta | Khooneye Man (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Har Eshghi Mimirad (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Koorosh Wantons | Khooneye Man (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Befuckam (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Canis | Dele Man (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Noghte Joosh (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Sijal | Fogholade (1) | Pending: No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required. | Bargard (2) | Published: 9 |
| Behzad Leito | Highway (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Ta Betoonam (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Sepehr Khalse | Delam Az Donya Gerefte (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Khodafez (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Shayea | Boro Khoone (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Romania (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Fadaei | Soghoot (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Ma Yademoon Nemire (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Sina Sae | Deja vu (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Metropolitan (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Hichkas | Rooye Jenazat Miraghsam (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Yani Chi Nemishe (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Yas | Esalat (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Sefareshi (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Reza Pishro | Mirrors (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Rock A Chock (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Ho3ein | 33 (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Be Mula (2) | Published: 10 |
| Tohi | Ba Man Miraghsi (feat. Sami Beigi) (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | CD (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Erfan | Dashi (1) | Published: 11 | Sarnevesht (2) | Pending: No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required. |
| Amir Tataloo | Navazesh (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Man Bahat Ghahram (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Sohrab Mj | 12 Be Bad (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Gangesh Balas (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Mehrad Hidden | Mano Bespar (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Khodafez (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Bahram | LAMS (1) | Published: 4 | Sangsar (2) | Pending: No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required. |
| Shahin Najafi | Dashi (1) | Published: 11 | 209 (2) | Published: 5 |
| Saman Wilson | Bitab (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Yeki Dige (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Alireza Jj | Berim Baham (1) | Pending: No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required. | +3:30 Tehran Maserati (2) | Pending: No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required. |
| Quf | Basse Moftbari (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Shak (feat. Fadaei) (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Ali Sorena | Goriz Az Markaz ... (1) | Pending: No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required. | Raghs (Pichak) (2) | Pending: No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required. |
| Sadegh | Shaba (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Baraye (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Sogand | Dashte Parvaneha (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Marize Ham (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Gdaal | Sarnevesht (1) | Pending: No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required. | Mage Man Mordam (2) | Pending: No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required. |
| Amir Khalvat | Dige Chi Kame? (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Paranoia (FreeStyle) (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Emad Ghavidel | Masire Dard (1) | Published: 6 | Battle for Homs (2) | Published: 12 |
| poobon | KI (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Mohem Ni (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Armin Zareei | Hala Hey (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Begoo Kojaei (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Zakhmi | Heyf (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Migzare (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Sina Mafee | Kheili Vaghte (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Shol Tekoon (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Catchybeatz | Mituni Mage (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Bavelamko (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Hamid Sefat | Goolle (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Satori (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Ali Ardavan | Ghalbe Banafsh (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Fasele (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Bamdad | Dayere (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Movaghat (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Dariu$h | VICE CITY (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | TASLIAT (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Parsalip | Khaterate Bad (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Chivaz (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Putak | Okay (1) | Pending: No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required. | Helia (2) | Pending: No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required. |
| Daniyal | 2 Ghotbi (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Bipolar (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Sami Low | Extasy (1) | Pending: No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required. | Azizam (2) | Published: 7 |
| Safir | Culture Mord (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Abraa (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Eycin | Chizi Namonde (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Azmayeshgah S3-8 (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Dalu | Mano Mishnasi (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Donyaye Movazi (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Amir Ribar | Kheshab (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Labriz (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Shapur | Marg Bar Kolle Nezam (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Ghasem Kojayi? (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Masin | Jenab Sarvan (1) | Pending: No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required.; yt-dlp failed (1): ERROR: [soundcloud] 2172665610: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) ERROR: [soundcloud] 2187742107: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) ERROR: [soundcloud] 2220396818: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) ERROR: [soundcloud] 2212433684: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) ERROR: [soundcloud] 2234445062: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) | Be Mula (2) | Pending: Existing source identity/review cannot be overwritten; recording requires reconciliation; yt-dlp failed (1): ERROR: [soundcloud] 1390888048: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) ERROR: [soundcloud] 1231449625: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) ERROR: [soundcloud] 1245974719: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) ERROR: [soundcloud] 1233444121: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) ERROR: [soundcloud] 1231447297: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) |
| Young Sudden | Vel Besho (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Tequila (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Naaji | Vasiat 2 (1) | Pending: yt-dlp failed (1): ERROR: [soundcloud] 2232131834: This video is DRM protected ERROR: [soundcloud] 2227936676: This video is DRM protected | Tocka (2) | Pending: No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required. |
| Ali Geramy | Flick Shot! (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | SLEEP MODE (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| XWHISKY | Sigar Teras (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Zemestoone Ghabli (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Ashna | Nicotine (1) | Pending: yt-dlp failed (1): ERROR: [soundcloud] 2372028032: This video is DRM protected | Tanha Tari (2) | Pending: yt-dlp failed (1): ERROR: [soundcloud] 1803248058: This video is DRM protected ERROR: [soundcloud] 2370542405: This video is DRM protected ERROR: [soundcloud] 1753410135: This video is DRM protected |
| Arman Miladi | Har Eshghi Mimirad (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Highway (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Saaren | Har Eshghi Mimirad (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Befuckam (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Heliyom | Road 61 (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Chikar Kardi (2) | Pending: No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required. |
| The Don | Mano Vel Nakonia (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Man Tanham (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Isam | Ta Betoonam (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Mesle Ghablan (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Arown | Highway (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | LEAVE (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Octave | Baby Bebin Baroone (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Doori o Doosti (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Maslak | Dopamine (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Mano Dari (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Shayan Yo | Taghsire Mane (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Babre Zakhmi (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Parsa | Burn (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Dead Inside (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Nazli Mcfian | yastıgımda saclar (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | WOA (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Raha | Extasy (1) | Pending: No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required. | Del (2) | Pending: No confidently matched complete recording in five bounded SoundCloud results. Admin source correction/manual upload required. |
| Matin Fattahi | YE ROO (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | SLEEP MODE (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| 021kid | CATALAN (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Beri (2) | Published: 13 |
| Mehyad | Nabasham (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Mese Sam (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Alipasha | Door Azin Shahr (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Kojayi (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Tlkhoon | Ajibe! (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | Havasam (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |
| Pouriya Adroit | WARCRAFT (1) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. | ADLIB (2) | Pending: No verified SoundCloud profile for credited artists. Verify an official full recording or use admin manual upload; Spotify is metadata only. |

Artifacts: [166 artist-slot rows](data/popular_track_selections.csv), [155 unique recording/publication rows](data/popular_track_publications.csv), [safe collection/readback/cleanup audit](data/popular_track_collection_audit.json).
Stop here. Album acquisition and automatic future-release publication were not enabled.
