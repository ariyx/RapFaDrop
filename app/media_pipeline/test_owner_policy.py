import subprocess
import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.id3 import TCOM, TPUB, TPE2, TIT3, TKEY
from PIL import Image

from .tagging import prepare_tagged_copy, CHANNEL_FIELDS, readback_tags, TaggingError
from .validation import quality_rank, quality_improved, delivery_eligible


class OwnerMediaPolicyTests(SimpleTestCase):
    @override_settings(MEDIA_CHANNEL_TAG_FIELDS={'comments', 'encoded_by', 'author_url'})
    def test_mp3_m4a_preserve_real_credits_and_remove_only_old_branding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cover = root / 'cover.png'
            Image.new('RGB', (32, 32), color='blue').save(cover)
            for extension, codec in [('mp3', 'libmp3lame'), ('m4a', 'aac')]:
                source, prepared = root / ('source.' + extension), root / ('prepared.' + extension)
                subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=duration=1', '-c:a', codec, '-y', str(source)], check=True, timeout=30)
                if extension == 'mp3':
                    audio = MP3(source)
                    if audio.tags is None: audio.add_tags()
                    audio.tags.add(TCOM(encoding=3, text='Official Composer'))
                    audio.tags.add(TPUB(encoding=3, text='Official Label'))
                    audio.tags.add(TPE2(encoding=3, text='Official Album Artist | @RapFaDrop'))
                    audio.tags.add(TIT3(encoding=3, text='@RapFaDrop'))
                    audio.tags.add(TKEY(encoding=3, text='Dm'))
                else:
                    audio = MP4(source)
                    audio['\xa9wrt'] = ['Official Composer']
                    audio['cprt'] = ['Official Rights']
                    audio['aART'] = ['Official Album Artist | @RapFaDrop']
                    audio['desc'] = ['@RapFaDrop']
                    audio['trkn'] = [(3, 8)]
                audio.save()
                report = prepare_tagged_copy(source, prepared, {'title': 'Official Title', 'artists': ['Track Artist'], 'album': 'Official Album'}, artwork_path=cover)
                self.assertTrue(report['readback']['channel_fields_read_back'])
                self.assertTrue(report['readback']['artwork_read_back'])
                if extension == 'mp3':
                    tags = MP3(prepared).tags
                    self.assertEqual(str(tags['TCOM']), 'Official Composer')
                    self.assertEqual(str(tags['TPUB']), 'Official Label')
                    self.assertEqual(str(tags['TPE2']), 'Official Album Artist')
                    self.assertEqual(str(tags['TKEY']), 'Dm')
                    self.assertNotIn('TIT3', tags)
                else:
                    tags = MP4(prepared).tags
                    self.assertEqual(tags['\xa9wrt'], ['Official Composer'])
                    self.assertEqual(tags['cprt'], ['Official Rights'])
                    self.assertEqual(tags['aART'], ['Official Album Artist'])
                    self.assertEqual(tags['trkn'], [(3, 8)])
                    self.assertNotIn('desc', tags)
                    self.assertEqual(bytes(tags['----:com.apple.iTunes:AUTHORURL'][0]), b'https://t.me/RapFaDrop')

    def test_quality_policy_no_lossless_no_fake_upgrade(self):
        aac = quality_rank({'codec_name': 'aac', 'audio_bitrate_bps': 160000})
        mp3 = quality_rank({'codec_name': 'mp3', 'audio_bitrate_bps': 320000})
        fake = quality_rank({'codec_name': 'mp3', 'audio_bitrate_bps': 320000}, {'transcoded_from_lossy': True})
        self.assertEqual(mp3['delivery_tier'], 2)
        self.assertEqual(aac['delivery_tier'], 1)
        self.assertTrue(quality_improved(mp3, aac))
        self.assertFalse(quality_improved(fake, aac))
        self.assertFalse(quality_improved(quality_rank({'codec_name': 'mp3', 'audio_bitrate_bps': 192000}), aac))
        self.assertFalse(delivery_eligible({'codec_name': 'flac'}))
        self.assertFalse(delivery_eligible({'codec_name': 'pcm_s16le'}))


    @override_settings(MEDIA_CHANNEL_TAG_FIELDS=CHANNEL_FIELDS)
    def test_all_eleven_owner_fields_are_embedded_in_mp3_and_m4a(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for ext, codec in [('mp3', 'libmp3lame'), ('m4a', 'aac')]:
                raw, prepared = root / ('raw.' + ext), root / ('prepared.' + ext)
                subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=duration=1', '-c:a', codec, '-y', str(raw)], check=True, timeout=30)
                report = prepare_tagged_copy(raw, prepared, {'title':'Song', 'artists':['Artist', 'Guest'], 'album':'Album', 'album_artists':['Album Artist']})
                self.assertFalse(report['unsupported_fields'])
                self.assertTrue(CHANNEL_FIELDS <= set(report['mapped_fields']))
                if ext == 'mp3':
                    audio = MP3(prepared)
                    for key in ['TIT3', 'TPUB', 'TENC', 'TCOP', 'TCOM', 'TPE3', 'TKEY']:
                        self.assertEqual(str(audio.tags[key]), '@RapFaDrop')
                    self.assertEqual(str(audio.tags['TALB']), 'Album | @RapFaDrop')
                    self.assertEqual(str(audio.tags['TPE2']), 'Album Artist | @RapFaDrop')
                    self.assertTrue(any(str(f) == '@RapFaDrop' for f in audio.tags.getall('COMM')))
                    self.assertEqual(str(audio.tags.getall('WOAR')[0]), 'https://t.me/RapFaDrop')
                    audio.tags['TPE2'] = TPE2(encoding=3, text='Album Artist')
                else:
                    audio = MP4(prepared)
                    for key in ['desc', '\xa9cmt', '\xa9too', 'cprt', '\xa9wrt']:
                        self.assertEqual(audio.tags[key], ['@RapFaDrop'])
                    for key in ['PUBLISHER', 'CONDUCTOR', 'INITIALKEY']:
                        self.assertEqual(bytes(audio.tags['----:com.apple.iTunes:' + key][0]), b'@RapFaDrop')
                    self.assertEqual(bytes(audio.tags['----:com.apple.iTunes:AUTHORURL'][0]), b'https://t.me/RapFaDrop')
                    self.assertEqual(audio.tags['\xa9alb'], ['Album | @RapFaDrop'])
                    self.assertEqual(audio.tags['aART'], ['Album Artist | @RapFaDrop'])
                    audio.tags['aART'] = ['Album Artist']
                audio.save()
                with self.assertRaises(TaggingError):
                    readback_tags(prepared, 'Song', ['Artist', 'Guest'], 'Album', '@RapFaDrop', False, CHANNEL_FIELDS)
