# Deployment and verification

## Recoverable encrypted backup and exact tested deployment

Current recovery commands and isolated/explicit production restore guidance are
in [ops/BACKUP_RESTORE.md](../ops/BACKUP_RESTORE.md). Run create/check/upload before
every application deployment or significant DB mutation. Use `ops/deploy.py`
with a root-only marker recording checks of the exact pushed SHA; it enforces
the backup, restore drill, upload, clean checkout and all four discovery-only
overlays before migration/default versioning and health verification. The daily
host timer is independent of Celery/publication. Archive config files contain
secrets and stay encrypted; the recovery identity is separate and must be saved
independently by the owner. No production restore was authorized or run as a drill.

## Current fresh production runtime (2026-10-06; supersedes historical OFF gates)

Exact application/runtime evidence is in [STATUS.md](STATUS.md). Production Compose
uses the four historical files below followed by protected `fresh-production`,
`fresh-independent` and `fresh-intermediary` overlays, in the order recorded in the
root-only backup config. All Compose files must also be included in `protected_files`
for encrypted recovery. Fresh bridge is ON; media has no bot credential and cannot
send; scoped publisher verifies exact bot/chat. Popular remains paused. Only the
media service enables independent recording and Spotsaver acquisition. Use the
protected complete config for every operation; omit no overlay. Exact-tested deploy
must perform backup/restore-drill/upload before checkout/migration/restart.
[Current configuration and preservation](reports/FRESH_INTERMEDIARY_AUTOMATION.md).

The independent upload rollout adds the protected eighth
`/var/lib/rapfadrop-operations/fresh-discovery.compose.json` overlay after these
seven files, and adds `fresh-discovery: metadata` to the exact protected service
roles. Include the new overlay in both `compose_files` and `protected_files` in
the root-only backup config. Discovery has no media/session/bot mounts and keeps
Telegram/live/publication switches disabled. Enable the discovery flag only in
beat and this worker; preserve existing media/publisher roles and the paused archive.
Use the complete protected config, verified backup/restore/upload and an exact
server-tested SHA for future deployment or configuration changes. First-watermark
and scheduled provider evidence is separate from Spotify source baselines.
[Rollout evidence](reports/MULTIPLATFORM_FRESH_DISCOVERY.md).

## Current discovery-only production override (2026-10-04)

Production application/operations is `a1a47841d7feded2caa50db0d7ee27b5c83e4688` after the encrypted-backup/defaults task. All current production Compose operations must include the protected **fourth** overlay, in this order:

```sh
docker compose -p rapfadrop \
  -f /opt/rapfadrop/compose.internal.yaml \
  -f /var/lib/rapfadrop-operations/spotify-pilot.compose.yaml \
  -f /var/lib/rapfadrop-operations/spotify-bridge.compose.yaml \
  -f /var/lib/rapfadrop-operations/discovery-only.compose.yaml ps
```

This overlay keeps the bridge OFF and beat on `spotify_pilot:app`. The media worker is removed; only the discovery worker (`spotify-pilot`, solo concurrency 1), beat and web run alongside PostgreSQL/Redis. Keep Telegram mode disabled, live sending false and publication worker false. Omitting the fourth file would reintroduce the earlier bridge-ON configuration. Current protected backup/restoration, exact-SHA checks and source preservation: [activation report](reports/SOURCE_ACTIVATION.md). Historical instructions below describe earlier milestones.

This runbook applies to RapFaDrop milestones. Keep application and documentation changes in the local Git checkout. Never edit application source directly on the server. Do not deploy draft behavior beyond the milestone being delivered.

## Local delivery

1. Read `AGENTS.md`, `docs/AGENTS.md`, `docs/STATUS.md`, `docs/PRODUCT_SPEC.md` and `docs/IMPLEMENTATION.md`; check the requested milestone and current Git branch/status.
2. Implement the milestone locally. Configure local-only values in `.env` based on `.env.example`; never copy real values into Git, command arguments, logs or documentation.
3. Run the milestone's relevant checks and Docker Compose smoke tests. Inspect `git diff --check` and `git status`; confirm credentials, `.env` values, downloaded audio, media artifacts and production data are not staged.
4. Commit the focused change and push the established branch with a normal push. Do not force-push.

Example local checks (run from the repository root):

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env } # never overwrite an existing local .env
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose exec web python manage.py check
docker compose exec web python manage.py test
Invoke-RestMethod http://localhost:8000/health/
docker compose logs --tail 100 web worker beat postgres redis
```

Use only checks applicable to the milestone. Stop local services with `docker compose down` when finished; never use `down -v`.

## Server deployment

The 2026-10-02 M6 Phase 2 read-only preflight confirmed key-only SSH access, but found no RapFaDrop checkout in the searched deployment roots and no Docker/Compose runtime. `/opt` and `/srv` are empty; an intended deployment path and RapFaDrop domain remain unset. Existing Nginx occupies ports 80/443 for another application with working local HTTPS. Host firewall is inactive; provider firewall is unverified. Preserve those workloads when planning subsequent setup. No server configuration or deployment occurred. See [`reports/M6_OPERATIONS.md`](reports/M6_OPERATIONS.md) for commands, observed capacity and evidence limits.

Connect to `root@91.107.178.12` using SSH authentication configured on the local machine. Do not put a password in a prompt, command argument, Git, logs or documentation. If SSH authentication is unavailable, complete the local commit and push, report the exact SSH key/setup blocker, and stop server work.

Locate the existing RapFaDrop checkout or clone `https://github.com/ariyx/RapFaDrop.git` into the deployment directory. Before updating an existing checkout:

- Confirm it is the intended repository and inspect its branch, status and current SHA.
- Require a clean working tree. Do not overwrite unrelated changes.
- Preserve `.env`, Compose named volumes and database contents. Never run `docker compose down -v` or delete volumes.
- Record the current deployed SHA. Fetch the pushed branch and deploy the exact commit SHA from the local delivery, not a moving branch tip.

For an existing data-bearing database, create and verify a recoverable PostgreSQL backup before applying schema migrations. Keep the backup outside Git and outside disposable media storage. Use the project's documented restoration procedure when available; do not improvise destructive recovery.

From the server checkout, with its existing `.env` intact, validate and deploy the selected commit:

```sh
git status --short --branch
git fetch origin
git show --no-patch --oneline <DEPLOY_SHA>
git checkout <DEPLOY_SHA>
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
docker compose logs --tail 100 web worker beat postgres redis
```

Run the milestone's migration command only when needed and only after the database backup requirement above is met. For this foundation, that command is:

```sh
docker compose exec -T web python manage.py migrate --noinput
```

Verify the health endpoint from the server and run the milestone-specific smoke checks. For M0, run only infrastructure checks and read-only source probes specified by `docs/IMPLEMENTATION.md`. Never publish audio or test messages to the production `@RapFaDrop` channel. Record provider output and errors as observed; do not report an unrun check as passing.

If a server test reveals an implementation defect, fix it in the local checkout, rerun local verification, commit and push the fix, then deploy and test that exact new SHA. Record environmental failures separately. Never patch the server copy to resolve an implementation failure.

## Temporary internal IP/HTTP deployment (owner-authorized M6)

The observed deployment lives at `/opt/rapfadrop`, exact SHA `e85ae5e248a55d29dfcdca6af9ccb4785a39ee0c`. Use **`docker compose -p rapfadrop -f compose.internal.yaml`** for this deployment; the default `compose.yaml` has a different networking/background-service configuration. The dedicated file starts only web, PostgreSQL and Redis with host networking. Django listens at `91.107.178.12:8000`; PostgreSQL and Redis bind only to `127.0.0.1:55432` and `127.0.0.1:56379`. Named database/media volumes persist state.

Server-only `.env` is root-owned mode `0600`, with generated secrets, `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,91.107.178.12`, `RAPFADROP_WEB_BIND_IP=91.107.178.12`, loopback database/broker endpoints, and all Telegram/publication switches disabled. Same-origin HTTP CSRF works without an added trusted origin. Docker was installed with bridge/firewall/forwarding management disabled before startup; exact daemon configuration and verification are in [`reports/M6_OPERATIONS.md`](reports/M6_OPERATIONS.md). Do not introduce bridge networks or change daemon settings without reviewing the firewall/network implications.

Server-IP `/health/` returned HTTP 200 with database `ok`; all three services were healthy. Nginx configuration hashes and firewall snapshots were unchanged. No migrations, accounts, sources, baselines or Telegram work were run. Application schema/panel initialization and backup/restore are deferred. This temporary HTTP deployment is not the full production HTTPS milestone.

## Completion record

For each milestone, report:

- Local commit SHA and pushed branch.
- Server-deployed SHA, or the precise reason the server step could not run.
- Local checks and their observed results.
- Server checks and their observed results.
- Provider probe results, including errors and limitations.
- Remaining blockers and environmental failures.

Update `docs/STATUS.md` with the observed SHA, completed evidence and next task after each milestone. Its prior checkpoint is not proof that a later build or deployment succeeded.

Do not claim a deployment, provider probe, migration or health check succeeded unless its output was observed.
