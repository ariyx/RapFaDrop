from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.utils import timezone

from sources.models import Artist, ArtistSource, BaselineRun, SourceItem
from archive_collection.models import Collection, Recording
from publication.gateway import TargetBlocked, guard_target
from publication.models import Publication, PublicationChannel
from .models import FreshControl, FreshDispatch, FreshTrack, ProcessingQueueItem, ReleaseTrack
from .fresh import build_manifest, classify, materialize, publication_scope, authorize_fresh_operation, validate_official


class FreshEligibilityTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.artist = Artist.objects.create(official_name='Verified artist', enabled=True)
        self.source = ArtistSource.objects.create(artist=self.artist, platform='spotify', enabled=True,
            verification='verified', native_profile_id='A' * 22, baseline_completed_at=self.now - timedelta(days=2))
        self.baseline = BaselineRun.objects.create(source=self.source, status='complete', started_at=self.now-timedelta(days=3), completed_at=self.source.baseline_completed_at)
        self.item = SourceItem.objects.create(source=self.source, platform='spotify', native_item_id='B'*22,
            title='New release', canonical_url='https://open.spotify.com/album/'+'B'*22,
            first_observed_at=self.now, source_release_at=self.now-timedelta(days=1),
            metadata={'spotify_discovery':True})
        self.metadata = {'album_type':'single', 'artist_ids':['A'*22], 'artist_credits':['Verified artist'],
            'track_count':1, 'tracks':[{'id':'C'*22,'title':'New recording','position':1,'duration_seconds':180,
                'artist_ids':['A'*22],'artist_credits':['Verified artist']}], 'artwork_url':'https://i.scdn.co/image/fixture'}

    def test_post_baseline_manifest_is_durable_and_idempotent_before_jobs(self):
        build_manifest(self.now)
        build_manifest(self.now)
        dispatch = FreshDispatch.objects.get()
        self.assertEqual(dispatch.disposition, 'eligible')
        self.assertEqual(dispatch.evidence['baseline_run_id'], self.baseline.pk)
        self.assertFalse(ProcessingQueueItem.objects.exists())

    def test_baseline_historical_additions_and_same_day_are_not_recent(self):
        self.item.from_baseline = True
        self.assertEqual(classify(self.item)[0], 'excluded')
        self.item.from_baseline = False
        self.item.source_release_at = self.now-timedelta(days=100)
        self.assertEqual(classify(self.item)[0], 'excluded')
        self.item.source_release_at = self.source.baseline_completed_at
        self.assertEqual(classify(self.item)[0], 'review')
        self.item.source_release_at = None
        self.assertEqual(classify(self.item)[0], 'review')

    def test_unpublished_frozen_popular_item_does_not_authorize_fresh_send(self):
        collection = Collection.objects.create(name='fixture', application_sha='0'*40, roster=[], paused=True)
        Recording.objects.create(collection=collection, spotify_id='C'*22, metadata={}, order=1)
        self.item.metadata['tracks'] = self.metadata['tracks']
        self.item.metadata['album_type'] = 'single'
        self.assertEqual(classify(self.item)[0], 'excluded')

    def test_materialize_complete_official_tracks_once_with_native_shared_release(self):
        dispatch = FreshDispatch.objects.create(source_item=self.item, disposition='eligible', reason='fixture')
        materialize(dispatch, self.metadata)
        materialize(dispatch, self.metadata)
        self.assertEqual(FreshTrack.objects.count(), 1)
        self.assertEqual(ProcessingQueueItem.objects.count(), 1)
        # The same native release observed via another artist/source shares identity.
        # Global provider native-ID uniqueness prevents two stored facts for same ID;
        # repeated materialization must not fork its canonical release.
        self.assertEqual(ReleaseTrack.objects.count(), 1)

    def test_native_artist_ids_verify_names_without_guessing_aliases(self):
        self.metadata['artist_credits'] = ['Official compact spelling']
        self.assertEqual(validate_official(self.item, self.metadata)[0], 'single')
        self.metadata['artist_ids'] = ['Z'*22]
        with self.assertRaisesRegex(ValueError, 'omit'):
            validate_official(self.item, self.metadata)

    def test_shared_native_recording_and_order_reuse_one_release_across_observations(self):
        first = FreshDispatch.objects.create(source_item=self.item, disposition='eligible', reason='fixture')
        first = materialize(first, self.metadata)
        shared = SourceItem.objects.create(source=self.source, platform='spotify', native_item_id='G'*22,
            title=self.item.title, first_observed_at=self.now, source_release_at=self.item.source_release_at)
        second = FreshDispatch.objects.create(source_item=shared, disposition='eligible', reason='fixture')
        second = materialize(second, self.metadata)
        self.assertEqual(first.release_id,second.release_id)
        self.assertEqual(first.tracks.get().track_id,second.tracks.get().track_id)
        self.assertEqual(ProcessingQueueItem.objects.count(),1)

    @override_settings(TELEGRAM_PRODUCTION_CHAT_ID='-1004311149640')
    def test_incomplete_album_with_new_ready_file_does_not_get_failure_backoff(self):
        from .fresh import process_dispatch
        from .models import SourceMatch
        from media_pipeline.models import MediaCandidate
        metadata = dict(self.metadata, album_type='album', track_count=3, tracks=[
            dict(self.metadata['tracks'][0], id=native*22, title=title, position=position)
            for position,(native,title) in enumerate([('C','One'),('F','Two'),('H','Three')],1)])
        dispatch = FreshDispatch.objects.create(source_item=self.item, disposition='eligible', reason='fixture', attempts=7)
        dispatch = materialize(dispatch,metadata)
        one,two,three=list(dispatch.tracks.order_by('position'))
        for ft in (one,two):
            match=SourceMatch.objects.get(track=ft.track, matching_method='fresh_official_track')
            candidate=MediaCandidate.objects.create(track=ft.track, release=dispatch.release, source_match=match,
                provider='manual', state='ready')
            if ft.pk==one.pk:
                ft.candidate=candidate
                ft.save()
        with patch('releases.fresh.verified_ready', side_effect=lambda c:c), patch('archive_collection.acquisition.find',
                return_value=(None,{'reason':'Complete audio unavailable'})) as finder:
            process_dispatch(dispatch,{})
        self.assertEqual(finder.call_args.kwargs['cache_age'],timedelta(seconds=self.source.poll_interval_seconds))
        dispatch.refresh_from_db()
        self.assertEqual(dispatch.attempts,0)
        self.assertLess((dispatch.due_at-timezone.now()).total_seconds(),61)
        self.assertFalse(Publication.objects.exists())

    def test_incomplete_or_duplicate_order_is_review(self):
        self.metadata['track_count'] = 2
        with self.assertRaisesRegex(ValueError, 'Complete'):
            validate_official(self.item, self.metadata)
        self.metadata['track_count'] = 1
        self.metadata['tracks'][0]['position'] = 2
        with self.assertRaisesRegex(ValueError, 'ordered'):
            validate_official(self.item, self.metadata)

    def test_waiting_for_recording_does_not_turn_into_hours_of_dispatch_delay(self):
        from .fresh import process_dispatch
        from .models import FreshProviderBackoff
        self.source.poll_interval_seconds=180
        self.source.save(update_fields=('poll_interval_seconds',))
        d=FreshDispatch.objects.create(source_item=self.item, disposition='eligible', reason='fixture', attempts=9)
        d=materialize(d,self.metadata)
        with patch('archive_collection.acquisition.find',return_value=(None,{'reason':'Recording not available yet'})) as finder:
            process_dispatch(d,{'youtube':'Sign in to confirm you are not a bot'})
        d.refresh_from_db()
        self.assertEqual(d.attempts,10)
        self.assertLessEqual((d.due_at-timezone.now()).total_seconds(),180)
        self.assertGreater((d.due_at-timezone.now()).total_seconds(),175)
        self.assertIn('youtube',finder.call_args.kwargs['blocked_providers'])
        self.assertGreater((FreshProviderBackoff.objects.get(platform='youtube').due_at-timezone.now()).total_seconds(),895)
        self.assertFalse(Publication.objects.exists())

    def test_album_primary_and_featured_credits_use_every_track(self):
        self.metadata.update(album_type='album', track_count=2, artist_ids=['A'*22, 'D'*22],
            artist_credits=['Verified artist','Guest'])
        row = dict(self.metadata['tracks'][0], id='F'*22, position=2)
        self.metadata['tracks'][0] = dict(self.metadata['tracks'][0], artist_ids=['A'*22, 'D'*22], artist_credits=['Verified artist','Guest'])
        self.metadata['tracks'].append(row)
        dispatch = FreshDispatch.objects.create(source_item=self.item, disposition='eligible', reason='fixture')
        dispatch = materialize(dispatch, self.metadata)
        self.assertEqual(list(dispatch.release.credited_artists.values_list('official_name',flat=True)), ['Verified artist'])
        self.assertEqual(dispatch.evidence['features'], ['Guest'])
        self.assertEqual(list(dispatch.tracks.order_by('position').values_list('position',flat=True)), [1,2])

    @override_settings(TELEGRAM_PRODUCTION_CHAT_ID='-1004311149640')
    def test_archive_publication_never_enters_fresh_recovery_scope(self):
        channel = PublicationChannel.objects.create(target='-1004311149640')
        archive = Publication.objects.create(channel=channel, identity_key='archive', kind='archive_audio')
        self.assertNotIn(archive.pk, publication_scope()[0])
        FreshControl.objects.create(paused=False)
        with self.assertRaisesRegex(TargetBlocked, 'outside'):
            authorize_fresh_operation(archive, 'send_audio')

    def test_production_guard_requires_all_switches_and_exact_identity(self):
        with self.assertRaises(TargetBlocked):
            guard_target('-1004311149640')
        with override_settings(FRESH_PIPELINE_ENABLED=True, PUBLICATION_WORKER_ENABLED=True,
            TELEGRAM_LIVE_ENABLED=True, TELEGRAM_MODE='production', TELEGRAM_EXPECTED_BOT_ID=8697681226,
            TELEGRAM_PRODUCTION_CHAT_ID='-1004311149640'):
            self.assertEqual(guard_target('@RapFaDrop'), '-1004311149640')
            with override_settings(TELEGRAM_EXPECTED_BOT_ID=1):
                with self.assertRaises(TargetBlocked):
                    guard_target('@RapFaDrop')

    def test_append_preserves_original_track_rows_and_session_snapshot(self):
        from publication.models import AlbumSession
        metadata = dict(self.metadata, album_type='album')
        dispatch = FreshDispatch.objects.create(source_item=self.item, disposition='eligible', reason='fixture')
        dispatch = materialize(dispatch, metadata)
        channel = PublicationChannel.objects.create(target='-1001111111111')
        session = AlbumSession.objects.create(channel=channel, release=dispatch.release, state='complete',
            entries=[{'track_id':dispatch.tracks.get().track_id,'position':1}], cursor=1)
        original = list(dispatch.tracks.values_list('pk','track_id','native_id','position'))
        metadata = dict(metadata, track_count=2, tracks=[*metadata['tracks'],
            dict(metadata['tracks'][0], id='F'*22, title='Later added recording', position=2)])
        materialize(dispatch, metadata, append=True)
        session.refresh_from_db()
        self.assertEqual(session.cursor,1)
        self.assertEqual(len(session.entries),1)
        self.assertEqual(list(dispatch.tracks.filter(position=1).values_list('pk','track_id','native_id','position')), original)
        self.assertEqual(dispatch.tracks.count(),2)
        self.assertEqual(ProcessingQueueItem.objects.count(),2)
        metadata['tracks'].reverse()
        with self.assertRaises(ValueError):
            materialize(dispatch, metadata, append=True)

    @override_settings(FRESH_PIPELINE_ENABLED=True, SPOTIFY_MEDIA_BRIDGE_ENABLED=True)
    def test_review_approval_enters_fresh_processing_once(self):
        from .models import SourceMatch, ReviewItem
        from .services import resolve_review
        match = SourceMatch.objects.create(source_item=self.item, state='review_required', matching_method='spotify_release_id_review')
        review = ReviewItem.objects.create(source_item=self.item, source_match=match, category='low_confidence', reason='Check native release')
        resolve_review(review, 'approve', resolution='Checked complete official native identity')
        resolve_review(review, 'approve', resolution='Checked complete official native identity')
        dispatch = FreshDispatch.objects.get()
        self.assertEqual(dispatch.disposition,'eligible')
        materialize(dispatch,self.metadata)
        materialize(dispatch,self.metadata)
        self.assertEqual(ProcessingQueueItem.objects.count(),1)


from publication.tests import PublicationFixtures
from publication.services import prepare_album, publish_single, advance_album, run_due


class FreshAlbumReuseTests(PublicationFixtures, TestCase):
    def test_media_worker_can_stage_without_publication_credentials_or_send_switches(self):
        from publication.services import reserve_audio
        candidate = self.candidate('Staged')
        with override_settings(FRESH_PIPELINE_ENABLED=True, SPOTIFY_MEDIA_BRIDGE_ENABLED=True,
                TELEGRAM_PRODUCTION_CHAT_ID='-1004311149640'):
            pub = reserve_audio(candidate,'-1004311149640')
            self.assertEqual(pub.state,'pending')
            self.assertFalse(self.gateway.calls)
            with self.assertRaises(TargetBlocked):
                guard_target('-1004311149640')
    def test_cleaned_prior_single_is_reused_without_requiring_old_local_media(self):
        single = self.release('Prior')
        candidate = self.candidate('Prior', release=single, position=1)
        pub = publish_single(candidate, self.target, gateway=self.gateway)
        from pathlib import Path
        Path(candidate.prepared_path).unlink()
        album = self.release('Album', release_type='lp')
        ReleaseTrack.objects.create(release=album, track=candidate.track, position=1)
        second = self.candidate('Second', release=album, position=2)
        session = prepare_album(album, self.target)
        self.assertEqual(session.state, 'prepared')
        self.assertEqual(session.entries[0]['prior_publication_id'], pub.pk)
        advance_album(session, gateway=self.gateway)
        titles = [c['title'] for c in self.gateway.calls if c['operation']=='send_audio']
        self.assertEqual(titles, ['Prior', 'Second'])

    def test_scoped_recovery_ignores_unrelated_pending_archive(self):
        candidate = self.candidate('Archive', release=self.release())
        from publication.services import reserve_audio
        pub = reserve_audio(candidate, self.target, kind='archive_audio')
        run_due(gateway=self.gateway, publication_ids=set(), session_ids=set())
        pub.refresh_from_db()
        self.assertEqual(pub.state, 'pending')
        self.assertFalse(self.gateway.calls)
