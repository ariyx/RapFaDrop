import json
from datetime import timedelta
from unittest.mock import Mock

import httpx
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from releases.models import CanonicalRelease, ProcessingQueueItem, ReviewItem, SourceMatch
from releases.services import ingest_source_item, resolve_review

from .models import Artist, ArtistSource, BaselineRun, SourceItem
from .services import baseline_source, poll_due_sources, poll_source
from .spotify_scraper import SpotifyMetadataError, ValidatedTransport


ARTIST_ID = "5F0BGBdSL945Bzxrq8aGbn"


def page(total, offset, count):
    groups = [{"releases": {"items": [{"uri": f"spotify:album:{i:022d}", "name": f"Release {i}"}]}}
              for i in range(offset, offset + count)]
    return httpx.Response(200, json={"data": {"artistUnion": {"discography": {"all": {"totalCount": total, "items": groups}}}}})


def request_url(offset):
    variables = json.dumps({"uri": f"spotify:artist:{ARTIST_ID}", "offset": offset, "limit": 50})
    from urllib.parse import urlencode
    return "https://api-partner.spotify.com/pathfinder/v1/query?" + urlencode({"operationName": "queryArtistDiscographyAll", "variables": variables})


class DiscographyIntegrityTests(SimpleTestCase):
    def test_complete_two_pages_and_exact_group_total(self):
        base = Mock()
        base.get.side_effect = [page(51, 0, 50), page(51, 50, 1)]
        transport = ValidatedTransport(base=base)
        transport.get(request_url(0))
        transport.get(request_url(50))
        transport.finish([object()] * 51)
        self.assertEqual((transport.pages, transport.groups, transport.total), (2, 51, 51))

    def test_missing_or_empty_looking_discography_fails(self):
        for payload in ({"data": {"artistUnion": {}}},
                        {"data": {"artistUnion": {"discography": {"all": {"totalCount": 50, "items": []}}}}}):
            with self.subTest(payload=payload):
                base = Mock()
                base.get.return_value = httpx.Response(200, json=payload)
                with self.assertRaises(SpotifyMetadataError):
                    ValidatedTransport(base=base).get(request_url(0))

    def test_failed_or_short_second_page_never_finishes(self):
        for bad in (httpx.Response(200, json={"data": {"artistUnion": {}}}), page(51, 50, 0)):
            base = Mock()
            base.get.side_effect = [page(51, 0, 50), bad]
            transport = ValidatedTransport(base=base)
            transport.get(request_url(0))
            with self.assertRaises(SpotifyMetadataError):
                transport.get(request_url(50))
        base = Mock()
        base.get.side_effect = [page(51, 0, 50), TimeoutError("private URL")]
        transport = ValidatedTransport(base=base)
        transport.get(request_url(0))
        with self.assertRaisesRegex(SpotifyMetadataError, "TimeoutError") as caught:
            transport.get(request_url(50))
        self.assertNotIn("private URL", str(caught.exception))

    def test_rate_limit_exposes_bounded_retry_after(self):
        base = Mock()
        base.get.return_value = httpx.Response(429, headers={"Retry-After": "600"})
        with self.assertRaises(SpotifyMetadataError) as caught:
            ValidatedTransport(base=base).get(request_url(0))
        self.assertEqual(caught.exception.retry_after, 600)


def spotify_item(native_id, title="New work"):
    return {"native_item_id": native_id, "title": title,
            "canonical_url": f"https://open.spotify.com/album/{native_id}",
            "source_release_at": None,
            "metadata": {"spotify_discovery": True, "artist_id": ARTIST_ID},
            "sanitized_raw_data": {"artist_id": ARTIST_ID, "release_id": native_id, "release_title": title}}


class FakeSpotify:
    def __init__(self, items, fail=False):
        self.items = items
        self.fail = fail
        self.calls = 0
        self.details = []

    def list_recent(self, source):
        self.calls += 1
        if self.fail:
            raise SpotifyMetadataError("incomplete discography")
        return [dict(item, metadata=dict(item["metadata"]), sanitized_raw_data=dict(item["sanitized_raw_data"])) for item in self.items]

    def fetch_item(self, source, item):
        self.details.append(item["native_item_id"])
        item["metadata"].update({"album_type": "single", "artist_credits": [source.artist.official_name]})
        return item


class FakeSoundCloud:
    def list_recent(self, source):
        return []


@override_settings(SPOTIFY_DISCOVERY_MODE="spotifyscraper")
class SpotifyPollingTests(TestCase):
    def setUp(self):
        self.artist = Artist.objects.create(official_name="Sijal", enabled=True)
        self.source = ArtistSource.objects.create(artist=self.artist, platform="spotify", native_profile_id=ARTIST_ID,
            canonical_url=f"https://open.spotify.com/artist/{ARTIST_ID}", enabled=True, verification="verified",
            poll_interval_seconds=120, next_poll_at=timezone.now() - timedelta(seconds=1))
        self.first = spotify_item("1" * 22, "Old work")
        self.second = spotify_item("2" * 22, "New work")

    def test_first_baseline_and_repeated_poll_have_no_queue_or_details(self):
        fake = FakeSpotify([self.first])
        run = baseline_source(self.source, adapter=fake)
        self.assertEqual(run.status, BaselineRun.Status.COMPLETE)
        self.assertEqual(SourceItem.objects.filter(source=self.source, from_baseline=True).count(), 1)
        self.assertEqual(fake.details, [])
        self.assertEqual(poll_source(self.source, adapter=fake), "success")
        self.assertEqual(SourceItem.objects.filter(source=self.source).count(), 1)
        self.assertFalse(ReviewItem.objects.exists())
        self.assertFalse(ProcessingQueueItem.objects.exists())

    def test_completed_baseline_cannot_absorb_new_ids_as_history(self):
        baseline_source(self.source, adapter=FakeSpotify([self.first]))
        self.source.refresh_from_db()
        fake = FakeSpotify([self.first, self.second])
        baseline_source(self.source, adapter=fake)
        self.assertEqual(fake.calls, 0)
        self.assertEqual(SourceItem.objects.filter(source=self.source).count(), 1)

    def test_failed_baseline_and_later_poll_preserve_snapshot_and_success_cursor(self):
        bad = FakeSpotify([], fail=True)
        with self.assertRaises(SpotifyMetadataError):
            baseline_source(self.source, adapter=bad)
        self.source.refresh_from_db()
        self.assertIsNone(self.source.baseline_completed_at)
        self.assertFalse(BaselineRun.objects.exists())
        good = FakeSpotify([self.first])
        baseline_source(self.source, adapter=good)
        self.source.refresh_from_db()
        success = self.source.last_success_at
        count = SourceItem.objects.count()
        self.assertEqual(poll_source(self.source, adapter=bad), "failed")
        self.source.refresh_from_db()
        self.assertEqual(self.source.last_success_at, success)
        self.assertEqual(SourceItem.objects.count(), count)
        self.assertEqual(self.source.consecutive_failures, 1)

    def test_rate_limit_backoff_does_not_block_soundcloud(self):
        class LimitedSpotify(FakeSpotify):
            def list_recent(self, source):
                raise SpotifyMetadataError("Spotify metadata HTTP 429", retry_after=600)

        soundcloud = ArtistSource.objects.create(artist=self.artist, platform="soundcloud", enabled=True,
            verification="verified", next_poll_at=timezone.now() - timedelta(seconds=1))
        start = timezone.now()
        results = poll_due_sources(now=start, adapters={"spotify": LimitedSpotify([]), "soundcloud": FakeSoundCloud()})
        self.assertEqual(results[self.source.pk], "failed")
        self.assertEqual(results[soundcloud.pk], "baselined")
        self.source.refresh_from_db()
        self.assertIsNone(self.source.baseline_completed_at)
        self.assertGreaterEqual(self.source.next_poll_at, start + timedelta(seconds=600))

    def test_new_id_is_enriched_once_and_reviewed_without_publication_work(self):
        baseline_source(self.source, adapter=FakeSpotify([self.first]))
        fake = FakeSpotify([self.first, self.second])
        self.assertEqual(poll_source(self.source, adapter=fake), "success")
        self.assertEqual(fake.details, [self.second["native_item_id"]])
        self.assertEqual(SourceItem.objects.filter(source=self.source).count(), 2)
        review = ReviewItem.objects.get()
        self.assertEqual(review.source_item.native_item_id, self.second["native_item_id"])
        self.assertTrue(review.evidence["regional_backfill_possible"])
        self.assertFalse(ProcessingQueueItem.objects.exists())
        self.assertEqual(poll_source(self.source, adapter=fake), "success")
        self.assertEqual(fake.details, [self.second["native_item_id"]])
        self.assertEqual(ReviewItem.objects.count(), 1)

    def test_cross_platform_candidate_stays_in_review_with_no_second_queue(self):
        soundcloud = ArtistSource.objects.create(artist=self.artist, platform="soundcloud", enabled=True, verification="verified")
        old = SourceItem.objects.create(source=soundcloud, platform="soundcloud", native_item_id="sc-1",
            title="New work", canonical_url="https://soundcloud.com/example/new-work",
            first_observed_at=timezone.now(), metadata={"duration": 180})
        self.assertEqual(ingest_source_item(old), "queued")
        existing = CanonicalRelease.objects.get()
        queue_count = ProcessingQueueItem.objects.count()
        baseline_source(self.source, adapter=FakeSpotify([self.first]))
        self.assertEqual(poll_source(self.source, adapter=FakeSpotify([self.first, self.second])), "success")
        match = SourceMatch.objects.get(source_item__platform="spotify")
        self.assertEqual(match.release_id, existing.pk)
        self.assertEqual(match.state, SourceMatch.State.REVIEW_REQUIRED)
        self.assertEqual(ProcessingQueueItem.objects.count(), queue_count)
        resolve_review(ReviewItem.objects.get(source_item__platform="spotify"), "approve")
        self.assertEqual(ProcessingQueueItem.objects.count(), queue_count)
