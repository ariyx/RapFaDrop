# RapFaDrop — product specification

Status: **implementation baseline for M0; later milestones remain subject to empirical checks and owner changes.**
Date: 2026-10-01.  
Implementation companion: [`IMPLEMENTATION.md`](IMPLEMENTATION.md).

## 1. Goal and boundaries

Monitor new Persian-language rap releases from an owner-managed artist allowlist and publish complete playable audio to the Telegram channel `@RapFaDrop`. Preserve official titles, artist names and artwork, apply configurable channel metadata to the file, and link to the release's SoundCloud/Spotify pages in the caption. The channel is an archive for the owner's personal interest and uses a public username. Multiple admins have separate accounts with the same access level. The panel is for administration, not a public user product.

The initial new-release channel must not automatically backfill historical tracks. A future second archive channel is possible. Model each canonical work and each channel publication separately so a future backfill cannot block current releases. The owner's decision is to publish the audio files; this technical document does not infer a separate licensing status.

## 2. Artist allowlist and source profiles

The owner approved the following **30 artists** as the initial list. Profile links are seed candidates found from public pages; verify profile identity and recent official works at activation. Do not silently replace a missing source with a fan account. The allowlist grows through the panel. Store official display name, aliases, native profile IDs, profile URLs, verification state, enabled state, timestamps and audit history.

| Artist | Spotify | SoundCloud |
| --- | --- | --- |
| Hossein Tiem (حسین تی‌ام) | [Tiem](https://open.spotify.com/artist/2ZgLpNVB2qQTifvz3l8xIY) | [justiem](https://soundcloud.com/justiem) |
| Hesam Tiem (حسام تی‌ام) | [HesamTiem](https://open.spotify.com/artist/6XsyaCX2jJLaS82vJoiiWi) | [hesamtiem](https://soundcloud.com/hesamtiem) |
| Amin Tijay (امین تیجی) | [Amin Tijay](https://open.spotify.com/artist/3JS9sHeI06RtolBR5s5O0L) | [amintijayy](https://soundcloud.com/amintijayy) |
| Mamazi (ممزی) | [Mamazi](https://open.spotify.com/artist/4L42EENVSu2ZE8cwhVVeh8) | [mamazioma](https://soundcloud.com/mamazioma) |
| Sajad Shahi (سجاد شاهی) | [Sajad Shahi](https://open.spotify.com/artist/3VzZOmXc8pZRfNxoiliE1A) | [sajadshahi](https://soundcloud.com/sajadshahi) |
| Sinazza (سیناتزا) | [Sinazza](https://open.spotify.com/artist/2su0Z5gmtSRUreY11ocP8M) | [sinazza](https://soundcloud.com/sinazza) |
| Hoomaan (هومان) | [Hoomaan](https://open.spotify.com/artist/6UJS43T8NPhmWmmpFY0hzP) | [hoomaanxx](https://soundcloud.com/hoomaanxx) |
| Vinak (ویناک) | [Vinak](https://open.spotify.com/artist/1sKlyO3CCEvjeTN6Uck39S) | [elvinako](https://soundcloud.com/elvinako) |
| Dorcci (دورچی) | [Dorcci](https://open.spotify.com/artist/6jj9lOTeZC28LkPoXK9hiT) | [dorcci](https://soundcloud.com/dorcci) |
| Hiphopologist (هیپ‌هاپولوژیست) | [Hiphopologist](https://open.spotify.com/artist/45YMrIBH74j8e2wNlRSSdK) | [hiphopologistsoroush](https://soundcloud.com/hiphopologistsoroush) |
| Chvrsi (چرسی) | [Chvrsi](https://open.spotify.com/artist/7Hj58arwOvp6exTny9r5Ie) | [chvrsi](https://soundcloud.com/chvrsi) |
| Poori (پوری) | [Poori](https://open.spotify.com/artist/5uEEhLt2ETeApnvs40MOxk) | [godpoori](https://soundcloud.com/godpoori) |
| Arta (آرتا) | [Arta](https://open.spotify.com/artist/6gPKjPIXbBBnuLyLEq79Sz) | [arta-mir](https://soundcloud.com/arta-mir) |
| Koorosh Wantons (کوروش وانتونز) | [Koorosh](https://open.spotify.com/artist/1UjD9VWeqDDlDSvNlnFTdl) | [koorowsh420](https://soundcloud.com/koorowsh420) |
| Canis (کنیس) | [Canis](https://open.spotify.com/artist/6OPdGHW0QD6WknWX2tlzJm) | [icanisofficial](https://soundcloud.com/icanisofficial) |
| Sijal (سیجل) | [Sijal](https://open.spotify.com/artist/5F0BGBdSL945Bzxrq8aGbn) | [sijalofficial](https://soundcloud.com/sijalofficial) |
| Behzad Leito (بهزاد لیتو) | [Behzad Leito](https://open.spotify.com/artist/4zNEj5bkHE0kNSpfIwgdvu) | [bezilei](https://soundcloud.com/bezilei) |
| Sepehr Khalse (سپهر خلسه) | [Sepehr Khalse](https://open.spotify.com/artist/2SFwcduI9cdZsG6UxnBm3C) | [Khal3music](https://soundcloud.com/Khal3music) |
| Shayea (شایع) | [Shayea](https://open.spotify.com/artist/3QNGoF6VzVNnkpjJDT3NHq) | [shayeaofficial](https://soundcloud.com/shayeaofficial) |
| Fadaei (فدایی) | [Fadaei](https://open.spotify.com/artist/5aWL79DpD45MzDMwCTZqsN) | Unconfirmed; [Mahdyar](https://soundcloud.com/mahdyar) is a supplementary collaborator source, not Fadaei's profile |
| Sina Sae (سینا ساعی) | [Sina Sae](https://open.spotify.com/artist/5er043agmHdVZkWTxL0Lpk) | [sinasae](https://soundcloud.com/sinasae) |
| Hichkas (هیچ‌کس) | [Hichkas](https://open.spotify.com/artist/2X90kCLyxyPeJ5nynJGbvT) | [hichkasofficial](https://soundcloud.com/hichkasofficial) |
| Yas (یاس) | [Yas](https://open.spotify.com/artist/7b8pXheEOc28fyFJnQzqmL) | [yastunes](https://soundcloud.com/yastunes) |
| Reza Pishro (رضا پیشرو) | [Reza Pishro](https://open.spotify.com/artist/0u4qrFczDmAsJesHPgbnru) | [pishromusic](https://soundcloud.com/pishromusic) |
| Ho3ein (حصین) | [Ho3ein](https://open.spotify.com/artist/5vVveQB8n4kETe67waTS3t) | Unconfirmed |
| Tohi (حسین تهی) | [Tohi](https://open.spotify.com/artist/7pBXdJN9S9N9nNifjPixET) | [tohi](https://soundcloud.com/tohi) |
| Erfan (عرفان) | [Erfan](https://open.spotify.com/artist/1yPzb9mqugowOfUs2vIOgL) | [erfanpaydar](https://soundcloud.com/erfanpaydar) |
| Amir Tataloo (امیر تتلو) | [Amir Tataloo](https://open.spotify.com/artist/5CEosSs2y4M9THNGI6mej8) | Unconfirmed |
| Sohrab Mj (سهراب ام‌جی) | [Sohrab Mj](https://open.spotify.com/artist/2B4DnBz9uzJN5nPgLEHCt7) | [mjsohrab](https://soundcloud.com/mjsohrab) |
| Mehrad Hidden (مهراد هیدن) | [Mehrad Hidden](https://open.spotify.com/artist/0jCVTRvQkILbJvpviTpvd1) | [mehradhiddenofficial](https://soundcloud.com/mehradhiddenofficial) |

For Fadaei, Ho3ein and Amir Tataloo, poll the verified Spotify profile independently while SoundCloud remains blank. A name without an authenticated source remains incomplete. On first activation of any artist, snapshot existing release IDs, dates, types and track/album membership for deduplication and a future archive; do not auto-post these historical items. Record a baseline and activation time separately so late discovery of old material does not look like a new release.

## 3. Discovery, acquisition and speed

- Independently poll SoundCloud and Spotify for the allowlist. YouTube/YouTube Music can help find a corresponding full recording or an official video link; they are not initially a separate artist-release feed.
- The owner has no Spotify Premium. Use an interchangeable experimental adapter for public Spotify metadata. The current spotDL/SpotipyFree path is a candidate only; actual artist/release coverage and stability must be tested. Spotify does not supply the full audio file in this design. Spotify failures do not stop SoundCloud polling.
- Use interchangeable media providers. Start by testing `yt-dlp` on SoundCloud and suitable YouTube sources. A wrapper that relies on the same extractor is not an independent backup. Choose another provider only after testing an actually independent failure path.
- If the full file cannot be found or every downloader fails, leave the release queued, retry with increasing delays and notify an admin. The admin may upload a correct complete file in the panel; run it through the same verification, cover, tag and publication flow. Never publish a post without audio or substitute a short preview.
- Prioritize speed: independent source polling, immediate processing on discovery, parallel album-file preparation, and an exclusive album publication block only during its sequential Telegram sends. Initial polling hypotheses are SoundCloud every ~1–2 minutes and Spotify every ~2–5 minutes, adapted to 30 artists, rate limits and measured results. Respect per-source backoff and any `Retry-After` response. Measure discovery, preparation, upload and end-to-end delays separately. No guaranteed latency is asserted before real tests.

## 4. Release behavior

### Singles and album membership

Publish an independent track when it is released and its identity and complete file are verified. If it later appears on an LP/EP, do not reupload that same recording as an album track. Instead, link the earlier channel post by track name in the album introduction. After posting the introduction, edit the earlier single's caption to add its `Album` link and keep its `DROP` header. Match native IDs across platforms, official artists/title, duration and release relationships; send an uncertain match for admin review.

### LPs and EPs

Post the official cover and introduction first, followed by each previously unposted track as its own audio message in the collection's original order. Do not reply the album tracks to the introduction. If a SoundCloud set could be an ordinary playlist, hold only the album introduction for type review; unrelated singles continue. Clear Spotify metadata or official description may establish the type.

**Before posting the album introduction**, acquire, verify and tag every track that still needs publication, with available official cover and channel metadata. Use the best real quality available at that point; the same Telegram message can later be upgraded to a genuinely better file. While preparing the album, other releases can publish. During the actual cover-and-tracks send sequence, newer releases wait while discovery and preparation continue.

If Telegram fails after tracks 1 and 2 while uploading track 3, retry track 3 and alert an admin. If still unresolved after **15 minutes**, release the general publication queue, preserve the album cursor and resume from track 3 later. This exception may break the album's visual continuity. Never resend already confirmed tracks.

A track officially added/released after the album introduction is posted becomes a new track post with a link to that introduction. Do not rewrite the old introduction solely for the addition; changes to album track order do not change posted message order.

### Provisional files, upgrades and editions

A verified independent single may be published immediately with complete playable audio, correct official title and artist, even when internal tags/quality still need improvement. Never send an incorrect match, truncated file or preview. Album-track publication follows the stricter pre-tagging rule above. Transcoding a low-quality source to a higher nominal bit rate does not improve quality. Test whether simple tagging is fast enough to avoid provisional uploads in normal operation.

When a truly better or correctly tagged file becomes available, replace audio in the **same Telegram message** using a tested media edit. A change to tags within the file requires another file upload. Send a correction reply to that message, then delete the reply after a panel-configurable default of **10 minutes**. Preserve the original message ID and URL; previously downloaded/forwarded copies are not updated automatically.

Post an official distinct instrumental, deluxe or rerelease as a version if its audio is genuinely different. Preserve its official title. If the original was posted, link `Original` in a track caption or `Original Album` in the edition's album introduction. Do not post an identical audio version twice; review uncertain comparisons. A newly found official music video or platform URL is added later by editing the existing caption. Source deletion/renaming does not automatically delete channel posts; the panel permits manual correction.

## 5. Approved caption defaults

Template order, literal text, optional rows and metadata settings are editable with variables and a rendered preview in the panel. Hide a row or block when its data is absent. Render link labels as clickable Telegram links, not bare URLs. The channel's visible name is `RapFaDrop` and audio title/artist appear in Telegram's file/player fields rather than being repeated in its caption.

### Independent single audio

```text
DROP                           [bold]

Music Video                    [official video URL, if found]
Spotify / SoundCloud           [each label only if that track has a URL]
Album                          [channel introduction URL, once posted]
Original                       [channel original-track URL for a distinct version]

t.me/RapFaDrop
```

If only one streaming URL exists, show just its label without `/`. Preserve `DROP` when a previously posted single later gains an album link.

### Audio from an LP/EP

```text
LP DROP                        [bold; EP DROP for EP; editable/removable]

Music Video                    [if found]
Spotify / SoundCloud           [available track links only]
Album                          [linked to this collection's introduction]
Original                       [if this is a distinct version with an earlier post]

t.me/RapFaDrop
```

### Album/EP cover introduction

This is illustrative text using the owner's edited example. The actual title, artist and guests come from verified official metadata. Only the title is bold and **only the guest names after `feat.` are italic**. The `•` precedes previously published single titles linked to their channel posts.

```text
REFIGH                         [bold]
LP · Reza Pishro × Tohi
feat. Ali Owj · Big Shaggy · Nassim  [guest names italic]

پیش‌تر از این آلبوم منتشر شده:
• CD
• Raghse Andam 3

@RapFaDrop
```

Use `EP` in place of `LP` for an EP. Hide the `feat.` row and the entire prior-singles block when absent. For an eligible edition with a prior introduction, show a linked `Original Album` before `@RapFaDrop`. If the list of links exceeds Telegram's effective caption limit, keep the introduction concise and place overflow links in a following text message. Inline buttons are deferred; a separate archive channel may be added later.

Candidate template variables: `title`, `artists`, `features`, `release_type`, `music_video_url`, `spotify_url`, `soundcloud_url`, `album_post_url`, `previous_singles`, `original_track_post_url`, `original_album_post_url`, and `channel`. Final variable naming and Telegram rendering are implementation details to verify in a test channel.

## 6. File metadata and artwork

- Preserve official title and artist in filenames and main audio fields. Use official art for embedded cover and album introduction.
- The owner wants `@RapFaDrop` placed, according to their visual reference, in `Subtitle`, `Comments`, as a suffix to `Album artist` and `Album`, and in configurable `Publisher`, `Encoded by`, `Author URL`, `Copyright`, `Composers`, `Conductors` and `Initial key` fields. Map these to each output format and verify actual Telegram player display with sample files. The tag policy is panel-editable.
- Keep verified official authorship/rights credits distinguishable from channel attribution. Placing a channel label in unusual fields reflects the owner's requested presentation and is not a claim that the channel created or owns the work. Review behavior when an official value already exists before overwriting it.

## 7. Admin panel and observability

Provide artist/profile management, source verification, caption/tag template preview and editing, queue and error views, publication links, configurable correction-reply deletion, manual media upload, suspicious-item decisions and metrics. Separate password accounts have equal admin access. Another admin may reset a password, with actor and change logged. Telegram review notifications include reasons and approve/reject/correct paths; one uncertain item must not block unrelated releases.

Review candidates include artist/title disagreement with official data, live/remix audio instead of the expected version, possible duplicate, low-confidence Spotify-to-file matching and ambiguous collection type. Thresholds and categories are configurable. Log source errors, admin decisions, release counts, discovery-to-publication latencies and media-provider performance. Delete temporary media after confirmed upload/message persistence; keep its provenance, quality and processing outcome. No permanent server-side audio archive is required initially.

## 8. Accepted implementation stack

Python 3.13; Django 5.2 LTS; PostgreSQL; Redis + Celery for background jobs and polling; FFmpeg/ffprobe and Mutagen for audio inspection/tags; `yt-dlp` as the first provider to test; Telegram Bot API for publishing; Docker Compose on the owner's server and HTTPS for the private panel. Keep public Spotify metadata and file-provider adapters replaceable. Do not assume either works until real probes pass. See `IMPLEMENTATION.md` for service boundaries, data, milestones and acceptance evidence.

## 9. Empirical gates for implementation

1. Probe the owner's [Vaghti Raft single](https://soundcloud.com/sijalofficial/vaghti-raft) and [OCD collection](https://soundcloud.com/sijalofficial/sets/ocd) for native IDs, ordering, metadata, file format, true audio quality, access and downloader errors. This has not yet been done in this documentation phase.
2. Probe an independent downloader failure path and public Spotify artist/release metadata access without Premium.
3. Verify Telegram send/edit media, caption/file limits, embedded art/tags, message ID preservation and reply deletion in a test channel. Reconcile uncertain sends without double posts.
4. Tune polling and backoff from actual measurements with the 30 seed artists, verify the profile identities and keep source failures isolated.
5. Validate conditional template rendering, album caption overflow, links added after publication and edition/original linkage with realistic fixtures and Telegram samples.

The owner will explicitly approve the final document before it is treated as a locked implementation reference. Detailed stage-by-stage acceptance is in `IMPLEMENTATION.md`.
