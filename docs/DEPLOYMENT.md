# Deployment and verification

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
