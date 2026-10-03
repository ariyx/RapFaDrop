import tempfile
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from media_pipeline.models import MediaAttempt, MediaCandidate
from media_pipeline.providers import ProviderError
from media_pipeline.providers import PROVIDERS
from media_pipeline.services import retry_candidate
from media_pipeline.services import request_candidate
from media_pipeline.tasks import process_spotify_bridge_media
from config.scheduling import beat_schedule
from sources.models import Artist, ArtistSource, SourceItem
from sources.services import baseline_source, poll_source

from .models import (CanonicalRelease, ProcessingQueueItem, ReleaseCredit, ReleaseTrack,
                     ReviewItem, SourceMatch, Track, TrackCredit)
from .services import ingest_source_item, resolve_review


@override_settings(SPOTIFY_MEDIA_BRIDGE_ENABLED=True)
class SpotifyBridgeTests(TestCase):
    def setUp(self):
        self.artist = Artist.objects.create(official_name="Sijal", enabled=True)
        self.spotify = ArtistSource.objects.create(artist=self.artist, platform="spotify", enabled=True,
            verification="verified", native_profile_id="5F0BGBdSL945Bzxrq8aGbn")
        self.soundcloud = ArtistSource.objects.create(artist=self.artist, platform="soundcloud", enabled=False,
            verification="verified", native_profile_id="sijalofficial")
        self.now = timezone.now()

    def _canonical(self, title, kind="single", tracks=None):
        release = CanonicalRelease.objects.create(title=title, release_type=kind)
        ReleaseCredit.objects.create(release=release, artist=self.artist)
        for position, (track_title, duration) in enumerate(tracks or [(title, 180)], 1):
            track = Track.objects.create(official_title=track_title, normalized_title=track_title.casefold(), duration_seconds=duration)
            TrackCredit.objects.create(track=track, artist=self.artist)
            ReleaseTrack.objects.create(release=release, track=track, position=position)
        return release

    def _sc_match(self, release, track, native_id, *, date=None, url=None, duration=180):
        item = SourceItem.objects.create(source=self.soundcloud, platform="soundcloud", native_item_id=native_id,
            title=track.official_title, canonical_url=url or f"https://soundcloud.com/sijalofficial/{native_id}",
            source_release_at=date or self.now, first_observed_at=self.now,
            metadata={"duration": duration, "uploader": "Sijal"})
        return SourceMatch.objects.create(source_item=item, release=release, track=track, confidence=98,
            state=SourceMatch.State.MATCHED, matching_method="verified_soundcloud")

    def _spotify_item(self, title, tracks, *, kind="single", date=None, native_id="1" * 22, baseline=False):
        metadata = {"spotify_discovery": True, "artist_credits": ["Sijal"], "album_type": kind,
                    "track_count": len(tracks), "tracks": [
                        {"id": str(position) * 22, "title": name, "position": position,
                         "duration_seconds": duration, "artist_credits": ["Sijal"]}
                        for position, (name, duration) in enumerate(tracks, 1)]}
        return SourceItem.objects.create(source=self.spotify, platform="spotify", native_item_id=native_id,
            title=title, canonical_url=f"https://open.spotify.com/album/{native_id}",
            source_release_at=date, first_observed_at=self.now, from_baseline=baseline, metadata=metadata)

    def test_new_single_uses_verified_soundcloud_without_audio_download_and_replay_is_idempotent(self):
        release = self._canonical("New Song")
        track = release.release_tracks.get().track
        sc = self._sc_match(release, track, "sc-new")
        item = self._spotify_item("New Song", [("New Song", 180)], date=self.now)
        self.assertEqual(ingest_source_item(item, now=self.now), "queued")
        self.assertEqual(ingest_source_item(item, now=self.now), "queued")
        match = SourceMatch.objects.get(source_item=item)
        self.assertEqual(match.release, release)
        self.assertEqual(match.track, track)
        self.assertEqual(ProcessingQueueItem.objects.count(), 1)
        candidate = MediaCandidate.objects.get()
        self.assertEqual(candidate.source_match, sc)
        self.assertEqual(candidate.provider, "yt-dlp")
        self.assertEqual(candidate.attempt_count, 0)
        self.assertFalse(ReviewItem.objects.exists())
        self.assertFalse(MediaAttempt.objects.exists())

    @override_settings(SPOTIFY_DISCOVERY_MODE="spotifyscraper")
    def test_complete_poll_bridges_only_new_id_after_historical_baseline(self):
        class FakeDiscovery:
            def __init__(self, rows):
                self.rows = rows
                self.details = []

            def list_recent(self, source):
                return [{**row, "metadata": dict(row["metadata"]),
                         "sanitized_raw_data": dict(row["sanitized_raw_data"])} for row in self.rows]

            def fetch_item(self, source, row):
                self.details.append(row["native_item_id"])
                row["source_release_at"] = self.now
                row["metadata"].update({"spotify_discovery": True, "album_type": "single",
                    "artist_credits": ["Sijal"], "track_count": 1,
                    "tracks": [{"id": "7" * 22, "title": "Poll Work", "position": 1,
                                "duration_seconds": 180, "artist_credits": ["Sijal"]}]})
                return row

        release = self._canonical("Poll Work")
        self._sc_match(release, release.release_tracks.get().track, "sc-poll")
        old_id, new_id = "8" * 22, "9" * 22
        def row(native_id, title):
            return {"native_item_id": native_id, "title": title,
                    "canonical_url": f"https://open.spotify.com/album/{native_id}",
                    "source_release_at": None, "metadata": {"spotify_discovery": True},
                    "sanitized_raw_data": {"release_id": native_id}}
        adapter = FakeDiscovery([row(old_id, "History")])
        adapter.now = self.now
        baseline_source(self.spotify, adapter=adapter, now=self.now)
        self.assertEqual(SourceItem.objects.get(native_item_id=old_id).from_baseline, True)
        self.assertFalse(ProcessingQueueItem.objects.exists())
        adapter.rows.append(row(new_id, "Poll Work"))
        self.assertEqual(poll_source(self.spotify, adapter=adapter, now=self.now), "success")
        self.assertEqual(adapter.details, [new_id])
        self.assertEqual(ProcessingQueueItem.objects.count(), 1)
        self.assertEqual(MediaCandidate.objects.count(), 1)
        self.assertEqual(poll_source(self.spotify, adapter=adapter, now=self.now), "success")
        self.assertEqual(adapter.details, [new_id])
        self.assertEqual(SourceItem.objects.filter(platform="spotify").count(), 2)

    def test_cross_platform_existing_queue_is_not_duplicated(self):
        release = self._canonical("Already Matched")
        track = release.release_tracks.get().track
        self._sc_match(release, track, "sc-existing")
        queue = ProcessingQueueItem.objects.create(release=release, track=track, due_at=self.now)
        item = self._spotify_item("Already Matched", [("Already Matched", 180)], date=self.now)
        self.assertEqual(ingest_source_item(item, now=self.now), "matched")
        self.assertEqual(ProcessingQueueItem.objects.get().pk, queue.pk)
        self.assertEqual(MediaCandidate.objects.count(), 1)

    def test_existing_soundcloud_candidate_is_enrolled_once_in_bridge_consumer(self):
        release = self._canonical("Existing Candidate")
        track = release.release_tracks.get().track
        self._sc_match(release, track, "sc-candidate")
        queue = ProcessingQueueItem.objects.create(release=release, track=track, due_at=self.now)
        candidate = request_candidate(queue, provider_name="yt-dlp")
        item = self._spotify_item("Existing Candidate", [("Existing Candidate", 180)], date=self.now)
        self.assertEqual(ingest_source_item(item, now=self.now), "matched")
        candidate.refresh_from_db()
        self.assertEqual(candidate.provenance["spotify_bridge_release_id"], item.native_item_id)
        self.assertEqual(MediaCandidate.objects.count(), 1)
        self.assertEqual(ProcessingQueueItem.objects.count(), 1)

    def test_historical_soundcloud_match_cannot_auto_bridge_regional_catalog_addition(self):
        release = self._canonical("Historical Match")
        track = release.release_tracks.get().track
        sc = self._sc_match(release, track, "sc-historical")
        sc.source_item.from_baseline = True
        sc.source_item.save(update_fields=("from_baseline",))
        item = self._spotify_item("Historical Match", [("Historical Match", 180)], date=self.now)
        self.assertEqual(ingest_source_item(item, now=self.now), "review_required")
        self.assertFalse(ProcessingQueueItem.objects.exists())

    def test_old_or_undated_catalog_addition_requires_review_then_approval_queues_manual_audio_once(self):
        for date in (None, self.now - timedelta(days=90)):
            with self.subTest(date=date):
                native_id = ("3" if date is None else "4") * 22
                item = self._spotify_item("Unknown New ID", [("Unknown New ID", 180)], date=date, native_id=native_id)
                self.assertEqual(ingest_source_item(item, now=self.now), "review_required")
                review = ReviewItem.objects.get(source_item=item)
                self.assertIn("catalog", review.evidence["bridge_reason"])
                self.assertFalse(ProcessingQueueItem.objects.exists())
                with self.assertRaisesRegex(ValueError, "resolution"):
                    resolve_review(review, "approve", now=self.now)
                approved = resolve_review(review, "approve", resolution="Operator verified this official current work", now=self.now)
                resolve_review(approved, "approve", resolution="Operator verified this official current work", now=self.now)
                self.assertEqual(ProcessingQueueItem.objects.count(), 1)
                candidate = MediaCandidate.objects.get()
                self.assertEqual(candidate.provider, "manual")
                self.assertEqual(candidate.state, MediaCandidate.State.REVIEW_REQUIRED)
                self.assertEqual(candidate.attempt_count, 0)
                ProcessingQueueItem.objects.all().delete()
                MediaCandidate.objects.all().delete()

    def test_album_queues_each_track_and_preserves_prior_single_without_duplicate_queue(self):
        single = self._canonical("Track One")
        prior = single.release_tracks.get()
        album = self._canonical("New Album", "lp", [("Track One", 180), ("Track Two", 205)])
        first, second = list(album.release_tracks.order_by("position"))
        # The existing canonical identity for a prior single is reused by the album.
        first.track = prior.track
        first.prior_single = prior
        first.save(update_fields=("track", "prior_single"))
        self._sc_match(single, prior.track, "sc-one", duration=180)
        self._sc_match(album, second.track, "sc-two", duration=205)
        item = self._spotify_item("New Album", [("Track One", 180), ("Track Two", 205)], kind="album", date=self.now)
        self.assertEqual(ingest_source_item(item, now=self.now), "queued")
        self.assertEqual(ProcessingQueueItem.objects.count(), 2)
        self.assertEqual(MediaCandidate.objects.count(), 2)
        self.assertEqual(album.release_tracks.get(position=1).prior_single_id, prior.pk)
        self.assertEqual(ingest_source_item(item, now=self.now), "matched")
        self.assertEqual(ProcessingQueueItem.objects.count(), 2)

    def test_album_without_verified_full_audio_stays_review_until_approval(self):
        item = self._spotify_item("Unmatched EP", [("First", 180), ("Second", 205)], kind="ep", date=self.now)
        self.assertEqual(ingest_source_item(item, now=self.now), "review_required")
        self.assertFalse(ProcessingQueueItem.objects.exists())
        review = resolve_review(item.review_item, "approve", resolution="Official EP confirmed; manual full audio required", now=self.now)
        self.assertEqual(review.state, ReviewItem.State.APPROVED)
        self.assertEqual(ProcessingQueueItem.objects.count(), 2)
        self.assertEqual(MediaCandidate.objects.filter(provider="manual", state="review_required").count(), 2)
        self.assertEqual(ReleaseTrack.objects.filter(release=review.source_match.release).count(), 2)
        resolve_review(review, "approve", resolution="Replay", now=self.now)
        self.assertEqual(ProcessingQueueItem.objects.count(), 2)

    def test_missing_audio_or_mismatched_duration_never_auto_queues(self):
        release = self._canonical("No Good Audio")
        track = release.release_tracks.get().track
        self._sc_match(release, track, "sc-wrong", duration=45)
        item = self._spotify_item("No Good Audio", [("No Good Audio", 180)], date=self.now)
        self.assertEqual(ingest_source_item(item, now=self.now), "review_required")
        self.assertIn("full-audio", item.review_item.evidence["bridge_reason"])
        self.assertFalse(ProcessingQueueItem.objects.exists())

    def test_failed_candidate_job_retries_without_new_queue_or_candidate(self):
        class FailedProvider:
            name = "yt-dlp"
            def can_handle(self, url):
                return True
            def probe(self, url, timeout=None):
                raise ProviderError("temporarily unavailable")

        release = self._canonical("Retry Work")
        track = release.release_tracks.get().track
        self._sc_match(release, track, "sc-retry")
        item = self._spotify_item("Retry Work", [("Retry Work", 180)], date=self.now)
        ingest_source_item(item, now=self.now)
        candidate = retry_candidate(MediaCandidate.objects.get(), provider=FailedProvider(), now=self.now)
        self.assertEqual(candidate.state, MediaCandidate.State.RETRY_WAIT)
        self.assertEqual(candidate.attempt_count, 1)
        ingest_source_item(item, now=self.now)
        self.assertEqual(ProcessingQueueItem.objects.count(), 1)
        self.assertEqual(MediaCandidate.objects.count(), 1)
        self.assertEqual(MediaAttempt.objects.count(), 1)

    @override_settings(PUBLICATION_WORKER_ENABLED=False, TELEGRAM_LIVE_ENABLED=False, TELEGRAM_MODE="disabled")
    def test_bounded_consumer_retries_verified_candidate_but_never_reprocesses_immediately(self):
        class FailedProvider:
            name = "yt-dlp"
            def can_handle(self, url):
                return url.startswith("https://soundcloud.com/")
            def probe(self, url, timeout=None):
                raise ProviderError("temporary SoundCloud failure")

        release = self._canonical("Consumer Work")
        self._sc_match(release, release.release_tracks.get().track, "sc-consumer")
        item = self._spotify_item("Consumer Work", [("Consumer Work", 180)], date=self.now)
        ingest_source_item(item, now=self.now)
        self.assertEqual(MediaCandidate.objects.get().provenance["spotify_bridge_release_id"], item.native_item_id)
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory), patch.dict(PROVIDERS, {"yt-dlp": FailedProvider()}):
            first = process_spotify_bridge_media()
            second = process_spotify_bridge_media()
        self.assertEqual(list(first.values()), [MediaCandidate.State.RETRY_WAIT])
        self.assertEqual(second, {})
        self.assertEqual(MediaCandidate.objects.get().attempt_count, 1)
        self.assertEqual(MediaAttempt.objects.count(), 1)
        self.assertEqual(ProcessingQueueItem.objects.count(), 1)

    def test_beat_schedule_requires_bridge_and_disabled_publication(self):
        self.assertIn("spotify-bridge-media", beat_schedule(False, False, "disabled", True))
        self.assertNotIn("spotify-bridge-media", beat_schedule(False, False, "disabled", False))
        self.assertNotIn("spotify-bridge-media", beat_schedule(True, True, "production", True))

    @override_settings(SPOTIFY_MEDIA_BRIDGE_ENABLED=False)
    def test_disabled_switch_stays_review_only(self):
        release = self._canonical("Bridge Off")
        track = release.release_tracks.get().track
        self._sc_match(release, track, "sc-off")
        item = self._spotify_item("Bridge Off", [("Bridge Off", 180)], date=self.now)
        self.assertEqual(ingest_source_item(item, now=self.now), "review_required")
        self.assertFalse(ProcessingQueueItem.objects.exists())
        self.assertFalse(MediaCandidate.objects.exists())

    def test_historical_release_id_is_never_bridged(self):
        release = self._canonical("History")
        track = release.release_tracks.get().track
        self._sc_match(release, track, "sc-history")
        item = self._spotify_item("History", [("History", 180)], date=self.now, baseline=True)
        self.assertEqual(ingest_source_item(item, now=self.now), "review_required")
        self.assertFalse(ProcessingQueueItem.objects.exists())
