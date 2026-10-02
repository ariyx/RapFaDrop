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

Follow-up requires an intended deployment directory, a RapFaDrop panel domain, Docker/Compose installation, and a host/network/proxy plan that preserves the existing site. Server configuration work and the remaining Phase 2 gates await further scope authorization. No production-readiness claim is made.
