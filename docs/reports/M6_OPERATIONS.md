# M6 operations evidence

## Server-only Spotify E2E completion, 2026-10-04

The owner-authorized isolated test is complete at tested/deployed application SHA `26afd28da5e20bbca37975b5a4512ea871dd6f72`. See [the full evidence report](SPOTIFY_E2E.md) for exact test-channel message IDs/deletion results, acquisition quality, stage timings, fixes, backup restore digests and limitations. The final full server suite passed 135 tests, and post-deployment publication checks passed 35 tests. A real reviewed single and nine-track LP passed through actual application acquisition/tagging/publication, retry/restart and replay. No live-release latency is claimed.

The disposable server project used PostgreSQL/Redis ports 55433/56380 and queue `isolated-e2e`, its own volumes and bounded runner/worker resources; no production task consumer or data volume was shared. Destination `-1004475982526` (`@RapFaDropTest`) and safety overrides were verified before every Telegram mutation. IDs 21–31 from the first run and 32–42 from the corrected repeat were all deleted. Test containers, database/media volumes, Redis queue, credential environment, source build archives/directories and draft image tag were removed. Only safe mode-0600 audit JSON/JSONL under root-only `/var/lib/rapfadrop-operations/e2e-20261004/` and protected deployment backups remain.

Both exact-SHA deployments followed checksum/list/37-table restore comparison before service replacement; temporary restore databases were dropped. Production application services were recreated using all three existing Compose files; PostgreSQL/Redis, firewall, Nginx and pilot overlays were preserved. Final production readback retained five enabled/verified Spotify sources, exactly 177 historical IDs with unchanged baseline/item digests, bridge ON, Telegram/publication OFF, zero downstream records and zero media files. No test resources remained. Do not activate production publication as part of this handoff. Historical sections below retain their original checkpoints.

Observed on 2026-10-02. The initial run was authorized for **Phase 2 server preflight and reporting only**; its server commands were read-only. Subsequent owner-authorized HTTP deployment and limited Phase 3 work are recorded separately below. M6 is incomplete.

## Server preflight

| Check | Observed result |
| --- | --- |
| SSH | Key-only authentication to `root@91.107.178.12` succeeded, exit 0. Remote `id` confirmed root. Strict existing-host-key verification was enabled. Password and keyboard-interactive authentication were disabled. |
| Local key setup | Default `~/.ssh/id_ed25519` and its public-key file exist. `ssh-add -l` reported no agent connection (exit 2); this did not prevent direct key authentication. No private-key contents were read or printed. |
| Server | Ubuntu 24.04.4 LTS, Linux `6.8.0-139-generic`. Final observation timestamp: `2026-10-02T15:08:30Z` (18:38:30 Asia/Tehran). |
| Repository | No RapFaDrop repository found in bounded searches of `/opt`, `/srv`, `/var/www`, `/root`, `/home` (depth approximately four). Six unrelated Git directories/worktrees were found under `/var/www`; recognized origins point to `ariyx/vpnsell`. These were not modified. RapFaDrop remote, working-tree cleanliness, branch and deployed SHA cannot be verified without a checkout. This search does not prove absence elsewhere on disk. |
| Deployment directory | `/opt` and `/srv` are empty. Common candidates `/opt/rapfadrop`, `/srv/rapfadrop`, `/var/www/RapFaDrop`, `/var/www/rapfadrop`, `/root/RapFaDrop`, `/root/rapfadrop` were absent. No intended path was supplied or created. |
| Docker / Compose | `docker` and `docker-compose` were not found on PATH; `docker --version` and `docker compose version` returned command-not-found. Docker service reported inactive. Package queries returned no installed Docker/Compose/containerd packages among the checked names. `/var/lib/docker` is absent. Container/volume/Compose configuration checks remain unavailable. |
| Disk | Root ext4 filesystem: 38 GiB total, 14 GiB used, 23 GiB available, 37% used. Inodes: 2,456,320 total, 189,965 used, 2,266,355 free (8% used). This is available capacity, not a production capacity test. |
| Host firewall | UFW inactive; nftables showed empty IPv4/IPv6 filter tables; iptables INPUT/FORWARD/OUTPUT policies ACCEPT. Provider/cloud firewall was not inspected. |
| Listening services | SSH on IPv4/IPv6 port 22; Nginx HTTP on IPv4/IPv6 port 80 and HTTPS on IPv4 port 443. MySQL 3306/33060 on loopback; Redis 6379 on IPv4/IPv6 loopback; resolver 53 on loopback. No PostgreSQL 5432 or application 8000 listener observed. These existing services belong to the host's current workload; RapFaDrop database/network isolation has not been configured. |
| Domain / HTTPS | Active Nginx site `bot.fon1xemergency.top`; server DNS resolution returned `91.107.178.12`. Certificate CN/SAN match that domain, issuer Let's Encrypt YE1, validity `2026-10-01T19:24:42Z` through `2026-12-30T19:24:41Z`. A certificate-verified HTTPS HEAD request through local Nginx returned `HTTP/1.1 200 OK`. This verifies the existing site's local TLS path, not a RapFaDrop panel or external HTTPS reachability. |
| RapFaDrop domain input | No RapFaDrop domain was established by the inspected inputs. Ignored local `.env` has `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`; no matching explicit deployment-domain or CSRF-origin entry was observed. Existing site/domain must not be assumed available for RapFaDrop. |

## Commands and evidence limits

SSH calls used:

```text
ssh -T -o BatchMode=yes -o PreferredAuthentications=publickey -o PasswordAuthentication=no -o KbdInteractiveAuthentication=no -o StrictHostKeyChecking=yes -o UpdateHostKeys=no -o ConnectTimeout=10 root@91.107.178.12 <read-only command>
```

Read-only commands included `id`, OS/kernel checks, bounded directory discovery, credential-free Git-origin inspection, `docker --version`, `docker compose version`, `systemctl is-active`, `dpkg-query`, `df -hT`, `df -i`, `ss -lntup`, `ufw status verbose`, `nft list ruleset`, `iptables -S`, selective Nginx site directives, certificate inspection and `getent ahostsv4`.

TLS request:

```sh
curl --noproxy '*' --resolve bot.fon1xemergency.top:443:127.0.0.1 -sS -I --connect-timeout 5 --max-time 10 https://bot.fon1xemergency.top/
```

Two piped diagnostic scripts ended with shell input/line-ending errors (exit 2 and 127) after emitting the checks above. Their outputs are individual observations, not a claim that either script passed end to end. A final direct SSH command confirmed authentication, UTC time, empty `/opt` and `/srv`, absent runtime commands/storage, and completed with exit 0. No password fallback was attempted.

## Local repository checkpoint

Local branch `main`, tracking `origin/main`; both local refs were `c982d5d63c6f7a28063726d09285fe53dd337b2f` before this documentation update. Origin is `https://github.com/ariyx/RapFaDrop.git`. Initial worktree had only untracked `docs/M6_AGENT_TASK.md`. No network fetch/push or application change was performed; cached upstream equality is not a new remote verification.

## Deferred gates

- Exact deployed SHA: unavailable; no RapFaDrop checkout located or deployment performed.
- Test-channel probe: not run in this Phase 2 task; prior local evidence remains in `M4_PUBLICATION.md`.
- Server-only `.env`, secrets/permissions, media/PostgreSQL volumes, production HTTPS/panel configuration: not created or changed.
- Backup/restore, migration, health and restart durability: not run.
- Production administrator accounts and pilot baselines: not created or run.
- Production publication: no activation or send; existing local configuration and server workloads were left untouched.

At the preflight checkpoint, follow-up required an intended deployment directory, a RapFaDrop panel domain, Docker/Compose installation, and a host/network/proxy plan that preserves the existing site. The later owner-authorized HTTP deployment below supersedes the missing runtime/directory blockers. No production-readiness claim is made.

## Subsequent owner-authorized IP/HTTP deployment

The owner subsequently authorized serving Django at `http://91.107.178.12:8000`, with `DEBUG=false`, PostgreSQL/Redis private, and no changes to Nginx, ports 80/443 or the firewall. Admin creation, source enablement, baselines and Telegram sends remain excluded. Earlier migration deferral was retained: this deployment checks database connectivity only, without initializing the application schema.

### Exact deployed configuration

- Checkout: `/opt/rapfadrop`, origin `https://github.com/ariyx/RapFaDrop.git`, clean detached HEAD at **`e85ae5e248a55d29dfcdca6af9ccb4785a39ee0c`**. The exact commit was pushed locally and confirmed with `git ls-remote` before server checkout. Subsequent evidence-only documentation commits are not deployed application revisions.
- Compose file: `compose.internal.yaml`, project name `rapfadrop`. Only `web`, `postgres` and `redis` exist in this deployment configuration; worker and beat are absent.
- Docker Engine `29.1.3` (Ubuntu package `29.1.3-0ubuntu3~24.04.2`); Compose `2.40.3+ds1-0ubuntu1~24.04.1`. Installed with `apt-get install --no-install-recommends -y docker.io docker-compose-v2` after `apt-get update`. Package upgrades were not requested; automatic service restarts were deferred with `NEEDRESTART_MODE=l`.
- `/etc/docker/daemon.json` was created before installation/startup with the following configuration. Docker uses no bridge and these services use host networking, avoiding Docker NAT/firewall changes. Host-networked database services are explicitly bound to loopback; neither has a public listener. This mode shares the host network namespace and is specific to this temporary deployment. [Docker's networking/firewall documentation](https://docs.docker.com/engine/network/packet-filtering-firewalls/) describes host networking as not creating network firewall rules.

```json
{
  "bridge": "none",
  "iptables": false,
  "ip6tables": false,
  "ip-forward": false
}
```

- Server `.env`: generated from `.env.example`, root owned, mode `0600`, ignored by Git and excluded from Docker's build context. Django secret and PostgreSQL password were generated on the server with Python `secrets.token_urlsafe`; values were never printed or copied from the workstation.
- Exact non-secret overrides:

```dotenv
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,91.107.178.12
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=55432
REDIS_URL=redis://127.0.0.1:56379/0
RAPFADROP_WEB_BIND_IP=91.107.178.12
RAPFADROP_TELEGRAM_MODE=disabled
RAPFADROP_TELEGRAM_LIVE_ENABLED=false
RAPFADROP_PUBLICATION_WORKER_ENABLED=false
RAPFADROP_TELEGRAM_BOT_TOKEN=
RAPFADROP_TELEGRAM_TEST_CHAT_ID=
RAPFADROP_TELEGRAM_REVIEW_CHAT_ID=
RAPFADROP_TELEGRAM_PRODUCTION_CHAT_ID=
```

Remaining non-secret media settings retain `.env.example` defaults. PostgreSQL database/user are both `rapfadrop`. No CSRF setting was added: runtime `CSRF_TRUSTED_ORIGINS=[]` accepts the exact same origin `http://91.107.178.12:8000` through Django's normal Origin check; unrelated origins remain rejected and CSRF tokens remain required. There is no proxy or HTTP-to-HTTPS redirect in this configuration.

| Service | Exact listener / configuration |
| --- | --- |
| web | Gunicorn `config.wsgi:application --bind 91.107.178.12:8000 --workers 2 --timeout 60`, non-root application user |
| postgres | `postgres:17.6-alpine`; `postgres -c listen_addresses=127.0.0.1 -c port=55432` |
| redis | `redis:8.2.1-alpine`; `redis-server --bind 127.0.0.1 --port 56379 --protected-mode yes --save "" --appendonly no` |
| persistence | `rapfadrop_postgres_data` mounted at `/var/lib/postgresql/data`; `rapfadrop_media_data` mounted at `/var/lib/rapfadrop/media` |

### Observed commands and results

Commands ran from `/opt/rapfadrop`:

```sh
docker compose -p rapfadrop -f compose.internal.yaml config --quiet
DOCKER_BUILDKIT=0 docker compose -p rapfadrop -f compose.internal.yaml build web
docker compose -p rapfadrop -f compose.internal.yaml up -d --no-build --wait --wait-timeout 90
docker compose -p rapfadrop -f compose.internal.yaml ps
docker compose -p rapfadrop -f compose.internal.yaml exec -T web python manage.py check
ss -lntp '( sport = :8000 or sport = :55432 or sport = :56379 or sport = :80 or sport = :443 )'
curl --noproxy '*' --fail --silent --show-error --max-time 10 -w '\nHTTP_STATUS=%{http_code}\n' http://91.107.178.12:8000/health/
```

- Local Compose configuration validation passed with only the temporary bind-IP environment variable supplied; ignored local credentials were not deployed. The missing-variable check also refused configuration when that bind IP was absent.
- Server Compose validation, legacy builder image build and three-service startup passed. Web image ID begins `388ec1924ebf`. All three containers were healthy.
- `ss` observed Gunicorn at **`91.107.178.12:8000`**, PostgreSQL at **`127.0.0.1:55432`**, and Redis at **`127.0.0.1:56379`**. Existing Nginx listeners and process IDs on 80/443 remained present.
- Server-IP health response: **HTTP 200**, body **`{"status": "ok", "database": "ok"}`**. This checks a real PostgreSQL `SELECT 1`; it does not certify application migrations or panel workflows.
- Django system check: **no issues**. Runtime assertions confirmed debug false, IP in allowed hosts, Telegram disabled with no bot token, and publication worker disabled.
- Django CSRF Origin checks accepted the exact IP/port HTTP origin and rejected an unrelated origin. A real health request with `Host: untrusted.example` returned **HTTP 400**.
- Normalized IPv4/IPv6 `iptables-save` and complete `nft list ruleset` output matched pre-installation snapshots exactly. SHA-256 listings of Nginx configuration files matched exactly. Nginx remained active; its existing certificate-verified local HTTPS request still returned **HTTP 200**. No Nginx configuration/reload or firewall command that changes rules was run.
- `.env` permissions observed: **600, root**. Server Git status remained clean at the exact deployed SHA.
- PostgreSQL reported **zero public application tables**: no migrations, application accounts, seeds, source state or baselines were created. The application panel/schema is not yet ready for authenticated use. Worker/beat were not started, and no Telegram request was made.
- Final verification completed with exit 0 at **`2026-10-02T15:21:04Z`** (18:51:04 Asia/Tehran). HTTP reachability was checked from the server through its own public IP, as requested; access from the owner's network/cloud ingress is not claimed.

At this connectivity checkpoint, backup/restore, migrations and restart recovery were deferred. The following owner-authorized Phase 3 checks supersede those deferrals. HTTPS, accounts, full panel readiness and controlled source/publication activation remain later gates.

## Limited Phase 3: backup, migrations and restart durability

Owner scope: continue on the deployed SHA, create and verify an initial backup before migrations, verify migration state, safely restart the deployed Compose services, and verify database/queue/audit persistence and server-IP health. No administrator creation, source enablement, baseline, production Telegram configuration or messages were authorized or performed.

### Checkpoint and protected backups

At entry, `/opt/rapfadrop` remained clean at detached SHA **`e85ae5e248a55d29dfcdca6af9ccb4785a39ee0c`**, with three healthy containers and zero public application tables. Runtime guards verified debug false, Telegram disabled, no bot/production-channel configuration, and publication worker disabled. Neither application source nor deployment configuration was changed, fetched, rebuilt or updated during this Phase 3 run.

Backups are server-only in **`/var/backups/rapfadrop`**, root-owned mode **0700**. Both custom-format archives and their `.sha256` sidecars are root-owned mode **0600**, outside Git and disposable media storage. Files were written under `umask 077` with overwrite refusal.

| Archive | Size | SHA-256 |
| --- | --- | --- |
| `initial_e85ae5e_20261002.dump` | 844 bytes | `7ee36aa89129e19e9495324bc38c49f67099bbc2588e828f51ac068094da55d0` |
| `migrated_e85ae5e_20261002.dump` | 164,498 bytes | `4a59f81592b22a763ac40ddee943eea23169ca3ce5bddd283c64a799c6768d40` |

The initial archive was created at `2026-10-02T15:26:31Z`. Its checksum passed, `pg_restore --list` parsed it, and restoration into the separately created `m6_initial_restore_20261002` database completed with `--exit-on-error --single-transaction`. `SELECT 1` succeeded and the restored database had zero public tables, matching the pre-migration source. **This restore validation completed before migrations.**

After migrations, a second archive was restored into `m6_migrated_restore_20261002`. All 37 public-table row counts and canonical JSON row-content hashes matched the deployed database exactly; the restored database also passed `migrate --check`. The initial empty-database test alone is not being used as evidence for restoring a populated application schema.

Commands used from `/opt/rapfadrop` (the same operations were repeated for the migrated archive and its distinct disposable database):

```sh
docker compose -p rapfadrop -f compose.internal.yaml exec -T postgres pg_dump -U rapfadrop -p 55432 -d rapfadrop --format=custom --no-owner --no-acl > /var/backups/rapfadrop/initial_e85ae5e_20261002.dump
sha256sum /var/backups/rapfadrop/initial_e85ae5e_20261002.dump > /var/backups/rapfadrop/initial_e85ae5e_20261002.dump.sha256
sha256sum --check /var/backups/rapfadrop/initial_e85ae5e_20261002.dump.sha256
docker compose -p rapfadrop -f compose.internal.yaml exec -T postgres createdb -U rapfadrop -p 55432 -T template0 m6_initial_restore_20261002
docker compose -p rapfadrop -f compose.internal.yaml exec -T postgres pg_restore -U rapfadrop -p 55432 --dbname=m6_initial_restore_20261002 --exit-on-error --single-transaction --no-owner --no-acl < /var/backups/rapfadrop/initial_e85ae5e_20261002.dump
```

These are manual, locally retained backups with observed restoration. Automatic schedule/retention, off-host copies and recovery under host/disk loss remain unverified.

### Migrations

```sh
docker compose -p rapfadrop -f compose.internal.yaml exec -T web python manage.py migrate --noinput
docker compose -p rapfadrop -f compose.internal.yaml exec -T web python manage.py migrate --check
docker compose -p rapfadrop -f compose.internal.yaml exec -T web python manage.py showmigrations
docker compose -p rapfadrop -f compose.internal.yaml exec -T web python manage.py makemigrations --check --dry-run
docker compose -p rapfadrop -f compose.internal.yaml exec -T web python manage.py check
```

All **25 migrations** applied with `OK`; all `showmigrations` entries were `[X]`. `migrate --check` passed before and after restarts; model drift check reported **No changes detected**; Django check reported **no issues**. There are now **37 public tables**. Django content types/permissions were initialized by normal migration hooks; no user, operator account, artist/source seed or application work was created.

### Restart and persistence evidence

Production table counts and row-content SHA-256 digests were recorded before restarts. Because queue/audit tables were empty, a meaningful non-empty durability fixture was added **only to the disposable migrated restore database**: one track, one cancelled `ProcessingQueueItem`, and one `OperatorAuditEvent` with a null actor. No account or source was needed. The event's correlation UUID was `bb44f0aa-a00c-4f53-b0ed-fda3f6b85633`; its exact row and queue row were included in the fingerprint comparison. No fixture was inserted into the deployed database.

| Stage | Safe action | Observed result after recovery |
| --- | --- | --- |
| Web | `restart -t 30 web`, then health-wait | Both databases' 37-table fingerprints unchanged; HTTP 200, PostgreSQL ready, Redis PONG |
| Redis | `restart -t 30 redis`, then health-wait | Same fingerprint/health results |
| PostgreSQL | Stop web gracefully, restart PostgreSQL, start web with dependency health-wait | Same fingerprint/health results, including non-empty disposable queue/audit rows |
| Full deployed stack | Stop web first, stop Redis/PostgreSQL, then `up -d --no-build --wait --wait-timeout 60` | Same fingerprint/health results; all three containers healthy |

All commands used `docker compose -p rapfadrop -f compose.internal.yaml`. Health waits used `up -d --no-build --wait --wait-timeout 60`, and graceful stops used `stop -t 30`. No `down -v`, volume removal, application rebuild or schema change occurred during restart tests. Web was paused for database/full-stack maintenance and resumed afterward. Worker and beat are absent from this deployment and were neither started nor tested. Redis is intentionally non-persistent; this verifies PostgreSQL-backed queue/audit durability, not survival of Redis transient messages.

Snapshots and the temporary fingerprint script remain in root-only `/var/lib/rapfadrop-operations`, outside the application checkout; fingerprints contain only table names, row counts and hashes. Both disposable databases were explicitly dropped after verification. A final database-name check found no `m6_%` databases, and production fingerprints still matched their pre-restart values.

### Final observed state

- Production: **zero users, artists, sources, source items, baselines, queue items, operator audit/request rows and publications**. Non-empty queue/audit restart evidence comes from the disposable copy, not real release processing. No source was activated and no provider or Telegram request was made.
- Both archive checksum checks still passed after restarts/cleanup; protected files were retained.
- All three containers healthy; `pg_isready` accepted connections; Redis returned `PONG`. Recent service logs showed orderly shutdown/startup and readiness.
- `ss` still observed Gunicorn at **`91.107.178.12:8000`**, PostgreSQL at **`127.0.0.1:55432`**, Redis at **`127.0.0.1:56379`**.
- Final server request to **`http://91.107.178.12:8000/health/`** returned **HTTP 200** and **`{"status": "ok", "database": "ok"}`**.
- Nginx configuration SHA-256 listings and normalized IPv4/IPv6 firewall/nftables snapshots still matched the original pre-installation evidence. No Nginx/firewall changes occurred.
- `.env` remained root-owned mode 0600; clean deployed Git SHA remained **`e85ae5e248a55d29dfcdca6af9ccb4785a39ee0c`**.
- Final verification completed with exit 0 at **`2026-10-02T15:31:28Z`** (**19:01:28 Asia/Tehran**).

This authorized Phase 3 slice is complete. No administrator was created. Full M6 remains incomplete: accounts/authenticated panel verification, RapFaDrop HTTPS, scheduled/off-host backups, worker/beat recovery, actual media/publication-ID durability, source pilots and production activation remain deferred to later owner authorization.

## Focused production static-file fix

The owner authorized a local application fix and exact-SHA deployment for the unstyled admin at `http://91.107.178.12:8000/admin/`, without changing debug, Nginx, sources, baselines, Telegram or other M6 behavior.

Before the fix, the server's `/admin/` redirected normally to `/admin/login/?next=/admin/` with final HTTP 200. Its HTML referenced admin assets, but `/static/admin/css/base.css`, `/static/admin/css/login.css`, `/static/admin/css/nav_sidebar.css` and `/static/admin/js/theme.js` each returned HTTP 404 with an HTML content type. Headless Chrome on the workstation visited the actual server-IP URL and displayed the unstyled login page: Times New Roman body font, transparent header background and failed assets. A before screenshot is in ignored local `tmp/admin-before.png`.

Root cause: Gunicorn served Django with `DEBUG=false`, but no static-file handler or `STATIC_ROOT` collection existed in the Docker image. The focused fix follows [WhiteNoise's Django setup](https://whitenoise.readthedocs.io/en/stable/django.html):

- Pin `whitenoise==6.12.0` in `requirements.txt`.
- Insert `whitenoise.middleware.WhiteNoiseMiddleware` immediately after `SecurityMiddleware`.
- Set `STATIC_URL="/static/"`, `STATIC_ROOT=BASE_DIR / "staticfiles"` (container `/app/app/staticfiles`).
- Use `whitenoise.storage.CompressedManifestStaticFilesStorage` for static files and retain Django's default `FileSystemStorage` for media. Static and private media roots remain separate.
- Run `DJANGO_DEBUG=false python manage.py collectstatic --noinput` in the Docker build after switching to the non-root application user. Assets are baked into the image; runtime does not require collection, database access or mutable static volumes. Ignore generated `app/staticfiles` in Git and Docker context.
- Add a meaningful `SimpleTestCase` which collects real admin assets into a temporary directory and requests both the original and manifest-hashed CSS URLs through the complete Django middleware stack with debug false. It asserts HTTP 200, CSS content/body, cache headers and immutable caching on the hashed URL.

Local checks observed before commit/deployment: Compose config passed; the image build collected **127 files, 381 post-processed**; Django check reported no issues; model drift check reported **No changes detected**; all **92 tests passed in 22.626 seconds**, including the production-static regression. Tests used the isolated local test database. Initial workstation Docker DNS resolution failed while fetching dependencies; retry through the already-configured local proxy succeeded using transient build arguments only, without committing proxy values. `git diff --check` passed. No browser tooling, screenshot, generated static asset or secret is included in the application commit.

The fix was committed, pushed and confirmed remotely as **`44d0c62cd59eb8701d9599ccf8aae5aadb5b46d0`**, then fetched and checked out at that exact detached SHA in `/opt/rapfadrop`. The server build collected **127 files, 381 post-processed**; only web was recreated using `docker compose -p rapfadrop -f compose.internal.yaml up -d --no-deps --no-build --wait --wait-timeout 60 web`. No runtime collectstatic was needed because the collected assets were already in the image. Server Django and migration-state checks passed; no migrations ran.

Server verification completed at **`2026-10-02T16:12:11Z`** (19:42:11 Asia/Tehran), exit 0:

- `/admin/` redirected to the login page with final HTTP **200**. `/static/admin/css/base.css` returned **200**, CSS content type and `Cache-Control: max-age=60, public`.
- The manifest URL `/static/admin/css/base.96c479cedf7a.css` and all seven CSS/JavaScript assets linked by the login page returned **200**. Hashed assets had `max-age=315360000, public, immutable` cache headers.
- A fresh headless Chrome context visited the actual server-IP admin URL. All seven static responses were **200**, with no failed static requests; computed body font was Segoe UI/system sans-serif, header background `rgb(65, 118, 144)`, and five stylesheets had nonzero CSS rule counts. The screenshot was visually inspected and showed the styled, centered Django login panel. Screenshot: ignored local `tmp/admin-after.png`. No account was created or login submitted for this check; authenticated dashboard workflows were not exercised.
- Runtime debug remained false; Telegram/publication safeguards passed. `/health/` returned HTTP **200** with database `ok`; all three services remained healthy.
- All 37 database-table row-count/content fingerprints matched the pre-deployment snapshot. PostgreSQL/Redis container IDs were unchanged. `.env` checksum, firewall snapshots and Nginx configuration hashes were unchanged. Clean server checkout remained at the exact deployed SHA.

The static-file fix and its requested browser/server checks are complete. This does not advance source verification, baselines, publication or the remaining M6 operational gates.

## Server-only approved seed import

The owner authorized the existing M1 idempotent seed command on the server only, with no manual artist/source creation, provider requests, verification, enablement, baselines, media or Telegram work. The server remained clean at **`44d0c62cd59eb8701d9599ccf8aae5aadb5b46d0`** in `/opt/rapfadrop`; web/PostgreSQL/Redis were healthy and worker/beat remained absent.

Inspection confirmed `sources/management/commands/seed_sources.py` uses an atomic transaction and `get_or_create`, preserves existing aliases, inserts candidate URLs/IDs without contacting providers, and records a `seed_imported` source audit event. Model defaults are `Artist.enabled=False`, `ArtistSource.enabled=False`, and verification `unverified`. Explicit UTF-8 comparison against `PRODUCT_SPEC.md` confirmed all 30 names, Persian aliases and Spotify/SoundCloud candidate URLs, including the three intentionally missing SoundCloud profiles. No code change was necessary.

Before import: **0 artists, 0 sources**. One user account already existed at task entry; no account was created by this task. The initial empty source tables were expected because deployment/migrations had not invoked the seed command.

Command, run from `/opt/rapfadrop`:

```sh
docker compose -p rapfadrop -f compose.internal.yaml exec -T web python manage.py seed_sources
```

Observed first run:

```text
Seed verified: 30 artists; 57 sources (30 and 57 created this run).
```

The same command was repeated once to verify idempotence:

```text
Seed verified: 30 artists; 57 sources (0 and 0 created this run).
```

| Server database / admin observation | Count |
| --- | --- |
| Artists | 30 |
| Artist sources | 57 |
| Spotify candidates | 30 |
| SoundCloud candidates | 27 |
| Enabled artists / enabled sources | 0 / 0 |
| Unverified sources | 57 |
| Source items / baseline runs | 0 / 0 |
| Processing queue / media candidates | 0 / 0 |
| Publications / publication attempts / operator requests | 0 / 0 / 0 |

Every seeded artist alias and candidate URL/native Spotify ID was read back and matched against the approved seed. Fadaei, Ho3ein and Amir Tataloo still have no SoundCloud row. The registered Django `ArtistAdmin` and `ArtistSourceAdmin` unfiltered querysets and actual `ChangeList` instances reported **30** and **57** respectively (`result_count` and `full_result_count` both matched). These admin checks were run in-process with a request factory; no HTTP request, browser login, account credential or authentication bypass endpoint was used.

Two expected `seed_imported` audit records report creation counts 30/57 and 0/0. No additional queue/media/source-discovery or publication record was created. Runtime checks confirmed debug false, Telegram disabled, no bot/production-target configuration and publication worker disabled. No HTTP/provider/Telegram requests, baseline or source activation occurred in this task. Application/server configuration was unchanged, and no deployment or restart was performed.

Final verification completed with exit 0 at **`2026-10-02T16:19:13Z`** (19:49:13 Asia/Tehran). Only this report and `STATUS.md` are changed for the documentation handoff. Sources remain disabled/unverified pending separate owner authorization and empirical verification.

## Controlled Sijal SoundCloud baseline pilot

The owner authorized one metadata-only baseline for the already verified Sijal SoundCloud source, with temporary enablement only if required, followed by disabling it. No application/configuration change or deployment occurred. The server remained clean at SHA **`44d0c62cd59eb8701d9599ccf8aae5aadb5b46d0`**.

### Preconditions and execution

Read-only inspection confirmed artist **Sijal**, artist ID **16**, SoundCloud source ID **32**, candidate URL **`https://soundcloud.com/sijalofficial`**, verification **`verified`**, source disabled and artist disabled. The verification and its existing `source_configured` audit event predated this task; no source was verified by the agent. All 57 sources were disabled, with no SourceItems or baseline runs. Telegram mode/live/publication worker were disabled and no bot or production-target configuration was present. Only web, PostgreSQL and Redis were running; worker/beat were absent.

The documented flow is:

```sh
docker compose -p rapfadrop -f compose.internal.yaml exec -T web python manage.py baseline_source 32
```

The deployed management command and service require both artist and source to be enabled. To guarantee cleanup, the equivalent Django **`call_command("baseline_source", 32)`** was invoked inside one server-side Python process with a `try/finally` wrapper. Only Sijal's artist/source flags were temporarily enabled; the `finally` block immediately restored both to false after the baseline. The existing `verified` state was preserved. Scoped `pilot_temporarily_enabled` and `pilot_disabled` audit events record this operation.

The provider was the deployed `SoundCloudAdapter.list_recent` using yt-dlp metadata extraction, **`skip_download=True`**, **`download=False`**, a **100-entry limit** and 30-second socket timeout. The wrapper imposed a 300-second overall bound, restricted adapter invocation to source 32, and sanitized any diagnostic URL before recording errors. Telegram's request method was guarded/instrumented to refuse calls, with an additional Telegram DNS guard. No provider/downloader/application source was edited.

Observed command output:

```text
Baseline complete: 51 source items; no publication work created.
```

### Results and timestamps

- **51** historical SourceItems stored, all `from_baseline=True`, belonging only to source 32.
- Exactly **one** complete BaselineRun, ID **1**, item count **51**.
- Stored baseline start/completion timestamp: **`2026-10-02T16:26:47.065255+00:00`** (19:56:47.065255 Asia/Tehran). The current service uses its initial `now` value for both fields, so the stored completion time is not a separately measured finish time.
- Actual post-provider observation: **`2026-10-02T16:27:19.746594+00:00`**; elapsed **32.699 seconds**.
- Provider errors: **none observed**. Captured warning/error lists were empty; the adapter's existing quiet/no-warning options remained in effect.
- **41** items supplied release timestamps and matching release dates; **10** supplied no release date and use upload timestamps as the existing adapter's `source_release_at` fallback. Fallback dates must not be described as proven release dates.
- Three records explicitly supplied `album_type=album` and album names **Solojal**, **Serotonin**, **OCD**. Type metadata was absent on the other 48; they were not reclassified as singles/LPs/EPs. Available source timestamps span 2022-07-26 through 2026-09-23.
- This is one bounded profile snapshot. It does not establish full catalog/album-membership coverage, sustained polling reliability or safe polling intervals.

### Stored stable IDs and source metadata

All IDs below are SoundCloud native IDs as persisted under the database uniqueness constraint `(platform, native_item_id)`. Times are UTC. The basis column identifies the 10 upload-time fallbacks; the other 41 times are explicitly reported release times. Type values are provider metadata, not inferred canonical classifications.

| Native ID | Source title | Stored source time (UTC) | Date basis | Reported type / album |
| --- | --- | --- | --- | --- |
| `1311063031` | Tavalod (with Behzad Leito, Alireza Jj & Sohrab Mj) | 2022-07-26T00:00:00Z | release timestamp | not supplied |
| `1440235624` | Istanbul (feat. Sepehr Khalse & Hoomaan) | 2023-02-05T00:00:00Z | release timestamp | not supplied |
| `1440235651` | Koja Gomet Kardam? (feat. The Don) | 2023-02-05T00:00:00Z | release timestamp | not supplied |
| `1440235696` | Oui | 2023-02-05T00:00:00Z | release timestamp | not supplied |
| `1440235720` | Zendegi (feat. Yasna) | 2023-02-05T00:00:00Z | release timestamp | not supplied |
| `1440235738` | Soulmate (feat. Yasna) | 2023-02-05T00:00:00Z | release timestamp | not supplied |
| `1440235753` | Faghat Vase Khodet (feat. Hoomaan) | 2023-02-05T00:00:00Z | release timestamp | not supplied |
| `1440235786` | Ket | 2023-02-05T00:00:00Z | release timestamp | not supplied |
| `1440235840` | Hanooz Vaght Hast (feat. Yasna) | 2023-02-05T00:00:00Z | release timestamp | not supplied |
| `1440235861` | Almas (feat. Yasna) | 2023-02-05T00:00:00Z | release timestamp | not supplied |
| `1440235900` | Ta Al (feat. Behzad Leito) | 2023-02-05T00:00:00Z | release timestamp | not supplied |
| `1440235912` | Pas Ki Bood? (feat. Yasna) | 2023-02-05T00:00:00Z | release timestamp | not supplied |
| `1440235924` | Oh No (feat. Behzad Leito & Sepehr Khalse) | 2023-02-05T00:00:00Z | release timestamp | not supplied |
| `1440235939` | Dobare Zaade Misham | 2023-02-05T00:00:00Z | release timestamp | not supplied |
| `1443622339` | Sijal, Mehrad Hidden & Sepehr Khalse - Nakhla | 2023-02-10T00:00:00Z | release timestamp | not supplied |
| `1561688443` | Ta Al (feat. Behzad Leito) [Shebi Remix] | 2023-07-11T08:09:07Z | upload timestamp fallback | not supplied |
| `1565996071` | Solojal | 2023-02-05T00:00:00Z | release timestamp | album: Solojal |
| `1754874489` | Amanati | 2024-02-23T00:00:00Z | release timestamp | not supplied |
| `1781578662` | Open (feat. Behzad Leito & Sepehr Khalse) | 2024-03-22T00:00:00Z | release timestamp | not supplied |
| `1800068251` | Bargard (feat. Sami Beigi & Behzad Leito) | 2024-04-13T00:00:00Z | release timestamp | not supplied |
| `1802477865` | Bede Fuck (feat. Tahas) | 2024-04-18T00:18:20Z | upload timestamp fallback | not supplied |
| `1802477904` | Bi Ghafiye | 2024-04-18T00:18:25Z | upload timestamp fallback | not supplied |
| `1802477922` | Ey Jan (feat. Sami Beigi & Sepehr Khalse) | 2024-04-18T00:18:28Z | upload timestamp fallback | not supplied |
| `1802477964` | Mama (feat. Mehrad Hidden & KAVIANO) | 2024-04-18T00:18:34Z | upload timestamp fallback | not supplied |
| `1802477985` | Mara Beboos (feat. Dynatonic & parmida) | 2024-04-18T00:18:39Z | upload timestamp fallback | not supplied |
| `1802478078` | Yebare Dige (feat. Isam) | 2024-04-18T00:18:48Z | upload timestamp fallback | not supplied |
| `1802478126` | Yeki Dar Mioon (feat. Canis) | 2024-04-18T00:18:57Z | upload timestamp fallback | not supplied |
| `1811428443` | Serotonin | 2024-04-18T00:00:00Z | release timestamp | album: Serotonin |
| `1956318575` | Oon Nayumadesh | 2024-11-14T00:00:00Z | release timestamp | not supplied |
| `2071557044` | Age Bargardi | 2025-04-12T00:00:00Z | release timestamp | not supplied |
| `2090739858` | Refigha (with Behzad Leito & Sepehr Khalse) | 2025-05-08T00:00:00Z | release timestamp | not supplied |
| `2098969191` | Cheshm Be Raah (with Sijal & Heliyom) | 2025-05-23T00:00:00Z | release timestamp | not supplied |
| `2110845924` | Man Delam Mikhad (with Sijal & Tahas) | 2025-06-29T00:00:00Z | release timestamp | not supplied |
| `2125248369` | Hofre (with Sijal & Sepehr Khalse) | 2025-07-11T00:00:00Z | release timestamp | not supplied |
| `2147740733` | OCD | 2025-11-28T00:00:00Z | release timestamp | album: OCD |
| `2155209837` | Eshghe Alaki (with Sohrab Mj & Heliyom) | 2025-08-22T00:00:00Z | release timestamp | not supplied |
| `2208102152` | Dele Man (with Heliyom) | 2025-11-12T00:00:00Z | release timestamp | not supplied |
| `2218317692` | Hichki Mese Man | 2025-11-28T00:00:00Z | release timestamp | not supplied |
| `2218317695` | Azadi (with Milanium) | 2025-11-28T00:00:00Z | release timestamp | not supplied |
| `2218317698` | 2 Ace (with Catchybeatz) | 2025-11-28T00:00:00Z | release timestamp | not supplied |
| `2218317701` | Bekhatere To (with Heliyom) | 2025-11-28T00:00:00Z | release timestamp | not supplied |
| `2218317704` | Kabol (with Maslak & Darab) | 2025-11-28T00:00:00Z | release timestamp | not supplied |
| `2218317707` | Seda (with Milanium & AHU) | 2025-11-28T00:00:00Z | release timestamp | not supplied |
| `2218317710` | Greece (with Heliyom) | 2025-11-28T00:00:00Z | release timestamp | not supplied |
| `2255168765` | Be Pish Iran | 2026-01-27T16:24:38Z | upload timestamp fallback | not supplied |
| `2318086613` | Leila | 2026-05-13T00:00:00Z | release timestamp | not supplied |
| `2331470378` | Chi Mishe | 2026-06-05T00:00:00Z | release timestamp | not supplied |
| `2339872610` | Miboosamet Are | 2026-06-19T00:00:00Z | release timestamp | not supplied |
| `2368809320` | Vaghti Raft | 2026-07-27T15:51:54Z | upload timestamp fallback | not supplied |
| `2390221908` | Bezar Bad Sham | 2026-09-01T00:00:00Z | release timestamp | not supplied |
| `2399929902` | Shakheye Gol | 2026-09-23T00:00:00Z | release timestamp | not supplied |

### Safety, isolation and idempotence

- Media candidates, media attempts, processing queue items, publications, publication attempts and operator requests: **0 before and after**. No media or publication work was dispatched or queued.
- Instrumented Telegram gateway calls: **0**; Telegram DNS attempts: **0**. No Telegram API request occurred in the pilot process; live/publication configuration remained disabled.
- Adapter source-call IDs: **`[32]`**. Serialized before/after database row comparisons confirmed **all other 56 sources and 29 artists unchanged**. No other source has items or a baseline run.
- A replay of all 51 stored normalized items through the same baseline `_upsert_items` step, inside a rolled-back transaction, reported **0 created**, preserving the item count. A database duplicate-ID query returned **0 duplicates**. This proves same-ID replay deduplication without a second live provider baseline or extra BaselineRun; newly discovered IDs on a later authorized run would be new rows.
- Final counts: **30 artists, 57 sources, 51 SourceItems, 1 complete baseline**. **0 enabled artists and 0 enabled sources**. Sijal's source remains verified; the other 56 remain unverified.
- Scheduled polling remains disabled: no worker/beat service was started, and both Sijal eligibility flags are false. The baseline's `next_poll_at=2026-10-02T16:28:17.065255+00:00` is retained but cannot make this disabled source eligible.
- Final independent database/service verification passed at **`2026-10-02T16:29:51Z`** (19:59:51 Asia/Tehran). All three deployed services were healthy. No application commit, migration, administrator or server configuration change occurred.

This pilot is complete and monitoring/publication remain disabled. Only `M6_OPERATIONS.md` and `STATUS.md` are changed for the documentation handoff. Remaining gates include broader verified-source coverage, backoff/rate-limit measurement, operator request execution, authenticated panel/recovery checks and later controlled activation.

## Controlled Sijal scheduled polling pilot — 2026-10-02

The owner authorized scheduled metadata polling for **Sijal SoundCloud source 32 only**, including worker/beat restart, followed by disabling the source again. The application remained the clean deployed SHA **`44d0c62cd59eb8701d9599ccf8aae5aadb5b46d0`** at `/opt/rapfadrop`. No application commit, migration, administrator, baseline, source verification, media acquisition or Telegram configuration change was authorized or performed.

### Server-only setup and commands

Preflight confirmed source 32 was verified and disabled, artist 16 was disabled, and its one completed baseline contained 51 historical items. All other sources/artists were disabled. Existing web/PostgreSQL/Redis were retained. Temporary worker/beat services used the exact deployed image `sha256:54dfd5b3560d010b26bef7fc7a7b4e75f3db0e997aa0d82d6cfbec14dacf6470`, host networking and the existing server environment through a protected overlay outside the application checkout:

```sh
docker compose -p rapfadrop \
  -f /opt/rapfadrop/compose.internal.yaml \
  -f /var/lib/rapfadrop-operations/polling-pilot.compose.yaml \
  up -d --no-deps --no-build --wait --wait-timeout 90 worker beat
```

The server-only `/var/lib/rapfadrop-operations/polling_pilot.py` loaded the deployed Celery app and instrumented its existing adapter; it did not replace polling/upsert/backoff logic. The corrected process-local Django/Celery configuration asserted that beat contained only `sijal-only-due-poll`, dispatching `sources.tasks.poll_due_artist_sources` every **60 seconds** to dedicated queue **`sijal-pilot`**. Source 32 retained its **90-second** interval; not-yet-due scheduler ticks returned an empty result without provider access. The deployed metadata-only yt-dlp options (`skip_download=True`, `download=False`, 100-entry bound) were retained. Provider instrumentation rejected any source ID other than 32, sanitized errors and guarded Telegram gateway/DNS access. Telegram mode/live/publication worker stayed disabled with no bot/production-target configuration.

```sh
celery -A polling_pilot:app worker -Q sijal-pilot --concurrency=1 \
  --pool=solo --loglevel=INFO --without-gossip --without-mingle \
  --hostname=sijal-pilot@%h
celery -A polling_pilot:app beat --loglevel=INFO \
  --schedule=/pilot-state/celerybeat-schedule --max-interval=5
python3 /var/lib/rapfadrop-operations/poll_pilot_controller.py
```

The root-only controller temporarily enabled **only source 32 and its required artist 16**, recording scoped audit events. It sampled database counts and row fingerprints every 10 seconds, bounded each window to 600 seconds, and installed a 12-minute systemd cleanup watchdog. The beat schedule file persisted across restart. Cleanup disabled both eligibility flags, stopped beat then worker, removed their temporary containers and cancelled the watchdog. Operational scripts/logs/results remained outside Git in the protected operations directory; the wrapper file was readable only through its explicit read-only container bind.

### Observer faults and publication-envelope cleanup

The first window started services at `16:41:04.073054Z`. It observed a successful 51-item poll and then HTTP 403. At `16:43:50.112891Z` the observer incorrectly applied the success timestamp assertion to the failed poll; its `finally` cleanup disabled Sijal and stopped both services by `16:43:53.381335Z`. This was an observer error, not a polling transaction failure. The observer was corrected to check success and failure timestamps separately, including the deployed exponential backoff formula.

Inspection also found that the initial process-local Celery schedule assignment had been overwritten by lazy loading of Django settings. That beat dispatched **six publication task envelopes** to the default Redis `celery` queue. The worker consumed only `sijal-pilot`, so none of those envelopes executed. All publication/attempt/database queue counts stayed zero and no Telegram call occurred. The six decoded envelopes were checked to contain only `publication.tasks.process_due_publications` and removed individually with Redis `LREM`; no unrelated broker data was purged. Default queue length was then zero. **Consequently, an absolute claim that no publication work was queued during the entire pilot would be false**, even though no publication worker ran and no durable publication work was created.

The wrapper was corrected by setting process-local `settings.CELERY_BEAT_SCHEDULE`/`CELERY_TASK_ROUTES`, forcing `app.config_from_object(..., namespace="CELERY", force=True)` and asserting the single polling schedule before startup. A disposable startup/import check without provider requests passed at `16:45:36.475041Z`; corrected beat logs contained only the polling schedule. Corrected services started at `16:46:08.821669Z`. No project file or persisted `.env` was changed by these corrections.

### Observed due polls and restart

All times below are **UTC on 2026-10-02**. Successful polls each returned the existing **51 IDs** listed in the baseline section above. Failure audits contain `SourceUnavailable` wrapping yt-dlp's `DownloadError`: `Unable to download JSON metadata: HTTP Error 403: Forbidden`. A 403 does not prove rate limiting; there was no observed 429 or Retry-After response.

| Window / audit ID | Poll start (stored success/error time) | Audit completion | Result / provider seconds | Stored next due | Failure count |
| --- | --- | --- | --- | --- | --- |
| Initial / 9 | 16:41:38.339832 | 16:42:07.169101 | 51 existing items / 28.769 s | 16:43:08.339832 | 0 |
| Initial / 10 | 16:43:38.343342 | 16:43:38.699920 | HTTP 403 / 0.313 s | 16:45:08.343342 | 1 |
| Corrected / 13 | 16:46:42.800338 | 16:47:13.247678 | 51 existing items / 30.362 s | 16:48:12.800338 | 0 |
| Corrected / 14 | 16:48:42.795259 | 16:48:43.169942 | HTTP 403 / 0.350 s | 16:50:12.795259 | 1 |
| Corrected, after restart / 15 | 16:50:42.791639 | 16:50:43.588396 | HTTP 403 / 0.770 s | 16:53:42.791639 | 2 |
| Corrected, after restart / 16 | 16:53:42.800639 | 16:54:12.813316 | 51 existing items / 29.948 s | 16:55:12.800639 | 0 |

The application stores its initial poll `now` in `last_success_at` or `last_error_at`; audit completion is measured separately. Success advances next due by exactly 90 seconds, resets failures and clears the error. Failure preserves last success and sets next due from error time using `min(90 * 2 ** (failures - 1), 21600)` seconds. The observed consecutive failures produced **90 then 180 seconds**, survived restart, and were cleared by the final success. The 60-second beat cadence explains approximately 30-second lateness on some due polls; no early provider retry was observed. Higher backoff steps, the six-hour cap and explicit 429 handling were not exercised.

Restart began at **`16:48:45.826710Z`** and completed at **`16:49:15.379633Z`**. With both Compose files above, the controller executed:

```sh
docker compose ... stop -t 30 beat
docker compose ... restart -t 90 worker
docker compose ... up -d --no-deps --no-build --wait --wait-timeout 90 worker beat
```

Here `...` means the same project and two absolute `-f` paths shown above. The scheduler state directory was retained. Database fingerprints were identical before and immediately after restart, and remained identical through two further due polls, including the final successful 51-item upsert. Corrected logs show **8 polling task dispatches**: **4 due provider calls** and **4 empty/not-yet-due task results**, with **0 publication task dispatches**. The completed corrected window lasted **522.865 seconds**; the aborted initial window lasted **200.991 seconds**. These are bounded observations, not evidence that a 90-second source interval is sustainable: three of six provider calls returned 403.

### Final safety and persisted state

- SourceItem row/content fingerprint matched the pre-pilot value throughout both windows and restart: **51 rows**, all historical `from_baseline=True`, **0 new rows**, **0 duplicate `(platform, native_item_id)` groups**. One completed BaselineRun was unchanged; no new baseline ran.
- ProcessingQueueItem, MediaCandidate, MediaAttempt, Publication, PublicationAttempt and OperatorActionRequest counts stayed **0**. No audio download, media task or publication execution occurred. The initial six discarded Redis publication envelopes are the exception documented above; the corrected window queued none.
- Instrumented provider-call IDs were **`[32, 32, 32, 32, 32, 32]`**. Other **56 source rows**, **29 artist rows** and other-source audit fingerprints matched throughout and across both windows. Their enabled/verification state was unchanged.
- Telegram gateway/DNS guard events: **0** across both windows. Telegram API calls: **0 observed**; bot/production target absent, Telegram and publication configuration disabled throughout, publication workers never consumed a queue.
- Cleanup completed at **`16:54:19.448832Z`**; both stop commands returned 0. Final controller verification at **`16:54:21.586538Z`** confirmed source 32 and artist 16 disabled and temporary worker/beat containers removed. The watchdog is inactive. Server-only evidence remains in `/var/lib/rapfadrop-operations/polling-pilot.result.json`, `polling-pilot.logs` and their `.attempt1` copies.
- Independent final readback at **`16:55:45Z`** confirmed **30 artists, 57 sources, 0 enabled artists/sources, 1 verified source, 51 historical items, 1 baseline and 0 duplicate IDs**. Redis `celery` and `sijal-pilot` queue lengths were **0**. Sijal retained `last_success_at=2026-10-02T16:53:42.800639+00:00`, `next_poll_at=2026-10-02T16:55:12.800639+00:00`, failure count 0 and an empty error; being disabled makes that timestamp ineligible for polling.
- Only original web/PostgreSQL/Redis services remained, all healthy. Server-IP `/health/` returned HTTP 200 with `{"status":"ok","database":"ok"}`. DEBUG=false, persisted `.env` fingerprint, clean deployed SHA, Nginx hashes and normalized IPv4/IPv6/nftables firewall snapshots were unchanged. Timestamp comments from `iptables-save` were excluded when comparing rules.

This controlled pilot is stopped. Polling, media/publication and Telegram remain disabled. Documentation-only delivery changes `M6_OPERATIONS.md` and `STATUS.md`; the server application SHA is unchanged. The stored-item/restart/isolation and observed error-backoff checks passed, but the initial publication-envelope scheduling requirement failed and was corrected. Further activation needs provider 403 diagnosis and a measured sustainable interval; permanent worker/beat operation, broader source coverage, explicit rate-limit behavior and media/publication recovery remain deferred.

## Controlled Spotify metadata pilot — 2026-10-03

The owner authorized deployment of the already-pushed SpotifyScraper 3.9.2 implementation and metadata-only activation. Times in this section are server UTC on 2026-10-03; Tehran is UTC+03:30. The server checkout was clean at `44d0c62cd59eb8701d9599ccf8aae5aadb5b46d0` and `/health/` returned HTTP 200 before work. The final deployed SHA is **`af0819bfeabd9a19b7bbdb9d007a3adfff947f71`**. The five Spotify source IDs below are distinct from the earlier Sijal SoundCloud source 32, which remains disabled.

### Interrupted-backup recovery and deployment

The protected archive `/var/backups/rapfadrop/pre_spotify_20261003.dump` (171,999 bytes, mode 0600, root-only directory) and SHA-256 sidecar (mode 0600) passed `sha256sum --check`; `pg_restore --list` parsed the archive. The interrupted run had restored it into disposable `spotify_restore_20261003`. Production and restore each had **37 tables, 30 artists and 57 sources**. A canonical row-content hash across every table matched exactly: `b2386785c7b71a128d502c3fb88f0f3735218a0fec4651e58b19ad4965b7790f`, with zero table mismatches. Raw `pg_dump --data-only` byte hashes differed, so they were not used as proof of restored content. After the row comparison, only `spotify_restore_20261003` was dropped; `psql -lqt` confirmed it absent. The protected archive remains for recovery.

Deployment used `git fetch origin main`, verified `origin/main` equals the exact SHA, `git checkout af0819bfeabd9a19b7bbdb9d007a3adfff947f71`, `docker compose -p rapfadrop -f compose.internal.yaml config --quiet`, and `build web`. The dedicated web image was recreated using `up -d --no-deps --no-build --wait --wait-timeout 90 web`. `migrate --noinput` applied **no migrations**; `migrate --check`, `makemigrations --check --dry-run`, and `manage.py check` passed. Web, PostgreSQL and Redis were healthy; `/health/` returned `{"status":"ok","database":"ok"}`. Server `.env` retained `TELEGRAM_MODE=disabled`, live/publication flags false, and no bot token. No application source was edited on the server.

### Identity, baseline and scheduled polling

The deployed read-only `probe_spotify_pilot --rounds 3` compared each stored source ID and live artist name with the database artist record before querying its full discography. All five matched; each of three complete polls per profile returned the same ID-set digest. The probe used **43 metadata HTTP requests**: two per artist identity plus three rounds of three requests for Sijal and two for each other artist. Each first/second/third discography call completed in seconds, with no reported error. A further read-only overlap check found no release IDs shared among the five profiles. No Premium, credentials, cookies, audio or Telegram access was used.

| Artist | Identity lookup latency (s) | Three complete discography latencies (s) | Metadata requests per discography call |
| --- | ---: | --- | ---: |
| Sijal | 0.587 | 0.778, 0.239, 0.272 | 3 |
| Fadaei | 0.428 | 0.290, 0.257, 0.224 | 2 |
| Ho3ein | 0.877 | 0.451, 0.138, 0.154 | 2 |
| Hichkas | 0.418 | 0.197, 0.195, 0.165 | 2 |
| Yas | 0.683 | 0.197, 0.188, 0.293 | 2 |

| Artist | Spotify source ID | Live identity | IDs per complete poll | Discography pages | Baseline time UTC | Final state |
| --- | ---: | --- | ---: | ---: | --- | --- |
| Sijal | 31 | exact | 89 | 2 | 13:10:42 | verified, enabled |
| Fadaei | 39 | exact | 33 | 1 | 13:10:44 | verified, enabled |
| Ho3ein | 48 | exact | 7 | 1 | 13:10:45 | verified, enabled |
| Hichkas | 42 | exact | 11 | 1 | 13:10:45 | verified, enabled |
| Yas | 44 | exact | 37 | 1 | 13:10:46 | verified, enabled |

Each source was enabled only for its own baseline, then paused until all five succeeded. The five completed baselines stored **177 historical Spotify SourceItems**, all marked `from_baseline`, without review, processing, media or publication work. Their `poll_interval_seconds` is **180**. No source failed identity or page validation; all five were enabled for polling at `13:13:13Z` after baseline inspection. Audit events record identity verification, the baseline pause and polling enablement. All other sources remain unchanged.

The server-only, protected `/var/lib/rapfadrop-operations/spotify-pilot.compose.yaml` layers onto `compose.internal.yaml`. It keeps host networking, the deployed `rapfadrop-web:latest` image, Spotify mode `spotifyscraper`, Telegram/publication switches disabled, and a single worker consuming only the `spotify-pilot` Redis queue. A read-only mounted `/var/lib/rapfadrop-operations/spotify_pilot.py` asserts those guards after Django/Celery lazy loading, installs only `spotify-pilot-poll` every **60 seconds**, and routes that task to the dedicated queue. This specifically avoids the stale publication-envelope fault seen in the earlier SoundCloud pilot. `docker compose ... config --quiet`, wrapper startup assertion, and web health passed before activation. Worker and beat started at approximately `13:11:58Z` and remained running. Their logs showed only `spotify-pilot-poll` dispatches; Redis default and pilot queues both measured zero after processing.

Three scheduled provider cycles per source succeeded at approximately **13:13:58–14:00Z**, **13:16:58–17:00Z**, and **13:20:58–21:00Z**. Worker task durations were **1.801, 1.832 and 1.744 seconds** for each five-source due batch. Each batch made the expected 11 Spotify metadata requests (Sijal 3; four other artists 2 each) and returned 89/33/7/11/37 IDs again. Beat dispatched every 60 seconds; non-due ticks returned `{}`. The third provider batch occurred 240 seconds after the second because the 13:19:58 tick ran just before the stored due timestamp and correctly skipped, then the 13:20:58 tick polled. Thus the configured 180-second source interval was respected without an early request, while observed provider spacing was 180 then 240 seconds. A further five-source batch succeeded at 13:24:58–25:00Z while documentation was prepared.

Final readback after the required three cycles found five enabled/verified Spotify sources, **177 Spotify SourceItems with 177 baseline flags**, no duplicate native Spotify IDs, three successful poll audits per source, zero poll-failure audits or consecutive failures, and zero reviews, matches, processing queue items, media candidates/attempts, publications/attempts and broker queue entries. No historical post, audio download or Telegram send was observed. Worker and beat were running, and web/PostgreSQL/Redis were healthy. Server-side `manage.py test sources.test_spotify_scraper` passed **10 tests** against a temporary test database, including a simulated 429 retry-after and independent SoundCloud progress. No live 401/403/429 or failure/backoff event occurred during this window; live failure independence remains unmeasured. No new release ID appeared, so detection latency cannot be inferred from these historical polls.

Commands and server-only evidence scripts are retained under `/var/lib/rapfadrop-operations/spotify_*` and the protected Compose overlay. The operational command is `docker compose -p rapfadrop -f /opt/rapfadrop/compose.internal.yaml -f /var/lib/rapfadrop-operations/spotify-pilot.compose.yaml`; it must be used for future web/worker/beat management so the Spotify mode and disabled-publication guards persist. The project checkout remained clean at the exact deployed SHA after verification. Production publication remains disabled.

## Controlled Spotify-to-media bridge deployment — 2026-10-03

The owner authorized this slice after the metadata-only pilot. The tested application SHA is **`0214e6dff71b3ac223bd4deddbe07ccd8ae13402`**, pushed normally to `origin/main`; server times below are UTC. No migration was added. This section records a live metadata pilot, not a production publication test.

The server preflight at `14:21–14:23Z` found the checkout clean at `af0819bfeabd9a19b7bbdb9d007a3adfff947f71`, healthy web/PostgreSQL/Redis and the existing isolated Spotify worker/beat. A fresh protected `pg_dump --format=custom` archive, `/var/backups/rapfadrop/pre_spotify_bridge_20261003.dump`, was created at `14:22:14Z` before checkout or service changes. It is **182,114 bytes**, mode **0600**, in the root-only backup directory, with a mode-0600 SHA-256 sidecar. `sha256sum --check` and `pg_restore --list` passed. Restoring into a disposable `spotify_bridge_restore_20261003` database and comparing canonical row-content digests across all **37** public tables produced identical source/restore digests `1fcceae9179e7d5ea38fc0609cf1a01b37d4a98a8ee49b060c084f5586169c49`, with `mismatches []`; only the disposable database was dropped. Verification completed at `14:23:36Z`. The initial streaming shell invocation consumed its remaining stdin after the dump, so checksum/restore comparison was rerun from a protected script; the corrected script completed with `set -eu` and the result above. The archive remains protected on the server.

Deployment used `git fetch origin main`, exact-SHA comparison, `git checkout 0214e6dff71b3ac223bd4deddbe07ccd8ae13402`, the established `docker compose -p rapfadrop -f compose.internal.yaml -f /var/lib/rapfadrop-operations/spotify-pilot.compose.yaml` configuration, `config --quiet`, `build web`, and `up -d --no-deps --no-build --wait --wait-timeout 90 web worker beat`. The bridge switch was **OFF** during this deployment. `migrate --noinput` applied no migrations; `migrate --check`, `makemigrations --check --dry-run`, and `manage.py check` passed. `/health/` returned HTTP 200 with database `ok`; web, worker and beat were healthy. The deployed temporary-database focused suite passed **25 tests**. Before activation, five verified/enabled Spotify sources (31 Sijal, 39 Fadaei, 42 Hichkas, 44 Yas, 48 Ho3ein) retained the 180-second interval and zero failures; there were exactly **177 historical and zero new Spotify items**, zero duplicate IDs, and zero reviews, matches, queue items, media candidates/attempts or publications/attempts. Redis default and `spotify-pilot` queue lengths were zero.

The server-only bridge configuration lives outside Git in protected `/var/lib/rapfadrop-operations/spotify-bridge.compose.yaml` and `spotify_bridge_pilot.py`, layered **after** the metadata pilot overlay. It sets `RAPFADROP_SPOTIFY_MEDIA_BRIDGE_ENABLED=true` only on the pilot web/poll/beat and a new dedicated `spotify-media` worker; Telegram mode remains `disabled`, live/publication flags remain false, and there is no bot token. The new worker consumes only `spotify-media` and mounts the same named `rapfadrop_media_data` volume at `/var/lib/rapfadrop/media` as web. The metadata worker remains isolated on `spotify-pilot`. The wrapper asserts the safety switches and mount path, routes only the metadata poll and bounded media task to their separate queues, and gives beat exactly those two 60-second schedules. A disposable wrapper import, Compose validation, and a media-volume writability check passed before activation. A pre-activation database readback at `14:27:09Z` showed zero new IDs/jobs/media. The four application services were recreated/started with all three Compose files at `14:27:37Z`; PostgreSQL and Redis remained running. Web health stayed HTTP 200/database `ok`.

At `14:28:31–33Z`, beat dispatched the metadata poll and media task to their separate queues. All five due metadata polls succeeded in **2.580 seconds**, with the same 177 IDs; the media task returned `{}` in **0.028 seconds** because there were no candidates. The media queue length was zero after consumption. No media file, media attempt, Telegram call or publication task was observed. Further observation and the final database/service readback follow below.

### Extended post-activation observation, 2026-10-04

The protected server log summary captured activity from `2026-10-03T14:27:30Z` through the final readback. It recorded **978 successful, empty** `media_pipeline.tasks.process_spotify_bridge_media` executions, **zero nonempty media-task results**, **284 metadata batches with at least one success**, **zero publication task dispatches/receipts**, and **zero worker task errors/tracebacks**. The log was retained outside Git as mode-0600 `/var/lib/rapfadrop-operations/spotify_bridge_runtime.log`. Metadata polls continued at the 60-second beat cadence, with due source calls approximately every 180 seconds; no new Spotify release ID appeared, so real discovery-to-ready latency remains unmeasured.

There was one real provider failure: Sijal source 31 logged `SpotifyMetadataError: Spotify metadata request failed: NetworkError` at `2026-10-03T18:50:36.248145Z` with a **180-second** retry interval. In the same batch, Fadaei, Hichkas, Yas and Ho3ein each succeeded with their unchanged 33/11/37/7 items. Sijal recovered at `18:53:32.350200Z` with its unchanged 89 items; its consecutive-failure count returned to zero. This is observed source-level failure independence and recovery, not evidence of a 401/403/429 rate limit. At the `2026-10-04T06:43:31Z` readback, the per-source success/failure audit counts were Sijal **304/1**, Fadaei **305/0**, Hichkas **305/0**, Yas **305/0**, Ho3ein **305/0**. All five remained verified/enabled with a 180-second source interval and zero current failures.

The final state/health script ran at `2026-10-04T06:42:27Z`: server checkout clean at **`0214e6dff71b3ac223bd4deddbe07ccd8ae13402`**, `/health/` HTTP 200/database `ok`, web/PostgreSQL/Redis healthy, metadata worker/beat/media worker running. Spotify items were **177/177 historical**, **0 new**, with **0 duplicate stable IDs**; reviews, source matches, processing queue jobs, media candidates, media attempts, publications and publication attempts were each **0**. The shared media volume contained **0 files**. Redis `spotify-pilot` and `spotify-media` queues were empty. No media acquisition or Telegram API activity was observed; Telegram mode/live/publication remain disabled and the server wrapper asserts no bot token. One envelope remained in Redis's **unconsumed default `celery` queue**. Header-only inspection identified it as `celery.backend_cleanup` housekeeping, not a publication task; it was left untouched. This is a broker housekeeping backlog to address separately if it accumulates.

For ongoing operations, use all three Compose files in order: `compose.internal.yaml`, `/var/lib/rapfadrop-operations/spotify-pilot.compose.yaml`, and `/var/lib/rapfadrop-operations/spotify-bridge.compose.yaml`. The server-only scripts `spotify_bridge_backup_verify.sh`, `spotify_bridge_final.sh`, `spotify_bridge_final_data.py`, `spotify_bridge_failure.py`, `spotify_bridge_state.py` and `spotify_bridge_log_summary.sh` record the reproducible verification commands. The bridge is enabled **only for future real discoveries**; historical baseline items were neither reprocessed nor converted to jobs. No production publication was enabled. No real new ID has yet exercised the automatic media path, so live provider acquisition and release-to-ready latency remain unverified.
