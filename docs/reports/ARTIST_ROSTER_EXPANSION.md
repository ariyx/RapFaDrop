# Owner-approved artist roster expansion

Observed metadata verification: 2026-10-04, on the server. Deployment/import evidence is recorded below after the exact tested SHA is deployed. Starting application SHA: `26afd28da5e20bbca37975b5a4512ea871dd6f72`; normal checkout base includes the later documentation handoff, not an obsolete application.

## Scope and inventory

The owner supplied 53 additions alongside the original 30 identities. Read-only production inventory found **30 artists and 57 sources**, with no additional contributor rows to reuse. The final [83-identity roster](../ARTIST_ROSTER.md) and [normalized manifest](../../app/sources/data/approved_roster.json) represent each identity once; the intended source count is **130** (83 Spotify, 47 SoundCloud). Existing curated URLs and IDs came from the current seed and database and were not reconstructed. No activation, new baseline, audio acquisition, release processing or Telegram send is authorized in this task.

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

Deployment is pending at this implementation checkpoint. Before deployment/import, stop production poll/media services briefly, create and checksum/list/restore a protected backup, compare all 37 table contents, review the actual database dry-run diff, deploy the exact tested pushed SHA with all three existing pilot Compose files, then apply/import twice and compare all pre-existing source fields. Resume only the previously active pilot services. Record final counts, health, hashes and SHA here; production publication stays OFF.

## Next scope

Stop after roster expansion. New-source polling/baselining and selecting or publishing each artist's latest album require separate authorization and an owner-reviewed release list. Unverified/mixed-feed sources require further identity/filtering work before activation.
