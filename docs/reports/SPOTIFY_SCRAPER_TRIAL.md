# SpotifyScraper trial — 2026-10-03

**Decision: reject the package for this project's public discovery adapter.** Keep `RAPFADROP_SPOTIFY_DISCOVERY_MODE=unavailable`; do not add a runtime dependency or a selectable adapter. The package's discography method crosses the task's explicit private-endpoint boundary, and its returned release references omit dates and types. No source was enabled, baselined, or polled by this trial. No media, queue, publication, Telegram, or deployment work was performed.

## Package and method audit

I inspected the published `spotifyscraper` **3.9.2** wheel from [PyPI](https://pypi.org/project/spotifyscraper/3.9.2/) (Python requirement `>=3.10`, compatible with the project's Python 3.13; core dependency `httpx>=0.27,<1.0`). That exact version is pinned in `requirements-spotify-scraper-trial.txt` for reproducible offline inspection, outside the application's installed requirements. The wheel was held only in ignored `tmp/spotify-trial/` for inspection. No package code was copied into the project and no dependency was added to `requirements.txt`.

The documented `SpotifyClient.get_discography(artist, max_releases=...)` loops over pages of 50 and calls `_anon_union("artist_discography", ...)`. `_anon_union` obtains a bearer token from a public embed and then `_anon_request` sends it to `https://api-partner.spotify.com/pathfinder/v1/query` using Spotify's internal persisted GraphQL operation `queryArtistDiscographyAll`. This is a private endpoint under the trial's rule, even though the package calls the token anonymous. Calling it would violate the task, so **no live `get_discography` request was made**. `get_artist` also attempts the same Pathfinder tier for richer metadata. The package's discography parser flattens `discography.all.items[].releases.items[]` into `AlbumRef(id, uri, name, images)`. `AlbumRef` has no release date, date precision, or release type. An `AlbumRef` cannot establish which release is new versus historical, or whether it is an album, single, or EP. Calling `get_album` per item would still depend on the prohibited path and would add unbounded work to a full discography scan. The package's advertised pagination and ordering were therefore inspected in code, **not observed from Spotify**.

This audit is a stopping gate before network probing. There is no responsible public-only way to exercise the package's discography function for five artists. The earlier [public Spotify discovery report](SPOTIFY_DISCOVERY.md) remains the only live Spotify evidence; it found identity and undated track subsets, not a usable release feed. This trial does not reclassify those tracks as releases.

## Five seeded artist probe plan and observed result

These are the five exact seed IDs selected for the trial. Sijal, Fadaei and Ho3ein are required; Yas and Hichkas give different observed embed subset sizes in the previous public trial. The same package gate applies before artist-specific I/O, so each result below is an **unexecuted package probe**, not an empty discography or a network failure.

| Artist | Native artist ID | Returned release IDs/title/type/date/precision/URL | Pagination/order | Package requests | Latency | Failure |
| --- | --- | --- | --- | ---: | --- | --- |
| Sijal | `5F0BGBdSL945Bzxrq8aGbn` | Unobserved | Unobserved | 0 | Not measured | Private Pathfinder endpoint required |
| Fadaei | `5aWL79DpD45MzDMwCTZqsN` | Unobserved | Unobserved | 0 | Not measured | Same preflight gate |
| Ho3ein | `5vVveQB8n4kETe67waTS3t` | Unobserved | Unobserved | 0 | Not measured | Same preflight gate |
| Yas | `7b8pXheEOc28fyFJnQzqmL` | Unobserved | Unobserved | 0 | Not measured | Same preflight gate |
| Hichkas | `2X90kCLyxyPeJ5nynJGbvT` | Unobserved | Unobserved | 0 | Not measured | Same preflight gate |

Repeated probes, ID/order stability, request latency, 403/429/timeout behavior, and actual pagination cannot be measured under this boundary. Package source inspection shows a finite `max_releases` return cap, but its pagination still fetches a complete 50-item page before truncation. This is a code property, not a live performance observation. No credentials, Premium account, cookies, proxy, login, or workaround were used.

## Contract and acceptance decision

The existing `SpotifyAdapter.list_recent` continues to raise `SourceUnavailable`, and the service's Spotify branch records source-specific backoff without calling a provider. There is no `SourceItem` mapping because no permitted live release fields were observed. Neither dates nor types are inferred from `AlbumRef` names, grouping, or order. No trial data was ingested. In particular, the required tests for mapping, pagination, partial payloads, package HTTP failures and idempotent ingestion would test an adapter that is ineligible and was not built. Existing fake-backed source isolation, disabled-source and publication scheduling tests remain the relevant executable guards.

The candidate fails two independent acceptance gates: permitted public-only access and enough release date/type data. Stable IDs, current release coverage, pagination, and error handling remain **unverified**, not passed. A later task needs a permitted method that exposes dated typed releases with stable IDs and bounded pagination before a controlled pilot can be proposed.

## Local verification

The wheel's published metadata and implementation were inspected without executing package network code. The host `pip download` path failed DNS resolution for `files.pythonhosted.org`; direct PyPI JSON metadata and the wheel URL were accessible through PowerShell. Docker Desktop's Linux engine was initially stopped, then started for local verification. `docker compose config --quiet` and `docker compose up --build -d` passed. Migrations had nothing to apply; migration drift reported no changes; Django check found zero issues; all **106 tests passed in 24.336 seconds**. `/health/` returned HTTP 200 with database `ok`. All five Compose services became healthy with a local ignored override that forced publication and Telegram switches off for worker/beat. The worker's beat schedule contained only `poll-due-artist-sources`. Local readback showed 31 artists, 58 sources, **zero enabled artists and sources**, 9 pre-existing SourceItems and zero baselines. The Compose stack was stopped with `down`, preserving volumes. Git whitespace and staged-file secret/media checks were performed before delivery. No server access was attempted.
