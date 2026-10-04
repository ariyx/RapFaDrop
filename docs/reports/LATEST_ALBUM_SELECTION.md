# Latest album/EP owner selection

Observed on the server, 2026-10-04. Application `5d89fcedcc1c01d5f9f00b533242e6d9045fbb0f`. All **83 artists** are represented: **68 release candidates**, **15 with no qualifying LP/EP in their complete catalogs**. Candidates are suggestions for owner review; none is ready to publish. Unverified identities and archival/edition ambiguities are explicitly held for review.

The sweep used the actual Spotify identity adapter and strictly validated every discography page, including total/offset/length/duplicate-ID checks. Catalog/release-detail reads ran at the starting application SHA `2a439a67ce5251c2004a4bce93c2ad770be11f8c`; the subsequent baseline/polling and SoundCloud probes ran at the deployed SHA above. Four initial network failures succeeded on one bounded retry. Release type and date/precision come from official discography responses; EP status is not inferred from track count. Selected release details validate stable IDs, complete ordered tracks, positive durations and primary artist credits. Compilations reported by Spotify were excluded; suspicious archival titles remain review-only rather than silently treated as original LPs. Up to four candidates per artist were allowed for primary-credit/compilation exclusions. Latest LP and EP references are included separately in the CSV; those secondary references have catalog evidence, not an independent full detail check. Where provider type differs between discography and detail, the explicit official discography classification is retained.

Primary and per-track artist credits, featured credits, dates, edition markers, prior-publication fields, full track order/durations, source confidence and exact probe links are in the [UTF-8 CSV](data/latest_album_selection.csv) and [detailed safe evidence](data/latest_album_evidence.json). Production contained zero publication records, so there are no stored prior Telegram links. Standard/unspecified means no title edition marker was found, not a verified standard-edition assertion.

SoundCloud assessment used bounded metadata-only official `/sets` scans (maximum 30 entries), then complete metadata for a title-matched set (maximum 100 tracks). It checked uploader identity, track title, order and duration; format presence indicates potential support only. No audio was downloaded, decoded, tagged or published. A title match with partial or uncertain tracks stays review-only. Lack of a match in this bounded scan is not proof that no recording exists elsewhere. Artists without a verified SoundCloud source have no proven media candidate.

| ID | Artist | Suggested release / explicit absence | Type | Official date | Tracks | Review state | Media evidence |
|---|---|---|---|---|---:|---|---|
| 1 | Hossein Tiem | [Colonel](https://open.spotify.com/album/0oi0AO9zZGcqRRS5nd3fvd) | LP | 2025-02-03 | 10 | requires review | not established |
| 2 | Hesam Tiem | [Ay](https://open.spotify.com/album/6RlbbqO6RIjqLyvuKajnUV) | LP | 2026-08-11 | 12 | requires review | not established |
| 3 | Amin Tijay | [RIP Underratedbo!](https://open.spotify.com/album/2YU2B2VwnmKFezMe0KCYWF) | LP | 2025-08-04 | 13 | requires review | not established |
| 4 | Mamazi | [Devil May Cry (D.M.C)](https://open.spotify.com/album/2ZmZaj0f8KSFdSiStWiHRr) | LP | 2025-04-15 | 19 | requires review | not established |
| 5 | Sajad Shahi | [MIRAS](https://open.spotify.com/album/7nbBAMwJArumwlmp2AM2SR) | LP | 2025-08-01 | 10 | requires review | not established |
| 6 | Sinazza | No qualifying LP/EP | — | — | — | no qualifying LP/EP in complete catalog | not established |
| 7 | Hoomaan | [Shahre Moon](https://open.spotify.com/album/34Th2FiVSnbZbUxsop0PBo) | LP | 2023-06-09 | 13 | requires review | not established |
| 8 | Vinak | [Concert Type (Vol. 1)](https://open.spotify.com/album/3ElC9tdBi3mZJDNtJsktSt) | LP | 2026-08-27 | 7 | requires review | not established |
| 9 | Dorcci | [YOUNG MORVARID](https://open.spotify.com/album/52qjd27T8RrB5vIvqIMKnE) | LP | 2025-02-21 | 12 | requires review | not established |
| 10 | Hiphopologist | [Enhelale Label](https://open.spotify.com/album/3FyXcxmpYzwXy0ZE76Oy7P) | EP | 2026-07-11 | 1 | requires review | not established |
| 11 | Chvrsi | [Mochale](https://open.spotify.com/album/00lH6uNeOKJfwyckC9toxJ) | EP | 2026-06-13 | 6 | requires review | not established |
| 12 | Poori | [Az Khoda Betars](https://open.spotify.com/album/4kusQzCYYlUcIgZnL3bH36) | LP | 2025-06-04 | 12 | requires review | not established |
| 13 | Arta | [HITMAN](https://open.spotify.com/album/643tLZ4wQii7WcMnjTmPdL) | LP | 2024-12-28 | 21 | requires review | not established |
| 14 | Koorosh Wantons | [TEHRAN 2585](https://open.spotify.com/album/1zoub0zRSL76zkkDsrwipt) | EP | 2026-06-08 | 5 | requires review | not established |
| 15 | Canis | [AKA](https://open.spotify.com/album/4rY8LwQfjEUPZEk7T6m5k1) | LP | 2024-10-12 | 11 | requires review | not established |
| 16 | Sijal | [OCD](https://open.spotify.com/album/2yHJfINmVWOpGLymx3JxaW) | LP | 2025-11-28 | 9 | suggested | not established |
| 17 | Behzad Leito | [Late Night Drive](https://open.spotify.com/album/2fgQ1CW4NipK8HCe4Gobn5) | LP | 2026-06-19 | 10 | requires review | not established |
| 18 | Sepehr Khalse | [Margo Zendegi](https://open.spotify.com/album/6YbfLFtFRkIO1YEvx4n9rz) | LP | 2026-08-11 | 9 | requires review | not established |
| 19 | Shayea | [Asli Mix 001](https://open.spotify.com/album/4xuR2xJ1C6kltAQPLFoggI) | EP | 2026-08-10 | 1 | requires review | not established |
| 20 | Fadaei | [Rend](https://open.spotify.com/album/6H2dUgWnssEDFFYGOxRlcK) | LP | 2026-01-05 | 8 | suggested | not established |
| 21 | Sina Sae | [Carnival Series Episode 1](https://open.spotify.com/album/2kA0wiTt80o0Rq8TPtWZxa) | EP | 2025-11-07 | 1 | requires review | not established |
| 22 | Hichkas | No qualifying LP/EP | — | — | — | no qualifying LP/EP in complete catalog | not established |
| 23 | Yas | [Old of YAS](https://open.spotify.com/album/7oQ2HPJmaoE8PZlGDAnkgG) | LP | 2008-06-05 | 18 | requires review | not established |
| 24 | Reza Pishro | [REFIGH](https://open.spotify.com/album/55M4NLSgJ9L44cEQgMIfH5) | LP | 2026-09-26 | 11 | requires review | not established |
| 25 | Ho3ein | No qualifying LP/EP | — | — | — | no qualifying LP/EP in complete catalog | not established |
| 26 | Tohi | [REFIGH](https://open.spotify.com/album/55M4NLSgJ9L44cEQgMIfH5) | LP | 2026-09-26 | 11 | requires review | not established |
| 27 | Erfan | [The Poet's Chamber](https://open.spotify.com/album/2Fcz6pS1lB234jeHGZ4TH0) | LP | 2025-11-14 | 8 | requires review | not established |
| 28 | Amir Tataloo | [Tars](https://open.spotify.com/album/20xFt3YcYMN4hyNQ0mqvon) | EP | 2026-09-29 | 1 | requires review | not established |
| 29 | Sohrab Mj | [Magnet](https://open.spotify.com/album/63uBYgmUpGSHeojA6jkHCb) | LP | 2025-01-16 | 10 | requires review | not established |
| 30 | Mehrad Hidden | [Alavis 2](https://open.spotify.com/album/4cqDo7W3Eu6jkbLp5DD92c) | EP | 2024-08-07 | 5 | requires review | not established |
| 84 | Bahram | [HEECH](https://open.spotify.com/album/0lXvCzjiBL50iJhcEJntB6) | LP | 2025-12-20 | 11 | suggested | set needs review |
| 85 | Shahin Najafi | [Sigma](https://open.spotify.com/album/1M7ICkaPMy3kIaAuINBGKj) | LP | 2022-07-16 | 8 | suggested | not established |
| 86 | Saman Wilson | [Bozorg, Vol. 2](https://open.spotify.com/album/4a8nVbcRrtPmXQZQLioG7o) | LP | 2015-02-27 | 19 | suggested | not established |
| 87 | Alireza Jj | [LEITMOTIV](https://open.spotify.com/album/2cypAUwFLV50MzFfWtlfFb) | LP | 2024-07-18 | 14 | suggested | not established |
| 88 | Quf | [Zir o Bam e Zirzamin](https://open.spotify.com/album/0vaU6nncOdSP8Rm1XvXoKH) | LP | 2011-09-29 | 12 | suggested | not established |
| 89 | Ali Sorena | [Mojassameh](https://open.spotify.com/album/1YomRnpVLMXxzVCgs3CVl9) | LP | 2025-02-20 | 20 | suggested | set needs review |
| 90 | Sadegh | [Nashod Begam](https://open.spotify.com/album/22C1OnNz1EvwYCEmrpBPxd) | LP | 2023-09-27 | 7 | suggested | not established |
| 91 | Sogand | [Khune](https://open.spotify.com/album/35wT0eSuG97nyh4su1wXHH) | EP | 2024-04-14 | 6 | suggested | not established |
| 92 | Gdaal | [Abraye Noghrei 3](https://open.spotify.com/album/7k3kmzV0rhopPPYvf7Yw0u) | LP | 2025-05-01 | 17 | suggested | partial coverage |
| 93 | Amir Khalvat | [Man](https://open.spotify.com/album/04SiDOxnvZSgNMjHQsl5dX) | EP | 2015-02-20 | 4 | suggested | not established |
| 94 | Emad Ghavidel | No qualifying LP/EP | — | — | — | no qualifying LP/EP in complete catalog | not established |
| 95 | poobon | [Midnight](https://open.spotify.com/album/2qCN8thNCMHWvzSQ47qt3A) | EP | 2021-02-14 | 6 | suggested | not established |
| 96 | Armin Zareei | [Toure Concertam](https://open.spotify.com/album/5TMBih6ttTA4dNLBQ69MW1) | EP | 2023-03-02 | 4 | suggested | not established |
| 97 | Zakhmi | [Mehraboon](https://open.spotify.com/album/75zv6v0DISo36fh9MLE9QL) | EP | 2021-07-12 | 5 | suggested | not established |
| 98 | Sina Mafee | [Mafia](https://open.spotify.com/album/1KejPTn7hcYDiokER7IsXT) | LP | 2025-05-14 | 11 | suggested | not established |
| 99 | Catchybeatz | [Zooze](https://open.spotify.com/album/75mbHoMrkobQUe5b1RCPti) | LP | 2022-12-24 | 8 | suggested | not established |
| 100 | Hamid Sefat | No qualifying LP/EP | — | — | — | no qualifying LP/EP in complete catalog | not established |
| 101 | Ali Ardavan | No qualifying LP/EP | — | — | — | no qualifying LP/EP in complete catalog | not established |
| 102 | Bamdad | [Mantaghe 5 Pelake 8](https://open.spotify.com/album/2JnDcFfeRxCGlLPv5aWJj2) | EP | 2025-08-15 | 3 | suggested | not established |
| 103 | Dariu$h | [BROKE TKAR [2018 - 2022 LEAKS]](https://open.spotify.com/album/7k1VaG1Ak2XAVPuvNufguK) | EP | 2024-09-16 | 5 | requires review | not established |
| 104 | Parsalip | [Parvaneha](https://open.spotify.com/album/0Lm0DJTiL6H6PB8SuSP4mL) | EP | 2020-07-14 | 4 | suggested | not established |
| 105 | Putak | [Red Horn](https://open.spotify.com/album/3av4laDlNglRFGODbCadkq) | LP | 2023-08-17 | 14 | suggested | partial coverage |
| 106 | Daniyal | [Keder](https://open.spotify.com/album/1cp7ptHDRGL2uVsnx3tNTI) | EP | 2020-03-08 | 6 | suggested | not established |
| 107 | Sami Low | [Lowkey](https://open.spotify.com/album/4GsYSSLgIYkgXMSGkvcItA) | LP | 2023-08-22 | 25 | suggested | not established |
| 108 | Safir | [Kandoo](https://open.spotify.com/album/2Xy0pXSPbnqJkEZHMYpdJH) | LP | 2023-12-10 | 18 | suggested | not established |
| 109 | Eycin | [BATMAN](https://open.spotify.com/album/6vHE6SgLMBAUzupuglg3GL) | LP | 2025-01-29 | 12 | suggested | not established |
| 110 | Dalu | No qualifying LP/EP | — | — | — | no qualifying LP/EP in complete catalog | not established |
| 111 | Amir Ribar | No qualifying LP/EP | — | — | — | no qualifying LP/EP in complete catalog | not established |
| 112 | Shapur | No qualifying LP/EP | — | — | — | no qualifying LP/EP in complete catalog | not established |
| 113 | Masin | [Dmt](https://open.spotify.com/album/5SWrdCmii8VxsYwd96waDc) | EP | 2025-07-14 | 3 | suggested | not established |
| 114 | Young Sudden | [Welcome to Gambron](https://open.spotify.com/album/37BISa2SRxjs7FJX5lxWt3) | LP | 2025-01-22 | 33 | suggested | not established |
| 115 | Naaji | [STARBOY](https://open.spotify.com/album/7AkUbPht8NClY4sA78YAt8) | LP | 2026-09-28 | 8 | suggested | potential full recording |
| 116 | Ali Geramy | [G](https://open.spotify.com/album/74pfaLWuj1ZIwTMTrVrotu) | LP | 2025-09-26 | 16 | suggested | not established |
| 117 | XWHISKY | [Virus, vol. 2](https://open.spotify.com/album/7InVsgJrA6VVLJFngsWC5h) | LP | 2024-03-21 | 15 | suggested | not established |
| 118 | Ashna | No qualifying LP/EP | — | — | — | no qualifying LP/EP in complete catalog | not established |
| 119 | Arman Miladi | [Paranoia](https://open.spotify.com/album/2Vj0WnvHmn3L0nza1Efk2d) | LP | 2024-03-08 | 17 | suggested | not established |
| 120 | Saaren | No qualifying LP/EP | — | — | — | no qualifying LP/EP in complete catalog | not established |
| 121 | Heliyom | [Jangale Arezooha](https://open.spotify.com/album/22PgFvBhpQ5gr17pJgrikU) | LP | 2025-07-11 | 9 | suggested | not established |
| 122 | The Don | [Prestige](https://open.spotify.com/album/7q0vI93TCn9NcpuzFC0eOC) | EP | 2023-08-22 | 6 | suggested | not established |
| 123 | Isam | [GALLERY TALK](https://open.spotify.com/album/3pU4AWSi1ggkUCsXS2wQ6F) | EP | 2025-07-08 | 6 | suggested | not established |
| 124 | Arown | No qualifying LP/EP | — | — | — | no qualifying LP/EP in complete catalog | not established |
| 125 | Octave | [Adam Bozorga](https://open.spotify.com/album/2W1pBaKkYDUXKyd8NHtCcb) | LP | 2023-08-23 | 8 | suggested | not established |
| 126 | Maslak | [Khato Neshoun](https://open.spotify.com/album/1Osk6KhD2Hyix5VGZMLFaA) | EP | 2022-03-21 | 5 | suggested | not established |
| 127 | Shayan Yo | [6](https://open.spotify.com/album/0nSfDYxx7FWSUZwsYnY3KW) | EP | 2025-04-27 | 6 | suggested | not established |
| 128 | Parsa | [MERCURY ANGEL](https://open.spotify.com/album/0tQeLVlLahdphQDgs5V5ai) | EP | 2026-08-25 | 4 | suggested | not established |
| 129 | Nazli Mcfian | No qualifying LP/EP | — | — | — | no qualifying LP/EP in complete catalog | not established |
| 130 | Raha | [Revival](https://open.spotify.com/album/1z1UIWoOBhNLXn6MQMGMab) | LP | 2025-12-16 | 8 | suggested | not established |
| 131 | Matin Fattahi | No qualifying LP/EP | — | — | — | no qualifying LP/EP in complete catalog | not established |
| 132 | 021kid | [C4](https://open.spotify.com/album/7qyawsVb9eOJoIysyHLQ1B) | EP | 2025-02-21 | 4 | suggested | not established |
| 133 | Mehyad | [Credit](https://open.spotify.com/album/37NEdEKaw2KCPbee1cq1ua) | LP | 2025-03-11 | 8 | suggested | not established |
| 134 | Alipasha | [Siah Sefid](https://open.spotify.com/album/64jQOx8sk364oFOEIHOd75) | LP | 2026-06-17 | 18 | suggested | not established |
| 135 | Tlkhoon | No qualifying LP/EP | — | — | — | no qualifying LP/EP in complete catalog | not established |
| 136 | Pouriya Adroit | [Cheqer Mood 2](https://open.spotify.com/album/2VlSXTzPnjjQOpIfoBEdpQ) | LP | 2024-08-19 | 18 | suggested | not established |

Owner selection is the next gate. Acquisition, complete-audio validation and publication require a later authorized task. No live-release detection latency was measured.
