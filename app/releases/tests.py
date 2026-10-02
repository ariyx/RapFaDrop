from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone as datetime_timezone
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import connections, connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from sources.models import Artist, ArtistSource, SourceItem

from .models import (
    CanonicalRelease,
    IdentityAuditEvent,
    ProcessingQueueItem,
    ReleaseCredit,
    ReleaseTrack,
    ReviewItem,
    SourceMatch,
    Track,
    TrackCredit,
)
from .normalization import normalize_text
from .services import ingest_source_item, resolve_review, retry_queue_item


def release_time(year=2025, month=5, day=1):
    return datetime(year, month, day, tzinfo=datetime_timezone.utc)


class IdentityTests(TestCase):
    def setUp(self):
        self.artist = Artist.objects.create(official_name="Hichkas", aliases=["هیچ‌کس"], enabled=True)
        self.soundcloud = ArtistSource.objects.create(
            artist=self.artist, platform=ArtistSource.Platform.SOUNDCLOUD,
            native_profile_id="hichkasofficial", canonical_url="https://soundcloud.com/hichkasofficial",
            enabled=True, verification=ArtistSource.Verification.VERIFIED,
        )
        self.spotify = ArtistSource.objects.create(
            artist=self.artist, platform=ArtistSource.Platform.SPOTIFY,
            native_profile_id="spotify-test", canonical_url="https://open.spotify.com/artist/spotify-test",
            enabled=True, verification=ArtistSource.Verification.VERIFIED,
        )

    def source_item(self, native_id, title, *, source=None, metadata=None, released_at=None):
        source = source or self.soundcloud
        return SourceItem.objects.create(
            platform=source.platform,
            native_item_id=str(native_id),
            source=source,
            title=title,
            canonical_url=f"https://{source.platform}.example/item/{native_id}",
            source_release_at=released_at or release_time(),
            first_observed_at=timezone.now(),
            metadata=metadata or {},
            sanitized_raw_data={"id": str(native_id), "title": title},
        )

    def test_exact_source_ingestion_retry_is_idempotent(self):
        item = self.source_item("sc-1", "Road", metadata={"duration": 201})
        self.assertEqual(ingest_source_item(item), "queued")
        self.assertEqual(ingest_source_item(item), "queued")
        self.assertEqual(CanonicalRelease.objects.count(), 1)
        self.assertEqual(Track.objects.count(), 1)
        self.assertEqual(SourceMatch.objects.count(), 1)
        self.assertEqual(ProcessingQueueItem.objects.count(), 1)

    def test_high_confidence_cross_platform_items_share_one_canonical_track_and_queue(self):
        soundcloud_item = self.source_item("sc-road", "Road feat. Shayea", metadata={"duration": 201})
        spotify_item = self.source_item("sp-road", "road ft Shayea", source=self.spotify, metadata={"duration": 202})
        self.assertEqual(ingest_source_item(soundcloud_item), "queued")
        self.assertEqual(ingest_source_item(spotify_item), "matched")
        self.assertEqual(Track.objects.count(), 1)
        self.assertEqual(CanonicalRelease.objects.count(), 1)
        self.assertEqual(ProcessingQueueItem.objects.count(), 1)
        self.assertEqual(spotify_item.identity_match.track, soundcloud_item.identity_match.track)
        # Official spelling remains the first verified source's display value.
        self.assertEqual(Track.objects.get().official_title, "Road feat. Shayea")

    def test_same_title_from_different_artists_never_auto_matches(self):
        second_artist = Artist.objects.create(official_name="Sijal", aliases=["سیجل"], enabled=True)
        second_source = ArtistSource.objects.create(artist=second_artist, platform="spotify", enabled=True, verification="verified")
        first = self.source_item("sc-same-title", "Azadi", metadata={"duration": 180})
        second = self.source_item("sp-same-title", "Azadi", source=second_source, metadata={"duration": 180})
        self.assertEqual(ingest_source_item(first), "queued")
        self.assertEqual(ingest_source_item(second), "queued")
        self.assertNotEqual(first.identity_match.track_id, second.identity_match.track_id)
        self.assertEqual(Track.objects.count(), 2)

    def test_mismatched_provider_artist_and_conflicting_release_date_require_review(self):
        wrong_artist = self.source_item("sc-wrong-owner", "Unknown Song", metadata={"duration": 100, "uploader": "Sijal"})
        self.assertEqual(ingest_source_item(wrong_artist), "review_required")
        self.assertEqual(wrong_artist.review_item.category, ReviewItem.Category.ARTIST_MISMATCH)

        original = self.source_item("sc-old-release", "Old Song", metadata={"duration": 100}, released_at=release_time(2022, 1, 1))
        self.assertEqual(ingest_source_item(original), "queued")
        reissue = self.source_item("sp-new-date", "Old Song", source=self.spotify, metadata={"duration": 100}, released_at=release_time(2025, 1, 1))
        self.assertEqual(ingest_source_item(reissue), "review_required")
        self.assertEqual(reissue.review_item.category, ReviewItem.Category.POSSIBLE_DUPLICATE)

    def test_persian_latin_alias_normalization_preserves_official_persisted_values(self):
        self.assertEqual(normalize_text("هیچ‌کس"), normalize_text("هيچ کس"))
        self.assertEqual(normalize_text("Road feat. Shayea"), normalize_text(" road FT Shayea! "))
        item = self.source_item("sc-persian-title", "هیچ‌کس و یاس", metadata={"duration": 190, "uploader": "هیچ‌کس"})
        self.assertEqual(ingest_source_item(item), "queued")
        track = Track.objects.get()
        track.refresh_from_db()
        self.artist.refresh_from_db()
        self.assertEqual(track.official_title, "هیچ‌کس و یاس")
        self.assertEqual(self.artist.official_name, "Hichkas")
        self.assertEqual(self.artist.aliases, ["هیچ‌کس"])
        self.assertEqual(track.normalized_title, normalize_text("هیچ‌کس و یاس"))

    def test_version_markers_create_distinct_reviewed_editions_not_automatic_merges(self):
        original_item = self.source_item("sc-original", "Song", metadata={"duration": 100})
        self.assertEqual(ingest_source_item(original_item), "queued")
        original = original_item.identity_match.track
        for suffix, edition in (("Remix", "remix"), ("Live", "live"), ("Instrumental", "instrumental"), ("Deluxe", "deluxe"), ("Rerelease", "rerelease")):
            with self.subTest(edition=edition):
                item = self.source_item(f"sc-{edition}", f"Song {suffix}", metadata={"duration": 100})
                self.assertEqual(ingest_source_item(item), "review_required")
                match = item.identity_match
                self.assertNotEqual(match.track_id, original.pk)
                self.assertEqual(match.track.edition, edition)
                self.assertEqual(match.track.edition_of_id, original.pk)
                if edition == "deluxe":
                    self.assertEqual(match.release.edition, "deluxe")
                    self.assertEqual(match.release.edition_of_id, original_item.identity_match.release_id)
                self.assertEqual(item.review_item.category, ReviewItem.Category.EDITION)
                self.assertFalse(ProcessingQueueItem.objects.filter(track=match.track).exists())

    def test_single_before_album_reuses_track_and_prior_single_without_second_queue_item(self):
        single = self.source_item("sc-single", "Same Track", metadata={"duration": 213}, released_at=release_time(2024, 1, 1))
        self.assertEqual(ingest_source_item(single), "queued")
        single_membership = ReleaseTrack.objects.get(release__release_type=CanonicalRelease.ReleaseType.SINGLE)
        album_track = self.source_item("sc-album-track", "Same Track", metadata={"duration": 214, "album": "Project", "album_type": "album", "track_number": 4}, released_at=release_time(2025, 9, 1))
        self.assertEqual(ingest_source_item(album_track), "matched")
        album_membership = ReleaseTrack.objects.get(release__release_type=CanonicalRelease.ReleaseType.LP)
        self.assertEqual(album_track.identity_match.track_id, single.identity_match.track_id)
        self.assertEqual(album_membership.position, 4)
        self.assertEqual(album_membership.prior_single_id, single_membership.pk)
        self.assertEqual(ProcessingQueueItem.objects.filter(track=single.identity_match.track).count(), 1)

    def test_ambiguous_playlist_and_low_confidence_are_reviewed_without_blocking_unrelated_work(self):
        playlist = self.source_item("sc-playlist", "Track A", metadata={"album": "Unclear Collection", "album_type": "playlist", "duration": 100})
        self.assertEqual(ingest_source_item(playlist), "review_required")
        self.assertEqual(playlist.review_item.category, ReviewItem.Category.COLLECTION_TYPE)
        self.assertIsNone(playlist.identity_match.release_id)

        first = self.source_item("sc-low-first", "Track B", metadata={"duration": 100})
        self.assertEqual(ingest_source_item(first), "queued")
        low_confidence = self.source_item("sp-low-second", "Track B", source=self.spotify)
        self.assertEqual(ingest_source_item(low_confidence), "review_required")
        self.assertEqual(low_confidence.review_item.category, ReviewItem.Category.LOW_CONFIDENCE)

        unrelated = self.source_item("sc-unrelated", "Track C", metadata={"duration": 190})
        self.assertEqual(ingest_source_item(unrelated), "queued")
        self.assertEqual(ProcessingQueueItem.objects.count(), 2)

    def test_review_approve_reject_correct_and_requeue_are_audited_and_idempotent(self):
        user = get_user_model().objects.create_user("reviewer", password="test-only")

        original = self.source_item("sc-edit-base", "Song", metadata={"duration": 100})
        ingest_source_item(original)
        version = self.source_item("sc-edit-version", "Song Live", metadata={"duration": 100})
        ingest_source_item(version)
        review = version.review_item
        approved = resolve_review(review, "approve", user, resolution="Confirmed distinct live edition")
        resolve_review(approved, "approve", user, resolution="Repeated approval")
        self.assertEqual(approved.state, ReviewItem.State.APPROVED)
        self.assertEqual(IdentityAuditEvent.objects.filter(review_item=review, action="review_approved").count(), 1)
        self.assertTrue(ProcessingQueueItem.objects.filter(track=version.identity_match.track).exists())

        ambiguous = self.source_item("sc-reject", "Playlist", metadata={"album": "Set", "album_type": "playlist"})
        ingest_source_item(ambiguous)
        rejected = resolve_review(ambiguous.review_item, "reject", user, resolution="Not an official release")
        resolve_review(rejected, "reject", user, resolution="Repeated rejection")
        self.assertEqual(IdentityAuditEvent.objects.filter(review_item=rejected, action="review_rejected").count(), 1)
        self.assertEqual(ingest_source_item(ambiguous), "ignored_duplicate")
        requeued = resolve_review(rejected, "requeue", user)
        self.assertEqual(requeued.state, ReviewItem.State.REQUEUED)
        self.assertEqual(ingest_source_item(ambiguous), "review_required")

        corrected_item = self.source_item("sc-correct", "Unknown Collection", metadata={"album": "Unknown Collection", "album_type": "playlist"})
        ingest_source_item(corrected_item)
        release = CanonicalRelease.objects.create(title="Unknown Collection", release_type=CanonicalRelease.ReleaseType.LP)
        ReleaseCredit.objects.create(release=release, artist=self.artist)
        track = Track.objects.create(official_title="Unknown Collection Track", normalized_title="unknown collection track", duration_seconds=90)
        TrackCredit.objects.create(track=track, artist=self.artist)
        ReleaseTrack.objects.create(release=release, track=track, position=1)
        corrected = resolve_review(corrected_item.review_item, "correct", user, release=release, track=track, resolution="Operator selected official LP")
        resolve_review(corrected, "correct", user, release=release, track=track)
        self.assertEqual(corrected.state, ReviewItem.State.CORRECTED)
        self.assertEqual(corrected_item.identity_match.track_id, track.pk)
        self.assertEqual(IdentityAuditEvent.objects.filter(review_item=corrected, action="review_corrected").count(), 1)
        self.assertTrue(ProcessingQueueItem.objects.filter(track=track).exists())

    def test_authenticated_admin_can_inspect_and_approve_a_review(self):
        admin_user = get_user_model().objects.create_superuser("admin-review", "admin@example.test", "test-only")
        self.client.force_login(admin_user)
        original = self.source_item("admin-original", "Admin Song", metadata={"duration": 100})
        self.assertEqual(ingest_source_item(original), "queued")
        edition = self.source_item("admin-live", "Admin Song Live", metadata={"duration": 100})
        self.assertEqual(ingest_source_item(edition), "review_required")
        review = edition.review_item

        change_url = f"/admin/releases/reviewitem/{review.pk}/change/"
        detail = self.client.get(change_url)
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Explicit version marker")
        self.assertContains(detail, "Admin Song Live")

        response = self.client.post("/admin/releases/reviewitem/", {
            "action": "approve_selected",
            "_selected_action": [str(review.pk)],
            "index": "0",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        review.refresh_from_db()
        self.assertEqual(review.state, ReviewItem.State.APPROVED)
        self.assertEqual(review.actor, admin_user)
        self.assertTrue(IdentityAuditEvent.objects.filter(review_item=review, actor=admin_user, action="review_approved").exists())
        self.assertTrue(ProcessingQueueItem.objects.filter(track=edition.identity_match.track).exists())

    def test_queue_retry_backoff_is_bounded_and_starts_no_media_or_publication_work(self):
        item = self.source_item("sc-retry", "Retry Track", metadata={"duration": 95})
        ingest_source_item(item)
        queue = ProcessingQueueItem.objects.get(track=item.identity_match.track)
        now = timezone.now()
        first = retry_queue_item(queue, "transient identity worker error", now=now, base_delay_seconds=30, maximum_delay_seconds=40)
        self.assertEqual(first.due_at, now + timedelta(seconds=30))
        second = retry_queue_item(first, "still unavailable", now=now, base_delay_seconds=30, maximum_delay_seconds=40)
        self.assertEqual(second.due_at, now + timedelta(seconds=40))
        self.assertEqual(second.attempt_count, 2)
        self.assertEqual(second.state, ProcessingQueueItem.State.RETRY_WAIT)
        self.assertEqual(second.last_error, "still unavailable")
        self.assertFalse(hasattr(second, "media_candidate"))
        self.assertFalse(hasattr(second, "publication"))


@skipUnless(connection.vendor == "postgresql", "Concurrent ingestion test requires PostgreSQL row locks")
class ConcurrentIngestionTests(TransactionTestCase):
    reset_sequences = True

    def test_concurrent_ingestion_of_same_source_item_creates_one_candidate(self):
        artist = Artist.objects.create(official_name="Concurrent Artist", enabled=True)
        source = ArtistSource.objects.create(artist=artist, platform="soundcloud", enabled=True, verification="verified")
        source_item = SourceItem.objects.create(
            platform="soundcloud", native_item_id="same-native-id", source=source,
            title="Concurrent Track", first_observed_at=timezone.now(), metadata={"duration": 140},
        )
        item_id = source_item.pk

        def ingest_once(_):
            connections.close_all()
            try:
                return ingest_source_item(SourceItem.objects.get(pk=item_id))
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(ingest_once, range(2)))
        self.assertCountEqual(results, ["queued", "queued"])
        self.assertEqual(SourceMatch.objects.filter(source_item=source_item).count(), 1)
        self.assertEqual(Track.objects.count(), 1)
        self.assertEqual(CanonicalRelease.objects.count(), 1)
        self.assertEqual(ProcessingQueueItem.objects.count(), 1)
