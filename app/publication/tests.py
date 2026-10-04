import subprocess
import tempfile
import threading
import time
from io import StringIO
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import OperationalError, close_old_connections, connection, connections
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from PIL import Image

from media_pipeline.models import MediaCandidate
from media_pipeline.tagging import prepare_tagged_copy
from media_pipeline.validation import probe_audio, quality_rank
from releases.models import CanonicalRelease, ReleaseCredit, ReleaseTrack, SourceMatch, Track, TrackCredit
from sources.models import Artist, ArtistSource, SourceItem

from .captions import CaptionError, DEFAULT_CONFIG, render_caption, visible_length
from .gateway import FakeGateway, GatewayError, GatewayResult, TargetBlocked, TelegramGateway, UncertainGatewayError
from .models import AlbumSession, CaptionTemplate, Publication, PublicationAttempt, PublicationChannel, PublicationReconciliation
from .services import PublicationError, advance_album, edit_caption, prepare_album, publish_single, reconcile, reserve_audio, run_due, upgrade_single
from .tasks import process_due_publications


class CaptionTests(SimpleTestCase):
    def test_single_conditionals_escape_and_one_platform(self):
        rendered = render_caption("single_audio", {"spotify_url": "https://open.spotify.com/track/example?a=1&b=2"})
        self.assertIn("<b>DROP</b>", rendered.html)
        self.assertIn("Spotify</a>", rendered.html)
        self.assertIn("&amp;b=2", rendered.html)
        self.assertNotIn(" / ", rendered.html)
        for missing in ("SoundCloud", "Music Video", ">Album<", ">Original<"):
            self.assertNotIn(missing, rendered.html)
        no_links = render_caption("single_audio", {}).html
        self.assertEqual(no_links, "<b>DROP</b>\n\nt.me/RapFaDrop")

    def test_intro_title_only_bold_guest_only_italic_and_required_marker(self):
        result = render_caption("album_intro", {"title": "راه & <script> 🎧", "artists": ["هیچ‌کس", "Artist <Two>"], "features": ["Guest & One", "مهمان"], "release_type": "EP", "previous_singles": [{"title": "Earlier <single>", "url": "https://t.me/test_channel/12"}]})
        self.assertIn("<b>راه &amp; &lt;script&gt; 🎧</b>", result.html)
        self.assertIn("EP · هیچ‌کس × Artist &lt;Two&gt;", result.html)
        self.assertIn("feat. <i>Guest &amp; One</i> · <i>مهمان</i>", result.html)
        self.assertEqual(result.html.count("<b>"), 1)
        self.assertIn('› <a href="https://t.me/test_channel/12">Earlier &lt;single&gt;</a>', result.html)
        self.assertNotIn("•", result.html)

    def test_empty_blocks_and_removable_album_header(self):
        intro = render_caption("album_intro", {"title": "Album", "artists": ["Artist"]}).html
        self.assertNotIn("feat.", intro)
        self.assertNotIn("پیش‌تر", intro)
        track = render_caption("album_track_audio", {"release_type": "ep", "album_post_url": "https://t.me/test_channel/1"}, {"ep_header": ""}).html
        self.assertNotIn("<b>", track)
        self.assertIn(">Album</a>", track)

    def test_overflow_contains_all_prior_links_within_limits(self):
        prior = [{"title": f"ترانه {index} " + "Long Title " * 10, "url": f"https://t.me/test_channel/{index+1}"} for index in range(100)]
        result = render_caption("album_intro", {"title": "راه", "artists": ["Artist"], "previous_singles": prior})
        self.assertLessEqual(visible_length(result.html), 1024)
        self.assertTrue(result.overflow)
        self.assertTrue(all(visible_length(chunk) <= 4096 for chunk in result.overflow))
        self.assertEqual((result.html + "\n".join(result.overflow)).count('href="https://t.me/test_channel/'), 100)
        self.assertTrue(all(row.startswith("› ") for chunk in result.overflow for row in chunk.splitlines()))

    def test_unsafe_url_and_oversized_core_are_refused(self):
        with self.assertRaises(CaptionError):
            render_caption("single_audio", {"soundcloud_url": "javascript:alert(1)"})
        with self.assertRaises(CaptionError):
            render_caption("single_audio", {"album_post_url": "https://evil.test/1"})
        with self.assertRaises(CaptionError):
            render_caption("single_audio", {"soundcloud_url": "https://soundcloud.com/example/song?token=fixture-secret"})
        with self.assertRaises(CaptionError):
            render_caption("album_intro", {"title": "X" * 1025, "artists": []})


class PublicationFixtures:
    target = "-1001111111111"

    def setUp(self):
        super().setUp()
        self.temp = tempfile.TemporaryDirectory(prefix="rapfadrop-m4-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.override = override_settings(MEDIA_ROOT=self.root, TELEGRAM_LIVE_ENABLED=False, PUBLICATION_WORKER_ENABLED=False, TELEGRAM_MODE="disabled", TELEGRAM_BOT_TOKEN="", TELEGRAM_TEST_CHAT_ID=self.target, TELEGRAM_REVIEW_CHAT_ID="-1002222222222", TELEGRAM_PRODUCTION_CHAT_ID="-1009999999999", PUBLICATION_CORRECTION_DELETE_SECONDS=600, PUBLICATION_ALBUM_HOLD_SECONDS=900)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.artist = Artist.objects.create(official_name="هیچ‌کس", aliases=["Hichkas"])
        self.source = ArtistSource.objects.create(artist=self.artist, platform="soundcloud", native_profile_id="m4fixture", canonical_url="https://soundcloud.com/m4fixture")
        self.cover = self.root / "official-cover.jpg"
        Image.new("RGB", (500, 500), (20, 80, 140)).save(self.cover)
        self.gateway = FakeGateway()
        self.now = timezone.now()
        self.serial = 0

    def release(self, title="Single", release_type="single", edition_of=None):
        release = CanonicalRelease.objects.create(title=title, release_type=release_type, state="approved", edition_of=edition_of)
        ReleaseCredit.objects.create(release=release, artist=self.artist)
        return release

    def candidate(self, title="راه & Road", *, release=None, track=None, position=1, bitrate=64, with_cover=True):
        self.serial += 1
        release = release or self.release(title)
        if track is None:
            track = Track.objects.create(official_title=title, duration_seconds=2)
            TrackCredit.objects.create(track=track, artist=self.artist)
            ReleaseTrack.objects.create(release=release, track=track, position=position)
            item = SourceItem.objects.create(platform="soundcloud", native_item_id=f"m4fixture-{self.serial}-{track.pk}", source=self.source, title=title, canonical_url=f"https://soundcloud.com/m4fixture/{track.pk}", metadata={"duration": 2}, first_observed_at=self.now)
            match = SourceMatch.objects.create(source_item=item, release=release, track=track, state="approved", confidence=100, matching_method="local-generated-fixture")
        else:
            match = track.source_matches.first()
        raw = self.root / f"original-{self.serial}.mp3"
        prepared = self.root / f"prepared-{self.serial}.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency={500+self.serial*27}:duration=2", "-c:a", "libmp3lame", "-b:a", f"{bitrate}k", "-y", str(raw)], check=True, timeout=30)
        facts = probe_audio(raw)
        report = prepare_tagged_copy(raw, prepared, {"title": track.official_title, "artists": [self.artist.official_name], "album": release.title}, artwork_path=self.cover if with_cover else None)
        return MediaCandidate.objects.create(track=track, release=release, source_match=match, provider="manual", state="ready", preparation_state="ready", artwork_state="embedded" if with_cover else "not_provided", candidate_path=str(raw), prepared_path=str(prepared), artwork_path=str(self.cover) if with_cover else "", sha256=facts["sha256"], observed_facts=facts, validation_report={"complete": True, "status": "valid"}, preparation_report=report, quality_rank=quality_rank(facts, {"provenance_confidence": 100}))

    def album(self, count=4):
        release = self.release("آلبوم <Album>", "lp")
        candidates = [self.candidate(title=name, release=release, position=index+1) for index, name in enumerate(["One", "Two", "Three", "Four"][:count])]
        return release, candidates


class PublicationTests(PublicationFixtures, TestCase):
    def test_pending_attempt_exists_before_gateway_and_duplicate_is_inert(self):
        candidate = self.candidate()
        original_execute = self.gateway.execute
        def execute(operation, target, payload):
            self.assertTrue(PublicationAttempt.objects.filter(state="pending").exists())
            self.assertTrue(PublicationChannel.objects.filter(in_flight__isnull=False).exists())
            return original_execute(operation, target, payload)
        self.gateway.execute = execute
        pub = publish_single(candidate, self.target, gateway=self.gateway)
        again = publish_single(candidate, self.target, gateway=self.gateway)
        self.assertEqual(pub.pk, again.pk)
        self.assertEqual(pub.state, "published")
        self.assertEqual(len(self.gateway.calls), 1)
        self.assertTrue(pub.message_url)

    def test_nonready_or_ambiguous_media_never_sends(self):
        candidate = self.candidate()
        candidate.state = "review_required"
        candidate.save()
        with self.assertRaises(PublicationError):
            publish_single(candidate, self.target, gateway=self.gateway)
        candidate.state = "ready"
        candidate.save()
        SourceMatch.objects.filter(pk=candidate.source_match_id).update(confidence=50)
        with self.assertRaises(PublicationError):
            publish_single(candidate, self.target, gateway=self.gateway)
        self.assertEqual(self.gateway.calls, [])

    def test_uncertain_send_stops_blind_resend_and_is_visible_in_admin(self):
        candidate = self.candidate()
        self.gateway.failures["send_audio"] = [UncertainGatewayError("Fixture response lost")]
        pub = publish_single(candidate, self.target, gateway=self.gateway)
        self.assertEqual(pub.state, "uncertain")
        publish_single(candidate, self.target, gateway=self.gateway, now=self.now+timedelta(hours=1))
        run_due(gateway=self.gateway, now=self.now+timedelta(hours=1))
        self.assertEqual(sum(call["operation"] == "send_audio" for call in self.gateway.calls), 1)
        record = PublicationReconciliation.objects.get(attempt__publication=pub)
        self.assertEqual(record.state, "open")
        actor = get_user_model().objects.create_superuser("reviewer", "reviewer@example.test", "fixture-only")
        self.client.force_login(actor)
        response = self.client.get("/admin/publication/publicationreconciliation/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "open")

    def test_lost_database_commit_requires_reconciliation_after_lease(self):
        candidate = self.candidate()
        with patch("publication.services._apply_success", side_effect=OperationalError("fixture DB interruption")):
            with self.assertRaises(OperationalError):
                publish_single(candidate, self.target, gateway=self.gateway, now=self.now)
        pub = publish_single(candidate, self.target, gateway=self.gateway, now=self.now+timedelta(minutes=3))
        self.assertEqual(pub.state, "uncertain")
        self.assertEqual(sum(call["operation"] == "send_audio" for call in self.gateway.calls), 1)
        self.assertTrue(pub.attempts.filter(reconciliation__state="open").exists())

    def test_operator_success_reconciliation_attaches_observed_message(self):
        candidate = self.candidate()
        self.gateway.failures["send_audio"] = [UncertainGatewayError()]
        pub = publish_single(candidate, self.target, gateway=self.gateway)
        actor = get_user_model().objects.create_user("operator", is_staff=True)
        attempt = pub.attempts.get(operation="send_audio")
        result = reconcile(attempt, actor=actor, decision="confirmed_success", evidence="Observed fixture message 901 in the isolated target", message_id=901, remote_chat_id=self.target)
        self.assertEqual(result.message_id, 901)
        self.assertEqual(result.state, "published")
        publish_single(candidate, self.target, gateway=self.gateway)
        self.assertEqual(sum(call["operation"] == "send_audio" for call in self.gateway.calls), 1)
        self.assertTrue(result.audit_events.filter(actor=actor, action="operator_reconciled").exists())

    def test_upgrade_same_message_and_reply_deleted_on_schedule(self):
        candidate = self.candidate()
        pub = publish_single(candidate, self.target, gateway=self.gateway, now=self.now)
        original_id, original_url = pub.message_id, pub.message_url
        better = self.candidate(release=candidate.release, track=candidate.track, bitrate=192)
        upgraded = upgrade_single(pub, better, gateway=self.gateway, now=self.now)
        self.assertEqual((upgraded.message_id, upgraded.message_url), (original_id, original_url))
        self.assertEqual(upgraded.candidate_id, better.pk)
        reply = Publication.objects.get(kind="correction")
        self.assertEqual(reply.delete_due_at, self.now+timedelta(minutes=10))
        self.assertEqual(self.gateway.calls[-1]["reply_to_message_id"], original_id)
        run_due(gateway=self.gateway, now=self.now+timedelta(minutes=9))
        self.assertFalse(any(call["operation"] == "delete" for call in self.gateway.calls))
        run_due(gateway=self.gateway, now=self.now+timedelta(minutes=10))
        reply.refresh_from_db()
        self.assertEqual(reply.state, "deleted")
        self.assertEqual(sum(call["operation"] == "send_audio" for call in self.gateway.calls), 1)
        self.assertEqual(sum(call["operation"] == "reply" for call in self.gateway.calls), 1)

    def test_failed_edit_retries_edit_without_replacement_post(self):
        candidate = self.candidate()
        pub = publish_single(candidate, self.target, gateway=self.gateway, now=self.now)
        better = self.candidate(release=candidate.release, track=candidate.track, bitrate=192)
        self.gateway.failures["edit_media"] = [GatewayError("Fixture definite rejection")]
        result = upgrade_single(pub, better, gateway=self.gateway, now=self.now)
        self.assertEqual(result.state, "retry_wait")
        self.assertEqual(result.candidate_id, candidate.pk)
        run_due(gateway=self.gateway, now=self.now+timedelta(minutes=2))
        result.refresh_from_db()
        self.assertEqual(result.candidate_id, better.pk)
        self.assertEqual(sum(call["operation"] == "send_audio" for call in self.gateway.calls), 1)
        self.assertEqual(sum(call["operation"] == "edit_media" for call in self.gateway.calls), 2)

    def test_uncertain_edit_preserves_original_and_never_resends_audio(self):
        candidate = self.candidate()
        pub = publish_single(candidate, self.target, gateway=self.gateway)
        better = self.candidate(release=candidate.release, track=candidate.track, bitrate=192)
        self.gateway.failures["edit_media"] = [UncertainGatewayError("Fixture edit response lost")]
        result = upgrade_single(pub, better, gateway=self.gateway)
        run_due(gateway=self.gateway, now=self.now+timedelta(hours=1))
        self.assertEqual(result.state, "uncertain")
        self.assertEqual(result.message_id, pub.message_id)
        self.assertEqual(result.candidate_id, candidate.pk)
        self.assertEqual(sum(call["operation"] == "edit_media" for call in self.gateway.calls), 1)
        self.assertEqual(sum(call["operation"] == "send_audio" for call in self.gateway.calls), 1)
        self.assertFalse(Publication.objects.filter(kind="correction").exists())

    def test_late_links_edit_existing_caption_with_stored_template_version(self):
        candidate = self.candidate()
        pub = publish_single(candidate, self.target, gateway=self.gateway)
        template = pub.template
        template.config = {**template.config, "header": "Changed"}
        with self.assertRaises(ValidationError):
            template.save()
        CaptionTemplate.objects.create(kind="single_audio", version=2, config={**DEFAULT_CONFIG, "header": "New header"})
        result = edit_caption(pub, {"music_video_url": "https://www.youtube.com/watch?v=official", "spotify_url": "https://open.spotify.com/track/fixture"}, gateway=self.gateway)
        self.assertEqual(result.message_id, pub.message_id)
        self.assertIn("<b>DROP</b>", result.caption_html)
        self.assertIn("Music Video</a>", result.caption_html)
        self.assertIn(" / ", result.caption_html)
        self.assertEqual(result.template.version, 1)

    def test_earlier_single_album_links_both_directions_and_skips_audio(self):
        candidate = self.candidate("Earlier")
        single = publish_single(candidate, self.target, gateway=self.gateway)
        release = self.release("Later LP", "lp")
        ReleaseTrack.objects.create(release=release, track=candidate.track, position=1, prior_single=candidate.track.release_memberships.first())
        other = self.candidate("New Track", release=release, position=2)
        session = prepare_album(release, self.target, context={"features": ["Guest"]})
        result = advance_album(session, gateway=self.gateway)
        self.assertEqual(result.state, "complete")
        single.refresh_from_db()
        result.intro.refresh_from_db()
        self.assertIn(single.message_url, result.intro.caption_html)
        self.assertIn("› ", result.intro.caption_html)
        self.assertIn(result.intro.message_url, single.caption_html)
        self.assertIn("<b>DROP</b>", single.caption_html)
        new_pub = Publication.objects.get(track=other.track)
        self.assertIn("<b>LP DROP</b>", new_pub.caption_html)
        audios = [call for call in self.gateway.calls if call["operation"] == "send_audio"]
        self.assertEqual([call["title"] for call in audios], ["Earlier", "New Track"])
        self.assertFalse(any("reply_to_message_id" in call for call in audios))

    def test_first_album_track_links_to_intro_confirmed_in_the_same_call(self):
        release, candidates = self.album(2)
        session = advance_album(prepare_album(release, self.target), gateway=self.gateway)
        self.assertEqual(session.state, "complete")
        intro = Publication.objects.get(pk=session.intro_id)
        self.assertTrue(intro.message_url)
        for call in self.gateway.calls:
            if call["operation"] == "send_audio":
                self.assertIn(intro.message_url, call["caption_html"])
        for pub in Publication.objects.filter(album_session=session, kind=Publication.Kind.TRACK):
            self.assertIn(intro.message_url, pub.caption_html)

    def test_album_missing_ready_track_blocks_intro_but_not_other_single(self):
        release, candidates = self.album(2)
        MediaCandidate.objects.filter(pk=candidates[1].pk).update(state="review_required")
        session = prepare_album(release, self.target)
        self.assertIsNone(session.intro_id)
        self.assertEqual(session.state, "waiting_media")
        unrelated = self.candidate("Unrelated")
        publish_single(unrelated, self.target, gateway=self.gateway)
        self.assertEqual([call["operation"] for call in self.gateway.calls], ["send_audio"])

    def test_album_rechecks_readiness_immediately_before_intro(self):
        release, candidates = self.album(2)
        session = prepare_album(release, self.target)
        self.assertIsNotNone(session.intro_id)
        MediaCandidate.objects.filter(pk=candidates[1].pk).update(state="invalid")
        result = advance_album(session, gateway=self.gateway)
        self.assertEqual(result.state, "waiting_media")
        self.assertFalse(self.gateway.calls)

    def test_prior_single_cover_is_not_substituted_for_official_album_cover(self):
        earlier = self.candidate("Earlier")
        publish_single(earlier, self.target, gateway=self.gateway)
        release = self.release("Album requiring its own cover", "lp")
        ReleaseTrack.objects.create(release=release, track=earlier.track, position=1)
        self.candidate("New Track", release=release, position=2, with_cover=False)
        session = prepare_album(release, self.target)
        self.assertIsNone(session.intro_id)
        self.assertIn("Official validated cover", session.last_error)

    def test_album_uncertain_intro_reconciles_then_resumes_without_resend(self):
        release, candidates = self.album(2)
        self.gateway.failures["send_intro"] = [UncertainGatewayError()]
        session = advance_album(prepare_album(release, self.target), gateway=self.gateway, now=self.now)
        self.assertEqual((session.state, session.cursor), ("uncertain", 0))
        run_due(gateway=self.gateway, now=self.now+timedelta(minutes=2))
        self.assertEqual(sum(call["operation"] == "send_intro" for call in self.gateway.calls), 1)
        actor = get_user_model().objects.create_user("album-operator", is_staff=True)
        attempt = session.intro.attempts.get(operation="send_intro")
        reconcile(attempt, actor=actor, decision="confirmed_success", evidence="Observed intro 777 in the isolated target", message_id=777, remote_chat_id=self.target)
        run_due(gateway=self.gateway, now=self.now+timedelta(minutes=3))
        session.refresh_from_db()
        self.assertEqual((session.state, session.cursor), ("complete", 2))
        self.assertEqual(sum(call["operation"] == "send_intro" for call in self.gateway.calls), 1)

    def test_known_send_failure_rechecks_media_before_retry(self):
        candidate = self.candidate()
        self.gateway.failures["send_audio"] = [GatewayError("Fixture rejection")]
        pub = publish_single(candidate, self.target, gateway=self.gateway, now=self.now)
        self.assertEqual(pub.state, "retry_wait")
        MediaCandidate.objects.filter(pk=candidate.pk).update(state="invalid")
        run_due(gateway=self.gateway, now=self.now+timedelta(minutes=3))
        pub.refresh_from_db()
        self.assertEqual(pub.state, "review_required")
        self.assertEqual(sum(call["operation"] == "send_audio" for call in self.gateway.calls), 1)

    def test_pending_general_send_resumes_and_bad_local_media_does_not_stall_it(self):
        bad = self.candidate("Bad local media")
        bad_pub = reserve_audio(bad, self.target)
        Path(bad.prepared_path).unlink()
        good = self.candidate("Good local media")
        reserve_audio(good, self.target)
        run_due(gateway=self.gateway)
        bad_pub.refresh_from_db()
        self.assertEqual(bad_pub.state, "review_required")
        self.assertEqual(Publication.objects.get(track=good.track).state, "published")

    def test_operator_non_delivery_proof_allows_retry(self):
        candidate = self.candidate()
        self.gateway.failures["send_audio"] = [UncertainGatewayError()]
        pub = publish_single(candidate, self.target, gateway=self.gateway)
        actor = get_user_model().objects.create_user("operator", is_staff=True)
        attempt = pub.attempts.get(operation="send_audio")
        with self.assertRaises(PublicationError):
            reconcile(attempt, actor=actor, decision="confirmed_not_delivered", evidence="")
        reconcile(attempt, actor=actor, decision="confirmed_not_delivered", evidence="Operator checked isolated test history and confirmed non-delivery", now=self.now)
        run_due(gateway=self.gateway, now=self.now+timedelta(seconds=1))
        pub.refresh_from_db()
        self.assertEqual(pub.state, "published")
        self.assertEqual(sum(call["operation"] == "send_audio" for call in self.gateway.calls), 2)

    @override_settings(TELEGRAM_LIVE_ENABLED=True, TELEGRAM_MODE="test", TELEGRAM_BOT_TOKEN="fixture-only-not-a-real-token")
    def test_real_gateway_audio_transport_payload_and_thumbnail_without_network(self):
        candidate = self.candidate()
        gateway = TelegramGateway()
        with patch.object(gateway, "_request", side_effect=[{"id": int(self.target), "type": "channel", "username": "isolated_test"}, {"message_id": 701, "chat": {"id": int(self.target)}}]) as request:
            result = gateway.execute("send_audio", self.target, {"audio_path": candidate.prepared_path, "artwork_path": candidate.artwork_path, "title": "راه & Road", "performer": "هیچ‌کس", "caption_html": "<b>DROP</b>"})
            self.assertEqual(result.message_id, 701)
            args = request.call_args.args
            self.assertEqual(args[0], "sendAudio")
            self.assertEqual(args[1]["parse_mode"], "HTML")
            self.assertNotIn("reply_parameters", args[1])
            thumbnail = args[2]["thumbnail"][1]
            self.assertLess(len(thumbnail), 200*1024)
            from io import BytesIO
            with Image.open(BytesIO(thumbnail)) as image:
                self.assertLessEqual(max(image.size), 320)

    def test_album_order_failure_release_and_cursor_resume(self):
        release, candidates = self.album()
        session = prepare_album(release, self.target)
        self.gateway.fail_audio_titles["Three"] = 1
        failed = advance_album(session, gateway=self.gateway, now=self.now)
        self.assertEqual(failed.cursor, 2)
        self.assertEqual(failed.state, "retry_wait")
        unrelated = self.candidate("General Queue")
        held = publish_single(unrelated, self.target, gateway=self.gateway, now=self.now+timedelta(minutes=1))
        self.assertEqual(held.state, "pending")
        released = publish_single(unrelated, self.target, gateway=self.gateway, now=self.now+timedelta(minutes=16))
        self.assertEqual(released.state, "published")
        session.refresh_from_db()
        self.assertEqual(session.state, "paused")
        resumed = advance_album(AlbumSession.objects.get(pk=session.pk), gateway=self.gateway, now=self.now+timedelta(minutes=17))
        self.assertEqual((resumed.state, resumed.cursor), ("complete", 4))
        titles = [call["title"] for call in self.gateway.calls if call["operation"] == "send_audio"]
        self.assertEqual(titles, ["One", "Two", "Three", "General Queue", "Three", "Four"])
        self.assertEqual(sum(call["operation"] == "send_intro" for call in self.gateway.calls), 1)
        self.assertTrue(any(call["operation"] == "notify" for call in self.gateway.calls))

    def test_late_album_track_is_independent_without_snapshot_rewrite(self):
        release, candidates = self.album(2)
        session = advance_album(prepare_album(release, self.target), gateway=self.gateway)
        frozen = list(session.entries)
        late = self.candidate("Late Track", release=release, position=3)
        pub = publish_single(late, self.target, gateway=self.gateway)
        session.refresh_from_db()
        self.assertEqual(session.entries, frozen)
        self.assertEqual(pub.kind, "single_audio")
        self.assertIn("<b>DROP</b>", pub.caption_html)
        self.assertIn(session.intro.message_url, pub.caption_html)

    def test_album_overflow_posts_are_durable_and_sent_once(self):
        release = self.release("Overflow LP", "lp")
        channel = PublicationChannel.objects.create(target=self.target)
        template = CaptionTemplate.objects.create(kind="single_audio", version=1, config=DEFAULT_CONFIG)
        for index in range(20):
            track = Track.objects.create(official_title=f"Earlier {index} " + "Long title "*8)
            ReleaseTrack.objects.create(release=release, track=track, position=index+1)
            Publication.objects.create(channel=channel, identity_key=f"audio:{track.canonical_id}", kind="single_audio", track=track, template=template, context={}, state="published", message_id=1000+index, message_url=f"https://t.me/test_archive/{1000+index}")
        self.candidate("New Album Track", release=release, position=21)
        session = prepare_album(release, self.target)
        self.assertTrue(session.overflow)
        result = advance_album(session, gateway=self.gateway)
        self.assertEqual(result.state, "complete")
        overflow = Publication.objects.filter(album_session=result, kind="overflow")
        self.assertEqual(overflow.count(), len(session.overflow))
        self.assertTrue(all(pub.state == "published" for pub in overflow))
        before = len(self.gateway.calls)
        advance_album(result, gateway=self.gateway)
        self.assertEqual(before, len(self.gateway.calls))

    def test_due_worker_expires_abandoned_attempt_without_resend(self):
        candidate = self.candidate()
        pub = reserve_audio(candidate, self.target)
        attempt = PublicationAttempt.objects.create(publication=pub, operation="send_audio", operation_key="initial", payload={}, started_at=self.now-timedelta(minutes=3))
        Publication.objects.filter(pk=pub.pk).update(state="sending")
        PublicationChannel.objects.filter(pk=pub.channel_id).update(in_flight=attempt, lease_until=self.now-timedelta(seconds=1))
        run_due(gateway=self.gateway, now=self.now)
        pub.refresh_from_db()
        self.assertEqual(pub.state, "uncertain")
        self.assertFalse(self.gateway.calls)

    def test_probe_without_credentials_is_status_only_and_explicitly_gated(self):
        output = StringIO()
        with patch("publication.management.commands.probe_telegram.TelegramGateway") as live:
            call_command("probe_telegram", configuration_status=True, stdout=output)
            self.assertIn('"live_probe": "not_run"', output.getvalue())
            with self.assertRaises(CommandError):
                call_command("probe_telegram", confirm_test_send=True)
            live.assert_not_called()

    def test_distinct_edition_original_link_and_identical_file_reuse(self):
        original_candidate = self.candidate("Original")
        original = publish_single(original_candidate, self.target, gateway=self.gateway)
        edition_release = self.release("Instrumental", edition_of=original_candidate.release)
        edition = self.candidate("Instrumental", release=edition_release)
        edition.track.edition_of = original_candidate.track
        edition.track.edition = "instrumental"
        edition.track.save()
        pub = publish_single(edition, self.target, gateway=self.gateway)
        self.assertEqual(pub.kind, "edition")
        self.assertIn(original.message_url, pub.caption_html)
        identical = self.candidate("Identical Reissue")
        identical.sha256 = original_candidate.sha256
        identical.save()
        reused = publish_single(identical, self.target, gateway=self.gateway)
        self.assertEqual(reused.pk, original.pk)
        self.assertEqual(sum(call["operation"] == "send_audio" for call in self.gateway.calls), 2)

    def test_production_target_block_and_default_worker_no_network(self):
        candidate = self.candidate()
        for target in ("@RapFaDrop", "@rapfadrop", "https://t.me/RapFaDrop", "-1009999999999"):
            with self.assertRaises(TargetBlocked):
                publish_single(candidate, target, gateway=self.gateway)
        with patch("publication.tasks.TelegramGateway") as live:
            self.assertEqual(process_due_publications(), "disabled")
            live.assert_not_called()
        with patch("publication.gateway.build_opener") as opener:
            with self.assertRaises(TargetBlocked):
                TelegramGateway()
            opener.assert_not_called()

    @override_settings(TELEGRAM_LIVE_ENABLED=True, TELEGRAM_MODE="test", TELEGRAM_BOT_TOKEN="fixture-only-not-a-real-token")
    def test_real_gateway_resolves_numeric_alias_before_any_mutation(self):
        gateway = TelegramGateway()
        with patch.object(gateway, "_request", return_value={"id": int(self.target), "username": "RapFaDrop"}) as request:
            with self.assertRaises(TargetBlocked):
                gateway.execute("send_text", self.target, {"caption_html": "fixture"})
            self.assertEqual(request.call_count, 1)
            self.assertEqual(request.call_args.args[0], "getChat")

    @override_settings(TELEGRAM_LIVE_ENABLED=True, TELEGRAM_MODE="test", TELEGRAM_BOT_TOKEN="fixture-only-not-a-real-token")
    def test_direct_gateway_method_cannot_bypass_target_preflight(self):
        gateway = TelegramGateway()
        with patch.object(gateway._opener, "open") as network:
            for target in ("@RapFaDrop", self.target):
                with self.assertRaises(TargetBlocked):
                    gateway.send_text(target, {"caption_html": "fixture"})
            network.assert_not_called()

    @override_settings(TELEGRAM_LIVE_ENABLED=True, TELEGRAM_MODE="test", TELEGRAM_BOT_TOKEN="fixture-only-not-a-real-token")
    def test_server_error_is_uncertain_even_with_structured_response(self):
        from io import BytesIO
        from urllib.error import HTTPError
        gateway = TelegramGateway()
        error = HTTPError("https://example.invalid/fixture", 500, "fixture", {}, BytesIO(b'{"ok":false,"error_code":500}'))
        with patch.object(gateway, "_guard_live", return_value=(self.target, "isolated_test")), patch.object(gateway._opener, "open", side_effect=error):
            with self.assertRaises(UncertainGatewayError):
                gateway.execute("send_text", self.target, {"caption_html": "fixture"})


@skipUnless(connection.vendor == "postgresql", "PostgreSQL row locking required")
class ConcurrentPublicationTests(PublicationFixtures, TransactionTestCase):
    def test_two_workers_create_one_send_with_committed_pending_attempt(self):
        candidate = self.candidate()
        barrier = threading.Barrier(2)
        original_execute = self.gateway.execute
        def delayed(operation, target, payload):
            self.assertTrue(PublicationAttempt.objects.filter(state="pending").exists())
            time.sleep(0.15)
            return original_execute(operation, target, payload)
        self.gateway.execute = delayed
        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return publish_single(MediaCandidate.objects.get(pk=candidate.pk), self.target, gateway=self.gateway).pk
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: worker(), range(2)))
        self.assertEqual(len(set(results)), 1)
        self.assertEqual(Publication.objects.filter(track=candidate.track).count(), 1)
        self.assertEqual(sum(call["operation"] == "send_audio" for call in self.gateway.calls), 1)
