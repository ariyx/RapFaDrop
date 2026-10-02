# Spotify discovery feasibility — local observations, 2026-10-02

**Decision: no production Spotify release adapter selected.** Spotify remains disabled/unavailable for release polling. Public identity resolution and embedded track subsets worked, but neither repeatedly listed current artist releases with dates and bounded pagination. SoundCloud and Spotify remain **parallel first-observation sources**; neither is globally primary. Spotify is discovery/metadata only, never an audio provider.

This task started on `main` at `3ad46e0dc03ed20c773e09d460427d0d7b7bd364`. Production was not contacted, deployed or activated. The last recorded server application SHA remains `44d0c62cd59eb8701d9599ccf8aae5aadb5b46d0`; its M6 results are historical evidence, not server checks performed by this task.

## Methods, scope and limits

The opt-in `probe_spotify_discovery` command made **40 unauthenticated metadata GETs** in two rounds across five approved seed artists. Observations began `2026-10-02T18:03:23.559745+00:00` and the last request began `18:05:54.997695+00:00` (21:33:23–21:35:54 Asia/Tehran). One preliminary host-side Sijal embed GET also returned HTTP 200; it inspected only entity/track field names, not release coverage. Structured results are from local Docker Python 3.13.

```sh
docker compose exec -T web python manage.py probe_spotify_discovery --rounds 2 --timeout 12
```

Checks used an ignored local Compose override with DEBUG=false, Spotify mode `unavailable`, Telegram/publication switches false and token/chat configuration empty. The existing `.env` was retained. Worker/beat were stopped before probes; the probe has no database writes or downstream task dispatch. Five seeds were read from the existing `SEEDS` constant, without running seed import or baseline commands.

Each GET had a **12-second socket timeout**, a **1 MiB response bound**, no redirects, credentials, session/cookie jar or automatic retry. Each method had an independent **26-second overall deadline**; connect/read phases can make total HTTP latency exceed the socket timeout, as observed for Ho3ein. One second separated samples. API pagination would stop after offsets 0/5, at most two pages, without following an untrusted `next` URL. All live API calls failed on page 1. No login, browser-cookie reuse, anonymous-token extraction, internal authenticated endpoint or access-control workaround was attempted. Full page bodies, preview/audio URLs and credentials were never retained in evidence or Git.

| Method | URL shape | Observed capability / order / pagination |
| --- | --- | --- |
| Public oEmbed | `https://open.spotify.com/oembed?url=https%3A%2F%2Fopen.spotify.com%2Fartist%2F<ID>` | Artist title/identity only. No release list, date/type, chronology or pagination. |
| Public artist HTML | `https://open.spotify.com/artist/<ID>` | `og:title` identity. The bounded parser found no dated JSON-LD albums or canonical album anchors. No current-release coverage or pagination established; client-rendered data was not pursued through authenticated APIs. |
| Public artist embed HTML | `https://open.spotify.com/embed/artist/<ID>` | `__NEXT_DATA__` public artist entity and ordered `trackList` subset: ten tracks for Sijal/Fadaei/Yas/Hichkas, eight for Ho3ein when available. Stable track IDs/titles/URLs, but **no release dates or album/single types**, no release chronology and no pagination. Not a recent-release feed. Preview fields were discarded without fetching audio. |
| Official Web API, no Authorization header | `https://api.spotify.com/v1/artists/<ID>/albums?include_groups=album%2Csingle&market=US&limit=5&offset=0` | **HTTP 401 for all ten calls**. No listing, order or pagination observed. Requires unavailable authenticated access; not selected. US was an explicit test market, not a global catalog assumption. |
| Prior `spotipyFree` candidate | Existing M0 diagnostic, not rerun here | M0 timed out before recent-release evidence. Its authentication/token acquisition path is outside this task's unauthenticated-method boundary; historical timeout is not a new measured result. |

The [official artist-albums reference](https://developer.spotify.com/documentation/web-api/reference/get-an-artists-albums) describes dated album objects and offset pagination; that documented shape is fixture-tested, not a live success here. [Spotify's current quota-mode documentation](https://developer.spotify.com/documentation/web-api/concepts/quota-modes) says development-mode app owners require Premium. No developer application/client credentials or Premium account were supplied, and no authenticated API request was attempted. [Official oEmbed documentation](https://developer.spotify.com/documentation/embeds/reference/oembed) describes presentation/identity metadata; oEmbed success cannot be substituted for release discovery.

## Five-artist results

| Artist | Seed native artist ID |
| --- | --- |
| Sijal | `5F0BGBdSL945Bzxrq8aGbn` |
| Fadaei | `5aWL79DpD45MzDMwCTZqsN` |
| Ho3ein | `5vVveQB8n4kETe67waTS3t` |
| Yas | `7b8pXheEOc28fyFJnQzqmL` |
| Hichkas | `2X90kCLyxyPeJ5nynJGbvT` |

Cells show round 1 / round 2, with measured total HTTP elapsed seconds:

| Artist | oEmbed | Artist page | Artist embed | Web API without auth |
| --- | --- | --- | --- | --- |
| Sijal | 200 (0.870 s) / 200 (0.760 s) | 200 (1.744 s) / 200 (1.013 s) | 200 (1.016 s) / 200 (2.501 s) | 401 (0.700 s) / 401 (0.558 s) |
| Fadaei | 200 (2.398 s) / 200 (1.298 s) | 200 (1.306 s) / 200 (11.123 s) | 200 (2.569 s) / 200 (1.053 s) | 401 (0.645 s) / 401 (2.090 s) |
| Ho3ein | 200 (1.415 s) / 200 (4.657 s) | 200 (5.329 s) / 200 (23.511 s) | 200 (0.850 s) / 200 (1.243 s) | 401 (0.546 s) / 401 (0.669 s) |
| Yas | 200 (1.659 s) / timeout (12.024 s) | 200 (7.646 s) / network unavailable (4.009 s) | 200 (1.844 s) / network unavailable (4.010 s) | 401 (0.471 s) / 401 (0.711 s) |
| Hichkas | 200 (0.792 s) / 200 (3.064 s) | 200 (1.798 s) / 200 (1.603 s) | 200 (1.036 s) / 200 (0.910 s) | 401 (0.904 s) / 401 (0.569 s) |

All native item IDs, titles, object types, canonical URLs, date/type nulls, request times, HTTP/error results, page count/order and latency are retained in [`SPOTIFY_DISCOVERY_EVIDENCE.json`](SPOTIFY_DISCOVERY_EVIDENCE.json). Every returned item is a track object, not a proven new album/single. The four repeatable embeds preserved the same IDs and order across rounds; Yas's failed second sample does not establish repeatability. No sampled method exposed a dated recent release, so no recent-release latency or new-release coverage claim is possible. For example, Sijal's first embedded track was `4shGMwLxYjEHaGqoGgbpw5` / **Fogholade**, with date/type absent; that rank is not evidence it was the newest release.

No HTTP 403/429 or numeric rate-limit/Retry-After headers were observed. 401 was an authentication failure, not rate limiting. Yas's safe network error does not distinguish DNS/TLS/connection causes. Two rounds do not establish sustained reliability or a safe polling interval.

## Implemented safeguards and local verification

- `RAPFADROP_SPOTIFY_DISCOVERY_MODE=unavailable` is documented in `.env.example`. Unknown modes also fail closed. No source flags or verification are inferred from an opened page; the production `SpotifyAdapter` never calls the experimental probe.
- Unavailable status is visible on the operator dashboard, Django source admin, `source_status` output and application startup/poll logs. An accidentally eligible Spotify row records per-source unavailable/error audits and exponential backoff without blocking SoundCloud. No adapter is silently promoted after identity success.
- Beat includes publication recovery only when publication worker and Telegram live switches are enabled and mode is test/production. The regression uses the **real lazy-loaded Celery app**, a persisted stale publication entry and a due scheduler tick; disabled publication removes the stale entry and dispatches only source polling.
- Fixture/fake tests cover identity-only oEmbed, embed ID validation/order/absent dates, public JSON-LD dates, API IDs/date precision, bounded pagination/overlap deduplication/untrusted next URLs, malformed data, 403/429/Retry-After, timeout/byte limits, unsupported configuration and SoundCloud/Spotify backoff isolation. No network or Telegram sends are part of the test suite.
- Final local Docker build passed; collectstatic copied 127 files and post-processed 381. All five Compose services became healthy. Migrations had **nothing to apply**, migration drift found **no changes**, Django check found **0 issues**, and **all 106 tests passed in 22.073 seconds**. `/health/` returned HTTP 200/database `ok`; admin CSS returned HTTP 200 with DEBUG=false.
- Live disabled-publication smoke check observed a beat polling dispatch and worker result `{}` with all sources disabled, **no publication dispatch**, and an empty default broker queue. All application-model row/count fingerprints were unchanged before/after probes, tests and local worker/beat checks. Local pre-existing development data was preserved: **31 artists, 58 sources, 9 SourceItems, 0 baselines**, 18 media candidates/attempts, 18 publication records/45 attempts and 0 processing queue items. These are existing local records, not server seed counts or work created by this task. All artist/source enabled flags remained false.
- No source activation/verification, baseline, media/publication enqueue, audio request or Telegram API call occurred outside isolated fixture tests. Production was not contacted. Local services were stopped with `down`, preserving named database/media volumes. Git whitespace and staged credential/media scans passed before delivery.

## Next action

Keep Spotify unavailable and all production source flags unchanged. A future task needs an owner-approved, available access method that repeatedly returns artist release IDs, dates/types, complete bounded pagination and observed failure/429 behavior under the no-Premium constraint. Public top-track subsets cannot satisfy this gate. If no such access exists, record that limitation rather than switching SoundCloud into a globally primary discovery role. Stop after local commit/push; this change is **not deployed**.
