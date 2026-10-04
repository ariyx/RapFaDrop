import json
from io import StringIO
from unittest.mock import patch
from django.test import TestCase,SimpleTestCase,override_settings
from django.utils import timezone
from django.core.management import call_command
from publication.captions import render_caption,DEFAULT_CONFIG
from publication.models import CaptionTemplate
from media_pipeline.providers import YouTubeProvider,ProviderProbe
from sources.models import Artist,ArtistSource
from .models import AcquisitionSource,RecordingAlias
from .acquisition import verify_source,find,title_matches
from . import tests as fixtures
from .tests import metadata,A


class CompactCaptionTests(SimpleTestCase):
    def test_context_headings_and_no_blank_rows(self):
        for kind,context,expected in [('archive_audio',{'release_type':'lp'},'FAVE'),('single_audio',{'release_type':'ep'},'DROP'),('album_track_audio',{'release_type':'ep'},'EP DROP'),('album_track_audio',{'release_type':'lp'},'LP DROP')]:
            text=render_caption(kind,context).html
            self.assertTrue(text.startswith('<b>'+expected+'</b>\n'))
            self.assertEqual(len(text.splitlines()),2)

    def test_link_priority_rejects_unconfirmed_and_other_chat(self):
        c={'spotify_url':'https://open.spotify.com/track/a','soundcloud_url':'https://soundcloud.com/a/b','album_post_url':'https://t.me/RapFaDropTest/1','album_intro_confirmed':True}
        self.assertIn('Spotify</a>',render_caption('archive_audio',c).html)
        c['album_post_url']='https://t.me/RapFaDrop/12'
        self.assertIn('Album</a>',render_caption('archive_audio',c).html)
        c['album_intro_confirmed']=False
        self.assertIn('Spotify</a>',render_caption('archive_audio',c).html)
        c.pop('spotify_url');self.assertIn('SoundCloud</a>',render_caption('archive_audio',c).html)

    def test_version_original_requires_valid_identity_and_confirmed_target(self):
        for version in ['instrumental','reissue','deluxe']:
            c={'version_type':version,'original_track_post_url':'https://t.me/RapFaDrop/2','original_confirmed':True}
            self.assertIn(version.capitalize()+' (<a',render_caption('edition',c).html)
            c['original_confirmed']=False
            self.assertIn('\n'+version.capitalize()+'\n',render_caption('edition',c).html)
        self.assertNotIn('Original',render_caption('single_audio',{'version_type':'quality_upgrade','original_confirmed':True}).html)

    def test_intro_exact_output_unchanged(self):
        text=render_caption('album_intro',{'title':'LP','artists':['Artist'],'release_type':'LP','previous_singles':[{'title':'Earlier','url':'https://t.me/RapFaDrop/2'}],'spotify_url':'https://open.spotify.com/album/a'}).html
        self.assertEqual(text,'<b>LP</b>\nLP · Artist\n\nPreviously released from this album:\n› <a href="https://t.me/RapFaDrop/2">Earlier</a>\n\n<a href="https://open.spotify.com/album/a">Spotify</a>\n\nt.me/RapFaDrop')

    def test_official_display_credits_but_not_versions_or_unknown_guests(self):
        m=metadata()
        self.assertTrue(title_matches('Artist - Song [Prod. Producer]',m))
        self.assertFalse(title_matches('Song (Live)',m))
        self.assertFalse(title_matches('Song feat. Unknown',m))

    def test_youtube_only_watch_urls_and_no_transport_shortcuts(self):
        p=YouTubeProvider()
        self.assertTrue(p.can_handle('https://www.youtube.com/watch?v=abcdefghijk'))
        for url in ['https://evil.test/watch?v=abcdefghijk','https://www.youtube.com/playlist?list=a','https://user@youtube.com/watch?v=abcdefghijk']:
            self.assertFalse(p.can_handle(url))


@override_settings(TELEGRAM_MODE='disabled',TELEGRAM_LIVE_ENABLED=False,PUBLICATION_WORKER_ENABLED=False,SPOTIFY_MEDIA_BRIDGE_ENABLED=False)
class ContinuationTests(TestCase):
    setUp=fixtures.CollectionTests.setUp
    select=fixtures.CollectionTests.select
    ready=fixtures.CollectionTests.ready
    gateway=fixtures.CollectionTests.gateway
    def test_acquisition_identity_separate_from_discovery_and_idempotent(self):
        evidence={'spotify_artist_id':A,'checked_at':timezone.now().isoformat(),'independent_links':['https://artist.example/links'],'response_native_id':'123'}
        obj=verify_source(self.artist,'soundcloud','123','https://soundcloud.com/artist',evidence)
        again=verify_source(self.artist,'soundcloud','123','https://soundcloud.com/artist',evidence)
        self.assertEqual(obj.pk,again.pk)
        self.assertEqual(ArtistSource.objects.count(),1)
        self.assertFalse(hasattr(obj,'enabled'))
        with self.assertRaises(ValueError):verify_source(self.artist,'soundcloud','456','https://soundcloud.com/fan',{})

    def test_catalog_cached_and_wrong_uploader_not_downloaded(self):
        r=self.select()
        source=AcquisitionSource.objects.create(artist=self.artist,platform='soundcloud',native_id='123',profile_url='https://soundcloud.com/artist',verified_at=timezone.now(),catalog_checked_at=timezone.now(),catalog=[{'id':'55','title':'Song','url':'https://soundcloud.com/artist/song'}])
        with patch('archive_collection.acquisition.YtDlpProvider') as constructor:
            p=constructor.return_value;p.can_handle.return_value=True
            p.probe.return_value=ProviderProbe('yt-dlp','https://soundcloud.com/artist/song','55','Song',180,'Artist',evidence={'uploader_id':'999'})
            self.assertIsNone(find(r)[0]);p._run.assert_not_called()
            p.probe.return_value=ProviderProbe('yt-dlp','https://soundcloud.com/artist/song','55','Song',180,'Artist',evidence={'uploader_id':'123'})
            self.assertEqual(find(r)[0][0].pk,source.pk)

    def test_audio_defaults_migrate_without_touching_intro_or_custom(self):
        old={k:v for k,v in DEFAULT_CONFIG.items() if k not in {'audio_layout','archive_header','brand_label','brand_url'}}
        intro=CaptionTemplate.objects.create(kind='album_intro',version=1,config={**old,'prior_heading':'unchanged marker'})
        audio=CaptionTemplate.objects.create(kind='archive_audio',version=1,config=old)
        custom=CaptionTemplate.objects.create(kind='single_audio',version=1,config={**old,'header':'Owner'})
        out=StringIO();call_command('refresh_owner_defaults',stdout=out);call_command('refresh_owner_defaults',stdout=StringIO())
        intro.refresh_from_db();custom.refresh_from_db();audio.refresh_from_db()
        self.assertTrue(intro.enabled);self.assertTrue(custom.enabled);self.assertFalse(audio.enabled)
        self.assertEqual(CaptionTemplate.objects.filter(kind='archive_audio').count(),2)
        self.assertIn('custom',out.getvalue().lower())

    def test_alias_reuses_confirmed_message_and_preserves_frozen_rows(self):
        from publication.services import perform,_audio_payload
        from .services import reconcile_recording_alias
        r,pub=self.ready();pub=perform(pub,'send_audio','initial',_audio_payload(pub),gateway=self.gateway())
        r.refresh_from_db();r.candidate.provenance={'source_url':'https://soundcloud.com/artist/song'};r.candidate.save(update_fields=('provenance',))
        other=self.collection.recordings.exclude(pk=r.pk).get()
        evidence={'checked_at':timezone.now().isoformat(),'independent_links':['https://soundcloud.com/artist/song'],
            'shared_native_item_id':r.candidate.source_match.source_item.native_item_id,'shared_recording_url':'https://soundcloud.com/artist/song','both_recordings_match_official_source':True}
        self.collection.paused=True;self.collection.save(update_fields=('paused',))
        alias=reconcile_recording_alias(other,r,evidence)
        self.assertEqual(reconcile_recording_alias(other,r,evidence).pk,alias.pk)
        other.refresh_from_db();self.assertEqual(other.publication.message_id,123)
        self.assertEqual(other.metadata,metadata(other.spotify_id,2))
        self.assertEqual(self.collection.recordings.count(),2)
        self.assertEqual(RecordingAlias.objects.count(),1)

    def test_youtube_fallback_matches_channel_and_stays_bounded(self):
        r=self.select();source=AcquisitionSource.objects.create(artist=self.artist,platform='youtube',native_id='UC'+'a'*22,profile_url='https://www.youtube.com/channel/UC'+'a'*22,verified_at=timezone.now(),catalog_checked_at=timezone.now(),catalog=[{'id':'abcdefghijk','title':'Artist - Song (Official Audio)','url':'https://www.youtube.com/watch?v=abcdefghijk'}])
        with patch('archive_collection.acquisition.YouTubeProvider') as constructor:
            p=constructor.return_value;p.can_handle.return_value=True
            p.probe.return_value=ProviderProbe('yt-dlp-youtube','https://www.youtube.com/watch?v=abcdefghijk','abcdefghijk','Artist - Song (Official Audio)',180,'Artist',evidence={'channel_id':source.native_id})
            found,evidence=find(r);self.assertEqual(found[0].pk,source.pk);self.assertEqual(evidence['provider_probes'],1)
            p.probe.side_effect=RuntimeError('403 bounded failure');self.assertIsNone(find(r)[0]);p.download.assert_not_called()
            source.refresh_from_db();self.assertGreater(source.retry_due_at,timezone.now())
            calls=p.probe.call_count;self.assertIsNone(find(r)[0]);self.assertEqual(p.probe.call_count,calls)
