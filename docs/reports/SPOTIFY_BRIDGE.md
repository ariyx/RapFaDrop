# Controlled Spotify discovery to media queue bridge

## Behavior and safety gate

`RAPFADROP_SPOTIFY_MEDIA_BRIDGE_ENABLED=false` is the default. A new Spotify ID is enriched with complete album/EP/single details after a successful discography poll. The 177 historical baseline IDs are not enriched or bridged. The poll persists a newly discovered item only after detail validation succeeds. Auto-queue requires a unique same-artist canonical release, matching release type and ordered track list, corroborating durations and recent release date, and a unique confident full-audio SoundCloud match for each track from a recently observed, nonbaseline source item. Regional catalog additions, editions, incomplete details, uncertain dates or audio, and ambiguous identity go to admin review with a reason. The existing Spotify URL is metadata, never a media provider.

An explicit operator approval of a reviewed new item creates at most one processing queue entry per canonical track. Prior singles retain their album relationship. If there is no verified supported full-audio match, the resulting candidate awaits a complete manual upload and validation; approval itself does not acquire or publish audio. A dedicated, bounded Celery task consumes only due Spotify-bridged SoundCloud candidates when Telegram and publication are disabled. It uses the existing M3 retry and audio completeness checks. The production deployment must route that task to a separate `spotify-media` worker with the shared media volume; the source-poll worker remains on `spotify-pilot`.

## Local verification, 2026-10-03

The rebuilt Docker image passed `docker compose config --quiet`, `manage.py makemigrations --check --dry-run` (no changes), and `manage.py check` with the bridge on and all publication/Telegram switches off. A disposable PostgreSQL test database passed **131 tests**, including simulated Spotify baseline/new-ID polls, full and truncated release details, cross-platform queue reuse, baseline and regional-backfill guards, single and album/EP membership, reviewed approval/manual audio, retry backoff, consumer replay, and disabled-switch behavior. No live provider media request or Telegram call occurred in these tests. The previously deployed five Spotify sources and 177 historical IDs were not changed locally.

Server deployment and observed production state are recorded in `M6_OPERATIONS.md` and `STATUS.md` after the exact tested SHA is deployed.

Server verification through 2026-10-04 UTC found 177 historical IDs, zero new IDs/jobs/media/publications, one recovered Sijal NetworkError and 978 empty media scans. The bridge is ON only in the protected server overlay; production Telegram publication is OFF. See [M6 operations](M6_OPERATIONS.md) for timestamps and commands.
