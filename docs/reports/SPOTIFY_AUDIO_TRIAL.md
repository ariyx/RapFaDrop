# Isolated Spotify audio feasibility trial

Observed on the server on **2026-10-05**, ending **09:35:48Z / 13:05:48 Tehran**.
Application stayed at `452c6196fbda4f96f6b9d6624e17ea1c677a5643`;
repository started at documentation commit `8143aca0c1c191dc0043a7acf9b0af6b1a3da626`.
Caption and collection services were inactive before and after this trial.
No production deployment, DB write, Telegram call or music resumption occurred.
[Safe measurements and preservation evidence](data/spotify_audio_trial.json).

## Pins and permitted paths

| Candidate | Version | Exact upstream commit |
| --- | --- | --- |
| Zotify | 0.6.14 | `08d844fe3e644ae6cd9bea34a3b4982e61129f33` |
| Votify | 1.9.9 | `db14e4d1aa01456e0ec3b55d6f7268787ba2e2c4` |
| musicdl | 2.14.0 | `e5c3bd51b518642c24027921e63f482865809b61` |
| librespot-python source inspected | 0.0.10 | `683d9e76f91ba7ae03919494dac8d899ca505651` |

Pinned source inspection established these gates:

- [Zotify's audio entry](https://github.com/zotify-dev/zotify/blob/08d844fe3e644ae6cd9bea34a3b4982e61129f33/zotify/zotify.py)
  loads a librespot Vorbis content stream. Its
  [dependency's song path](https://github.com/kokarare1212/librespot-python/blob/683d9e76f91ba7ae03919494dac8d899ca505651/librespot/audio/__init__.py)
  obtains a track audio key and applies `AesAudioDecrypt` to protected CDN data.
- [Votify's song processing](https://github.com/glomatico/votify/blob/db14e4d1aa01456e0ec3b55d6f7268787ba2e2c4/votify/interface/song.py)
  obtains a decryption key before downloading. Its
  [Vorbis path](https://github.com/glomatico/votify/blob/db14e4d1aa01456e0ec3b55d6f7268787ba2e2c4/votify/interface/audio.py)
  uses the same librespot audio-key machinery, then applies AES decryption.
  AAC/FLAC paths require Widevine device material or desktop decryption machinery.

These are technical code-path findings, not observed entitlement failures or a
claim that a legitimate account cannot play these recordings. Under the owner's
explicit no-DRM-bypass boundary, extracting clear files through these protected
audio key/decryption paths was stopped before authentication or acquisition.
No device keys, stream keys or access-control patches were obtained or used.
Their librespot paths would not be independent fallbacks.

The [musicdl Spotify client](https://github.com/CharlesPikachu/musicdl/blob/e5c3bd51b518642c24027921e63f482865809b61/musicdl/modules/sources/spotify.py)
contains multiple third-party parsers. Only `_parsewithmusicfabapi` and
`_parsewithspotsaverapi` were selected. RapidAPI's embedded shared credential path
was excluded. Spotube, licensing/fingerprint flows, signature flows and all other
fallbacks were left unexecuted. No embedded key or owner account credential was
used. Spotsaver explicitly maps Spotify title/artist to `videoId`/`candidateIds`
and requests MP3 from an intermediary; it is a video-match acquisition path.
MusicFab's response likewise does not establish direct Spotify origin.

## Authentication and quality

A filename/schema-only inspection of `/root`, `/home`, the protected operations
directory and the server checkout found no suitable saved Spotify credentials or
Netscape Spotify session cookie file. Values were not printed. Account tier is
**unknown**, not assumed Free or Premium; no login or purchase was attempted.
Zotify supports a stored librespot credential file or private terminal
username/password prompt; Votify requires owner-owned Netscape Spotify cookies
containing `sp_dc`, then initializes its session. These are authentication
prerequisites, not download failures. Login instructions were not requested from
the owner because authentication alone would not remove the prohibited audio
path dependency. Any future authorized account material must stay outside Git
in a private directory (0700), with files 0600, and never be pasted into chat.

Upstream describes Vorbis 160 kb/s versus Premium-only Vorbis 320 kb/s; that
claim was not empirically verified for an account here. No Free-account 320
promise is made. MP3 output at 320 kb/s would not demonstrate native Spotify
MP3, native source quality, or a quality upgrade. Native source formats/quality
for the downloaded intermediary files remain **unknown**. No local conversion
or upsampling was performed; intermediary conversion parameters were unavailable.

## Same-track comparison

The three comparison IDs were read from the frozen production collection,
without changing selection: one previously acquired post and two pending tracks
with different credited artists. No validated edition/variant relationship was
invented. Expected versions are the precise selected Spotify IDs/albums below.

| Artist — recording (album) | Spotify track ID | Expected seconds | Zotify / Votify | musicdl selected paths |
| --- | --- | ---: | --- | --- |
| HesamTiem, Tiem — West SidE (Ay) | `0IrFAuYmzjMY3pwEwifk7S` | 187.800 | Not attempted: common protected-audio gate, no session | MusicFab CDN timeout; Spotsaver complete-duration MP3, identity unverified |
| poobon, Mamazi — YND (YND) | `0nOTYCGtkJttIajOpwniMr` | 137.579 | Same precondition; no repeated attempts | MusicFab skipped after shared timeout; Spotsaver complete-duration MP3, identity unverified |
| Sajad Shahi, Ashkan Kagan — Khastam (Khastam) | `3QmYSZE5mYQTSklmQhh4cA` | 199.171 | Same precondition; no repeated attempts | MusicFab skipped after shared timeout; Spotsaver complete-duration MP3, identity unverified |
| Freshness: Amin Tijay, Lil Deafo, !Leo, Neemski — Yadegarit (Pellezterari) | `3yhTL64et9hrK0JjN5r811` | 193.170 | Outside original three-track attempt set | MusicFab skipped; Spotsaver **rejected: duration mismatch** |

The freshness sample's release date is 2026-10-05; ordinary production discovery
observed its album at 08:32:20Z. This provider trial is neither a measurement of
live release-detection latency nor evidence that the intermediary has that
fresh recording: its file was substantially shorter.

## Observed files and timings

All four files were measured by ffprobe and decoded completely with
`ffmpeg -v error -xerror -map 0:a:0 -f null -`. All decoded without error.
All were MP3 container/codec, measured **320,000 bit/s**, **44,100 Hz**, **stereo**.
Spotsaver's client request selects MP3 format, without an explicit bitrate.

| Recording | Actual seconds | Bytes | Acquisition + inspection seconds | Duration assessment |
| --- | ---: | ---: | ---: | --- |
| West SidE | 188.107750 | 7,524,310 | 13.176 | Compatible (+0.308 s); exact version not established |
| YND | 137.717550 | 5,508,702 | 4.384 | Compatible (+0.139 s); exact version not established |
| Khastam | 198.791825 | 7,951,673 | 9.692 | Compatible (−0.379 s); exact version not established |
| Yadegarit | 158.119175 | 6,324,767 | 4.224 | Reject: −35.051 s, only 81.9% of expected duration |

The timings include provider requests, download, ffprobe and full decode; they
are not download-only timings. Per-request timings and file hashes are in JSON.
Provider title/artist/album matched the Spotify metadata supplied by the service;
the files had no title/artist/album tags. That metadata and compatible duration
do **not** independently verify the original video, recording or version.
Direct Spotify provenance is unproven for every downloaded file.

MusicFab returned HTTP 200 metadata (397 bytes), then the GET from
`cdn-spotify.zm.io.vn` hit a read timeout; **12.510 seconds**, two requests.
No further tracks were attempted on that provider. Spotsaver returned files
through `yt1s-worker-4/5.dlsrv.online`, including public GET redirects.
An initial redirect-limited attempt stopped before audio; after inspecting the
path, the harness allowed public HTTPS GET redirects within the same budget.
Four final samples used **five requests each**.

A metadata-only identity follow-up omitted the upstream browser headers and
returned four HTTP 403 responses. It supplied no independent video evidence and
is not a finding that the working download endpoint is unavailable. This helper
should have stopped after its first shared failure; no further retry was made.
Total provider HTTP calls: **30** (2 MusicFab, 4 initial Spotsaver, 20 final
Spotsaver, 4 metadata follow-up). Spotify login/audio calls: **zero**.

## Isolation, checks and cleanup

Server preflight had 12 GiB free disk and about 836 MiB available memory. Disposable
containers reused the existing immutable Python/tool image
`sha256:7231b4307b19a628850312348d3a6465d909f0fc9747ebabaa89524fba4ce0c5`;
the application was not rebuilt or executed for acquisition. The pinned selected
musicdl functions were AST-extracted into a small harness, with only response
packaging helpers supplied locally. This tests those exact provider methods,
not installation of musicdl's complete CLI or its default fallback chain.
Requests was 2.34.2. Containers had read-only source/root filesystem, no production
credentials or DB/Redis/media volume, no capabilities, 0.5 CPU, 384 MiB RAM,
64 PIDs and a 32 MiB tmpfs. No dependencies were installed.

The initial Docker bridge preflight could not resolve hosts because server IPv4
forwarding is disabled; no provider HTTP call was made in that run. Acquisition
used host networking with HTTPS/public-address validation, denying private
addresses and the production public IP. No firewall/runtime setting changed.
Limits were 60 seconds and six requests per sample, 5-second connect/10-second
read timeouts, 25 MB audio/1 MB metadata responses. Only provider-returned URLs
were fetched; no authentication/entitlement or DRM bypass was attempted.

Before/after read-only checks matched: paused collection, 83 active verified
Spotify sources, 84 baselines, 155 frozen rows/166 slots, 41 publications,
105 publication attempts, 201 media candidates, 51 media attempts and zero
downstream jobs. Bridge/publication worker/live Telegram stayed OFF, Telegram
mode disabled, services inactive and production health/database OK.
No main application suite was rerun for this isolated report-only task.

After evidence recording, all **four media files / 27,309,452 bytes** and the four
source checkouts were removed. Both disposable containers exited and were
removed. No trial credentials were created. Only safe audit JSON/logs remain in
the private trial directory; production media, music posts and backup messages
were untouched. No cleanup blocker remains.

## Decision

**None qualifies for a direct Spotify adapter pilot under the current boundary.**
Zotify/Votify were stopped at documented authentication/protected-audio gates,
not measured failed downloads. MusicFab did not deliver a file. Spotsaver
delivered three duration-compatible files and one rejected freshness sample,
through a video-match intermediary with unknown native quality and unresolved
recording/version provenance. It must not be labelled direct Spotify, native
320 kb/s or ready to publish. An intermediary pilot would first require an
independently verified source recording/video binding and enforced rejection of
mismatched candidates; this trial does not recommend production integration.
Stop before integration, bulk acquisition or publication.
