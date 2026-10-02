# RapFaDrop

Self-hosted Persian rap release monitor and Telegram archive for the owner's curated artist list.

**Status:** M0 documentation baseline. No running service or working downloader is claimed yet. Provider and Telegram behavior must be verified during implementation.

## Start here

- [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md) — product decisions, seed artists and source profiles, captions, admin rules and open field tests (English).
- [`docs/IMPLEMENTATION.md`](docs/IMPLEMENTATION.md) — architecture, data model, workflows, milestones, acceptance evidence and first coding-agent task (English).
- [`docs/AGENTS.md`](docs/AGENTS.md) — full coding-agent instructions (English). The root [`AGENTS.md`](AGENTS.md) points agents here automatically.
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — repeatable local verification, exact-SHA server deployment, safety checks and milestone completion record.
- [`docs/STATUS.md`](docs/STATUS.md) — observed repository status, outstanding empirical gates and the exact next implementation handoff.
- [`docs/M0_AGENT_TASK.md`](docs/M0_AGENT_TASK.md) — scoped, copyable coding-agent task and acceptance report for M0.

The first implementation slice is repository setup and Dockerized feasibility probes against the owner's SoundCloud examples and public Spotify metadata. Audio publishing to the live channel starts only after the corresponding integration checks and configuration.

Repository: <https://github.com/ariyx/RapFaDrop.git>
