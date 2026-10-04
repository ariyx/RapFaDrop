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
tag/artwork readback and an entire FFmpeg decode. ARCHIVE captions preserve full
Spotify credits, optional track-level links, and the footer; no historical DROP or
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
