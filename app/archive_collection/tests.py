import tempfile
from pathlib import Path
from unittest.mock import patch
from django.test import TestCase, SimpleTestCase, override_settings
from django.utils import timezone
from publication.captions import render_caption
from publication.gateway import TargetBlocked, GatewayError, GatewayResult, UncertainGatewayError
from publication.models import Publication, PublicationChannel, PublicationReconciliation
from publication.services import perform, _audio_payload
from sources.models import Artist, ArtistSource
from media_pipeline.models import MediaCandidate
from .models import Collection, ArtistSelection, Recording, Slot
from .popular import validate_popular, select_two
from .services import commit_selection, ensure_manual_candidate, identity_matches, reserve, authorize_publication
from .gateway import CollectionGateway

A = "a" * 22
B = "b" * 22


def metadata(native=A, rank=1):
    return {"id": native, "title": "Song", "credits": [{"id": A, "name": "Artist"}],
            "rank": rank, "duration_seconds": 180, "album_id": B, "album_title": "Album",
            "spotify_url": f"https://open.spotify.com/track/{native}", "playable": True,
            "album_artists": ["Artist"], "track_number": 2, "disc_number": 1}


class PopularTests(SimpleTestCase):
    def test_skip_ineligible_and_two_slots(self):
        rows = [metadata(A, 1), metadata(B, 2), metadata("c" * 22, 3), metadata("d" * 22, 4)]
        rows[0]["playable"] = False
        chosen, skipped = select_two(rows, A)
        self.assertEqual([r["rank"] for r in chosen], [2, 3])
        self.assertEqual(skipped[0]["rank"], 1)

    def test_missing_partial_and_wrong_artist_rejected(self):
        for raw in (None, {}, {"uri": f"spotify:artist:{A}", "profile": {"name": "Artist"},
                "discography": {"topTracks": {"items": [], "totalCount": 2}}}):
            with self.assertRaises(RuntimeError):
                validate_popular(raw, A)

    def test_archive_caption_no_drop_and_optional_links(self):
        result = render_caption("archive_audio", {"title": "Song", "artists": ["Artist"],
            "spotify_url": f"https://open.spotify.com/track/{A}"}).html
        self.assertIn("Fave", result)
        self.assertNotIn("<b>Drop</b>", result)
        self.assertNotIn(">Album<", result)
        self.assertNotIn(" / ", result)
        self.assertNotIn("Song", result)
        self.assertNotIn("Artist", result)
        self.assertTrue(result.startswith('<a href="https://t.me/RapFaDrop"><b>Fave</b></a>\n› '))


@override_settings(TELEGRAM_MODE="disabled", TELEGRAM_LIVE_ENABLED=False,
                  PUBLICATION_WORKER_ENABLED=False, SPOTIFY_MEDIA_BRIDGE_ENABLED=False)
class CollectionTests(TestCase):
    def setUp(self):
        self.collection = Collection.objects.create(name="fixture", application_sha="f" * 40)
        self.artist = Artist.objects.create(official_name="Artist", enabled=True)
        self.source = ArtistSource.objects.create(artist=self.artist, platform="spotify", native_profile_id=A,
            canonical_url=f"https://open.spotify.com/artist/{A}", verification="verified", enabled=True,
            baseline_completed_at=timezone.now())
        self.selection = ArtistSelection.objects.create(collection=self.collection, source=self.source, roster_position=0)

    def select(self, rows=None):
        commit_selection(self.selection, {"artist_id": A, "selected": rows or [metadata(), metadata(B, 2)]})
        self.collection.frozen_at = timezone.now()
        self.collection.paused = False
        self.collection.save()
        return self.collection.recordings.first()

    def test_shared_ids_one_recording_and_distinct_ids_preserved(self):
        commit_selection(self.selection, {"artist_id": A, "selected": [metadata(), metadata(B, 2)]})
        other = Artist.objects.create(official_name="Other")
        source = ArtistSource.objects.create(artist=other, platform="spotify", native_profile_id=A)
        selection = ArtistSelection.objects.create(collection=self.collection, source=source, roster_position=1)
        commit_selection(selection, {"artist_id": A, "selected": [metadata()]})
        self.assertEqual(Recording.objects.count(), 2)
        self.assertEqual(Slot.objects.count(), 3)

    def test_frozen_replay_does_not_replace_selection(self):
        r = self.select()
        commit_selection(self.selection, {"artist_id": A, "selected": [metadata("c" * 22)]})
        self.assertEqual(Recording.objects.count(), 2)
        self.assertEqual(self.collection.recordings.first().spotify_id, r.spotify_id)

    def test_frozen_metadata_edit_is_rejected(self):
        from django.core.exceptions import ValidationError
        r = self.select()
        r.metadata = {**r.metadata, "title": "Changed selection"}
        with self.assertRaises(ValidationError):
            r.save()
        self.collection.roster = [{"artist_id": 999}]
        with self.assertRaises(ValidationError):
            self.collection.save()

    def test_conflicting_shared_metadata_rolls_back(self):
        commit_selection(self.selection, {"artist_id": A, "selected": [metadata()]})
        other = ArtistSource.objects.create(artist=Artist.objects.create(official_name="Other"), platform="spotify", native_profile_id=A)
        sel = ArtistSelection.objects.create(collection=self.collection, source=other, roster_position=1)
        bad = metadata()
        bad["title"] = "Different version"
        with self.assertRaises(ValueError):
            commit_selection(sel, {"artist_id": A, "selected": [bad]})
        self.assertFalse(sel.slots.exists())

    def ready(self):
        r = self.select()
        candidate = ensure_manual_candidate(r)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.media_override = override_settings(MEDIA_ROOT=self.directory.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        path = Path(self.directory.name) / "fixture.mp3"
        path.write_bytes(b"fixture bytes; gateway is fake")
        candidate.state = "ready"
        candidate.preparation_state = "ready"
        candidate.validation_report = {"complete": True, "full_decode": "passed"}
        candidate.prepared_path = str(path)
        candidate.observed_facts = {"duration_seconds": 180}
        candidate.save()
        r.refresh_from_db()
        return r, reserve(r)

    def gateway(self, error=None):
        collection_id = self.collection.pk
        class FixtureGateway:
            calls = 0
            def execute(self, operation, target, payload):
                self.calls += 1
                if error:
                    raise error
                return GatewayResult(123, target)
        gateway = FixtureGateway()
        gateway.collection_id = collection_id
        return gateway

    def test_scoped_send_replay_and_paused_isolation(self):
        r, pub = self.ready()
        gateway = self.gateway()
        pub = perform(pub, "send_audio", "initial", _audio_payload(pub), gateway=gateway)
        perform(pub, "send_audio", "initial", _audio_payload(pub), gateway=gateway)
        self.assertEqual(gateway.calls, 1)
        self.collection.paused = True
        self.collection.save()
        with self.assertRaises(TargetBlocked):
            authorize_publication(self.collection.pk, pub, "send_audio", _audio_payload(pub))

    def test_unrelated_publication_and_link_only_rejected(self):
        _, pub = self.ready()
        unrelated = Publication.objects.create(channel=pub.channel, identity_key="unrelated", kind="single_audio")
        with self.assertRaises(TargetBlocked):
            authorize_publication(self.collection.pk, unrelated, "send_text", {"caption_html": "link only"})
        with self.assertRaises(TargetBlocked):
            authorize_publication(self.collection.pk, pub, "send_audio", {**_audio_payload(pub), "title": "Wrong"})

    def test_timeout_reconciliation_blocks_restart_resend(self):
        _, pub = self.ready()
        gateway = self.gateway(UncertainGatewayError("Lost response"))
        pub = perform(pub, "send_audio", "initial", _audio_payload(pub), gateway=gateway)
        perform(pub, "send_audio", "initial", _audio_payload(pub), gateway=gateway)
        self.assertEqual(gateway.calls, 1)
        self.assertEqual(pub.state, "uncertain")
        self.assertEqual(PublicationReconciliation.objects.count(), 1)

    def test_definite_failure_waits_before_retry(self):
        _, pub = self.ready()
        gateway = self.gateway(GatewayError("429", retry_after=300))
        pub = perform(pub, "send_audio", "initial", _audio_payload(pub), gateway=gateway)
        perform(pub, "send_audio", "initial", _audio_payload(pub), gateway=gateway)
        self.assertEqual(gateway.calls, 1)
        self.assertEqual(pub.state, "retry_wait")

    def test_candidate_identity_requires_verified_profile_and_version(self):
        profile = ArtistSource.objects.create(artist=self.artist, platform="soundcloud", canonical_url="https://soundcloud.com/official")
        row = {"uploader_url": profile.canonical_url, "title": "Song", "duration": 180}
        self.assertEqual(identity_matches(row, metadata(), [profile])[0], profile)
        row["title"] = "Song Remix"
        self.assertIsNone(identity_matches(row, metadata(), [profile])[0])
        row.update(title="Song", uploader_url="https://soundcloud.com/fan")
        self.assertIsNone(identity_matches(row, metadata(), [profile])[0])

    def test_unavailable_manual_workflow_keeps_official_all_credits(self):
        from media_pipeline.services import _official_metadata
        r = self.select()
        candidate = ensure_manual_candidate(r)
        self.assertEqual(_official_metadata(candidate)["artists"], ["Artist"])
        self.assertEqual(candidate.state, "review_required")
        self.assertEqual(Publication.objects.count(), 0)

    def test_ordinary_gateway_still_blocks_production(self):
        from publication.gateway import FakeGateway
        self.select()
        with self.assertRaises(TargetBlocked):
            FakeGateway().execute("send_audio", "-1004311149640", {})

    def test_collection_gateway_rechecks_identity_and_permission(self):
        self.select()
        gateway = CollectionGateway(self.collection, "fixture-not-a-real-token", 123)
        bot = {"id": 123, "is_bot": True, "username": "Fixture"}
        chat = {"id": -1004311149640, "type": "channel", "username": "RapFaDrop", "title": "Fixture"}
        member = {"status": "administrator", "can_post_messages": True}
        with patch.object(gateway, "_request", side_effect=[bot, chat, member]):
            self.assertEqual(gateway._guard_live(self.collection.target)[0], self.collection.target)
        for answers in ([{**bot, "id": 456}, chat, member], [bot, {**chat, "id": -100111}, member],
                [bot, chat, {**member, "can_post_messages": False}]):
            with patch.object(gateway, "_request", side_effect=answers):
                with self.assertRaises(TargetBlocked):
                    gateway._guard_live(self.collection.target)

    def test_collection_gateway_cannot_send_without_durable_attempt(self):
        self.select()
        gateway = CollectionGateway(self.collection, "fixture-not-a-real-token", 123)
        with self.assertRaises(TargetBlocked):
            gateway.execute("send_audio", self.collection.target, {"caption_html": "unreserved"})

    @override_settings(SPOTIFY_MEDIA_BRIDGE_ENABLED=True)
    def test_collection_refuses_future_bridge_enabled(self):
        self.select()
        gateway = CollectionGateway(self.collection, "fixture-not-a-real-token", 123)
        with self.assertRaises(TargetBlocked):
            gateway._guard_live(self.collection.target)

    def test_incomplete_selection_is_explicit_without_invented_second_slot(self):
        commit_selection(self.selection, {"artist_id": A, "selected": [metadata()]})
        self.selection.refresh_from_db()
        self.assertEqual(self.selection.slots.count(), 1)
        self.assertIn("Fewer than two", self.selection.error)

    def test_run_retains_reserved_publication_link_and_replay(self):
        from .services import run, status
        r, pub = self.ready()
        Recording.objects.filter(pk=r.pk).update(publication=None)
        gateway = self.gateway()
        with patch("archive_collection.services.time.sleep"):
            run(self.collection, gateway, limit=1)
        r.refresh_from_db()
        self.assertEqual(r.publication_id, pub.pk)
        self.assertEqual(r.publication.message_id, 123)
        self.assertEqual(status(self.collection)["published"], 1)
        with patch("archive_collection.services.time.sleep"):
            run(self.collection, gateway, limit=1)
        self.assertEqual(gateway.calls, 1)

    def test_caption_refresh_edits_same_message_without_retained_media(self):
        from publication.services import edit_caption
        _, pub = self.ready()
        gateway = self.gateway()
        pub = perform(pub, "send_audio", "initial", _audio_payload(pub), gateway=gateway)
        Path(pub.candidate.prepared_path).unlink()
        pub.caption_html = "<b>ARCHIVE</b>\nSong\nArtist"
        pub.save(update_fields=("caption_html",))
        pub = edit_caption(pub, {}, gateway=gateway)
        self.assertEqual(pub.message_id, 123)
        self.assertNotIn("Song", pub.caption_html)
        self.assertNotIn("Artist", pub.caption_html)
        edit_caption(pub, {}, gateway=gateway)
        self.assertEqual(gateway.calls, 2)  # one send and one edit; no duplicate audio

    def test_credited_display_suffixes_match_but_unknown_guests_and_versions_do_not(self):
        profile = ArtistSource.objects.create(artist=self.artist, platform="soundcloud", canonical_url="https://soundcloud.com/official")
        m = metadata()
        m["credits"].append({"id": B, "name": "Guest"})
        for title in ("Song (feat. Guest)", "Artist - Song (Ft. Guest)", "Song - Artist & Guest"):
            row = {"uploader_url": profile.canonical_url, "title": title, "duration": 180}
            self.assertEqual(identity_matches(row, m, [profile])[0], profile)
        for title in ("Song (feat. Unknown)", "Song (feat. Guest) Remix", "Song - Artist & Unknown"):
            row = {"uploader_url": profile.canonical_url, "title": title, "duration": 180}
            self.assertIsNone(identity_matches(row, m, [profile])[0])


    def test_same_recording_retag_edits_existing_message_without_correction_or_resend(self):
        from publication.services import upgrade_single
        r, pub = self.ready()
        gateway = self.gateway()
        pub = perform(pub, 'send_audio', 'initial', _audio_payload(pub), gateway=gateway)
        old = pub.candidate
        new = MediaCandidate.objects.create(track=old.track, release=old.release, source_match=old.source_match,
            provider='manual', state='ready', preparation_state='ready', sha256=old.sha256,
            prepared_path=old.prepared_path, observed_facts=old.observed_facts,
            validation_report=old.validation_report, preparation_report={'owner_policy': 'eleven-fields'},
            quality_rank=old.quality_rank, provenance={'policy_retag_of': old.pk})
        r.candidate = new
        r.save(update_fields=('candidate',))
        pub = upgrade_single(pub, new, gateway=gateway, correction_notice=False)
        self.assertEqual(pub.message_id, 123)
        self.assertEqual(pub.candidate_id, new.pk)
        self.assertEqual(gateway.calls, 2)
        self.assertEqual(Publication.objects.count(), 1)
        from publication.services import ensure_correction
        attempt = pub.attempts.get(operation='edit_media')
        ensure_correction(pub, attempt, gateway=gateway)
        attempt.response.pop('correction_notice')
        ensure_correction(pub, attempt, gateway=gateway)
        self.assertEqual(Publication.objects.count(), 1)
        upgrade_single(pub, new, gateway=gateway, correction_notice=False)
        self.assertEqual(gateway.calls, 2)

    def test_retag_rejects_different_recording_bytes(self):
        r, pub = self.ready()
        gateway = self.gateway()
        pub = perform(pub, 'send_audio', 'initial', _audio_payload(pub), gateway=gateway)
        old = pub.candidate
        new = MediaCandidate.objects.create(track=old.track, release=old.release, source_match=old.source_match,
            provider='manual', state='ready', preparation_state='ready', sha256='different',
            prepared_path=old.prepared_path, observed_facts=old.observed_facts,
            validation_report=old.validation_report, provenance={'policy_retag_of': old.pk})
        r.candidate = new
        r.save(update_fields=('candidate',))
        with self.assertRaises(TargetBlocked):
            authorize_publication(self.collection.pk, pub, 'edit_media', _audio_payload(pub, new))
