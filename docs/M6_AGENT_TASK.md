# M6 coding-agent task — server readiness, test-channel verification, and controlled activation

Read `AGENTS.md`, `docs/STATUS.md`, `docs/DEPLOYMENT.md`, `docs/PRODUCT_SPEC.md`, `docs/IMPLEMENTATION.md`, `docs/M4_AGENT_TASK.md`, `docs/M5_AGENT_TASK.md`, and all M0–M5 reports before acting. Add this file as `docs/M6_AGENT_TASK.md`.

## Goal

Complete the operational readiness of RapFaDrop: verify the real Telegram integration only in an isolated test channel, deploy an exact Git commit to the server, protect data and secrets, validate recovery, and activate verified sources through a controlled baseline without publishing historical material.

Production publication to `@RapFaDrop` is the final activation step. It must remain disabled until every required gate below is observed and documented.

## Required inputs

Use only local/server configuration, never Git, for:

- Telegram bot token, isolated test-channel ID, optional review-channel ID, and production-channel ID
- server SSH authentication
- PostgreSQL password and Django secret key
- deployment domain and reverse-proxy TLS contact/configuration, when available
- initial named administrator accounts

If an input is missing, complete independent checks, record the precise blocker, and leave the dependent gate open.

## Phase 1 — real test-channel verification

Use the opt-in M4 live integration probe with `RAPFADROP_TELEGRAM_MODE=test`, explicit live enablement, and an isolated test-channel ID. Ensure the production channel is rejected.

Observe and record:

1. send of disposable prepared audio;
2. correct caption, official file metadata, and artwork;
3. in-place edit of the same Telegram message using its stored message ID;
4. correction reply creation and scheduled deletion;
5. stored publication URL/message ID and restart-safe state;
6. refusal to send to the production channel.

Never use the production channel for this probe. Clean disposable test-channel messages/files when the evidence has been recorded.

## Phase 2 — server preflight

1. Authenticate to the server with SSH keys or an approved secure method. Do not place passwords in commands, prompts, reports, Git, shell history, or environment output.
2. Locate/create the intended RapFaDrop checkout and verify repository remote, clean status, deployed SHA, Docker/Compose availability, disk space, firewall, and service ports.
3. Create a server-only `.env` from `.env.example` with strong generated secrets and server values. Restrict its filesystem permissions. Keep PostgreSQL/Redis private to Docker/internal networking.
4. Configure a production media volume and PostgreSQL named volume. Do not use `docker compose down -v`.
5. Configure HTTPS for the private panel using the chosen domain and reverse proxy. Restrict `DJANGO_ALLOWED_HOSTS`, set production debug false, secure cookies, trusted CSRF origins, and proxy headers as required.
6. Create a recoverable PostgreSQL backup before migrations. Perform and document one restore validation using a non-production copy or safe test database before calling backups reliable.

## Phase 3 — exact-SHA deployment and recovery

Deploy only the final commit SHA that was pushed and reviewed locally.

1. Fetch Git, verify that exact SHA, and check out that detached SHA or an immutable release branch.
2. Run `docker compose config --quiet`, build images, bring services up, run migrations after backup, and verify service health and the authenticated health endpoint.
3. Create initial separate administrator accounts through the documented secure bootstrap flow. Verify that credentials do not appear in logs.
4. Restart web, worker, beat, and the full Compose stack one at a time where safe. Verify durable PostgreSQL state, media candidates, publication IDs, queue records, and audit history remain intact.
5. Verify logs, health endpoint, reverse-proxy TLS, private-panel login, and backup schedule/retention. Record actual commands/results without secrets.

Never edit application source directly on the server. If a defect appears, fix locally, test locally, commit/push, and redeploy the new exact SHA.

## Phase 4 — controlled source activation

Do not enable all 57 candidates at once.

1. In the panel, verify source identity and current official profile evidence for a small SoundCloud pilot set.
2. Enable one verified source, run its first baseline, and inspect stored source items. Confirm that no historical work enters media or publication queues and no Telegram message is sent.
3. Repeat for a small pilot group. Confirm idempotent restart/baseline behavior, source-specific backoff, queue visibility, Persian display/aliases, and no cross-source contamination.
4. Keep Spotify release polling disabled until a bounded working method is empirically verified. Its failure must not affect SoundCloud.
5. Expand the verified SoundCloud allowlist gradually only after observed stability and rate-limit behavior are acceptable.

## Phase 5 — production publication activation

Only after Phases 1–4 are complete:

1. Set the production channel ID explicitly and switch Telegram mode to production through server-only configuration.
2. Confirm the bot has the required administrator permissions in `@RapFaDrop`.
3. Keep sources/baselines unchanged; do not backfill historical releases.
4. Start with one verified source and closely observe a newly discovered, confidently identified, complete prepared release.
5. Confirm one publication, correct caption/tag/artwork, durable message ID/URL, queue cleanup, and audit record.
6. If a fault occurs, disable publication worker/source through configuration or panel, preserve evidence, and recover from durable state without duplicate posting.

## Acceptance criteria

M6 is complete only when documentation includes observed evidence for:

- real isolated test-channel send, edit, correction deletion, and production-target safeguard;
- exact server SHA, Compose/health/migration results, HTTPS/private-panel access, and separate admin accounts;
- a tested recoverable database backup/restore;
- restart durability for database, queue, publications, and audit state;
- pilot source baseline with zero historical channel posts;
- measured source success/failure/backoff behavior;
- controlled production activation with no duplicate or historical publication, if the owner has completed Phase 5.

If Phase 5 is intentionally deferred, report the deployment as production-ready but publication disabled. Do not label the channel live.

## Documentation and completion report

Update `docs/STATUS.md`, `docs/DEPLOYMENT.md`, `docs/PRODUCT_SPEC.md` if operational defaults changed, and add `docs/reports/M6_OPERATIONS.md`.

Report:

```text
Exact deployed SHA:
Test-channel probe results:
Server preflight and HTTPS results:
Backup/restore and restart results:
Admin/account results:
Pilot source/baseline results:
Production publication status and observed result, or blocker:
Open risks and follow-up work:
```

