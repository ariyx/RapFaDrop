"""Keep the beat schedule consistent with publication safety switches."""


def beat_schedule(publication_enabled, telegram_enabled, telegram_mode, spotify_bridge_enabled=False, fresh_enabled=False):
    schedule = {"poll-due-artist-sources": {"task": "sources.tasks.poll_due_artist_sources", "schedule": 10.0}}
    if spotify_bridge_enabled and not publication_enabled and not telegram_enabled:
        schedule["spotify-bridge-media"] = {
            "task": "media_pipeline.tasks.process_spotify_bridge_media", "schedule": 60.0,
        }
    if publication_enabled and telegram_enabled and telegram_mode in {"test", "production"}:
        schedule["publication-recovery-and-correction-deletion"] = {
            "task": "publication.tasks.process_due_publications", "schedule": 30.0,
        }
    if fresh_enabled and spotify_bridge_enabled:
        schedule["fresh-release-processing"] = {"task": "releases.tasks.process_fresh_releases", "schedule": 15.0,
                                               "options": {"queue": "fresh-media-v1", "expires": 15}}
    schedule["poll-due-artist-sources"]["options"] = {"queue": "spotify-pilot", "expires": 10}
    return schedule
