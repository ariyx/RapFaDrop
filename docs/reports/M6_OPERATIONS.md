# M6 operations evidence

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
