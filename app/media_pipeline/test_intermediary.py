import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from django.test import SimpleTestCase
from media_pipeline.intermediary import SpotsaverProvider,find_spotsaver
from media_pipeline.providers import ProviderError


class IntermediaryTests(SimpleTestCase):
    def setUp(self):
        self.p=SpotsaverProvider();self.url='https://open.spotify.com/track/'+'a'*22
        self.expected={'title':'Song','duration_seconds':180,'album_title':'Album','credits':[{'id':'a','name':'Artist'},{'id':'b','name':'Guest'}]}
        self.metadata={'items':[{'title':'Song','artist':'Artist, Guest','album':'Album','duration':180}]}
        self.selected={'videoId':'abcdefghijk'}
        self.public={'title':'Artist - Song (translation)','author_name':'Artist'}

    def probe(self,metadata=None,public=None):
        with patch.object(self.p,'_request',side_effect=[metadata or self.metadata,self.selected,public or self.public]):
            return self.p.probe(self.url,expected=self.expected)

    def test_owner_permitted_unknown_encoding_has_public_metadata_identity(self):
        probe=self.probe()
        self.assertEqual(probe.provider_item_id,'abcdefghijk')
        self.assertTrue(probe.evidence['source_quality_unknown'])
        self.assertNotIn('downloadUrl',probe.evidence)

    def test_wrong_title_credit_native_id_or_album_rejected(self):
        for values in [{'title':'Other'},{'artist':'Artist'},{'id':'b'*22},{'album':'Remix Edition'},{'duration':100}]:
            with self.subTest(values=values),self.assertRaises(ProviderError):
                self.probe(metadata={'items':[{**self.metadata['items'][0],**values}]})

    def test_video_wrong_artist_or_preview_version_rejected(self):
        for public in [{'title':'Other - Song','author_name':'Other'},{'title':'Artist - Song (Demo)'},{'title':'Artist - Song Reaction'}]:
            with self.subTest(public=public),self.assertRaises(ProviderError):self.probe(public=public)

    def test_download_explicitly_different_binding_is_not_owner_permitted(self):
        probe=self.probe()
        with patch.object(self.p,'_request',return_value={'videoId':'other-video','downloadUrl':'https://x.dlsrv.online/a'}),tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ProviderError,'another video'):self.p.download(probe,directory)

    def test_ephemeral_download_url_is_not_retained_in_result(self):
        probe=self.probe()
        with patch.object(self.p,'_request',side_effect=[{'downloadUrl':'https://x.dlsrv.online/a?signature=private'},b'ID3fake-unit-fixture']),tempfile.TemporaryDirectory() as directory:
            result=self.p.download(probe,directory)
            self.assertEqual(result.evidence['output_video_binding'],'unreported_owner_permitted')
            self.assertNotIn('signature',str(result.evidence))
            self.assertEqual(Path(result.path).stat().st_mode & 0o777,0o600)

    def test_private_address_and_unpermitted_provider_never_requested(self):
        with patch('media_pipeline.intermediary.socket.getaddrinfo',return_value=[(None,None,None,None,('127.0.0.1',443))]),patch('media_pipeline.intermediary.requests.Session') as session:
            with self.assertRaises(ProviderError):self.p._request(self.p._context(60),'GET','https://x.dlsrv.online/a',binary=True)
            session.assert_not_called()
        with self.assertRaises(ProviderError):self.p._request(self.p._context(60),'GET','https://evil.test/a',binary=True)

    def test_shared_failure_sets_only_intermediary_hold_and_cached_miss(self):
        r=SimpleNamespace(native_id='a'*22,metadata=self.expected,evidence={},save=Mock());blocked={}
        with patch.object(SpotsaverProvider,'probe',side_effect=ProviderError('Spotsaver shared HTTP 429')) as probe:
            self.assertIsNone(find_spotsaver(r,blocked)[0]);self.assertEqual(set(blocked),{'spotsaver'})
            self.assertIsNone(find_spotsaver(r,blocked)[0]);probe.assert_called_once()
