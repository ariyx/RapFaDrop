# Popular-track archive collection

The owner authorizes only the initial two-slot Popular collection in production
`-1004311149640` (`@RapFaDrop`). Automatic future discovery publication stays OFF.

`archive_collection` records a frozen roster, one complete artist-specific Top
Tracks observation per artist, at most two slots, and unique stable Spotify track
identities. Shared tracks satisfy multiple slots without replacement selections.
The installed SpotifyScraper 3.9.2 adapter supplies `queryArtistOverview`; raw
credit URIs are retained because its parsed Top Tracks credits omit native artist
IDs. Album detail corroborates selected recording identity and numbering. This is
returned web-player Top Tracks ordering in an anonymous server session, not a
measurement of live discovery or a promise of identical ordering in every market.

A dedicated explicit CLI uses no Celery task or beat entry. Its production gateway
requires the exact frozen recording/candidate/publication/payload and durable
pending attempt, an unpaused collection, all ordinary music switches OFF, pinned
bot ID, exact channel ID/username and posting permission. Ordinary publication
paths retain their production block. Channel leases, definite-failure backoff and
uncertain-send reconciliation remain the existing application's mechanisms.

Acquisition uses bounded five-result SoundCloud metadata searches only when a
credited artist has a verified official profile. Exact title/version, credited
profile and duration must match before downloading. An unavailable file creates
an explicit archive metadata fact and review-required candidate for the existing
authenticated manual-upload workflow, without discovery ingestion, a historical
baseline change or a processing queue task. Unverified uploader/search identities
are not promoted to official sources. Complete files undergo duration validation,
tag/artwork readback and an entire FFmpeg decode. Official file metadata retains
complete Spotify credits. Owner-requested ARCHIVE captions contain only the bold
ARCHIVE heading, conditional platform/related links and footer; no historical DROP or
fabricated album/test-channel URL. Telegram success stores media file IDs as well
as message IDs; bounded getFile readback compares actual uploaded bytes. Confirmed
readback allows disposable media cleanup, never production-message deletion.

Server commands use the protected collection Compose file, not a general media
worker. Replace NAME only to deliberately create a separate collection; reruns of
the same name preserve observed selections, including explicit unresolved slots.

```sh
C=/var/lib/rapfadrop-operations/popular-collection.compose.yaml
docker compose -p rapfadrop-popular -f "$C" run --rm collection popular_collection status
docker compose -p rapfadrop-popular -f "$C" run --rm collection popular_collection pause
docker compose -p rapfadrop-popular -f "$C" run --rm collection popular_collection resume
docker compose -p rapfadrop-popular -f "$C" run --rm collection popular_collection run --credentials /var/lib/rapfadrop-operations/popular-collection.json
docker compose -p rapfadrop-popular -f "$C" run --rm collection popular_collection export --output /collection-report
```

Freeze only after create/restore-check/upload of a recovery point and exact tested
SHA deployment. `freeze --sha SHA` starts paused. `resume` enables this explicit
collection only; no background retry service exists. Each invocation is bounded
to 166 unfinished recordings; definite acquisition errors back off 5 minutes to
6 hours. Failed/ambiguous audio remains visible; uncertain Telegram delivery
requires existing operator reconciliation. `pause` can stop further sends while
an active acquisition completes. Database advisory locking excludes concurrent
CLI dispatchers; channel serialization persists before every external mutation.

Execution evidence and the complete 83-artist coverage table will be recorded
below after the server run. Until then no production publication is claimed.


## Owner caption and metadata correction (2026-10-04)

The owner replaced the earlier three-field policy with all eleven channel fields:
subtitle/comments/publisher/encoded_by/copyright/composers/conductors/initial_key
contain @RapFaDrop; album and album artist append ` | @RapFaDrop`; author_url is
https://t.me/RapFaDrop. MP3 uses ID3 frames; M4A uses native atoms plus UTF-8 iTunes
freeform PUBLISHER/CONDUCTOR/INITIALKEY/AUTHORURL atoms. Player display of freeform
atoms varies; actual file readback is required. Main title and track artists stay
official. Album introduction prior-single heading is now English:
`Previously released from this album:`.

Retagging creates a separate immutable prepared candidate from retained originals,
with complete decode and equal raw recording SHA, then edits the same stored
Telegram message through a durable edit_media attempt. It sends no correction or
replacement audio post. Restarts reuse the persisted candidate; uncertain edits
require reconciliation. A separate caption edit removes archive title/artist rows.

A real collection run exposed a stale-instance save clearing the reserved
Recording-to-Publication FK after successful sends. Publication/Attempt message IDs
survived. The fix reloads after reservation; repair-links only attaches exact
confirmed candidate/track/channel/archive bindings while paused and never sends.
Four existing confirmed messages (4?7) require this repair, caption refresh and
all-field retagging before further collection sends. Official SoundCloud display
suffix matching now accepts only complete frozen Spotify credited names, preserving
version/duration/official-profile requirements; unknown guests/remixes stay blocked.

Selection SHA remains frozen at eb074f6e808836554ea474904473fc920bab039a, with 83
artists, 166 slots and 155 unique recordings. Exports distinguish that observation
SHA from the SHA performing the later preparation/publication. Server checks and
final execution evidence will be appended after verification.
