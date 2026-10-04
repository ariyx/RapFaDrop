# Discovery source activation

Server-only, 2026-10-04. Tested, normally pushed and deployed application SHA **`5d89fcedcc1c01d5f9f00b533242e6d9045fbb0f`**, starting from `2a439a67ce5251c2004a4bce93c2ad770be11f8c`. Exact-SHA isolated server checks passed **151 full tests**, **27 focused tests**, Django checks and migration drift. Documentation-only follow-up commits do not change the deployed application.

## Isolation and backup

Before state changes, beat/discovery/media workers were stopped and the protected `/var/backups/rapfadrop/pre_source_activation_20261004.dump` (217535 bytes, mode 0600) passed checksum/list verification and restoration. All 37 table digests matched (`44a533a1495a4c1bb47d282aa0a63087d0c0be9b281b21db2d3b302c679c0a47`); the restore database was removed. Preflight found about 17 GiB disk free and 945 MiB available RAM of 3819 MiB.

A fourth protected overlay, `/var/lib/rapfadrop-operations/discovery-only.compose.yaml`, overrides bridge OFF on every app service and selects the existing metadata-only `spotify_pilot:app` beat schedule. Production commands now require all four overlays in order: repository `compose.internal.yaml`, `spotify-pilot.compose.yaml`, `spotify-bridge.compose.yaml`, `discovery-only.compose.yaml`. The original protected overlays and credentials were preserved. Media worker was stopped and removed. Metadata worker consumes only `spotify-pilot`, solo concurrency 1; one beat schedules polling every 60 seconds, while sources use 180 seconds. Telegram mode disabled, live switch false, publication worker false. Bridge remains OFF deliberately; do not remove the fourth overlay during this handoff.

## Baselines, activation and preservation

Production retains **83 artists / 130 sources**. Existing active sources: **5**; newly activated: **53**, currently active overall **58** (58 Spotify / 0 SoundCloud). Baseline qualification observed 2259 catalog memberships; memberships overlap across collaborators and differ from unique stored item counts. The 2259 observed memberships created **2107** unique historical items; **152** memberships already existed globally or overlapped other catalogs, with zero duplicate stored native IDs. Unique source items now **2335**; successful baseline runs now **59**. Every newly enabled source has a successful baseline and all its observed IDs are globally present. Recalling baseline returns its same completed run; restarting the activation controller skips completed source results. Database unique constraints prevent duplicate platform/native IDs and artist/platform sources.

All **228 prior item records**, including the five sources' **177 Spotify IDs**, and all **6 prior baseline records** passed full field-by-field preservation checks. Artist names/aliases and every source's curated artist/platform/native ID/URL/verification are unchanged. Existing five enabled flags, 180-second intervals and completed-baseline timestamps are preserved. Their normal poll timestamps advance. No existing source was rebaselined. Unverified identities were not promoted just because a catalog responded.

The guarded `baseline_source --while-disabled` path requires verified identity, disabled source, bridge OFF and all publication switches OFF. SoundCloud completeness rejects missing entries, repeated IDs and responses reaching the 100-entry cap; shared/repost feeds are held without artist filtering. Failed qualification leaves the source disabled. Atomic baseline writes and interruption/resumption passed dedicated tests.

## Scheduled observations

**53/53** newly activated sources have at least three scheduled outcomes. Successful new-source polls: **216**; failed outcomes: **1**. Observed completion spacing ranged **169.89–258.11 seconds** (completion timestamps include provider duration; scheduled due time uses the batch start). Measured new-source polling provider requests: **478**; summed provider duration **122.692 seconds**. Failed-provider backoff is stored independently, and two consecutive failures pause only the affected newly activated source. Arown source 185 had one 5.051-second NetworkError (one attempted HTTP request), backed off 180 seconds independently, and recovered; all newly active sources ended with zero consecutive failures. Amir Ribar source 168 also had one transient qualification failure and succeeded on its single retry before activation. No live-release latency is claimed.

Qualification, per-source ordered scheduled outcomes, request/page counts, elapsed timings, retry delays, baseline native-ID sets/digests and all 130 final source states are in [safe evidence](data/source_activation_evidence.json). SoundCloud qualification HTTP request counts are not instrumented; they are not included in measured Spotify totals. Catalog/identity probes and bounded media-probe timings are separately preserved in [album evidence](data/latest_album_evidence.json). Release-detail timing/request metrics were not exposed by the starting application version and are unavailable; they are not reported as zero. These metadata timings are not acquisition or publication timings; no such stages occurred.

## Final source inventory

| Source | Artist | Platform | Verification | Enabled | Result / held reason |
|---|---|---|---|---|---|
| 1 | Hossein Tiem | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 2 | Hossein Tiem | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 3 | Hesam Tiem | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 4 | Hesam Tiem | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 5 | Amin Tijay | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 6 | Amin Tijay | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 7 | Mamazi | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 8 | Mamazi | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 9 | Sajad Shahi | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 10 | Sajad Shahi | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 11 | Sinazza | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 12 | Sinazza | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 13 | Hoomaan | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 14 | Hoomaan | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 15 | Vinak | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 16 | Vinak | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 17 | Dorcci | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 18 | Dorcci | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 19 | Hiphopologist | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 20 | Hiphopologist | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 21 | Chvrsi | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 22 | Chvrsi | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 23 | Poori | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 24 | Poori | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 25 | Arta | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 26 | Arta | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 27 | Koorosh Wantons | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 28 | Koorosh Wantons | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 29 | Canis | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 30 | Canis | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 31 | Sijal | spotify | verified | ON | Existing active; baseline preserved |
| 32 | Sijal | soundcloud | verified | OFF | ERROR: [soundcloud:user] sijalofficial: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) |
| 33 | Behzad Leito | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 34 | Behzad Leito | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 35 | Sepehr Khalse | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 36 | Sepehr Khalse | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 37 | Shayea | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 38 | Shayea | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 39 | Fadaei | spotify | verified | ON | Existing active; baseline preserved |
| 40 | Sina Sae | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 41 | Sina Sae | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 42 | Hichkas | spotify | verified | ON | Existing active; baseline preserved |
| 43 | Hichkas | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 44 | Yas | spotify | verified | ON | Existing active; baseline preserved |
| 45 | Yas | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 46 | Reza Pishro | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 47 | Reza Pishro | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 48 | Ho3ein | spotify | verified | ON | Existing active; baseline preserved |
| 49 | Tohi | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 50 | Tohi | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 51 | Erfan | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 52 | Erfan | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 53 | Amir Tataloo | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 54 | Sohrab Mj | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 55 | Sohrab Mj | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 56 | Mehrad Hidden | spotify | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 57 | Mehrad Hidden | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 131 | Bahram | spotify | verified | ON | Activated after complete baseline |
| 132 | Bahram | soundcloud | verified | OFF | ERROR: [soundcloud:user] bahramnouraei: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) |
| 133 | Shahin Najafi | spotify | verified | ON | Activated after complete baseline |
| 134 | Shahin Najafi | soundcloud | verified | OFF | ERROR: [soundcloud:user] shahinnajafimusic: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) |
| 135 | Saman Wilson | spotify | verified | ON | Activated after complete baseline |
| 136 | Alireza Jj | spotify | verified | ON | Activated after complete baseline |
| 137 | Quf | spotify | verified | ON | Activated after complete baseline |
| 138 | Ali Sorena | spotify | verified | ON | Activated after complete baseline |
| 139 | Ali Sorena | soundcloud | verified | OFF | ERROR: [soundcloud:user] alisorena: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) |
| 140 | Sadegh | spotify | verified | ON | Activated after complete baseline |
| 141 | Sadegh | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 142 | Sogand | spotify | verified | ON | Activated after complete baseline |
| 143 | Gdaal | spotify | verified | ON | Activated after complete baseline |
| 144 | Gdaal | soundcloud | verified | OFF | ERROR: [soundcloud:user] gdaal: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) |
| 145 | Amir Khalvat | spotify | verified | ON | Activated after complete baseline |
| 146 | Emad Ghavidel | soundcloud | verified | OFF | ERROR: [soundcloud:user] ghavidelemad: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) |
| 147 | Emad Ghavidel | spotify | verified | ON | Activated after complete baseline |
| 148 | poobon | spotify | verified | ON | Activated after complete baseline |
| 149 | Armin Zareei | spotify | verified | ON | Activated after complete baseline |
| 150 | Zakhmi | spotify | verified | ON | Activated after complete baseline |
| 151 | Sina Mafee | spotify | verified | ON | Activated after complete baseline |
| 152 | Catchybeatz | spotify | verified | ON | Activated after complete baseline |
| 153 | Hamid Sefat | spotify | verified | ON | Activated after complete baseline |
| 154 | Ali Ardavan | spotify | verified | ON | Activated after complete baseline |
| 155 | Bamdad | spotify | verified | ON | Activated after complete baseline |
| 156 | Dariu$h | spotify | verified | ON | Activated after complete baseline |
| 157 | Parsalip | spotify | verified | ON | Activated after complete baseline |
| 158 | Putak | spotify | verified | ON | Activated after complete baseline |
| 159 | Putak | soundcloud | verified | OFF | ERROR: [soundcloud:user] pooriaputak: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) |
| 160 | Daniyal | spotify | verified | ON | Activated after complete baseline |
| 161 | Daniyal | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 162 | Sami Low | spotify | verified | ON | Activated after complete baseline |
| 163 | Sami Low | soundcloud | verified | OFF | ERROR: [soundcloud:user] samiloww: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) |
| 164 | Safir | spotify | verified | ON | Activated after complete baseline |
| 165 | Eycin | spotify | verified | ON | Activated after complete baseline |
| 166 | Eycin | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 167 | Dalu | spotify | verified | ON | Activated after complete baseline |
| 168 | Amir Ribar | spotify | verified | ON | Activated after complete baseline |
| 169 | Amir Ribar | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 170 | Shapur | spotify | verified | ON | Activated after complete baseline |
| 171 | Masin | spotify | verified | ON | Activated after complete baseline |
| 172 | Masin | soundcloud | verified | OFF | ERROR: [soundcloud:user] masinrap: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) |
| 173 | Young Sudden | spotify | verified | ON | Activated after complete baseline |
| 174 | Naaji | spotify | verified | ON | Activated after complete baseline |
| 175 | Naaji | soundcloud | verified | OFF | ERROR: [soundcloud:user] naajiofficial: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) |
| 176 | Ali Geramy | spotify | verified | ON | Activated after complete baseline |
| 177 | XWHISKY | spotify | verified | ON | Activated after complete baseline |
| 178 | Ashna | spotify | verified | ON | Activated after complete baseline |
| 179 | Ashna | soundcloud | verified | OFF | ERROR: [soundcloud:user] ashnarap: Unable to download JSON metadata: HTTP Error 403: Forbidden (caused by <HTTPError 403: Forbidden>) |
| 180 | Arman Miladi | spotify | verified | ON | Activated after complete baseline |
| 181 | Saaren | spotify | verified | ON | Activated after complete baseline |
| 182 | Heliyom | spotify | verified | ON | Activated after complete baseline |
| 183 | The Don | spotify | verified | ON | Activated after complete baseline |
| 184 | Isam | spotify | verified | ON | Activated after complete baseline |
| 185 | Arown | spotify | verified | ON | Activated after complete baseline |
| 186 | Octave | spotify | verified | ON | Activated after complete baseline |
| 187 | Octave | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 188 | Maslak | spotify | verified | ON | Activated after complete baseline |
| 189 | Shayan Yo | spotify | verified | ON | Activated after complete baseline |
| 190 | Shayan Yo | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 191 | Parsa | spotify | verified | ON | Activated after complete baseline |
| 192 | Nazli Mcfian | spotify | verified | ON | Activated after complete baseline |
| 193 | Raha | spotify | verified | ON | Activated after complete baseline |
| 194 | Matin Fattahi | spotify | verified | ON | Activated after complete baseline |
| 195 | Matin Fattahi | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 196 | 021kid | spotify | verified | ON | Activated after complete baseline |
| 197 | 021kid | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 198 | Mehyad | spotify | verified | ON | Activated after complete baseline |
| 199 | Alipasha | spotify | verified | ON | Activated after complete baseline |
| 200 | Alipasha | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |
| 201 | Tlkhoon | spotify | verified | ON | Activated after complete baseline |
| 202 | Pouriya Adroit | spotify | verified | ON | Activated after complete baseline |
| 203 | Pouriya Adroit | soundcloud | unverified | OFF | Unverified identity / unresolved profile; not eligible |

## Downstream safety and next task

Final downstream readback: `{"MediaAttempt": 0, "MediaCandidate": 0, "ProcessingQueueItem": 0, "Publication": 0, "PublicationAttempt": 0, "ReviewItem": 0}`; media files **0**. Processing/media/publication tables remained empty. Identity reviews, if any real unseen discoveries occur, remain supported by the normal bridge-OFF ingestion path. No Telegram API mutation or audio download occurred in this task. No historical release was queued. Production health and queue/resource readback are recorded in the final operations evidence. Isolated test resources are removed after verification; protected backup and safe audit artifacts are retained.

Owner review: [83-artist latest LP/EP report](LATEST_ALBUM_SELECTION.md), [CSV](data/latest_album_selection.csv). Stop at selection; keep publication OFF.

## Measured request volume and cleanup readback

These are measured metadata requests, not audio acquisition or live-release detection timings. Request counts include adapter bootstrap requests. Successful final catalog measurements exclude the four superseded failed attempts; failed detail/qualification HTTP counts without exposed instrumentation remain unavailable.

| Phase | Measured requests | Sum of provider elapsed seconds | Scope |
|---|---:|---:|---|
| Artist identity inventory | 166 | 64.117 | 83 final successful identity responses |
| Complete catalog inventory | 202 | 36.655 | 83 responses, 119 validated pages |
| Spotify qualification identity + baseline metadata | 223 | 54.135 | 53 newly activated sources; failed first attempt excluded |
| SoundCloud final set probes | 450 | 28.301 | Nine selected artists with verified SoundCloud sources |
| Superseded Sijal set probe | 60 | 6.082 | Title match; corrected owner check retry returned 403 |
| Acquisition / preparation / upload | — | — | Not performed or authorized in this task |

The observed scheduler produced **18 completed polling batches**, totaling **151.333 seconds**, maximum batch **32.531 seconds**. Polling request totals are separately reported above and retained per outcome. Qualification stagger was 60–234 seconds in six-second steps, cycling after 30 sources; actual activation itself was serial and spread over several minutes.

Final readback: discovery and media Redis lists both **0**; the default list retains the same single inert `celery.backend_cleanup` task from before this task. Production web/database health passed, PostgreSQL and Redis stayed healthy, application checkout was clean at the exact deployed SHA. Available disk was **16 GiB**, available RAM **971 MiB** after cleanup. Only production web, metadata worker, metadata beat, PostgreSQL and Redis remain. Unrelated services/firewall/Nginx were unchanged.

The isolated `rapfadrop-roster-check` containers, tmpfs database/Redis/media, test image tag, source archives and temporary source builds were removed; no isolated project containers or volumes remain. No production volume was removed. Protected backups, safe audit JSON/JSONL and the discovery-only configuration are retained. An actual activation-controller rerun produced no source actions, baseline runs, IDs, artists or sources. No cleanup failure remains. No Telegram posts were created, so message IDs/deletions are not applicable.
