# Docker recovery and corrected independent discovery

Evidence date:2026-10-07. Final tested/deployed application:
**d8e016595a5a0ef36c8f8dd1389deafa8485db81**.
Safe [evidence](data/docker_recovery_evidence.json) and
[83-artist discovery coverage](data/fresh_discovery_coverage.csv) retain their
explicit observation timestamps. No credentials, audio or Telegram file IDs are included.

## Diagnosis and recovery

Docker29.1.3 answered listing/most container operations but inspection of beat
blocked indefinitely. A SIGUSR1 diagnostic showed ContainerInspect waiting on a
mutex and an old container-exit handler waiting on its output stream for over18h.
This establishes the observed Docker wait/lock failure, not the initiating cause
or proof that every earlier problem came from insufficient memory.

Protected original daemon configuration was retained outside Git. Enabled
`live-restore`, validated the configuration, reloaded Docker and confirmed the
setting before restarting only dockerd. All eight containerd task PIDs remained
unchanged across that recovery; PostgreSQL, Redis and application containers kept
running. Inspection of beat and the protected backup safety guard then passed.
Docker was not upgraded; no subscription/account, swap or networking change was
made by this repair. The mechanism follows [Docker live-restore documentation](https://docs.docker.com/engine/daemon/live-restore/).
`/etc/docker/daemon.json` is now included in encrypted protected-file backups.

## Application correction and checks

Previously tested RSS correction b2627b0 was deployed after restoring48 tables
and uploading backup messages124/125. It accepts the observed YouTube root ID
without UC only when the full author URI and every entry ID match the registered
channel, and keeps Shorts out of automatic full-audio processing.

One remaining SoundCloud failure was verified empirically: registered
`https://soundcloud.com/Khal3music`, native9300066, returned the same native account
and20 valid URLs under lowercase `/khal3music/`. Generic handle comparison now
ignores case; native account identity, URL host/path shape and recording identity
checks remain enforced. Curated source URLs and historical records were preserved.
Regression coverage accepts case normalization and rejects another handle/native
account. The isolated real20-entry check passed in9.365s with no audio/Telegram calls.

Exact d8e0165 passed **274 application tests in158.729s**, **15 focused feed tests
in1.105s**, and **10 backup tests in0.109s**. System/migration/drift checks passed.
The isolated check runner used768MiB; the previous384MiB run had OOMKilled set.
Disposable test containers/database/Redis/media were removed; project-label
checks found no remaining containers or volumes. No production volume/post was removed.

Both documented deploy operations returned a Docker-command error after checkout
and service recreation. They were not reported as clean automated successes.
The same protected postchecks were completed separately: all six runtime images
matched, changed source-file hashes matched the exact tested commit, guard/checks/
health passed, and baseline/frozen table hashes matched. Original failure receipts
remain protected for diagnosis. Repeated read-only Compose exec checks returned0;
the earlier individual failing command was not established. No safety guard was bypassed.

Pre-d8 backup `rapfadrop-20261007T142650Z-0f2995d9.tar.age` restored48 tables and
uploaded as126/127. Final recovery archive
`rapfadrop-20261007T144123Z-b7d0f856.tar.age` restored48 tables and uploaded as128/129;
it covers d8, all eight overlays and the Docker daemon configuration.

## Polling, preservation and limits

**83 approved artists /83 active verified Spotify sources /84 original baselines**.
All83 sources' latest three polling outcomes succeeded. All100 independent feeds
have watermarks and at least three successful scheduled polls, with no listed
feed errors:92 verified profile feeds for75 artists plus8 bounded public searches.
Every approved artist has at least one successful independent feed. Counters are
durable totals; this does not imply three fresh polls for every feed inside one
short observation window. Frozen155 recordings/166 slots and protected table
hashes were preserved. Popular stays paused; owner-authorized fresh bridge/media/
publication stay enabled, with exact-target publication confined to its publisher.
Zero uncertain music sends were observed; existing posts/backups remain retained.

Discovery uses its dedicated credential-free queue, four readers, batches capped
at12,512MiB/1CPU. Success schedules45s later, but observed feed success ages around
three minutes show this is not a guaranteed45s full-roster cycle or first-minute
release detection. Public search and bounded upload windows are not exhaustive
catalogs. Recording/version uncertainty, unavailable full files, provider backoff
and incomplete album staging can still prevent a send. Discovery health does not
mean all media is ready or native320 quality is available.

## Observed autonomous publication82

The owner reported [message82](https://t.me/RapFaDrop/82) after it was automatically
published: **The Don — Ki Eshgho Yade Man Dad**. Spotify discovery first observed
release2Hm1tVjQVG3MUdXiGvXXsd at15:29:51.025676UTC; publication succeeded at
15:30:35.356830UTC: **44.331s from first server observation to publication**.
This is a real automatic production release, not a replay or owner-seeded test.
The upstream timestamp is only a release-day value; upstream detection latency
cannot be inferred from it.

Spotsaver supplied complete measured **MP3/320,000 bit/s/44.1kHz/stereo/310.2302s,
12,409,208bytes**, expected310.595s. Acquisition3.572s; validation/preparation0.514s.
Full decode, duration match, title/artists/channel fields and embedded artwork
readback passed; one send attempt succeeded and its dispatcher completed.
Actual upload time is uninstrumented: equal attempt timestamps do not mean0s.
Original encoding/provenance is unknown; this is not a native Spotify320 claim.
No new download, resend, edit or deletion was performed during this audit.

This successful sample and healthy feeds establish working autonomous paths,
not every future release/version/provider/album scenario or guaranteed instant delivery.
