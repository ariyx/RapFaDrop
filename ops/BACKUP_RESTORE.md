# Recovery operations

Run on the server as root. age 1.x provides authenticated streaming encryption.
The recovery identity is generated once, mode 0600, outside Git and all archives.
The owner must save an independent offline copy before relying on disaster recovery.
To deliberately view it in a private terminal (never paste into chat/logs):

```sh
sudo cat /var/lib/rapfadrop-secrets/backup.agekey
```

Protected configuration: `/var/lib/rapfadrop-operations/backup.json`. It specifies
all four ordered Compose files, explicit protected file paths, identity path,
backup directory, dedicated backup chat and credential file. No music settings
are enabled. No chat fallback exists. Only chat `-1004475982526` is permitted;
production `-1004311149640` is rejected. Backup documents are labeled BACKUP and
must not be removed by test-message cleanup.

```sh
python3 /opt/rapfadrop/ops/backup.py create --reason pre-deployment
python3 /opt/rapfadrop/ops/backup.py check /var/backups/rapfadrop/encrypted/ARTIFACT.tar.age
python3 /opt/rapfadrop/ops/backup.py upload /var/backups/rapfadrop/encrypted/ARTIFACT.tar.age
python3 /opt/rapfadrop/ops/backup.py readback /var/backups/rapfadrop/encrypted/ARTIFACT.tar.age
python3 /opt/rapfadrop/ops/backup.py restore-drill /var/backups/rapfadrop/encrypted/ARTIFACT.tar.age
python3 /opt/rapfadrop/ops/backup.py retention
```

`create` briefly stops web, worker and beat, captures a consistent PostgreSQL
custom dump and schema/table content hashes, migration/runtime/SHA manifest,
checksums, required protected configs and this guide. Services resume before
encryption/upload: no database transaction stays open during either. No audio,
Redis broker snapshot or recovery identity enters the archive. `check` performs
a real restore into a uniquely named DB with no connected worker or dispatcher;
it compares every public table/count/content and schema then drops only that DB.
Protect the backup config/token paths with 0600 and parent directories 0700.

An encrypted archive is split into numbered parts of at most 45MB, plus a
JSON reassembly manifest. Concatenate in numerical order; check each part and
combined SHA256 from the manifest before decryption. Hosted Bot API upload limit
is 50MB; getFile/download limit is 20MB, so larger parts cannot be read back by
this API and are explicitly marked blocked. The tool preserves the local
artifact and durable message IDs on failures. It retries missing files on the
next explicit upload, with one bounded automatic retry for a definite HTTP 429
whose retry-after is at most 30 seconds. Definite API rejection is retryable;
an uncertain send is blocked until an operator reconciles
the channel and uses `upload ... --reconciled-absent`. Do not use that override
when the pending file actually exists; retain/reconcile its message ID first.
Telegram copies are retained indefinitely until separate owner-controlled
deletion. Local retention keeps seven distinct daily + four distinct weekly
restore-verified artifacts; the last usable and incomplete uploads are kept.
Legacy raw dumps are outside automated retention, root-only, pending deliberate
owner archival/deletion; this tool does not delete earlier recovery points.

Daily schedule: systemd timer 03:17 UTC plus up to five minutes jitter, persistent.
It creates, restores/checks and uploads a backup, then applies retention. It does
not use Celery or enable music tasks. Before deployment or a significant DB
mutation, run create/check/upload and record the verified artifact before
proceeding. A failed upload is visible in local sidecar/service exit status;
manual retry does not require repeating DB backup.

Exact-SHA deployment is integrated with the same exclusive backup lock:

```sh
python3 /opt/rapfadrop/ops/deploy.py TESTED_SHA --tested-marker ROOT_ONLY_TEST_MARKER
```

This refuses a dirty checkout or mismatched marker, creates/restores/uploads an
encrypted recovery point, then deploys only that SHA with all four overlays,
applies migrations/default versioning and verifies health/safety. The marker
must be written only after server checks of that exact commit. A daily backup
cannot race this deployment. Deployment failures retain the archive and require
operator inspection; there is no automatic destructive rollback.

## Explicit production recovery

Never use production recovery for a drill. First save the archive/identity off
the server, deploy the archive's exact application SHA using the backup-before-
deploy procedure, and review archived protected configuration in isolation.
Keep bridge, media and publication OFF. The command requires an explicit phrase,
checks an isolated restore, creates/checks a fresh pre-restore backup, stops web,
workers and beat, recreates the production DB, restores and compares it. It leaves
services stopped even on success. Recovery after failure uses the reported
pre-restore archive; never blindly restart after an error.

```sh
python3 /opt/rapfadrop/ops/backup.py restore-production ARTIFACT.tar.age \
  --confirm RESTORE-RAPFADROP-PRODUCTION
```

For a replacement host, install Docker/Compose/age, obtain the recorded app SHA,
restore protected files from the decrypted archive to their recorded paths
**after reviewing permissions and host-specific IP/path values**, provision the
PostgreSQL/Redis containers only, restore the dump, then compare manifest counts/
schema/content. Copying archived configs is deliberately not automatic. Re-run
Django migration/check and inspect all safety switches before starting web and
metadata worker/beat with all four overlays. Never replay a Redis queue dump.
PostgreSQL contains pending/retry/uncertain publication identities; file paths
may refer to missing disposable audio. Reacquire or manually prepare through the
validated pipeline after explicit authorization, reconcile uncertain Telegram
sends first, and rebuild tasks from durable due states rather than blind sends.
Published message history remains in the DB; no bulk audio is backed up daily.

The archive includes its checksummed standalone `backup.py` so that recovery
does not depend on an older application SHA having this tool in Git. Initial
offline inspection after downloading/concatenating the parts is:

```sh
umask 077
mkdir -m 700 /root/rapfadrop-recovery
# Check combined SHA256 against the downloaded reassembly manifest first.
age -d -i /PRIVATE/OFFLINE/backup.agekey -o /root/rapfadrop-recovery/recovery.tar recovery.tar.age
tar -tf /root/rapfadrop-recovery/recovery.tar
```

Use the included tool's safe extraction (`unpack`) or Python tarfile `filter=data`
into this isolated directory; compare every member against `manifest.json`.
Never extract directly over live production paths. For replacement-host restore,
after reviewing/restoring config and starting only PostgreSQL/Redis, the dump
command is:

```sh
docker exec -i rapfadrop-postgres-1 pg_restore -U rapfadrop -p 55432 \
  -d rapfadrop --exit-on-error --single-transaction --no-owner --no-acl \
  < /root/rapfadrop-recovery/database.dump
```

An existing production DB must instead use the guarded `restore-production`
command and its pre-restore backup requirement. An empty replacement host has
no prior DB to back up. The original archive, download manifest and offline
identity must be retained independently until restoration has been verified.
