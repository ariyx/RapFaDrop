# Refreshed latest album/EP owner inventory

Generated **2026-10-04T14:47:54.222104+00:00**. Application/deployed SHA **`5d89fcedcc1c01d5f9f00b533242e6d9045fbb0f`**. Current source database observed **2026-10-04T14:25:08.527320+00:00** and preservation checked **2026-10-04T14:37:46.159582+00:00**. **83/83 approved artists are represented exactly once**, all with active verified Spotify sources. The inventory has **68 artist candidate rows / 67 unique latest releases**, plus separately labeled alternatives: **73 unique release-selection rows total**. No release is ready to publish.

## Files and separate status fields

- [83-artist CSV](data/latest_album_selection.csv): current source verification/enabled state, release eligibility/classification, complete ordered tracks/credits, alternatives and media availability are separate fields.
- [Unique release-selection CSV](data/latest_album_release_selection.csv): keyed by `spotify:album:<native ID>`, with selecting artists, all associated approved contributors, attribution coverage and alternative selection kinds. REFIGH appears once.
- [Complete monitored Spotify album/EP catalog CSV](data/spotify_album_ep_catalog.csv): 289 artist/release memberships across all 83 complete catalogs. This includes every ALBUM/EP catalog entry, not only the latest suggestion; historical entries without detail validation are labeled accordingly.
- [Fresh safe evidence](data/latest_album_refresh_evidence.json): per-response timestamps, raw upstream types, complete track details, official comparison probes and preservation proof.
- [Initial historical CSV](data/latest_album_selection_20261004_initial.csv) and [initial evidence](data/latest_album_evidence.json): retained unchanged. The 25 old unverified flags are historical, not the current authoritative server state.

`owner_selection_candidate` means metadata is eligible for owner consideration. It does not mean audio has been acquired, validated or prepared. Every CSV row has `ready_to_publish=false`. Current source verification does not remove classification, edition, attribution or media review reasons. Counts by eligibility: `{"no_candidate_in_monitored_catalog": 15, "owner_selection_candidate": 63, "release_review": 5}`.

## Four extended one-track EPs

The actual discography responses and `albumUnion.type` both return **EP** for all four. SpotifyScraper's album-union parser lowercases that upstream field; RapFaDrop passes the validated type through. Neither derives EP from track count. **No adapter defect was established**, so no code fix or deployment was made. The library's generic embed fallback can label an embedded entity `album`, but these four records include raw API type evidence and did not use that fallback. One-track count does not invalidate an EP.

| Artist | Release | Duration | Raw catalog / raw album / adapter | Independent official evidence | Classification finding | Latest detailed unambiguous alternative |
|---|---|---:|---|---|---|---|
| Hiphopologist | [Enhelale Label](https://open.spotify.com/album/3FyXcxmpYzwXy0ZE76Oy7P) | 522.937 s | EP / EP / ep | No matching independent explicit designation found | classification_review | [Heart Attack](https://open.spotify.com/album/6fNHYJD6cQh0U5bMW6ArBj) |
| Shayea | [Asli Mix 001](https://open.spotify.com/album/4xuR2xJ1C6kltAQPLFoggI) | 630.296 s | EP / EP / ep | [Asli Mix 001 - EP](https://music.apple.com/us/album/asli-mix-001-ep/6809735076?uo=4) | EP_confirmed_Spotify_and_Apple | [Pizza](https://open.spotify.com/album/1LbPKdJfPK1vPdwZqdNgEq) |
| Sina Sae | [Carnival Series Episode 1](https://open.spotify.com/album/2kA0wiTt80o0Rq8TPtWZxa) | 778.98 s | EP / EP / ep | [Carnival Series Episode 1 - EP](https://music.apple.com/us/album/carnival-series-episode-1-ep/1851728595?uo=4) | EP_confirmed_Spotify_and_Apple | [Deja vu](https://open.spotify.com/album/3Wb9GGGGiEidDo0RntlSLq) |
| Amir Tataloo | [Tars](https://open.spotify.com/album/20xFt3YcYMN4hyNQ0mqvon) | 881.202 s | EP / EP / ep | No matching independent explicit designation found | classification_review | [Sayeh](https://open.spotify.com/album/1iL9DwnGphoCy7tpyzQWH9) |

The two independently corroborated EPs retain EP eligibility despite having one extended track. The other two remain classification review, retaining Spotify's observed EP designation rather than guessing Single. Alternative rows are separate choices and are not silently substituted for the latest candidate. Independent Apple checks cover the US catalog and a bounded search; absence from those results is not a global absence claim.

## REFIGH and complete attribution

Native album `55M4NLSgJ9L44cEQgMIfH5` is one 11-track release associated with both approved artists **Tohi** and **Reza Pishro**. Tohi is credited on **11/11 tracks**; Reza Pishro on **8/11** (positions 2–9), Ali Owj on two, Big Shaggy on one, and Nassim on one. These counts come from the complete ordered track credits. Release-level credits alone do not establish that each performer is a primary album artist. Tohi is the all-track principal candidate; Reza Pishro's co-primary versus featured attribution remains for review. Reza's latest detailed unambiguous artist alternative is included separately. The artist inventory still has one row per approved artist, while the release table reserves this album only once.

Principal/featured candidate fields are explicitly inferred from complete credit coverage, not official role declarations. Some track-credit native artist IDs are absent from the provider model; names are retained and associated with approved identities only when unambiguous. No role or missing native ID was fabricated.

## OCD: historical success versus current availability

[The dated server E2E report](SPOTIFY_E2E.md) validates OCD `2yHJfINmVWOpGLymx3JxaW` and the exact official [SoundCloud set](https://soundcloud.com/sijalofficial/sets/ocd). Final replay began **2026-10-04T09:30:20.944249Z** at application **`26afd28da5e20bbca37975b5a4512ea871dd6f72`**. Complete real recordings passed full decode/audio validation, official embedded tags/artwork, all-track staging, ordered test-channel publication, prior-single reuse, retry/restart and byte-matched Telegram readback. The complete album test took **602.057 seconds**; this was historical replay, not live detection latency.

Test channel `-1004475982526`: prior single **33**, cover **34**, remaining ordered tracks **35–42**; all deleted. Test audio/database/queue resources were removed. Original quality was AAC/M4A, 44.1 kHz stereo, approximately 160 kb/s; no quality upconversion. This fresh inventory performs **no acquisition or Telegram operation**. Later metadata-only checks returned 403; historical success does not establish current provider availability or publication readiness. OCD's historical validation is now recorded separately from the current untested/unconfirmed availability field.

## No-candidate outcomes and other reviews

Fifteen artists have **no qualifying LP/EP found in the complete monitored Spotify catalog**, not a confirmed lifelong absence of albums. Every monitored catalog was revalidated through the supported adapter. Bounded independent Apple searches and the attempted official-release pages are retained with timestamps, including unrelated same-name results that were excluded. **No artist is classified as confirmed absent across all official sources.** Hichkas's attempted Mojaz Bandcamp pages could not be verified, so independent/off-catalog coverage remains a limitation rather than evidence of absence. A future source correction or explicit official release may change these results; no source was reset in this task.

Archival/leaked editions, including Yas's “Old of YAS” and Dariu$h's “BROKE TKAR [2018 - 2022 LEAKS]”, remain release review despite their now-verified source identities. Earlier partial SoundCloud coverage, mismatched set/track metadata, blocked probes and unresolved media-source notes are retained separately. Current full-audio availability was not re-probed or claimed ready.

| Artist | Candidate | Explicit release review reason |
|---|---|---|
| Hiphopologist | Enhelale Label | Spotify explicitly labels an extended one-track release EP; independent explicit release classification was not corroborated; do not infer Single from track count |
| Yas | Old of YAS | Edition/archival status requires review: archival/leaked/collection review |
| Reza Pishro | REFIGH | Artist is not credited on every track; co-primary versus featured/guest album attribution requires review |
| Amir Tataloo | Tars | Spotify explicitly labels an extended one-track release EP; independent explicit release classification was not corroborated; do not infer Single from track count |
| Dariu$h | BROKE TKAR [2018 - 2022 LEAKS] | Edition/archival status requires review: archival/leaked/collection review |

## Owner-review table: all 83 artists

All source verification/enabled values in this table's CSV are current and verified/true. The table keeps release eligibility and media evidence separate; alternatives are optional owner choices.

| ID | Artist | Latest candidate / scoped absence | Type / tracks | Release eligibility | Separate alternative | Media evidence |
|---|---|---|---|---|---|---|
| 1 | Hossein Tiem | [Colonel](https://open.spotify.com/album/0oi0AO9zZGcqRRS5nd3fvd) | LP / 10 | owner_selection_candidate | — | Unconfirmed / review |
| 2 | Hesam Tiem | [Ay](https://open.spotify.com/album/6RlbbqO6RIjqLyvuKajnUV) | LP / 12 | owner_selection_candidate | — | Unconfirmed / review |
| 3 | Amin Tijay | [RIP Underratedbo!](https://open.spotify.com/album/2YU2B2VwnmKFezMe0KCYWF) | LP / 13 | owner_selection_candidate | — | Unconfirmed / review |
| 4 | Mamazi | [Devil May Cry (D.M.C)](https://open.spotify.com/album/2ZmZaj0f8KSFdSiStWiHRr) | LP / 19 | owner_selection_candidate | — | Unconfirmed / review |
| 5 | Sajad Shahi | [MIRAS](https://open.spotify.com/album/7nbBAMwJArumwlmp2AM2SR) | LP / 10 | owner_selection_candidate | — | Unconfirmed / review |
| 6 | Sinazza | No qualifying LP/EP found in monitored Spotify catalog | — / — | no_candidate_in_monitored_catalog | — | Unconfirmed / review |
| 7 | Hoomaan | [Shahre Moon](https://open.spotify.com/album/34Th2FiVSnbZbUxsop0PBo) | LP / 13 | owner_selection_candidate | — | Unconfirmed / review |
| 8 | Vinak | [Concert Type (Vol. 1)](https://open.spotify.com/album/3ElC9tdBi3mZJDNtJsktSt) | LP / 7 | owner_selection_candidate | — | Unconfirmed / review |
| 9 | Dorcci | [YOUNG MORVARID](https://open.spotify.com/album/52qjd27T8RrB5vIvqIMKnE) | LP / 12 | owner_selection_candidate | — | Unconfirmed / review |
| 10 | Hiphopologist | [Enhelale Label](https://open.spotify.com/album/3FyXcxmpYzwXy0ZE76Oy7P) | EP / 1 | release_review | [Heart Attack](https://open.spotify.com/album/6fNHYJD6cQh0U5bMW6ArBj) | Unconfirmed / review |
| 11 | Chvrsi | [Mochale](https://open.spotify.com/album/00lH6uNeOKJfwyckC9toxJ) | EP / 6 | owner_selection_candidate | — | Unconfirmed / review |
| 12 | Poori | [Az Khoda Betars](https://open.spotify.com/album/4kusQzCYYlUcIgZnL3bH36) | LP / 12 | owner_selection_candidate | — | Unconfirmed / review |
| 13 | Arta | [HITMAN](https://open.spotify.com/album/643tLZ4wQii7WcMnjTmPdL) | LP / 21 | owner_selection_candidate | — | Unconfirmed / review |
| 14 | Koorosh Wantons | [TEHRAN 2585](https://open.spotify.com/album/1zoub0zRSL76zkkDsrwipt) | EP / 5 | owner_selection_candidate | — | Unconfirmed / review |
| 15 | Canis | [AKA](https://open.spotify.com/album/4rY8LwQfjEUPZEk7T6m5k1) | LP / 11 | owner_selection_candidate | — | Unconfirmed / review |
| 16 | Sijal | [OCD](https://open.spotify.com/album/2yHJfINmVWOpGLymx3JxaW) | LP / 9 | owner_selection_candidate | — | Historical E2E passed; current untested |
| 17 | Behzad Leito | [Late Night Drive](https://open.spotify.com/album/2fgQ1CW4NipK8HCe4Gobn5) | LP / 10 | owner_selection_candidate | — | Unconfirmed / review |
| 18 | Sepehr Khalse | [Margo Zendegi](https://open.spotify.com/album/6YbfLFtFRkIO1YEvx4n9rz) | LP / 9 | owner_selection_candidate | — | Unconfirmed / review |
| 19 | Shayea | [Asli Mix 001](https://open.spotify.com/album/4xuR2xJ1C6kltAQPLFoggI) | EP / 1 | owner_selection_candidate | [Pizza](https://open.spotify.com/album/1LbPKdJfPK1vPdwZqdNgEq) | Unconfirmed / review |
| 20 | Fadaei | [Rend](https://open.spotify.com/album/6H2dUgWnssEDFFYGOxRlcK) | LP / 8 | owner_selection_candidate | — | Unconfirmed / review |
| 21 | Sina Sae | [Carnival Series Episode 1](https://open.spotify.com/album/2kA0wiTt80o0Rq8TPtWZxa) | EP / 1 | owner_selection_candidate | [Deja vu](https://open.spotify.com/album/3Wb9GGGGiEidDo0RntlSLq) | Unconfirmed / review |
| 22 | Hichkas | No qualifying LP/EP found in monitored Spotify catalog | — / — | no_candidate_in_monitored_catalog | — | Unconfirmed / review |
| 23 | Yas | [Old of YAS](https://open.spotify.com/album/7oQ2HPJmaoE8PZlGDAnkgG) | LP / 18 | release_review | — | Unconfirmed / review |
| 24 | Reza Pishro | [REFIGH](https://open.spotify.com/album/55M4NLSgJ9L44cEQgMIfH5) | LP / 11 | release_review | [Nirvana](https://open.spotify.com/album/3qjVDg0hjqQnTg3lGzEvgK) | Unconfirmed / review |
| 25 | Ho3ein | No qualifying LP/EP found in monitored Spotify catalog | — / — | no_candidate_in_monitored_catalog | — | Unconfirmed / review |
| 26 | Tohi | [REFIGH](https://open.spotify.com/album/55M4NLSgJ9L44cEQgMIfH5) | LP / 11 | owner_selection_candidate | — | Unconfirmed / review |
| 27 | Erfan | [The Poet's Chamber](https://open.spotify.com/album/2Fcz6pS1lB234jeHGZ4TH0) | LP / 8 | owner_selection_candidate | — | Unconfirmed / review |
| 28 | Amir Tataloo | [Tars](https://open.spotify.com/album/20xFt3YcYMN4hyNQ0mqvon) | EP / 1 | release_review | [Sayeh](https://open.spotify.com/album/1iL9DwnGphoCy7tpyzQWH9) | Unconfirmed / review |
| 29 | Sohrab Mj | [Magnet](https://open.spotify.com/album/63uBYgmUpGSHeojA6jkHCb) | LP / 10 | owner_selection_candidate | — | Unconfirmed / review |
| 30 | Mehrad Hidden | [Alavis 2](https://open.spotify.com/album/4cqDo7W3Eu6jkbLp5DD92c) | EP / 5 | owner_selection_candidate | — | Unconfirmed / review |
| 84 | Bahram | [HEECH](https://open.spotify.com/album/0lXvCzjiBL50iJhcEJntB6) | LP / 11 | owner_selection_candidate | — | Unconfirmed / review |
| 85 | Shahin Najafi | [Sigma](https://open.spotify.com/album/1M7ICkaPMy3kIaAuINBGKj) | LP / 8 | owner_selection_candidate | — | Unconfirmed / review |
| 86 | Saman Wilson | [Bozorg, Vol. 2](https://open.spotify.com/album/4a8nVbcRrtPmXQZQLioG7o) | LP / 19 | owner_selection_candidate | — | Unconfirmed / review |
| 87 | Alireza Jj | [LEITMOTIV](https://open.spotify.com/album/2cypAUwFLV50MzFfWtlfFb) | LP / 14 | owner_selection_candidate | — | Unconfirmed / review |
| 88 | Quf | [Zir o Bam e Zirzamin](https://open.spotify.com/album/0vaU6nncOdSP8Rm1XvXoKH) | LP / 12 | owner_selection_candidate | — | Unconfirmed / review |
| 89 | Ali Sorena | [Mojassameh](https://open.spotify.com/album/1YomRnpVLMXxzVCgs3CVl9) | LP / 20 | owner_selection_candidate | — | Unconfirmed / review |
| 90 | Sadegh | [Nashod Begam](https://open.spotify.com/album/22C1OnNz1EvwYCEmrpBPxd) | LP / 7 | owner_selection_candidate | — | Unconfirmed / review |
| 91 | Sogand | [Khune](https://open.spotify.com/album/35wT0eSuG97nyh4su1wXHH) | EP / 6 | owner_selection_candidate | — | Unconfirmed / review |
| 92 | Gdaal | [Abraye Noghrei 3](https://open.spotify.com/album/7k3kmzV0rhopPPYvf7Yw0u) | LP / 17 | owner_selection_candidate | — | Partial coverage (earlier probe) |
| 93 | Amir Khalvat | [Man](https://open.spotify.com/album/04SiDOxnvZSgNMjHQsl5dX) | EP / 4 | owner_selection_candidate | — | Unconfirmed / review |
| 94 | Emad Ghavidel | No qualifying LP/EP found in monitored Spotify catalog | — / — | no_candidate_in_monitored_catalog | — | Unconfirmed / review |
| 95 | poobon | [Midnight](https://open.spotify.com/album/2qCN8thNCMHWvzSQ47qt3A) | EP / 6 | owner_selection_candidate | — | Unconfirmed / review |
| 96 | Armin Zareei | [Toure Concertam](https://open.spotify.com/album/5TMBih6ttTA4dNLBQ69MW1) | EP / 4 | owner_selection_candidate | — | Unconfirmed / review |
| 97 | Zakhmi | [Mehraboon](https://open.spotify.com/album/75zv6v0DISo36fh9MLE9QL) | EP / 5 | owner_selection_candidate | — | Unconfirmed / review |
| 98 | Sina Mafee | [Mafia](https://open.spotify.com/album/1KejPTn7hcYDiokER7IsXT) | LP / 11 | owner_selection_candidate | — | Unconfirmed / review |
| 99 | Catchybeatz | [Zooze](https://open.spotify.com/album/75mbHoMrkobQUe5b1RCPti) | LP / 8 | owner_selection_candidate | — | Unconfirmed / review |
| 100 | Hamid Sefat | No qualifying LP/EP found in monitored Spotify catalog | — / — | no_candidate_in_monitored_catalog | — | Unconfirmed / review |
| 101 | Ali Ardavan | No qualifying LP/EP found in monitored Spotify catalog | — / — | no_candidate_in_monitored_catalog | — | Unconfirmed / review |
| 102 | Bamdad | [Mantaghe 5 Pelake 8](https://open.spotify.com/album/2JnDcFfeRxCGlLPv5aWJj2) | EP / 3 | owner_selection_candidate | — | Unconfirmed / review |
| 103 | Dariu$h | [BROKE TKAR [2018 - 2022 LEAKS]](https://open.spotify.com/album/7k1VaG1Ak2XAVPuvNufguK) | EP / 5 | release_review | [Sarbaz 0](https://open.spotify.com/album/76NyIF90AK368y0Dmqn0Wz) | Unconfirmed / review |
| 104 | Parsalip | [Parvaneha](https://open.spotify.com/album/0Lm0DJTiL6H6PB8SuSP4mL) | EP / 4 | owner_selection_candidate | — | Unconfirmed / review |
| 105 | Putak | [Red Horn](https://open.spotify.com/album/3av4laDlNglRFGODbCadkq) | LP / 14 | owner_selection_candidate | — | Partial coverage (earlier probe) |
| 106 | Daniyal | [Keder](https://open.spotify.com/album/1cp7ptHDRGL2uVsnx3tNTI) | EP / 6 | owner_selection_candidate | — | Unconfirmed / review |
| 107 | Sami Low | [Lowkey](https://open.spotify.com/album/4GsYSSLgIYkgXMSGkvcItA) | LP / 25 | owner_selection_candidate | — | Unconfirmed / review |
| 108 | Safir | [Kandoo](https://open.spotify.com/album/2Xy0pXSPbnqJkEZHMYpdJH) | LP / 18 | owner_selection_candidate | — | Unconfirmed / review |
| 109 | Eycin | [BATMAN](https://open.spotify.com/album/6vHE6SgLMBAUzupuglg3GL) | LP / 12 | owner_selection_candidate | — | Unconfirmed / review |
| 110 | Dalu | No qualifying LP/EP found in monitored Spotify catalog | — / — | no_candidate_in_monitored_catalog | — | Unconfirmed / review |
| 111 | Amir Ribar | No qualifying LP/EP found in monitored Spotify catalog | — / — | no_candidate_in_monitored_catalog | — | Unconfirmed / review |
| 112 | Shapur | No qualifying LP/EP found in monitored Spotify catalog | — / — | no_candidate_in_monitored_catalog | — | Unconfirmed / review |
| 113 | Masin | [Dmt](https://open.spotify.com/album/5SWrdCmii8VxsYwd96waDc) | EP / 3 | owner_selection_candidate | — | Unconfirmed / review |
| 114 | Young Sudden | [Welcome to Gambron](https://open.spotify.com/album/37BISa2SRxjs7FJX5lxWt3) | LP / 33 | owner_selection_candidate | — | Unconfirmed / review |
| 115 | Naaji | [STARBOY](https://open.spotify.com/album/7AkUbPht8NClY4sA78YAt8) | LP / 8 | owner_selection_candidate | — | Potential support (earlier probe) |
| 116 | Ali Geramy | [G](https://open.spotify.com/album/74pfaLWuj1ZIwTMTrVrotu) | LP / 16 | owner_selection_candidate | — | Unconfirmed / review |
| 117 | XWHISKY | [Virus, vol. 2](https://open.spotify.com/album/7InVsgJrA6VVLJFngsWC5h) | LP / 15 | owner_selection_candidate | — | Unconfirmed / review |
| 118 | Ashna | No qualifying LP/EP found in monitored Spotify catalog | — / — | no_candidate_in_monitored_catalog | — | Unconfirmed / review |
| 119 | Arman Miladi | [Paranoia](https://open.spotify.com/album/2Vj0WnvHmn3L0nza1Efk2d) | LP / 17 | owner_selection_candidate | — | Unconfirmed / review |
| 120 | Saaren | No qualifying LP/EP found in monitored Spotify catalog | — / — | no_candidate_in_monitored_catalog | — | Unconfirmed / review |
| 121 | Heliyom | [Jangale Arezooha](https://open.spotify.com/album/22PgFvBhpQ5gr17pJgrikU) | LP / 9 | owner_selection_candidate | — | Unconfirmed / review |
| 122 | The Don | [Prestige](https://open.spotify.com/album/7q0vI93TCn9NcpuzFC0eOC) | EP / 6 | owner_selection_candidate | — | Unconfirmed / review |
| 123 | Isam | [GALLERY TALK](https://open.spotify.com/album/3pU4AWSi1ggkUCsXS2wQ6F) | EP / 6 | owner_selection_candidate | — | Unconfirmed / review |
| 124 | Arown | No qualifying LP/EP found in monitored Spotify catalog | — / — | no_candidate_in_monitored_catalog | — | Unconfirmed / review |
| 125 | Octave | [Adam Bozorga](https://open.spotify.com/album/2W1pBaKkYDUXKyd8NHtCcb) | LP / 8 | owner_selection_candidate | — | Unconfirmed / review |
| 126 | Maslak | [Khato Neshoun](https://open.spotify.com/album/1Osk6KhD2Hyix5VGZMLFaA) | EP / 5 | owner_selection_candidate | — | Unconfirmed / review |
| 127 | Shayan Yo | [6](https://open.spotify.com/album/0nSfDYxx7FWSUZwsYnY3KW) | EP / 6 | owner_selection_candidate | — | Unconfirmed / review |
| 128 | Parsa | [MERCURY ANGEL](https://open.spotify.com/album/0tQeLVlLahdphQDgs5V5ai) | EP / 4 | owner_selection_candidate | — | Unconfirmed / review |
| 129 | Nazli Mcfian | No qualifying LP/EP found in monitored Spotify catalog | — / — | no_candidate_in_monitored_catalog | — | Unconfirmed / review |
| 130 | Raha | [Revival](https://open.spotify.com/album/1z1UIWoOBhNLXn6MQMGMab) | LP / 8 | owner_selection_candidate | — | Unconfirmed / review |
| 131 | Matin Fattahi | No qualifying LP/EP found in monitored Spotify catalog | — / — | no_candidate_in_monitored_catalog | — | Unconfirmed / review |
| 132 | 021kid | [C4](https://open.spotify.com/album/7qyawsVb9eOJoIysyHLQ1B) | EP / 4 | owner_selection_candidate | — | Unconfirmed / review |
| 133 | Mehyad | [Credit](https://open.spotify.com/album/37NEdEKaw2KCPbee1cq1ua) | LP / 8 | owner_selection_candidate | — | Unconfirmed / review |
| 134 | Alipasha | [Siah Sefid](https://open.spotify.com/album/64jQOx8sk364oFOEIHOd75) | LP / 18 | owner_selection_candidate | — | Unconfirmed / review |
| 135 | Tlkhoon | No qualifying LP/EP found in monitored Spotify catalog | — / — | no_candidate_in_monitored_catalog | — | Unconfirmed / review |
| 136 | Pouriya Adroit | [Cheqer Mood 2](https://open.spotify.com/album/2VlSXTzPnjjQOpIfoBEdpQ) | LP / 18 | owner_selection_candidate | — | Unconfirmed / review |

## Verification and scope

Validated 83 unique artist rows, complete native-ID/ordered-track consistency for selected and alternative releases, unique release keys, shared-release associations and exact current database flags. The server preservation readback retained **3934 items**, **84 baselines**, **1 reviews** and all 83 source identities/activation/intervals. Normal scheduled discovery may advance poll timestamps; this inventory performed no database writes. Downstream processing/media/publication counts remain `{"MediaAttempt": 0, "MediaCandidate": 0, "ProcessingQueueItem": 0, "Publication": 0, "PublicationAttempt": 0}`, media files **0**, bridge/publication **OFF**, media worker absent. No new baseline, activation, source reset, audio acquisition, downstream task or Telegram mutation occurred. Application code is unchanged, so application tests/redeployment were not needed; inventory consistency and server Django/migration checks were run.

Stop at owner selection. The owner must choose releases before a separate acquisition and publication task.
