import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from django.test import SimpleTestCase
from PIL import Image
from .artwork import fetch_recorded_spotify_artwork
from .providers import ProviderError
from .tagging import validate_artwork

class FrozenArtworkTests(SimpleTestCase):
    def test_official_spotify_cover_is_bounded_and_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            image=root/'fixture.png'
            Image.new('RGB',(32,32),color='blue').save(image)
            response=Mock(is_redirect=False,headers={'Content-Length':str(image.stat().st_size)})
            response.iter_content.return_value=[image.read_bytes()]
            session=Mock()
            session.get.return_value=response
            with patch('media_pipeline.artwork.requests.Session',return_value=session):
                cover=fetch_recorded_spotify_artwork('https://i.scdn.co/image/frozen-id',root/'cover')
            self.assertEqual(validate_artwork(cover)['format'],'PNG')
            self.assertEqual(session.get.call_count,1)
            self.assertFalse(session.get.call_args.kwargs['allow_redirects'])

    def test_untrusted_cover_and_redirect_are_rejected_before_fetching_external_host(self):
        with tempfile.TemporaryDirectory() as directory:
            for url in ['http://i.scdn.co/image/id','https://fan.example/image/id','https://user:pass@i.scdn.co/image/id','https://i.scdn.co/unrelated']:
                session=Mock()
                with patch('media_pipeline.artwork.requests.Session',return_value=session):
                    with self.assertRaises(ProviderError):
                        fetch_recorded_spotify_artwork(url,Path(directory)/'cover')
                session.get.assert_not_called()
            response=Mock(is_redirect=True,headers={'Location':'https://fan.example/cover'})
            session=Mock();session.get.return_value=response
            with patch('media_pipeline.artwork.requests.Session',return_value=session):
                with self.assertRaises(ProviderError):
                    fetch_recorded_spotify_artwork('https://i.scdn.co/image/id',Path(directory)/'cover')
            self.assertEqual(session.get.call_count,1)
