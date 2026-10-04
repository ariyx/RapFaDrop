from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings

from sources.adapters import SoundCloudAdapter, SourceUnavailable, SpotifyAdapter
from sources.models import Artist, ArtistSource, BaselineRun, SourceItem, SourceAuditEvent
from sources.services import baseline_source, poll_source
from sources.tests import FakeAdapter, item


@override_settings(SPOTIFY_MEDIA_BRIDGE_ENABLED=False, TELEGRAM_MODE='disabled', TELEGRAM_LIVE_ENABLED=False, PUBLICATION_WORKER_ENABLED=False)
class DisabledBaselineTests(TestCase):
    def setUp(self):
        self.artist = Artist.objects.create(official_name='Disabled artist')
        self.source = ArtistSource.objects.create(artist=self.artist, platform='soundcloud', verification='verified')

    def test_disabled_source_baselines_without_activation_and_reuses_completed_run(self):
        adapter = FakeAdapter([item('1'), item('1'), item('2')])
        run = baseline_source(self.source, adapter, allow_disabled=True)
        self.source.refresh_from_db()
        self.artist.refresh_from_db()
        self.assertFalse(self.source.enabled)
        self.assertFalse(self.artist.enabled)
        self.assertEqual(SourceItem.objects.count(), 2)
        self.assertFalse(SourceItem.objects.filter(from_baseline=False).exists())
        self.assertEqual(baseline_source(self.source, adapter, allow_disabled=True).pk, run.pk)
        self.assertEqual(adapter.calls, 1)
        self.assertEqual(BaselineRun.objects.count(), 1)

    @override_settings(SPOTIFY_MEDIA_BRIDGE_ENABLED=True)
    def test_disabled_baseline_refuses_bridge_on_before_provider_access(self):
        adapter = FakeAdapter([item('1')])
        with self.assertRaises(ValueError):
            baseline_source(self.source, adapter, allow_disabled=True)
        self.assertEqual(adapter.calls, 0)
        self.assertEqual(BaselineRun.objects.count(), 0)

    def test_default_still_requires_enabled_state_and_unverified_is_rejected(self):
        with self.assertRaises(ValueError):
            baseline_source(self.source, FakeAdapter())
        self.source.verification = 'unverified'
        with self.assertRaises(ValueError):
            baseline_source(self.source, FakeAdapter(), allow_disabled=True)

    def test_interrupted_disabled_baseline_rolls_back_and_resumes(self):
        adapter = FakeAdapter([item('1')])
        with patch('sources.services._upsert_items', side_effect=RuntimeError('interrupted')):
            with self.assertRaises(RuntimeError):
                baseline_source(self.source, adapter, allow_disabled=True)
        self.assertFalse(SourceItem.objects.exists())
        self.assertFalse(self.source.enabled)
        baseline_source(self.source, adapter, allow_disabled=True)
        self.assertEqual(SourceItem.objects.count(), 1)
        self.assertEqual(BaselineRun.objects.filter(status='complete').count(), 1)


class CompleteSoundCloudTests(TestCase):
    def check(self, entries):
        provider = MagicMock()
        provider.__enter__.return_value.extract_info.return_value = {'entries': entries}
        with patch('sources.adapters.yt_dlp.YoutubeDL', return_value=provider):
            return SoundCloudAdapter().list_recent(ArtistSource(canonical_url='https://soundcloud.com/example'))

    def test_entry_cap_cannot_be_used_as_a_complete_baseline(self):
        with self.assertRaises(SourceUnavailable):
            self.check([{'id':str(i)} for i in range(100)])

    def test_missing_and_duplicate_entries_cannot_be_silently_dropped(self):
        for entries in [None, [None], [{'id':'1'},{'id':'1'}]]:
            with self.assertRaises(SourceUnavailable):
                self.check(entries)


@override_settings(SPOTIFY_DISCOVERY_MODE='spotifyscraper')
class PollMetricsTests(TestCase):
    def test_spotify_adapter_retains_discography_and_detail_metrics(self):
        adapter = SpotifyAdapter()
        probe = MagicMock(last_probe={'requests':3,'pages':2,'elapsed_seconds':.2})
        with patch('sources.spotify_scraper.SpotifyScraperDiscovery', return_value=probe):
            adapter.list_recent(None)
            probe.last_probe={'requests':2,'pages':0,'elapsed_seconds':.1}
            adapter.fetch_item(None,{})
        self.assertEqual(adapter.last_probe['requests'],5)
        self.assertEqual(adapter.last_probe['pages'],2)

    def test_provider_metrics_are_audited_on_success(self):
        from django.utils import timezone
        artist=Artist.objects.create(official_name='Active',enabled=True)
        source=ArtistSource.objects.create(artist=artist,platform='soundcloud',enabled=True,verification='verified',baseline_completed_at=timezone.now())
        adapter=FakeAdapter([item('1')])
        adapter.last_probe={'requests':2,'pages':1,'elapsed_seconds':.2}
        self.assertEqual(poll_source(source,adapter),'success')
        self.assertEqual(SourceAuditEvent.objects.get(event_type='poll_succeeded').detail['provider_probe']['requests'],2)
