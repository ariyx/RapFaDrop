import json
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from media_pipeline.providers import ProviderProbe
from .models import AcquisitionSource
from .acquisition import credits_match,find,title_matches
from . import tests as fixtures
from .tests import metadata


class AcquisitionCompletionTests(TestCase):
    setUp=fixtures.CollectionTests.setUp
    select=fixtures.CollectionTests.select

    def make_source(self,platform='soundcloud',native='123',rows=None):
        return AcquisitionSource.objects.create(artist=self.artist,platform=platform,native_id=native,
            profile_url='https://soundcloud.com/artist' if platform=='soundcloud' else 'https://www.youtube.com/channel/'+native,
            verified_at=timezone.now(),catalog_checked_at=timezone.now(),catalog=rows or [])

    def test_collaborator_requires_credit_evidence_even_on_verified_channel(self):
        source=self.make_source('youtube','UC'+'a'*22)
        m={**metadata(),'credits':[*metadata()['credits'],{'id':'c'*22,'name':'Second Artist'}]}
        p=ProviderProbe('yt-dlp-youtube','url','video','Artist - Song',180,'Artist',evidence={})
        self.assertFalse(credits_match(p,m,source))
        p=ProviderProbe('yt-dlp-youtube','url','video','Artist - Song',180,'Artist',evidence={'description':'Song · Artist · Second Artist\nProvided to YouTube by Label'})
        self.assertTrue(credits_match(p,m,source))
        p=ProviderProbe('yt-dlp-youtube','url','video','Artist - Song',180,'Artist',evidence={'description':'Second ArtistExtra'})
        self.assertFalse(credits_match(p,m,source))

    def test_unrelated_duration_compatible_channel_not_accepted(self):
        r=self.select();source=self.make_source('youtube','UC'+'a'*22,[{'id':'abcdefghijk','title':'Song','url':'https://www.youtube.com/watch?v=abcdefghijk'}])
        with patch('archive_collection.acquisition.YouTubeProvider') as make:
            p=make.return_value;p.can_handle.return_value=True
            p.probe.return_value=ProviderProbe('yt-dlp-youtube','url','abcdefghijk','Song',180,'Artist',evidence={'channel_id':'UC'+'b'*22})
            self.assertIsNone(find(r)[0]);p.download.assert_not_called()

    def test_variants_and_unrelated_titles_are_not_candidates(self):
        for title in ['Song (Live)','Song Remix','Song Instrumental','Song Sped Up','Song Slowed','Other Song','Song (Preview)']:
            self.assertFalse(title_matches(title,metadata()),title)
        self.assertTrue(title_matches('Artist - Song (Official Audio)',metadata()))

    def test_catalog_expansion_finds_older_official_track_and_is_bounded(self):
        r=self.select();source=self.make_source(rows=[{'id':str(i),'title':'Other '+str(i)} for i in range(50)])
        with patch('archive_collection.acquisition.YtDlpProvider') as make:
            p=make.return_value;p.can_handle.return_value=True
            p._run.return_value=json.dumps({'entries':[{'id':'55','title':'Song','url':'https://soundcloud.com/artist/song'}]})
            p.probe.return_value=ProviderProbe('yt-dlp','url','55','Song',180,'Artist',evidence={'uploader_id':'123'})
            self.assertEqual(find(r)[0][0].pk,source.pk)
            args=p._run.call_args.args[0]
            self.assertEqual(args[args.index('--playlist-start')+1],'51')
            self.assertEqual(args[args.index('--playlist-end')+1],'150')
            source.refresh_from_db();self.assertEqual(source.evidence['catalog_bound'],150)
            find(r);self.assertEqual(p._run.call_count,1)

    def test_youtube_search_accepts_only_verified_native_channel(self):
        r=self.select();source=self.make_source('youtube','UC'+'a'*22)
        with patch('archive_collection.acquisition.YouTubeProvider') as make:
            p=make.return_value;p.can_handle.return_value=True
            p._run.return_value=json.dumps({'entries':[{'id':'abcdefghijk','title':'Artist - Song (Official Audio)','url':'https://www.youtube.com/watch?v=abcdefghijk'}]})
            p.probe.return_value=ProviderProbe('yt-dlp-youtube','url','abcdefghijk','Artist - Song (Official Audio)',180,'Artist',evidence={'channel_id':source.native_id})
            self.assertEqual(find(r)[0][0].pk,source.pk)
            self.assertIn('ytsearch10:Artist Song',p._run.call_args.args[0])
            find(r);self.assertEqual(p._run.call_count,1)

    def test_shared_challenge_blocks_other_youtube_sources_but_not_soundcloud(self):
        r=self.select();self.make_source('youtube','UC'+'a'*22,[{'id':'abcdefghijk','title':'Song','url':'https://www.youtube.com/watch?v=abcdefghijk'}])
        blocked={}
        with patch('archive_collection.acquisition.YouTubeProvider') as make:
            p=make.return_value;p.can_handle.return_value=True;p.probe.side_effect=RuntimeError('Sign in to confirm you are not a bot')
            self.assertIsNone(find(r,blocked_providers=blocked)[0])
            self.make_source('youtube','UC'+'b'*22,[{'id':'lmnopqrstuv','title':'Song','url':'https://www.youtube.com/watch?v=lmnopqrstuv'}])
            self.assertIsNone(find(r,blocked_providers=blocked)[0]);self.assertEqual(p.probe.call_count,1)
            sc=self.make_source(rows=[{'id':'55','title':'Song','url':'https://soundcloud.com/artist/song'}])
            with patch('archive_collection.acquisition.YtDlpProvider') as other:
                other.return_value.can_handle.return_value=True
                other.return_value.probe.return_value=ProviderProbe('yt-dlp','url','55','Song',180,'Artist',evidence={'uploader_id':'123'})
                self.assertEqual(find(r,blocked_providers=blocked)[0][0].pk,sc.pk)

    def test_catalog_403_does_not_trigger_search_or_other_source_calls(self):
        r=self.select();s=self.make_source();s.catalog_checked_at=None;s.save(update_fields=('catalog_checked_at',))
        self.make_source(native='456')
        with patch('archive_collection.acquisition.YtDlpProvider') as make:
            p=make.return_value;p._run.side_effect=RuntimeError('HTTP 403')
            blocked={};self.assertIsNone(find(r,blocked_providers=blocked)[0])
            self.assertEqual(p._run.call_count,1);p.probe.assert_not_called()
            self.assertIn('soundcloud',blocked)

    def test_matching_music_video_stays_review_without_trimming(self):
        r=self.select();s=self.make_source('youtube','UC'+'a'*22,[{'id':'abcdefghijk','title':'Artist - Song (Official Music Video)','url':'https://www.youtube.com/watch?v=abcdefghijk'}])
        with patch('archive_collection.acquisition.YouTubeProvider') as make:
            p=make.return_value;p.can_handle.return_value=True
            p.probe.return_value=ProviderProbe('yt-dlp-youtube','url','abcdefghijk','Artist - Song (Official Music Video)',180,'Artist',evidence={'channel_id':s.native_id})
            found,evidence=find(r)
            self.assertIsNone(found);self.assertIn('manual identity review',evidence['reason'])
            p.download.assert_not_called()
