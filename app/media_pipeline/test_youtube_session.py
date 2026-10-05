import tempfile
from pathlib import Path
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from media_pipeline.providers import YouTubeProvider, YtDlpProvider, ProviderError


class YouTubeSessionTests(SimpleTestCase):
    def test_private_session_copy_and_runtime_are_youtube_only(self):
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / 'protected.txt'
            original.write_text('# Netscape HTTP Cookie File\n')
            original.chmod(0o600)
            observed = []
            def invoke(args, timeout):
                copy = Path(args[1])
                self.assertEqual(args[0], '--cookies')
                self.assertNotEqual(copy, original)
                self.assertEqual(copy.stat().st_mode & 0o777, 0o600)
                self.assertIn('deno:/runtime/deno', args)
                copy.write_text('updated private session')
                observed.append(copy)
                return 'result'
            with override_settings(MEDIA_YOUTUBE_COOKIES_FILE=str(original), MEDIA_YOUTUBE_JS_RUNTIME='deno:/runtime/deno'), patch.object(YtDlpProvider, '_run', side_effect=invoke):
                self.assertEqual(YouTubeProvider()._run(['--version'], 10), 'result')
            self.assertFalse(observed[0].exists())
            self.assertEqual(original.read_text(), '# Netscape HTTP Cookie File\n')

    @override_settings(MEDIA_YOUTUBE_COOKIES_FILE='/missing/private/session.txt')
    def test_missing_session_never_falls_back_to_anonymous(self):
        with patch.object(YtDlpProvider, '_run') as run:
            with self.assertRaises(ProviderError):
                YouTubeProvider()._run(['--version'], 10)
            run.assert_not_called()

    @override_settings(MEDIA_YOUTUBE_COOKIES_FILE='', MEDIA_YOUTUBE_JS_RUNTIME='')
    def test_unconfigured_provider_preserves_existing_behavior(self):
        with patch.object(YtDlpProvider, '_run', return_value='ok') as run:
            YouTubeProvider()._run(['--version'], 10)
            run.assert_called_once_with(['--version'], 10)
