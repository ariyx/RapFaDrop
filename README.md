# RapFaDrop

Self-hosted Persian rap release monitor and Telegram archive for the owner's curated artist list.

**Status:** M0 foundation. Provider feasibility is recorded from observed probes in `docs/reports/`; no Telegram publishing is implemented.

## Local M0 setup

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

## Start here

- [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md) — product decisions, seed artists and source profiles, captions, admin rules and open field tests (English).
- [`docs/IMPLEMENTATION.md`](docs/IMPLEMENTATION.md) — architecture, data model, workflows, milestones, acceptance evidence and first coding-agent task (English).
- [`docs/AGENTS.md`](docs/AGENTS.md) — full coding-agent instructions (English). The root [`AGENTS.md`](AGENTS.md) points agents here automatically.
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — repeatable local verification, exact-SHA server deployment, safety checks and milestone completion record.
- [`docs/STATUS.md`](docs/STATUS.md) — observed repository status, outstanding empirical gates and the exact next implementation handoff.
- [`docs/M0_AGENT_TASK.md`](docs/M0_AGENT_TASK.md) — scoped, copyable coding-agent task and acceptance report for M0.

The first implementation slice is repository setup and Dockerized feasibility probes against the owner's SoundCloud examples and public Spotify metadata. Audio publishing to the live channel starts only after the corresponding integration checks and configuration.

Repository: <https://github.com/ariyx/RapFaDrop.git>
