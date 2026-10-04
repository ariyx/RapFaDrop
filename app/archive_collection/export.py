import csv
import json
from pathlib import Path
from django.utils import timezone
from .services import status


def export(collection, directory, *, processing_sha=""):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    generated = timezone.now().isoformat()
    selections = []
    for selection in collection.selections.select_related("source__artist").order_by("roster_position"):
        slots = {slot.number: slot for slot in selection.slots.select_related("recording__publication")}
        for number in (1, 2):
            slot = slots.get(number)
            r = slot.recording if slot else None
            selections.append({"artist_id": selection.source.artist_id, "artist": selection.source.artist.official_name,
                "source_id": selection.source_id, "spotify_artist_id": selection.source.native_profile_id,
                "slot": number, "popular_rank": slot.popular_rank if slot else "", "spotify_id": r.spotify_id if r else "",
                "title": r.metadata["title"] if r else "", "state": r.state if r else "unresolved",
                "reason": r.reason if r else selection.error, "message_id": r.publication.message_id if r and r.publication_id else "",
                "observed_at": selection.evidence.get("observed_at", str(selection.observed_at)),
                "endpoint": selection.evidence.get("endpoint", ""), "market": selection.evidence.get("market", ""),
                "generated_at": generated, "selection_application_sha": collection.application_sha, "processing_application_sha": processing_sha})
    recordings = []
    for r in collection.recordings.select_related("candidate", "publication"):
        candidate, pub = r.candidate, r.publication
        recordings.append({"spotify_id": r.spotify_id, "spotify_url": r.metadata["spotify_url"], "title": r.metadata["title"],
            "credited_artists": json.dumps(r.metadata["credits"], ensure_ascii=False), "album_id": r.metadata["album_id"],
            "album": r.metadata.get("album_title", ""), "duration_seconds": r.metadata["duration_seconds"],
            "track_number": r.metadata.get("track_number"), "disc_number": r.metadata.get("disc_number"),
            "artists_satisfied": " | ".join(r.slots.select_related("selection__source__artist").values_list("selection__source__artist__official_name", flat=True)),
            "state": r.state, "reason": r.reason, "candidate_id": r.candidate_id, "provider": candidate.provider if candidate else "",
            "media_source": candidate.provenance.get("source_url", "") if candidate else "",
            "codec": candidate.observed_facts.get("codec_name", "") if candidate else "",
            "audio_bitrate_bps": candidate.observed_facts.get("audio_bitrate_bps", "") if candidate else "",
            "audio_duration": candidate.observed_facts.get("duration_seconds", "") if candidate else "",
            "quality_provenance": json.dumps(candidate.provenance if candidate else {}, ensure_ascii=False),
            "tag_readback": json.dumps(candidate.preparation_report if candidate else {}, ensure_ascii=False),
            "message_id": pub.message_id if pub else "", "message_url": pub.message_url if pub else "",
            "retry_due_at": str(r.retry_due_at or ""), "timings_evidence": json.dumps(r.evidence, ensure_ascii=False),
            "generated_at": generated, "selection_application_sha": collection.application_sha, "processing_application_sha": processing_sha})
    for filename, rows in [("popular_track_selections.csv", selections), ("popular_track_publications.csv", recordings)]:
        with (directory / filename).open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=list(rows[0]) if rows else ["spotify_id"])
            writer.writeheader()
            writer.writerows(rows)
    report = {**status(collection), "generated_at": generated, "selection_application_sha": collection.application_sha, "processing_application_sha": processing_sha,
        "discovery_requests": sum(s.evidence.get("requests", 0) for s in collection.selections.all()),
        "discovery_seconds_summed": sum(s.evidence.get("discovery_seconds", 0) for s in collection.selections.all()),
        "artists": [{"artist": s.source.artist.official_name, "slots": s.slots.count(), "error": s.error,
                     "evidence": s.evidence} for s in collection.selections.select_related("source__artist").order_by("roster_position")]}
    (directory / "popular_track_evidence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
