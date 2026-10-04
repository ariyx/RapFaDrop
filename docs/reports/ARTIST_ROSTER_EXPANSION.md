# Owner-approved artist roster expansion

Completed 2026-10-04, on the server. **Tested, pushed and deployed application SHA: `2a439a67ce5251c2004a4bce93c2ad770be11f8c`**. The implementation commit is `3d3ebe37d3f11352e0801d0a3f9e84cc0f3c4dd9`; the final follow-up removes unrelated Reza Bahram directory evidence from Bahram's manifest. Starting deployment was `26afd28da5e20bbca37975b5a4512ea871dd6f72`. The normal checkout included its later documentation handoff and current application implementation. A local GitHub connection failure was resolved by routing the normal authenticated push through an SSH SOCKS tunnel; provider verification and all runtime tests used the server.

## Scope and inventory

The owner supplied 53 additions alongside the original 30 identities. Read-only production inventory found **30 artists and 57 sources**, with no additional contributor rows to reuse. The final [83-identity roster](../ARTIST_ROSTER.md) and [normalized manifest](../../app/sources/data/approved_roster.json) represent each identity once. Production now has **83 artists and 130 sources** (83 Spotify, 47 SoundCloud): **30 artists/57 sources reused**, **53 artists/73 sources added**. Existing curated URLs and IDs came from the current seed and database and were not reconstructed. No new-source activation, baseline, audio acquisition, release processing or Telegram send occurred.

`seed_sources` now imports the manifest offline in an atomic transaction with a PostgreSQL advisory lock. It resolves existing artists using canonical names, Unicode-normalized aliases and exact native profile identities/URLs; ambiguous identities abort the entire import. It preserves existing display names, aliases, source configuration, verification and scheduling fields. Missing owner aliases are added without removing curated aliases. Sources are inserted only when absent for that artist/platform; existing source rows are not saved or reset. Every created candidate gets an audit event with provenance and verification outcome. `--dry-run` reviews the diff and rolls back all writes. Repeating the import creates no artist/source rows. The original `SEEDS` constant remains the frozen input for the older five-artist diagnostic command; the current import uses the 83-identity JSON manifest.

## Server metadata verification

The actual SpotifyScraper adapter resolved all **53** added artist IDs to the supplied display names and validated complete discographies: **2259 release references**, **223 instrumented HTTP calls** for identity/discography. These were metadata-only reads, not baseline/poll calls and not persisted SourceItems. The transport retained its page/byte/request/timeout bounds and no automatic retries. Eight selected catalog anchor lookups validated complete track lists and official artist credits for Daniyal, Shapur, Ashna, Masin, Amir Ribar, Dalu, Bamdad and Emad Ghavidel. Examples included Dashte Laleh/2 Ghotbi, Kavir/Sefid/Kamin, Donyaye Movazi with EMVI, and Mamooli with RadPro. Additional release/detail research calls are outside the 223 figure.

Emad's supplied [Masti Rooye Poshte Bame Khis release](https://open.spotify.com/album/1wnDymgG8JqAlPueaUIjkD) returned artist credit **`32AFrGu19C0cGtRkgzJDAb`, Emad Ghavidel**. That artist's identity and complete 15-release discography passed, including both supplied catalog anchors. The album URL is evidence only; the source stores the actual artist-profile URL.

Targeted [FarsiChart artist pages](https://farsichart.com/fa/artists/) supplied supporting platform links for 44 page observations (some identities had more than one observation), corroborated against primary platform profiles/catalogs. Four supplied Volt.fm pages returned HTTP errors from the server; that is not evidence of profile absence. The [021kid official link hub](https://linktr.ee/021kid) linked both the exact approved Spotify ID and `/021kid` on SoundCloud. No broad rediscovery was performed for Spotify candidates that passed.

SoundCloud checks called the actual metadata adapter with an explicit first-three-entry bound, no media download and no retries. **17/19 supplied root-feed samples returned metadata**; Shayan Yo and Alipasha failed with DRM extraction errors. A follow-up `/tracks` identity investigation returned HTTP 403 for all 21 examined profiles; corrected/new Eycin and 021kid root-adapter checks also returned 403. Primary public pages continued to resolve names. No rate-limit diagnosis or confirmed absence is inferred from these errors. No signed audio URLs or provider response bodies are retained in the manifest.

**Verified SoundCloud additions (10):** Bahram, Shahin Najafi, Ali Sorena, Gdaal, Emad Ghavidel, Putak, Sami Low, Masin, Naaji and Ashna. Their primary profile display names and stable own-uploader IDs matched the bounded recent catalog sample. This establishes identity and adapter sample compatibility, **not complete SoundCloud feed coverage**, future availability or full-audio availability.

**Unverified SoundCloud candidates (10):**

| Identity | Outcome |
| --- | --- |
| Sadegh | Root sample also contains Sogand uploader; artist filtering is unsupported |
| Daniyal | Owner-confirmed profile, but root sample also contains Pidar; artist filtering is unsupported |
| Amir Ribar | Root sample also contains HAMIX; artist filtering is unsupported |
| Octave | Root sample also contains Raha; artist filtering is unsupported |
| Matin Fattahi | Root sample also contains Sajad Shahi and NoTsH; artist filtering is unsupported |
| Pouriya Adroit | Root sample also contains Peaky and Big Shaggy; artist filtering is unsupported |
| Shayan Yo | Metadata extraction failed on DRM-protected item |
| Alipasha | Metadata extraction failed on DRM-protected item |
| 021kid | Official hub corroborates identity; actual adapter returned HTTP 403 |
| Eycin | Directory links to `/eycin1` and the supplied Spotify ID; primary profile name resolves, but HTTP 403 prevents catalog/adapter corroboration |

The supplied `/ey-cin` sample returned HESSY, Eli and LiteWorkx Media Group recordings without a matching artist catalog. It was held as mismatched-feed evidence and was **not imported as the monitoring URL**. The alternative `/eycin1` is an unverified candidate, not an established replacement identity. Sami Low was not substituted with SamiLone; Heliyom and Isam retain their approved spellings. All supplied Persian spellings are stored verbatim as aliases. Dariu$h refers to داریوش تبهکار; its additional historical profile `2g70ffi2wQKq3rcSuViJM2` is retained as an unattached research candidate, not an automatically added second source.

## Unresolved profiles

The following 33 additions have no corroborated SoundCloud profile after the targeted directory/reference research: Saman Wilson, Alireza Jj, Quf, Sogand, Amir Khalvat, poobon, Armin Zareei, Zakhmi, Sina Mafee, Catchybeatz, Hamid Sefat, Ali Ardavan, Bamdad, Dariu$h, Parsalip, Safir, Dalu, Shapur, Young Sudden, Ali Geramy, XWHISKY, Arman Miladi, Saaren, Heliyom, The Don, Isam, Arown, Maslak, Parsa, Nazli Mcfian, Raha, Mehyad and Tlkhoon. No placeholder source row or guessed URL was inserted. Original unresolved SoundCloud identities Fadaei, Ho3ein and Amir Tataloo remain unchanged.

For Shapur, [Mahdyar's Kavir](https://soundcloud.com/mahdyar/kavir) is official release/publisher evidence. Mahdyar is not Shapur's personal profile; the current adapter cannot restrict a shared publisher feed to one artist, so no Mahdyar source was attached or enabled.

## Verification and deployment checkpoint

Focused tests cover native-ID/alias reuse, Persian alias persistence, atomic ambiguity rejection, no-write dry-run, complete source-field preservation, evidence requirements, profile/album URL separation and safe repeated full-roster import. All new records are asserted disabled. Tests run in a separate server Compose project with PostgreSQL at 55433, Redis at 56380, no worker, no bot credentials, separate temporary media and resource bounds. Production ports/volumes and queues are not shared.

The final exact pushed SHA was fetched and exported from Git on the server, built and tested without changing the deployed checkout: **19 focused tests passed in 8.925 seconds; all 143 tests passed in 63.568 seconds**. Django system checks and migration-drift checks passed. Earlier draft/full runs also passed; these final figures refer specifically to the deployed SHA.

Production beat, metadata worker and media worker were briefly stopped before a consistent backup. Root-only `/var/backups/rapfadrop/pre_roster_expansion_20261004.dump` is **201480 bytes**, mode **0600**, with a mode-0600 SHA-256 sidecar. Checksum and `pg_restore --list` passed. The isolated `roster_restore_20261004` restoration compared all **37 public tables**, with source and restore content digest **`4e4d11d139320309eb1cdb3e3f16c032e2099b410b953c7f06cba6d1e34a58fd`**, zero mismatches; the restore database was dropped and its absence rechecked.

The clean server checkout moved to the exact tested SHA. All three existing Compose files were retained in order: `/opt/rapfadrop/compose.internal.yaml`, `/var/lib/rapfadrop-operations/spotify-pilot.compose.yaml`, `/var/lib/rapfadrop-operations/spotify-bridge.compose.yaml`. The application image/web were rebuilt/recreated, migration/check commands passed without schema changes, and the actual database dry-run diff was reviewed before import: 53 missing artists, 73 missing sources, zero curated differences. Its rollback preserved row counts/data (PostgreSQL sequences can advance during a rolled-back dry-run). The first import produced exactly that diff. The second created **0 artists/0 sources**, reused all 83/130, and left every artist/source row identical to the first import.

All **57 pre-existing source rows matched every field** against the frozen pre-import snapshot, including URLs, native IDs, enabled/verification state, baseline fields, next-poll timestamps, intervals and failure state. Existing artist display names/enable flags and aliases were preserved. All **53 new artists and 73 new sources remain disabled**; the new sources have 63 verified/10 unverified flags, null scheduling/baseline timestamps and no SourceItems/BaselineRuns. Each imported candidate has its manifest provenance/outcome and a source audit event. Admin querysets expose exactly 83 artists/130 sources. Pilot services resumed using the same routing and configuration; subsequent normal polling may advance due/success timestamps.

Final production verification: health **HTTP 200 / database ok**; exactly five original enabled/verified Spotify sources (Sijal 31, Fadaei 39, Hichkas 42, Yas 44, Ho3ein 48), all at 180 seconds. The **177 historical Spotify IDs** retain digest `bad43929b7c93f9a77d61a9a4a3feafc130de248898784ffad2031950828b7d4`. The earlier 51 SoundCloud baseline items also remain, making 228 total SourceItems; their combined digest before/after is `fb7dbbf4a804e1a9cde184f3fbdc6df41f9ce262f41f994fb4b437d358014cde`. BaselineRun digest remains `c7d071ba1adc750ce13e93bb6dd3d06e3fa2c4d2a2eec464191ddbd677461639`. Reviews, processing jobs, media candidates/attempts, publications/attempts and media files are each zero. Pilot/media queues are empty; the original inert default-queue housekeeping envelope remains untouched.

The protected bridge remains **ON**, Telegram mode **disabled**, live/publication switches **false**, with no production bot token. `.env` and both protected pilot overlays passed their before/after checksum comparison. No firewall, Nginx, production volume or activation setting changed. No audio download or live Telegram request was made in this roster task; test-generated media and fake gateway operations were confined to the isolated test environment.

The disposable test containers, tmpfs database/media, Redis/queue, exported source directories/archive and test image tag were removed. No test container or project volume remains. Safe inventory, metadata outcomes, import comparisons, test/deployment logs and final state are retained as mode-0600 files in root-only `/var/lib/rapfadrop-operations/roster-20261004/`; the protected pre-import backup remains outside Git. There is no incomplete cleanup. Production checkout remains clean at the application SHA; documentation-only follow-up commits are intentionally not deployed.

## Next scope

Stop after roster expansion. New-source polling/baselining and selecting or publishing each artist's latest album require separate authorization and an owner-reviewed release list. Unverified/mixed-feed sources require further identity/filtering work before activation.
