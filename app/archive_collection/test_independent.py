import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from media_pipeline.providers import ProviderError, ProviderProbe
from media_pipeline.validation import quality_rank, quality_improved
from .acquisition import find_independent_soundcloud


class IndependentRecordingTests(SimpleTestCase):
    def setUp(self):
        self.recording = SimpleNamespace(metadata={'title':'Song', 'duration_seconds':180,
            'credits':[{'id':'a','name':'Artist'}, {'id':'b','name':'Guest'}]}, evidence={}, save=Mock())
        self.url = 'https://soundcloud.com/independent/song'
        self.row = {'id':'55','title':'Artist Guest - Song','url':self.url}
        self.probe = ProviderProbe('yt-dlp', self.url, '55', self.row['title'], 180, 'Independent',
            evidence={'uploader_id':'123','uploader_url':'https://soundcloud.com/independent'})

    def find(self, probe=None, blocked=None):
        with patch('archive_collection.acquisition.YtDlpProvider') as constructor:
            provider=constructor.return_value
            provider._run.return_value=json.dumps({'entries':[self.row]})
            provider.can_handle.return_value=True
            provider.probe.return_value=probe or self.probe
            result=find_independent_soundcloud(self.recording, blocked_providers=blocked)
            return result, provider

    def test_recording_match_requires_no_artist_profile_and_caches_search(self):
        (found,evidence),provider=self.find()
        self.assertIsNotNone(found)
        self.assertIsNone(found[0].pk)
        self.assertEqual(found[0].evidence['identity_role'],'independent_uploader')
        self.assertEqual(evidence['provider_probes'],1)
        (_, _), provider=self.find()
        provider._run.assert_not_called()

    def test_wrong_duration_native_id_uploader_and_missing_guest_rejected(self):
        for probe in [replace(self.probe,duration_seconds=170), replace(self.probe,provider_item_id='56'),
                      replace(self.probe,evidence={'uploader_id':'','uploader_url':'https://soundcloud.com/independent'}),
                      replace(self.probe,title='Artist - Song'),
                      replace(self.probe,title='Artist Guest - Song (Demo)')]:
            with self.subTest(probe=probe):
                (found,_),_=self.find(probe)
                self.assertIsNone(found)

    def test_provider_hold_performs_no_requests(self):
        (found,evidence),provider=self.find(blocked={'soundcloud':'429'})
        self.assertIsNone(found)
        self.assertEqual(evidence['provider_probes'],0)
        provider._run.assert_not_called()
        provider.probe.assert_not_called()

    def test_shared_challenge_stops_and_is_visible(self):
        blocked={}
        with patch('archive_collection.acquisition.YtDlpProvider') as constructor:
            constructor.return_value._run.side_effect=ProviderError('HTTP 429')
            found,evidence=find_independent_soundcloud(self.recording,blocked_providers=blocked)
        self.assertIsNone(found)
        self.assertIn('soundcloud',blocked)
        self.assertIn('independent_search_error',evidence['checks'][0])

    def test_unknown_source_320_is_not_a_quality_upgrade(self):
        rank=quality_rank({'codec_name':'mp3','audio_bitrate_bps':320000}, {'source_quality_unknown':True})
        self.assertEqual(rank['delivery_tier'],1)
        self.assertFalse(quality_improved(rank,{'codec_name':'mp3','audio_bitrate_bps':128000}))
