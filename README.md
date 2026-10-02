# RapFaDrop

Self-hosted Persian rap release monitor and Telegram archive for the owner's curated artist list.

**Status:** M4 publication orchestration and captions are implemented. Normal tests use a fake gateway; live Telegram integration remains unverified until an isolated test-channel probe passes. Observed evidence is in `docs/reports/`.

## Local setup

Requirements: Docker Engine with Compose. Copy `.env.example` to `.env` once, replace both placeholder secrets locally, and never commit `.env`.

```powershell
Copy-Item .env.example .env
docker compose config --quiet
docker compose up --build -d
docker compose exec web python manage.py migrate --noinput
docker compose exec web python manage.py check
docker compose exec web python manage.py test
Invoke-RestMethod http://localhost:8000/health/
docker compose ps
```

Stop the stack without deleting PostgreSQL data:

```powershell
docker compose down
```

## Opt-in read-only probes

Probes never run at service startup or test discovery. They print sanitized JSON and omit signed media URLs. Redirect output to a local file when needed.

```powershell
docker compose exec -T web python manage.py probe_soundcloud `
  https://soundcloud.com/sijalofficial/vaghti-raft `
  https://soundcloud.com/sijalofficial/sets/ocd

docker compose exec -T web python manage.py probe_spotify `
  5F0BGBdSL945Bzxrq8aGbn 5aWL79DpD45MzDMwCTZqsN 5vVveQB8n4kETe67waTS3t

docker compose exec -T web python manage.py probe_media `
  https://soundcloud.com/sijalofficial/vaghti-raft
```

The media command downloads into an OS temporary directory, runs `ffprobe`, and removes the directory before returning. It does not publish or retain audio. A nonzero exit means the structured result contains a concrete error.

## M4 test-channel commands

Publication is disabled by default. Keep bot credentials in the ignored local `.env`. Live commands require `RAPFADROP_TELEGRAM_MODE=test`, `RAPFADROP_TELEGRAM_LIVE_ENABLED=true`, a bot token and an isolated `RAPFADROP_TELEGRAM_TEST_CHAT_ID`. Configure a separate review destination for notifications. Production username `@RapFaDrop` and its configured numeric ID are blocked, including target aliases resolved by `getChat`.

```powershell
docker compose exec -T web python manage.py probe_telegram --configuration-status
# Explicit live probe: generated audio passes through M3, then send/edit/reply/delete.
docker compose exec -T web python manage.py probe_telegram --confirm-test-send
# Explicit publication of an existing ready candidate or fully staged canonical album.
docker compose exec -T web python manage.py publish_ready --candidate-id <ID> --confirm-test-send
docker compose exec -T web python manage.py publish_ready --album-id <ID> --confirm-test-send
```

The publication worker remains disabled unless `RAPFADROP_PUBLICATION_WORKER_ENABLED=true` is explicitly configured. It processes reserved work, definite-failure retries, album cursors and due correction deletions; it does not activate sources or discover new work. Uncertain outcomes appear in Django admin and require observed operator evidence through `reconcile_publication`; they are never blindly resent. Published media is retained for upgrades and safe recovery. The disposable live probe removes its confirmed test posts and generated media; an incomplete probe retains candidate files needed for reconciliation.

## Start here

- [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md) — product decisions, seed artists and source profiles, captions, admin rules and open field tests (English).
- [`docs/IMPLEMENTATION.md`](docs/IMPLEMENTATION.md) — architecture, data model, workflows, milestones, acceptance evidence and first coding-agent task (English).
- [`docs/AGENTS.md`](docs/AGENTS.md) — full coding-agent instructions (English). The root [`AGENTS.md`](AGENTS.md) points agents here automatically.
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — repeatable local verification, exact-SHA server deployment, safety checks and milestone completion record.
- [`docs/STATUS.md`](docs/STATUS.md) — observed repository status, outstanding empirical gates and the exact next implementation handoff.
- [`docs/M0_AGENT_TASK.md`](docs/M0_AGENT_TASK.md) — scoped, copyable coding-agent task and acceptance report for M0.

The first implementation slice is repository setup and Dockerized feasibility probes against the owner's SoundCloud examples and public Spotify metadata. Audio publishing to the live channel starts only after the corresponding integration checks and configuration.

Repository: <https://github.com/ariyx/RapFaDrop.git>
