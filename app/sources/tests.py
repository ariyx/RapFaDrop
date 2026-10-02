from io import StringIO
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .adapters import SpotifyAdapter, SourceUnavailable, normalize_soundcloud_item
from .models import Artist, ArtistSource, BaselineRun, SourceAuditEvent, SourceItem
from .services import baseline_source, poll_due_sources


def item(native_id, title="Track"):
    return {
        "native_item_id": str(native_id), "title": title,
        "canonical_url": f"https://soundcloud.com/example/{native_id}",
        "source_release_at": None, "metadata": {"duration": 120},
        "sanitized_raw_data": {"id": native_id, "title": title},
    }


class FakeAdapter:
    def __init__(self, items=None, fail=False):
        self.items = items or []
        self.fail = fail
        self.calls = 0

    def list_recent(self, source):
        self.calls += 1
        if self.fail:
            raise RuntimeError("simulated provider failure")
        return self.items


class SeedTests(TestCase):
    def test_imports_thirty_disabled_unverified_artists_and_candidates(self):
        call_command("seed_sources", verbosity=0)
        self.assertEqual(Artist.objects.count(), 30)
        self.assertEqual(ArtistSource.objects.count(), 57)
        self.assertFalse(Artist.objects.filter(enabled=True).exists())
        self.assertFalse(ArtistSource.objects.filter(enabled=True).exists())
        self.assertFalse(ArtistSource.objects.exclude(verification="unverified").exists())
        self.assertEqual(Artist.objects.exclude(aliases=[]).count(), 30)
        call_command("seed_sources", verbosity=0)
        self.assertEqual(Artist.objects.count(), 30)
        self.assertEqual(ArtistSource.objects.count(), 57)

    def test_persian_alias_round_trips_through_seed_model_management_and_admin(self):
        expected = "حسین تی‌ام"
        call_command("seed_sources", verbosity=0)
        artist = Artist.objects.get(official_name="Hossein Tiem")
        self.assertEqual(artist.aliases, [expected])

        # Reseeding adds the authoritative alias without deleting owner-managed aliases.
        artist.aliases.append("owner spelling")
        artist.save(update_fields=("aliases", "updated_at"))
        call_command("seed_sources", verbosity=0)
        artist.refresh_from_db()
        self.assertEqual(artist.aliases, [expected, "owner spelling"])

        status_output = StringIO()
        call_command("source_status", stdout=status_output)
        self.assertIn(expected, status_output.getvalue())

        user = get_user_model().objects.create_superuser("unicode-admin", "admin@example.test", "test-password")
        self.client.force_login(user)
        response = self.client.get(reverse("admin:sources_artist_changelist"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hossein Tiem")
        self.assertContains(response, expected)

    def test_unconfirmed_soundcloud_sources_stay_empty_without_fan_substitution(self):
        call_command("seed_sources", verbosity=0)
        for name in ("Fadaei", "Ho3ein", "Amir Tataloo"):
            artist = Artist.objects.get(official_name=name)
            self.assertFalse(artist.sources.filter(platform="soundcloud").exists())
        self.assertFalse(ArtistSource.objects.filter(canonical_url__icontains="mahdyar").exists())


class PollingTests(TestCase):
    def setUp(self):
        self.artist = Artist.objects.create(official_name="Test Artist", enabled=True)
        self.source = ArtistSource.objects.create(
            artist=self.artist, platform="soundcloud", native_profile_id="test",
            canonical_url="https://soundcloud.com/test", enabled=True,
            verification="verified", poll_interval_seconds=90,
            next_poll_at=timezone.now() - timedelta(seconds=1),
        )

    def test_disabled_and_unverified_sources_are_not_polled(self):
        adapter = FakeAdapter([item("1")])
        self.source.enabled = False
        self.source.save()
        self.assertEqual(poll_due_sources(adapters={"soundcloud": adapter}), {})
        self.assertEqual(adapter.calls, 0)
        self.source.enabled = True
        self.source.verification = "unverified"
        self.source.save()
        self.assertEqual(poll_due_sources(adapters={"soundcloud": adapter}), {})
        self.assertEqual(adapter.calls, 0)

    def test_initial_baseline_is_idempotent_and_creates_no_publication_work(self):
        adapter = FakeAdapter([item("42"), item("42")])
        first = baseline_source(self.source, adapter=adapter)
        second = baseline_source(self.source, adapter=adapter)
        self.assertEqual(first.status, BaselineRun.Status.COMPLETE)
        self.assertEqual(first.item_count, 2)
        self.assertEqual(second.item_count, 2)
        self.assertEqual(SourceItem.objects.count(), 1)
        stored = SourceItem.objects.get()
        self.assertTrue(stored.from_baseline)
        self.assertEqual(stored.native_item_id, "42")
        self.assertFalse(hasattr(stored, "publication"))
        self.assertIsNotNone(self.source.__class__.objects.get(pk=self.source.pk).baseline_completed_at)

    def test_interrupted_baseline_rolls_back_items_and_can_resume(self):
        adapter = FakeAdapter([item("1"), item("2")])
        from . import services
        real_upsert = services._upsert_items

        def fail_after_first(source, values, observed_at, from_baseline):
            real_upsert(source, values[:1], observed_at, from_baseline)
            raise RuntimeError("simulated interruption")

        with patch("sources.services._upsert_items", side_effect=fail_after_first):
            with self.assertRaises(RuntimeError):
                baseline_source(self.source, adapter=adapter)
        self.assertEqual(SourceItem.objects.count(), 0)
        self.assertEqual(BaselineRun.objects.filter(status="failed").count(), 1)
        completed = baseline_source(self.source, adapter=adapter)
        self.assertEqual(completed.status, "complete")
        self.assertEqual(SourceItem.objects.count(), 2)

    def test_failure_backoff_does_not_stop_another_due_source(self):
        other_artist = Artist.objects.create(official_name="Other Artist", enabled=True)
        healthy = ArtistSource.objects.create(
            artist=other_artist, platform="soundcloud", native_profile_id="other",
            canonical_url="https://soundcloud.com/other", enabled=True,
            verification="verified", baseline_completed_at=timezone.now() - timedelta(days=1),
            next_poll_at=timezone.now() - timedelta(seconds=1), poll_interval_seconds=60,
        )
        self.source.baseline_completed_at = timezone.now() - timedelta(days=1)
        self.source.poll_interval_seconds = 60
        self.source.save()
        now = timezone.now()
        results = poll_due_sources(now=now, adapters={
            "soundcloud": FakeAdapter([item("new")], fail=False),
        })
        self.assertEqual(results[self.source.pk], "success")
        self.assertEqual(results[healthy.pk], "success")
        self.assertEqual(SourceItem.objects.count(), 1)
        # A later failing run only advances its source-specific backoff.
        broken = FakeAdapter(fail=True)
        self.source.refresh_from_db()
        self.source.next_poll_at = now
        self.source.save(update_fields=("next_poll_at",))
        healthy.refresh_from_db()
        healthy.next_poll_at = now
        healthy.save(update_fields=("next_poll_at",))
        # Route by canonical URL while retaining independent provider outcomes.
        class PerSource:
            def list_recent(self, source):
                if source.pk == self_source_id:
                    return broken.list_recent(source)
                return [item("healthy-new")]
        self_source_id = self.source.pk
        results = poll_due_sources(now=now, adapters={"soundcloud": PerSource()})
        self.source.refresh_from_db()
        healthy.refresh_from_db()
        self.assertEqual(results[self.source.pk], "failed")
        self.assertEqual(results[healthy.pk], "success")
        self.assertEqual(self.source.consecutive_failures, 1)
        self.assertEqual((self.source.next_poll_at - now).total_seconds(), 60)
        self.assertEqual(healthy.consecutive_failures, 0)
        self.assertTrue(SourceAuditEvent.objects.filter(source=self.source, event_type="poll_failed").exists())

    def test_item_metadata_is_sanitized(self):
        normalized = normalize_soundcloud_item({"id": 1, "title": "T", "description": "lyrics", "url": "https://media/private?token=secret", "formats": [{"url": "secret"}]})
        self.assertNotIn("description", normalized["sanitized_raw_data"])
        self.assertNotIn("url", normalized["sanitized_raw_data"])
        self.assertNotIn("formats", normalized["sanitized_raw_data"])
        self.assertNotIn("secret", str(normalized))

    def test_spotify_identity_does_not_enable_release_polling(self):
        self.source.enabled = False
        self.source.save(update_fields=("enabled",))
        spotify = ArtistSource.objects.create(artist=self.artist, platform="spotify", native_profile_id="spotify-id", canonical_url="https://open.spotify.com/artist/spotify-id", enabled=True, verification="verified", next_poll_at=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(SourceUnavailable):
            SpotifyAdapter().list_recent(spotify)
        result = poll_due_sources(adapters={"spotify": SpotifyAdapter()})
        self.assertEqual(result[spotify.pk], "unavailable")
        self.assertFalse(spotify.release_polling_available)
        self.assertFalse(SourceItem.objects.filter(platform="spotify").exists())
