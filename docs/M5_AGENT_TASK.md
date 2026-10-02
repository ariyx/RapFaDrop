# M5 coding-agent task — administration, configuration, and observability

Read `AGENTS.md`, `docs/STATUS.md`, `docs/PRODUCT_SPEC.md`, `docs/IMPLEMENTATION.md`, `docs/M4_AGENT_TASK.md`, and completed M0–M4 reports before changing code. Add this file as `docs/M5_AGENT_TASK.md` before implementation.

## Goal

Implement M5 only: the private Django administration panel, separate equal-permission administrator accounts, safe operational settings, review/error/manual-upload workflows, audit history, and basic observability.

Do not deploy to the server, enable source monitoring against real profiles, run a real baseline, send to the production channel, or begin M6.

## Scope and existing behavior

M1–M4 already provide artists/sources, reviews, queue state, media candidates/manual upload, publications, templates, and fake Telegram behavior. M5 must make these capabilities operable through a coherent private Django panel. Reuse those domain services; do not duplicate lifecycle logic in views.

Use Django templates and Django admin/custom admin views. Do not add a separate frontend framework.

## Accounts, access, and audit

1. Provide separate named administrator accounts. Do not create or document a shared account.
2. Create one application admin role/group with the same operational permissions for all approved admins: artist/source control, review decisions, template/settings edits, manual upload, retry/requeue, and operational views.
3. Use Django's password hashing and authentication. Provide a safe staff bootstrap/manage command that reads credentials from interactive input or environment only; never commit credentials.
4. Provide admin-initiated password reset or reset-link generation for another admin, with an audit event. Do not expose passwords in UI, logs, or audit data.
5. Require login for every panel route. Enforce CSRF, secure redirect handling, and permission checks at the view/service layer.
6. Record actor, timestamp, object, action, before/after summary, and correlation/reference ID for consequential actions. Audit records are read-only in the panel and cannot be silently altered through ordinary UI actions.

## Required panel areas

### Artists and sources

- List/search/filter 30 artists, aliases, source platform, verification, enabled state, last success/error, next due poll, and baseline state.
- Verify or reject a candidate profile with evidence/notes, enable/disable only verified sources, and trigger safe manual poll/baseline actions.
- Make the risk visible when an admin attempts to enable a source without baseline completion. Do not silently run a production baseline in tests.

### Reviews and identity

- List/filter review items by reason, age, source, release/track, and state.
- Show source evidence and proposed match. Support approve, reject, correct, and requeue through M2 services.
- Include durable links to canonical item, source item, queue item, media candidate, and publication when available.

### Media and queue

- Show candidate validation/tag/artwork facts, provider attempts, retry due times, and safe local diagnostics.
- Surface M3 manual upload for an identified item and display validation failures without exposing stored media directly.
- List queue items and publication attempts. Allow safe retry/requeue only through idempotent domain services.

### Templates and settings

- Manage versioned caption templates and tag policy values through forms.
- Support only documented variables and conditional blocks. No arbitrary Python, unrestricted template execution, JavaScript injection, or unescaped raw markup.
- Render a preview with realistic fixtures before activation. Validate Telegram escaping/entities and show omitted optional rows.
- Make correction-reply deletion timeout configurable, defaulting to 10 minutes.
- Keep the approved previous-single marker as `›`. Ensure the UI/default template does not use `•`.
- Store active template/settings version and audit every change. Existing publications retain their stored template version.

### Publications and operations

- Show publication message IDs/URLs, state, caption version, upgrade/edit attempts, album session cursor, and reconciliation status.
- Provide a compact metrics view: source success/failure counts, review backlog, queue state counts, media provider outcomes, and discovery-to-ready/published timing where data exists.
- Add admin notification configuration fields only as placeholders/local settings. A Telegram notification send requires M4 gateway configuration and must be test-channel safe.

## Input and data handling

- Escape all remote/user-controlled text in HTML and Telegram previews.
- Validate uploaded file type/size using M3 policy; keep media outside static/public directories.
- Do not expose bot tokens, raw source payloads, signed media URLs, absolute server paths, or credentials in the panel.
- Keep Persian text and aliases correct in forms, search, filters, exports, and audit summaries.

## Required tests

Use Django test client and fakes. Add meaningful tests for at least:

1. Anonymous users cannot access panel routes; CSRF and permissions protect mutations.
2. Two separate equal-role admins can carry out permitted actions; unprivileged users cannot.
3. Password-reset operation creates an audit event without recording a password/token.
4. Artist/source verification, enable/disable, manual poll/baseline requests, and unsafe-enable warning call domain services and are audited.
5. Review approve/reject/correct/requeue works through M2 services and is idempotent.
6. Manual upload and media retry routes call M3 services and preserve validation/audit records.
7. Template/tag setting validation rejects unsafe/unknown variables and previews valid conditional captions correctly.
8. The default/preview album prior-single marker is `›`, never `•`.
9. Correction timeout settings and publication/album/reconciliation views show accurate M4 state.
10. Persian alias search/display and audit summaries survive authenticated panel flows.
11. Metrics aggregate safely from existing data and do not require real provider or Telegram calls.
12. Sensitive values and media paths are absent from normal rendered pages and audit output.

## Documentation and delivery

- Update `docs/STATUS.md`, `docs/PRODUCT_SPEC.md`, and `docs/IMPLEMENTATION.md` for observed M5 decisions.
- Add `docs/reports/M5_ADMIN.md` covering panel routes, role permissions, audited actions, template safety, metrics, and open integration gates.
- Run Docker Compose, migrations, migration-drift check, Django check, full automated tests, health checks, and secret/media scans locally.
- Commit focused changes and push normally to `main`.
- Do not deploy, start a real source poll/baseline, or start M6.

## Completion report

```text
Implemented:
Local commit SHA and pushed branch:
Local checks (command → observed result):
Admin roles and access-control results:
Review/media/template workflow results:
Audit/metrics results:
Documentation updated:
Open gates and proposed M6 scope:
```

Stop after M5 and await the owner's review.
