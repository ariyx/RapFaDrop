# Recoverable backups, caption ordering, metadata and quality policy

Date: 2026-10-04. Evidence timestamps are UTC; owner schedule is Asia/Tehran.
Application delivery began at `c65d6ba71fb47c7cb784464004aba132019842e3`;
the receipt-retention correction is `a1a47841d7feded2caa50db0d7ee27b5c83e4688`.
Final deployment/audit details are recorded below and in the safe evidence JSON.
The documentation SHA is the commit containing this report, obtainable with
`git log -1 --format=%H -- docs/reports/BACKUP_CAPTION_METADATA_QUALITY.md` and
reported explicitly in the owner handoff. The preceding documentation SHA was
`0ac21ddcb1df1bfae28f3350a377b2698d94f998`.

## Implemented

- Host `ops/backup.py`: consistent PostgreSQL custom dump, every public-table
  count/content hash, schema hash, migrations, app SHA/image ID, Python/Postgres/
  Docker/age versions, package/FFmpeg inventory, checksummed protected `.env`,
  four Compose files, two pilot wrappers, dedicated backup configuration/token,
  standalone recovery tool and restoration guide. Authenticated age 1.1.1
  encryption uses a once-generated private recovery identity outside all
  archives, Git and Telegram. No bulk audio or Redis queue dump is included.
- Backup-only Telegram configuration has no publication-chat fallback. The
  exact channel `-1004475982526` is verified with getChat before uploads;
  `-1004311149640` is forbidden. Documents are labeled BACKUP, split at 45MB,
  with a numbered/checksummed reassembly manifest. Durable intent/message IDs,
  one bounded definite-429 retry, explicit retry/reconciliation rules and local
  preservation prevent blind duplicate sends after an uncertain response.
- Isolated restore compares all 37 tables and schema, without any connected
  worker or task dispatcher, then drops only its generated database. The guarded
  production-restore command requires a phrase, isolated check and a fresh
  pre-restore backup; it stops services and deliberately leaves them stopped.
  No production restore was executed. Exact-SHA deployment shares the backup
  lock and requires a server-tested marker and restore-verified uploaded backup.
- Root systemd service/timer is independent of Celery. Schedule: 03:17 UTC plus
  up to five minutes jitter, or 06:47–06:52 Tehran. Local retention keeps seven
  distinct daily/four weekly verified snapshots and never removes the last
  usable artifact or incomplete uploads. Safe receipts persist after artifact
  expiration. Telegram copies have separate manual retention and were retained.
- All default audio/intro captions put related/video/prior/original links before
  the final Spotify/SoundCloud information block, then a blank line and
  `t.me/RapFaDrop`. Missing links omit rows/separators, official stored album
  message links remain authoritative, and normal escaping/overflow and edition/
  reconciliation behavior remains. Introductions can use confident collection
  SourceMatch URLs; no fabricated introduction or test link is added.
- `refresh_owner_defaults` versions only known legacy defaults, preserves and
  reports customized templates/settings, and is idempotent. Production had no
  stored CaptionTemplate/OperatorSettings rows, so repeated runs changed none;
  there are no remaining stored custom-template ordering exceptions. Historical
  Telegram messages were not edited.
- Default branding is only comments/encoded_by `@RapFaDrop` and author_url
  `https://t.me/RapFaDrop`. MP3 writes a named COMM, TENC and WOAR frame; M4A
  uses ©cmt, ©too and explicit iTunes AUTHORURL freeform. Real composer, publisher,
  rights, key, album artist, numbering and artwork survive. Cleanup on preparation
  removes only exact recognizable legacy branding; it does not bulk mutate files.
  Production had zero media files. Custom M4A publisher/conductor/key mappings
  remain explicitly unsupported; a custom author URL atom is not a claim about
  Telegram/desktop UI display.
- Selection prefers complete confidently matched MP3 near 320kbps unless known
  lossy-transcoded, with immediate compressed MP3/AAC fallback. ffprobe stream
  bitrate is separate from bytes/duration, which includes tag/art overhead.
  The bounded yt-dlp selector performs no quality-inventing transcode, and no
  new provider is introduced. Ordinary WAV/FLAC selection and lossless conversion
  are unsupported. Cross-codec numeric bitrate cannot establish an upgrade;
  known lossy transcodes cannot replace an existing message as an upgrade.

## Server verification and preservation

All Docker/network/integration work ran on the existing server. Local work was
source/document editing, syntax/diff checks, Git and SSH transfer only. Preflight
found 16GiB free disk and about 1GiB available RAM of 3819MiB. The disposable
test project had its own PostgreSQL/Redis endpoints 55433/56380, tmpfs media,
disabled providers/publication and no Telegram token or worker consuming
production tasks. It was removed after checks. Representative media tests used
generated tones/artwork in disposable storage; no real music was downloaded.

The exact `c65d6ba` server suite passed 156 application tests in 61.712 seconds,
five focused policy tests, seven initial backup tests, Django checks and no
migration drift. After the retention defect below, the exact `a1a4784` check
again ran the full 156-test application suite and eight backup tests. Its app,
Dockerfile and requirements are byte-identical to `c65d6ba`, proven by Git diff,
so the isolated tests used the already deployed image for that unchanged code.
Tag tests read actual MP3/M4A files, including artwork and legitimate credits.
Backup tests cover age authentication/tampering, manifest integrity, split/
reassembly, isolated cleanup, production-restore refusal, last-usable retention,
receipt persistence, definite rejection retry and uncertain-upload blocking.

Preservation checks compare every existing artist/item/baseline/review/downstream
row and source identity, enabled/verified state, baseline timestamps and interval.
Normal metadata polling is allowed to advance success/due/error bookkeeping;
no schedule/source is reset. The final state is 83 approved/enabled artists,
130 sources, 83 active verified Spotify sources, 3934 items, 84 baselines and the
same single open Dalu review. Processing jobs, media candidates/attempts,
publications/attempts and production media files remain zero. Bridge OFF,
media worker absent, Telegram mode disabled/live false/publication worker false.
Metadata queue/media queue are empty; the pre-existing inert backend-cleanup
envelope in the unconsumed default queue is preserved.

The final config readback found a protected `.env` legacy eleven-field branding
list overriding code defaults. After another encrypted restore-verified backup,
only that exact known-default setting was replaced with
`comments,encoded_by,author_url`; every other environment line and all original
overlays/wrappers were preserved. All three application services confirmed the
three fields and OFF switches. Server changes are age installation, root-only
backup configuration/identity/credential, backup systemd units/timer, this single
tag-setting migration and exact-SHA application rollout. Nginx/firewall settings
were not modified. No automatic source, bridge or music activation occurred.

## Defects and limits

Actual tag tests exposed URL-keyed ID3 WOAR readback; reading/cleaning by frame
family fixes author-URL validation without erasing legitimate parallel frames.
The server `.env` override was corrected separately as configuration, not an
application-source patch on the server. A real retention exercise exposed that
the initial policy also deleted safe upload receipts. `a1a4784` preserves them
and adds a focused regression; archived bytes may expire while durable message
IDs/readback evidence remain available. An early pre-deployment receipt expired
before this correction and its exact message IDs cannot be independently
reconstructed from retained local evidence. Its upload had succeeded before
deployment; this audit gap is not presented as verified message-ID evidence.

Hosted Bot API download/readback is bounded to 20MB, while uploads allow 50MB;
larger 45MB parts are explicitly marked blocked for hosted readback. Real small
archives in this task passed byte-for-byte readback and isolated restoration.
Future source authenticity/perceptual quality, unsupported lossless conversion,
and Telegram presentation of custom tags are not established by generated
fixtures. No live-release latency or new music E2E claim is made.

The recovery secret is mode 0600 under a 0700 directory, generated once/reused,
and deliberately never printed or sent. **It has not been delivered to an
independent owner-controlled location.** The owner must privately save an
offline copy using the deliberate retrieval command in the runbook before
relying on recovery after total server loss. Pending jobs may reference missing
disposable media; restore does not blindly replay Redis or uncertain sends.

## Recovery and handoff

Final tested/deployed application/operations SHA:
`a1a47841d7feded2caa50db0d7ee27b5c83e4688`.
Latest retained archive:
`/var/backups/rapfadrop/encrypted/rapfadrop-20261004T164756Z-6d77e66a.tar.age`,
573768 bytes, mode 0600; SHA256
`ce9f017af67916de83e39c9c1ad1b31aa565e9838e0852d04cb8c659968ce848`.
It was created at 16:47:56 UTC, isolated restoration matched all 37 tables/schema
at 16:48:20.387632 UTC, and backup-channel messages **55** (archive part) and
**56** (reassembly manifest) both passed SHA256 readback. They are retained,
not music test posts. The final deployment used the separately verified
16:46:38 UTC pre-deployment archive, with durable messages **53/54**.
Other locally recorded backup message IDs are **43/44**, **47/48**, **49/50**
and **51/52**; their Telegram documents remain retained. Older local same-day
archives expired under daily/weekly retention, while the corrected policy
retains safe receipts independently. The early expired pre-deployment receipt
exception is disclosed above rather than guessing its message IDs.

Final safe audit began at 16:50:24.411748 UTC and completed with health/cleanup
confirmation. It verified readback from expired archives' retained receipts
51/52 and 53/54, one current local encrypted artifact, no restore databases,
deleted disposable source directories, and the enabled/active timer. Its next
observed execution is 2026-10-05 03:21:23 UTC / **06:51:23 Tehran**.

The recovery identity is `/var/lib/rapfadrop-secrets/backup.agekey`.
Deliberate private retrieval: `sudo cat /var/lib/rapfadrop-secrets/backup.agekey`.
Do not paste the result into chat, reports, Git, logs or Telegram. This command
does not mean an independent copy has been delivered.

[Create/check/isolated and guarded production restore commands](../../ops/BACKUP_RESTORE.md).
Safe checksums, timestamps, restore/readback evidence, messages, retained-artifact
and timer/cleanup status: [audit evidence](data/backup_policy_evidence.json).
Backup documents are recovery material and were not deleted as music-test posts.
Stop here before popular tracks, album acquisition or music publication.
