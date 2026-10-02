# M0 feasibility report

Observed locally on 2026-10-02 UTC. All probes were read-only and opt-in. No Telegram API call or channel post was made. Commands ran in the Compose `web` container. The local network required an uncommitted host proxy mapping; results below contain no proxy value, signed media URL, cookie, token, or downloaded file.

## SoundCloud metadata: verified

Tool: `yt-dlp 2026.08.19`.

- Track URL `https://soundcloud.com/sijalofficial/vaghti-raft`: native ID `2368809320`, title `Vaghti Raft`, owner `Sijal` / owner ID `801842584`, duration `176.046` seconds, source upload timestamp/date `1785167514` / `2026-07-27`. The extractor returned no distinct source release timestamp/date. Probe and first-observed time: `2026-10-02T10:16:29.601815+00:00`. Metadata-only elapsed time: `4.309` seconds.
- Available track variants: HTTP and HLS MP3 at a reported 128 kbps; HLS AAC at reported 96 and 160 kbps. Signed URLs were intentionally omitted.
- Set URL `https://soundcloud.com/sijalofficial/sets/ocd`: native ID `2147740733`, title `OCD`, owner `Sijal`, nine tracks. The extractor explicitly reported `album=OCD` and `album_type=album`, so the probe classified it as an LP from source-explicit evidence. Set-level upload/release timestamps were unavailable. Probe and first-observed time: `2026-10-02T10:16:33.911111+00:00`. Elapsed time: `13.290` seconds.
- Original order was: (1) `Hichki Mese Man` `2218317692`; (2) `2 Ace (with Catchybeatz)` `2218317698`; (3) `Dele Man (with Heliyom)` `2208102152`; (4) `Bekhatere To (with Heliyom)` `2218317701`; (5) `Kabol (with Maslak & Darab)` `2218317704`; (6) `Seda (with Milanium & AHU)` `2218317707`; (7) `Eshghe Alaki (with Sohrab Mj & Heliyom)` `2155209837`; (8) `Greece (with Heliyom)` `2218317710`; (9) `Azadi (with Milanium)` `2218317695`.
- Tracks 1, 2, 4, 5, 6, 8, and 9 reported upload date `2025-11-24` and release date `2025-11-28`. Track 3 reported upload `2025-11-06` and release `2025-11-12`; track 7 reported upload `2025-08-18` and release `2025-08-22`. Every set item exposed the same four reported MP3/AAC variant classes as the supplied track.

These observations prove access to the two supplied examples, not polling reliability for all allowlisted profiles.

## Spotify public metadata: partially verified

Profiles: Sijal `5F0BGBdSL945Bzxrq8aGbn`, Fadaei `5aWL79DpD45MzDMwCTZqsN`, and Ho3ein `5vVveQB8n4kETe67waTS3t`. Fadaei and Ho3ein have no confirmed SoundCloud profile in the seed data.

- `spotipyFree 1.9.14` initially had an undeclared `websockets` runtime dependency; pinning `websockets 17.1` made the adapter importable.
- On all three profiles, the adapter's artist/release path exceeded the explicit five-second operation timeout. This method did not return recent release IDs, types, dates, pagination, rate-limit headers, or errors from Spotify itself.
- Spotify's public oEmbed endpoint returned HTTP 200 without login or Premium and confirmed the three native IDs and display names `Sijal`, `Fadaei`, and `Ho3ein`. Per-profile total elapsed times in the first successful pass were `6.398`, `6.403`, and `6.249` seconds. No rate-limit headers were present. In the final three-profile rerun, Fadaei's oEmbed fallback also exceeded the five-second bound while the other two succeeded; a separate ten-second rerun returned Fadaei in `10.789` seconds. This is observed latency instability, not reliable polling.
- oEmbed exposes profile identity but no recent-release list or pagination. Spotify full audio was not requested or obtained. Therefore a no-Premium monitoring adapter is not verified, and no conclusion is drawn about all 30 profiles.

## Media acquisition: verified for one candidate

`yt-dlp 2026.08.19` downloaded `Vaghti Raft` into an OS temporary directory and `ffprobe 7.1.5` inspected the completed file. Observed native ID `2368809320`; AAC audio, 44,100 Hz, stereo, stream bit rate `160016` bps; container duration `176.053696` seconds, size `3552597` bytes, overall bit rate `161432` bps. The final rerun took `15.244` seconds and reproduced the same media measurements. Temporary storage was deleted when each command returned.

This verifies one candidate acquisition, not authorization or availability for every release. No independent second provider was tested, so M0 names no working fallback.

## Infrastructure and environment

`docker compose config --quiet`, image builds, `docker compose up --build -d`, Django migrations/checks/tests, the database-backed HTTP health response, and health checks for all five services passed locally. The focused suite contained eight tests after the final probe timeout/fallback cases were added. Docker's default DNS could not resolve Python package hosts on this workstation; builds succeeded through the owner's already-running local proxy using command-line build arguments only. No proxy configuration was committed.
