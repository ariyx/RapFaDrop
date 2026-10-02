# M6 operations evidence

Observed on 2026-10-02. Owner authorization for this run was **Phase 2 server preflight and reporting only**. All server commands were read-only; no application commit was deployed, migrations run, account created, source enabled, or Telegram request made. M6 is incomplete.

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

M6 remains incomplete: backup/restore, schema migrations, full panel readiness, HTTPS for RapFaDrop, accounts, restart/recovery and controlled source/publication activation remain later gates. This is an owner-authorized HTTP connectivity deployment only.
