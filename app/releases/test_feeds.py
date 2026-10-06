from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from sources.models import Artist,ArtistSource,SourceItem
from archive_collection.models import AcquisitionSource
from media_pipeline.providers import ProviderProbe,PROVIDERS
from .models import FreshDiscoveryFeed,FreshDispatch
from .feeds import poll_feed,provider_metadata,validate_feed_boundary
from .fresh import materialize,validate_official


class IndependentFeedTests(TestCase):
    def test_shared_collaborator_profile_does_not_claim_another_artists_upload(self):
        self.source.evidence={'identity_role':'collaborator'};self.source.save()
        self.bootstrap()
        other=Artist.objects.create(official_name='Other artist',enabled=True)
        ArtistSource.objects.create(artist=other,platform='spotify',native_profile_id='b'*22,enabled=True,verification='verified')
        shared=AcquisitionSource.objects.create(artist=other,platform='soundcloud',native_id=self.source.native_id,
            profile_url=self.source.profile_url,evidence={'identity_role':'collaborator'},verified_at=self.now)
        second=FreshDiscoveryFeed.objects.create(acquisition_source=shared,enabled=True)
        poll_feed(second,reader=lambda source:[self.row],now=self.now-timedelta(hours=1))
        row={**self.row,'id':'789','title':'Other artist - New recording'}
        poll_feed(self.feed,reader=lambda source:[row,self.row],now=self.now)
        self.assertFalse(SourceItem.objects.filter(native_item_id='789').exists())
        poll_feed(second,reader=lambda source:[row,self.row],now=self.now)
        self.assertEqual(SourceItem.objects.get(native_item_id='789').source.artist_id,other.pk)
        self.assertEqual(FreshDispatch.objects.count(),1)
    def test_search_watch_is_explicit_and_rejects_upload_without_performer_evidence(self):
        feed=FreshDiscoveryFeed.objects.create(search_artist=self.artist,enabled=True)
        poll_feed(feed,reader=lambda source:[self.row],now=self.now-timedelta(hours=1))
        poll_feed(feed,reader=lambda source:[{**self.row,'id':'789'}],now=self.now)
        item=SourceItem.objects.get(native_item_id='789');p=self.probe()
        from dataclasses import replace
        with patch.object(PROVIDERS['yt-dlp'],'probe',return_value=replace(p,uploader='Unrelated uploader')):
            with self.assertRaisesRegex(ValueError,'explicit performer'):provider_metadata(item)
        with patch.object(PROVIDERS['yt-dlp'],'probe',return_value=p):m=provider_metadata(item)
        self.assertEqual(m['artist_credits'],['Verified artist'])
    def setUp(self):
        self.now=timezone.now();self.artist=Artist.objects.create(official_name='Verified artist',enabled=True)
        self.root=ArtistSource.objects.create(artist=self.artist,platform='spotify',native_profile_id='a'*22,enabled=True,verification='verified')
        self.source=AcquisitionSource.objects.create(artist=self.artist,platform='soundcloud',native_id='123',profile_url='https://soundcloud.com/verified',evidence={'identity_role':'artist'},verified_at=self.now)
        self.feed=FreshDiscoveryFeed.objects.create(acquisition_source=self.source,enabled=True)
        self.row={'id':'456','title':'New recording','url':'https://soundcloud.com/verified/new'}
    def bootstrap(self):
        poll_feed(self.feed,reader=lambda source:[self.row],now=self.now-timedelta(hours=1));self.feed.refresh_from_db()
    def new_item(self):
        self.bootstrap();row={**self.row,'id':'789'}
        poll_feed(self.feed,reader=lambda source:[row,self.row],now=self.now)
        return SourceItem.objects.get(platform='soundcloud',native_item_id='789')
    def probe(self,**kwargs):
        return ProviderProbe('yt-dlp','https://soundcloud.com/verified/new','789','New recording',180,'Verified artist','https://i1.sndcdn.com/art-large.jpg',
            {'uploader_id':kwargs.get('uploader','123'),'timestamp':kwargs.get('timestamp',(self.now-timedelta(seconds=30)).timestamp())})
    def test_first_window_is_watermarked_without_historical_jobs(self):
        self.bootstrap();self.assertEqual(self.feed.seen_ids,['456']);self.assertFalse(SourceItem.objects.exists());self.assertFalse(FreshDispatch.objects.exists())
        self.assertFalse(self.root.baseline_completed_at)
    def test_new_upload_persists_wakes_once_and_replay_is_idempotent(self):
        self.bootstrap();row={**self.row,'id':'789'}
        with patch('releases.feeds.wake_media') as wake:
            poll_feed(self.feed,reader=lambda source:[row,self.row],now=self.now)
            poll_feed(self.feed,reader=lambda source:[row,self.row],now=self.now)
        self.assertEqual(wake.call_count,1);self.assertEqual(FreshDispatch.objects.count(),1)
        self.assertEqual(SourceItem.objects.get().platform,'soundcloud')
    def test_only_explicit_native_catchup_can_cross_first_watermark(self):
        self.feed.catchup_native_ids=['456'];self.feed.save()
        poll_feed(self.feed,reader=lambda source:[self.row],now=self.now)
        self.assertEqual(FreshDispatch.objects.count(),1);self.assertTrue(SourceItem.objects.get().metadata['catchup_authorized'])
    def test_exact_native_provider_identity_is_required_before_materialization(self):
        item=self.new_item()
        with patch.object(PROVIDERS['yt-dlp'],'probe',return_value=self.probe(uploader='999')):
            with self.assertRaisesRegex(ValueError,'identity mismatch'):provider_metadata(item)
        self.assertFalse(item.freshdispatch.release_id)
    def test_old_reappearing_upload_cannot_become_new_release(self):
        item=self.new_item()
        with patch.object(PROVIDERS['yt-dlp'],'probe',return_value=self.probe(timestamp=(self.now-timedelta(days=10)).timestamp())):
            with self.assertRaisesRegex(ValueError,'Historical upload'):provider_metadata(item)
    def test_complete_provider_single_uses_real_ids_and_later_spotify_reuses_track(self):
        item=self.new_item()
        with patch.object(PROVIDERS['yt-dlp'],'probe',return_value=self.probe()):m=provider_metadata(item)
        d=materialize(item.freshdispatch,m);track=d.tracks.get().track
        self.assertEqual(d.tracks.get().native_id,'789');self.assertEqual(d.tracks.get().metadata['spotify_url'],'')
        spotify=SourceItem.objects.create(source=self.root,platform='spotify',native_item_id='b'*22,title='New recording',source_release_at=self.now,first_observed_at=self.now)
        dm={**m,'tracks':[{**m['tracks'][0],'id':'c'*22}]};sd=FreshDispatch.objects.create(source_item=spotify,disposition='eligible',reason='fixture')
        self.assertEqual(materialize(sd,dm).tracks.get().track_id,track.pk)
    def test_missing_artwork_and_explicit_feature_are_held(self):
        item=self.new_item();p=self.probe()
        from dataclasses import replace
        for invalid in (replace(p,artwork_source_url=''),replace(p,title='New recording feat Unknown')):
            with patch.object(PROVIDERS['yt-dlp'],'probe',return_value=invalid):
                with self.assertRaises(ValueError):provider_metadata(item)
    def test_provider_native_pattern_cannot_accept_fabricated_spotify_id(self):
        item=self.new_item()
        with patch.object(PROVIDERS['yt-dlp'],'probe',return_value=self.probe()):m=provider_metadata(item)
        m['tracks'][0]['id']='z'*22
        with self.assertRaisesRegex(ValueError,'Incomplete ordered'):validate_official(item,m)
    def test_fullwidth_structured_guest_credits_are_preserved_without_fake_spotify_identity(self):
        item=self.new_item();p=self.probe()
        from dataclasses import replace
        p=replace(p,evidence={**p.evidence,'artist':'Verified artist， Guest Singer'})
        with patch.object(PROVIDERS['yt-dlp'],'probe',return_value=p):m=provider_metadata(item)
        d=materialize(item.freshdispatch,m)
        self.assertEqual(d.tracks.get().metadata['credits'][1]['name'],'Guest Singer')
        self.assertTrue(d.tracks.get().metadata['credits'][1]['id'].startswith('name:'))
        self.assertFalse(Artist.objects.get(official_name='Guest Singer').enabled)
    def test_structured_artist_cannot_be_inferred_from_uploader_when_omitted(self):
        item=self.new_item();p=self.probe()
        from dataclasses import replace
        p=replace(p,evidence={**p.evidence,'artist':'Different Artist'})
        with patch.object(PROVIDERS['yt-dlp'],'probe',return_value=p):
            with self.assertRaisesRegex(ValueError,'omit monitored'):provider_metadata(item)
