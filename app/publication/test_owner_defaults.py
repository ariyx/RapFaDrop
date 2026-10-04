from io import StringIO
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from operations.models import OperatorSettings
from operations.management.commands.refresh_owner_defaults import OLD_ROWS, OLD_TAGS, NEW_TAGS
from .captions import DEFAULT_CONFIG, render_caption
from .models import CaptionTemplate


class OwnerCaptionTests(SimpleTestCase):
    def test_all_audio_kinds_platforms_last_and_omissions(self):
        context = {'release_type': 'ep', 'music_video_url': 'https://example.com/video', 'album_post_url': 'https://t.me/RapFaDrop/1', 'original_track_post_url': 'https://t.me/RapFaDrop/2', 'spotify_url': 'https://open.spotify.com/track/a', 'soundcloud_url': 'https://soundcloud.com/a/b'}
        for kind in ['single_audio', 'album_track_audio', 'edition']:
            html = render_caption(kind, context).html
            self.assertLess(html.index('Music Video</a>'), html.index('Album</a>'))
            self.assertLess(html.index('Original</a>'), html.index('Spotify</a>'))
            self.assertTrue(html.endswith('SoundCloud</a>\n\nt.me/RapFaDrop'))
            self.assertNotIn('\n\n\n', html)
        self.assertEqual(render_caption('single_audio', {}).html, '<b>DROP</b>\n\nt.me/RapFaDrop')
        self.assertNotIn(' / ', render_caption('edition', {'spotify_url': context['spotify_url']}).html)

    def test_intro_related_links_then_platforms_then_footer(self):
        html = render_caption('album_intro', {'title': 'Album', 'artists': ['Artist'], 'original_album_post_url': 'https://t.me/RapFaDrop/1', 'spotify_url': 'https://open.spotify.com/album/a', 'previous_singles': [{'title': 'Single', 'url': 'https://t.me/RapFaDrop/2'}]}).html
        self.assertIn('Previously released from this album:', html)
        self.assertLess(html.index('Single</a>'), html.index('Original Album</a>'))
        self.assertLess(html.index('Original Album</a>'), html.index('Spotify</a>'))
        self.assertTrue(html.endswith('Spotify</a>\n\nt.me/RapFaDrop'))


class DefaultMigrationTests(TestCase):
    def test_known_defaults_versioned_custom_preserved_and_idempotent(self):
        old = {**DEFAULT_CONFIG, 'rows': OLD_ROWS, 'intro_footer': '@RapFaDrop', 'prior_heading': 'پیش‌تر از این آلبوم منتشر شده:'}
        legacy = CaptionTemplate.objects.create(kind='single_audio', version=1, config=old)
        custom = CaptionTemplate.objects.create(kind='edition', version=1, config={**old, 'header': 'Owner custom', 'prior_heading': 'Owner custom heading'})
        setting = OperatorSettings.objects.create(pk=1, tag_fields=list(OLD_TAGS))
        out = StringIO()
        call_command('refresh_owner_defaults', stdout=out)
        call_command('refresh_owner_defaults', stdout=StringIO())
        self.assertEqual(CaptionTemplate.objects.filter(kind='single_audio').count(), 2)
        legacy.refresh_from_db(); custom.refresh_from_db(); setting.refresh_from_db()
        self.assertFalse(legacy.enabled)
        self.assertEqual(custom.config['header'], 'Owner custom')
        self.assertTrue(custom.enabled)
        self.assertIn('Customized template retained', out.getvalue())
        self.assertEqual(set(setting.tag_fields), set(NEW_TAGS))
