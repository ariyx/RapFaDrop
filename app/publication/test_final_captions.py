from io import StringIO
from unittest.mock import patch
from django.test import SimpleTestCase, TestCase, override_settings
from django.core.management import call_command
from operations.management.commands.refresh_owner_defaults import known_audio_default
from publication.captions import DEFAULT_CONFIG, render_caption
from publication.models import CaptionTemplate, PublicationAttempt
from publication.services import perform, _audio_payload
from publication.gateway import TargetBlocked
from archive_collection import tests as fixtures
from archive_collection.services import refresh_published, authorize_publication


class FinalCaptionTests(SimpleTestCase):
    def test_exact_link_line_combinations_and_production_album_only(self):
        head='<a href="https://t.me/RapFaDrop"><b>Fave</b></a>'
        sp='<a href="https://open.spotify.com/track/a">Spotify</a>'
        sc='<a href="https://soundcloud.com/a/b">SoundCloud</a>'
        album='<a href="https://t.me/RapFaDrop/12">Album</a>'
        cases=[({},head),({'spotify_url':'https://open.spotify.com/track/a'},head+'\n› '+sp),({'soundcloud_url':'https://soundcloud.com/a/b'},head+'\n› '+sc),({'spotify_url':'https://open.spotify.com/track/a','soundcloud_url':'https://soundcloud.com/a/b'},head+'\n› '+sp+' · '+sc)]
        for context,expected in cases:
            self.assertEqual(render_caption('archive_audio',context).html,expected)
        context=cases[-1][0]|{'album_post_url':'https://t.me/RapFaDrop/12','album_intro_confirmed':True}
        self.assertEqual(render_caption('archive_audio',context).html,head+'\n› '+sp+' · '+album)
        context['album_post_url']='https://t.me/RapFaDropTest/12'
        self.assertEqual(render_caption('archive_audio',context).html,cases[-1][1])
        context.pop('spotify_url');context['album_post_url']='https://t.me/RapFaDrop/12'
        self.assertEqual(render_caption('archive_audio',context).html,head+'\n› '+album)

    def test_nested_heading_escaping_and_version_without_dangling_parentheses(self):
        html=render_caption('edition',{'version_type':'deluxe','original_confirmed':True,'original_album_post_url':'https://t.me/RapFaDrop/4','spotify_url':'https://open.spotify.com/track/a?x=1&y=2'},{'header':'A & <B>','audio_layout':'linked_heading'}).html
        self.assertTrue(html.startswith('<a href="https://t.me/RapFaDrop"><b>A &amp; &lt;B&gt;</b></a>\nDeluxe (<a'))
        self.assertIn('&amp;y=2',html)
        self.assertEqual(len(html.splitlines()),3)
        html=render_caption('edition',{'version_type':'deluxe','original_album_post_url':'https://t.me/RapFaDropTest/4','original_confirmed':True}).html
        self.assertTrue(html.endswith('\nDeluxe'));self.assertNotIn('(',html)


@override_settings(TELEGRAM_MODE='disabled',TELEGRAM_LIVE_ENABLED=False,PUBLICATION_WORKER_ENABLED=False,SPOTIFY_MEDIA_BRIDGE_ENABLED=False)
class FinalCaptionUpdateTests(TestCase):
    setUp=fixtures.CollectionTests.setUp
    select=fixtures.CollectionTests.select
    ready=fixtures.CollectionTests.ready
    gateway=fixtures.CollectionTests.gateway

    def test_previous_compact_default_migrates_once_custom_and_intro_untouched(self):
        previous={**DEFAULT_CONFIG,'audio_layout':'compact','archive_header':'FAVE','header':'DROP','lp_header':'LP DROP','ep_header':'EP DROP'}
        audio=CaptionTemplate.objects.create(kind='archive_audio',config=previous)
        intro=CaptionTemplate.objects.create(kind='album_intro',config=previous)
        custom=CaptionTemplate.objects.create(kind='single_audio',config=previous|{'brand_label':'Owner brand'})
        self.assertTrue(known_audio_default(previous));self.assertFalse(known_audio_default(custom.config))
        call_command('refresh_owner_defaults',stdout=StringIO());call_command('refresh_owner_defaults',stdout=StringIO())
        audio.refresh_from_db();intro.refresh_from_db();custom.refresh_from_db()
        self.assertFalse(audio.enabled);self.assertTrue(intro.enabled);self.assertTrue(custom.enabled)
        self.assertEqual(CaptionTemplate.objects.filter(kind='archive_audio').count(),2)
        self.assertEqual(CaptionTemplate.objects.get(kind='archive_audio',enabled=True).config,DEFAULT_CONFIG)

    def test_paused_caption_capability_is_idempotent_and_cannot_send_or_retag(self):
        r,pub=self.ready();gateway=self.gateway()
        pub=perform(pub,'send_audio','initial',_audio_payload(pub),gateway=gateway)
        old={**DEFAULT_CONFIG,'audio_layout':'compact','archive_header':'FAVE','header':'DROP','lp_header':'LP DROP','ep_header':'EP DROP'}
        legacy=CaptionTemplate.objects.create(kind='archive_audio',version=2,config=old)
        CaptionTemplate.objects.exclude(pk=legacy.pk).filter(kind='archive_audio').update(enabled=False)
        pub.template=legacy;pub.caption_html=render_caption(pub.kind,pub.context,old).html;pub.save()
        call_command('refresh_owner_defaults',stdout=StringIO())
        self.collection.paused=True;self.collection.save(update_fields=('paused',))
        gateway.allow_paused_caption_edits=True
        result=refresh_published(self.collection,gateway)
        self.assertEqual(result[0]['state'],'published')
        count=PublicationAttempt.objects.count();refresh_published(self.collection,gateway)
        self.assertEqual(PublicationAttempt.objects.count(),count)
        self.collection.refresh_from_db();pub.refresh_from_db()
        self.assertTrue(self.collection.paused);self.assertEqual(pub.message_id,123)
        self.assertTrue(pub.caption_html.startswith('<a href="https://t.me/RapFaDrop"><b>Fave</b></a>'))
        with self.assertRaises(TargetBlocked):authorize_publication(self.collection.pk,pub,'send_audio',{},allow_paused_caption_edits=True)
        with self.assertRaises(TargetBlocked):authorize_publication(self.collection.pk,pub,'edit_media',{},allow_paused_caption_edits=True)
