import shutil
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone as datetime_timezone
from pathlib import Path
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connection, connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from PIL import Image

from releases.models import ProcessingQueueItem, SourceMatch
from releases.services import ingest_source_item
from sources.models import Artist, ArtistSource, SourceItem

from .models import MediaAttempt, MediaAuditEvent, MediaCandidate
from .providers import DownloadResult, ProviderError, ProviderProbe, YtDlpProvider
from .services import acquire_candidate, best_ready_candidate, request_candidate, retry_candidate
from .tagging import prepare_tagged_copy, readback_tags, validate_artwork
from .validation import compare_duration, probe_audio, quality_rank


class FakeProvider:
    name = "fake-soundcloud"

    def __init__(self, audio_path=None, *, failure=None, delay=0):
        self.audio_path = Path(audio_path) if audio_path else None
        self.failure = failure
        self.delay = delay
        self.probe_calls = 0
        self.download_calls = 0

    def can_handle(self, url):
        return url.startswith("https://soundcloud.com/")

    def probe(self, source_url, timeout=None):
        self.probe_calls += 1
        if self.failure:
            raise self.failure
        return ProviderProbe(self.name, source_url, "native-track", "Fake Source Title", 30.0, "Verified Artist", evidence={"test_fixture": True})

    def download(self, probe, destination, timeout=None):
        self.download_calls += 1
        if self.failure:
            raise self.failure
        if self.delay:
            time.sleep(self.delay)
        target = Path(destination) / "download.mp3"
        shutil.copyfile(self.audio_path, target)
        return DownloadResult(target, "native-track", "Fake Source Title", 30.0, "Verified Artist", {"test_fixture": True})


class MediaPipelineTests(TestCase):
    @override_settings(FRESH_SPOTSAVER_ENABLED=True)
    def test_intermediary_rechecks_selected_video_and_retains_unknown_quality(self):
        from unittest.mock import Mock,patch
        from .services import retry_candidate
        self.match.matching_method='fresh_official_track'
        self.match.evidence={'official_metadata':{'title':'Song','artists':['Artist'],'album':'Album','album_artists':['Artist']}}
        self.match.save()
        candidate=self._candidate('spotsaver');candidate.expected_duration_seconds=30
        candidate.provenance={'fresh_manifest_id':1,'native_item_id':'abcdefghijk','acquisition_platform':'spotsaver',
            'source_url':'https://open.spotify.com/track/'+'a'*22,'matched_metadata':{'title':'Song'},'source_quality_unknown':True}
        candidate.save()
        provider=Mock();provider.name='spotsaver';provider.can_handle.return_value=True
        provider.probe.return_value=ProviderProbe('spotsaver',candidate.provenance['source_url'],'changedvideo','Song',30,'Artist')
        invalid=retry_candidate(candidate,provider=provider)
        self.assertEqual(invalid.state,'invalid');provider.download.assert_not_called()
        self.assertIn('video changed',invalid.last_error)

    def test_fresh_full_file_rejects_six_seconds_missing_despite_generic_ratio(self):
        from unittest.mock import patch
        from .services import _accept_audio_file
        candidate=self._candidate('fresh-duration')
        candidate.provenance={'fresh_manifest_id':1}
        candidate.save()
        attempt=MediaAttempt.objects.create(candidate=candidate,provider=candidate.provider,started_at=timezone.now())
        facts={**probe_audio(self.low_audio),'duration_seconds':144}
        with patch('media_pipeline.services.probe_audio',return_value=facts):
            candidate=_accept_audio_file(candidate,attempt,self.low_audio,expected=150)
        self.assertEqual(candidate.state,'invalid')
        self.assertEqual(candidate.duration_comparison['status'],'fresh_recording_duration_conflict')
        self.assertFalse(candidate.prepared_path)

    def test_independent_credits_rechecked_before_download(self):
        from unittest.mock import Mock
        from .services import retry_candidate
        candidate=self._candidate('yt-dlp')
        candidate.expected_duration_seconds=30
        candidate.provenance={'fresh_manifest_id':1,'origin_status':'independent_uploader',
            'source_url':'https://soundcloud.com/u/song','acquisition_platform':'soundcloud',
            'native_item_id':'55','recording_uploader_id':'123','source_recording_title':'Song',
            'matched_credits':[{'id':'a','name':'Missing guest'}]}
        candidate.save()
        provider=Mock();provider.name='yt-dlp';provider.can_handle.return_value=True
        provider.probe.return_value=ProviderProbe('yt-dlp',candidate.provenance['source_url'],'55','Song',30,'Other',evidence={'uploader_id':'123'})
        result=retry_candidate(candidate,provider=provider)
        self.assertEqual(result.state,'invalid')
        self.assertIn('credits changed',result.last_error)
        provider.download.assert_not_called()

    @classmethod
    def setUpTestData(cls):
        cls.artist = Artist.objects.create(official_name="هیچ‌کس", aliases=["Hichkas"], enabled=True)
        cls.source = ArtistSource.objects.create(
            artist=cls.artist, platform="soundcloud", native_profile_id="hichkasofficial",
            canonical_url="https://soundcloud.com/hichkasofficial", enabled=True, verification="verified",
        )

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rapfadrop-media-tests-")
        self.addCleanup(self.temp.cleanup)
        self.media_root = Path(self.temp.name) / "managed-media"
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root, MEDIA_MAX_UPLOAD_BYTES=20 * 1024 * 1024, MEDIA_DOWNLOAD_TIMEOUT_SECONDS=30)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.low_audio = Path(self.temp.name) / "low.mp3"
        self.high_audio = Path(self.temp.name) / "high.mp3"
        self.preview_audio = Path(self.temp.name) / "preview.mp3"
        self.cover = Path(self.temp.name) / "cover.jpg"
        self._make_audio(self.low_audio, 30, 64)
        self._make_audio(self.high_audio, 30, 192)
        self._make_audio(self.preview_audio, 10, 64)
        Image.new("RGB", (500, 500), color=(30, 90, 150)).save(self.cover, format="JPEG")
        self.item = SourceItem.objects.create(
            platform="soundcloud", native_item_id=f"media-{self._testMethodName}", source=self.source,
            title="هیچ‌کس راه", canonical_url=f"https://soundcloud.com/hichkasofficial/media-{self._testMethodName}",
            source_release_at=datetime(2025, 5, 1, tzinfo=datetime_timezone.utc), first_observed_at=timezone.now(),
            metadata={"duration": 30.0}, sanitized_raw_data={"id": "media-fixture"},
        )
        self.assertEqual(ingest_source_item(self.item), "queued")
        self.match = self.item.identity_match
        self.queue = ProcessingQueueItem.objects.get(track=self.match.track)

    @staticmethod
    def _make_audio(path, seconds, bitrate):
        subprocess.run([
            "ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=1000:duration={seconds}",
            "-c:a", "libmp3lame", "-b:a", f"{bitrate}k", "-y", str(path),
        ], check=True, timeout=30)

    def _candidate(self, provider="fake-soundcloud"):
        return MediaCandidate.objects.create(track=self.match.track, release=self.match.release, source_match=self.match, provider=provider)

    def test_provider_failure_is_audited_retryable_and_never_publishes(self):
        provider = FakeProvider(failure=ProviderError("failed URL https://media.invalid/file?token=secret"))
        candidate = acquire_candidate(self.queue, provider_name=provider.name, provider=provider)
        self.assertEqual(candidate.state, MediaCandidate.State.RETRY_WAIT)
        self.assertEqual(candidate.attempt_count, 1)
        self.assertTrue(candidate.retry_due_at > timezone.now())
        self.assertNotIn("secret", candidate.last_error)
        self.assertEqual(candidate.attempts.get().state, MediaAttempt.State.RETRY_WAIT)
        self.assertTrue(candidate.audit_events.filter(action="candidate_retry_scheduled").exists())
        self.assertFalse(hasattr(candidate, "publication"))

    def test_candidate_selects_supported_match_after_older_spotify_match(self):
        self.item.platform = "spotify"
        self.item.canonical_url = "https://open.spotify.com/track/unsupported"
        self.item.save()
        sc = SourceItem.objects.create(source=self.source, platform="soundcloud", native_item_id="supported-sc",
            title=self.item.title, canonical_url="https://soundcloud.com/hichkasofficial/supported",
            first_observed_at=timezone.now(), metadata={"duration": 30})
        match = SourceMatch.objects.create(source_item=sc, release=self.match.release, track=self.match.track,
                                          confidence=100, state="approved", matching_method="operator")
        candidate = request_candidate(self.queue, provider_name="yt-dlp")
        self.assertEqual(candidate.source_match, match)
        self.assertEqual(candidate.state, MediaCandidate.State.CANDIDATE)

    def test_provider_identity_change_requires_review_before_any_download(self):
        from unittest.mock import Mock
        for field in ("provider_item_id", "title", "uploader"):
            with self.subTest(field=field):
                MediaCandidate.objects.all().delete()
                provider = Mock(name="identity-provider")
                provider.name = "yt-dlp"
                provider.can_handle.return_value = True
                fields = dict(provider="yt-dlp", source_url=self.item.canonical_url,
                              provider_item_id=self.item.native_item_id, title=self.item.title,
                              duration_seconds=30, uploader=self.artist.official_name)
                fields[field] = "unrelated"
                provider.probe.return_value = ProviderProbe(**fields)
                candidate = acquire_candidate(self.queue, provider_name="yt-dlp", provider=provider)
                self.assertEqual(candidate.state, MediaCandidate.State.REVIEW_REQUIRED)
                self.assertEqual(candidate.last_outcome, "provider_identity_mismatch")
                self.assertEqual(candidate.attempts.get().state, MediaAttempt.State.REVIEW_REQUIRED)
                provider.download.assert_not_called()
                self.assertEqual(candidate.prepared_path, "")

    def test_retry_recovers_candidate_without_losing_source_provenance(self):
        failed = FakeProvider(failure=ProviderError("transient"))
        original_source_id = self.item.pk
        candidate = acquire_candidate(self.queue, provider_name=failed.name, provider=failed, now=timezone.now() - timedelta(minutes=5))
        self.assertEqual(candidate.state, MediaCandidate.State.RETRY_WAIT)
        ready = retry_candidate(candidate, provider=FakeProvider(self.low_audio))
        self.assertEqual(ready.state, MediaCandidate.State.READY)
        self.assertEqual(ready.attempt_count, 2)
        self.assertEqual(ready.provenance["source_item_id"], original_source_id)
        self.assertEqual(ready.attempts.count(), 2)

    def test_spotify_source_is_review_only_without_full_audio_download(self):
        spotify_source = ArtistSource.objects.create(
            artist=self.artist, platform="spotify", native_profile_id="artistfixture",
            canonical_url="https://open.spotify.com/artist/artistfixture", enabled=True, verification="verified",
        )
        item = SourceItem.objects.create(
            platform="spotify", native_item_id="spotify-fixture", source=spotify_source,
            title="Spotify fixture", canonical_url="https://open.spotify.com/track/spotifyfixture",
            first_observed_at=timezone.now(), metadata={"duration": 30},
        )
        self.assertEqual(ingest_source_item(item), "queued")
        queue = ProcessingQueueItem.objects.get(track=item.identity_match.track)
        candidate = acquire_candidate(queue, provider_name="yt-dlp", provider=YtDlpProvider())
        self.assertEqual(candidate.state, MediaCandidate.State.REVIEW_REQUIRED)
        self.assertEqual(candidate.attempt_count, 0)
        self.assertEqual(candidate.last_outcome, "unsupported_source")
        self.assertEqual(candidate.provider, "yt-dlp")

    def test_valid_media_captures_ffprobe_facts_and_reaches_ready_with_persian_tags_and_artwork(self):
        provider = FakeProvider(self.low_audio)
        candidate = acquire_candidate(self.queue, provider_name=provider.name, provider=provider)
        candidate.refresh_from_db()
        self.assertEqual(candidate.state, MediaCandidate.State.READY)
        self.assertTrue(candidate.observed_facts["audio_stream_count"])
        self.assertGreater(candidate.observed_facts["measured_bitrate_bps"], 0)
        self.assertEqual(candidate.duration_comparison["status"], "match")
        prepared = Path(candidate.prepared_path)
        self.assertTrue(prepared.is_file())
        self.assertEqual(candidate.sha256, candidate.observed_facts["sha256"])
        self.assertEqual(candidate.preparation_report["readback"]["title_matches"], True)
        self.assertEqual(candidate.preparation_report["unsupported_fields"], [])
        self.assertTrue(readback_tags(prepared, "هیچ‌کس راه", ["هیچ‌کس"], "هیچ‌کس راه", "@RapFaDrop", False)["main_artists_match"])

    def test_missing_audio_and_corrupt_media_are_rejected(self):
        corrupt = Path(self.temp.name) / "corrupt.mp3"
        corrupt.write_bytes(b"not an audio file")
        from .validation import MediaValidationError
        with self.assertRaises(MediaValidationError):
            probe_audio(corrupt)

        silent = Path(self.temp.name) / "silent.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=16x16:d=2", "-an", "-y", str(silent)], check=True, timeout=30)
        with self.assertRaises(MediaValidationError):
            probe_audio(silent)

    def test_preview_is_invalid_and_partial_staging_is_cleaned(self):
        class PreviewProvider(FakeProvider):
            def download(inner_self, probe, destination, timeout=None):
                target = Path(destination) / "preview.mp3"
                shutil.copyfile(self.preview_audio, target)
                return DownloadResult(target, "native-track", "Fake Source Title", 10.0, "Verified Artist", {})

        candidate = acquire_candidate(self.queue, provider_name="fake-preview", provider=PreviewProvider(self.preview_audio))
        self.assertEqual(candidate.state, MediaCandidate.State.INVALID)
        self.assertEqual(candidate.duration_comparison["status"], "truncated_or_preview")
        self.assertFalse(candidate.candidate_path)
        self.assertFalse(list((self.media_root / ".staging").glob("**/*")))

    def test_missing_or_material_duration_evidence_routes_to_review(self):
        missing, status = compare_duration(30, None)
        self.assertEqual(status, "review_required")
        self.assertEqual(missing["status"], "missing_expected")
        conflict, status = compare_duration(60, 30)
        self.assertEqual(status, "review_required")
        self.assertEqual(conflict["status"], "material_mismatch")

        self.item.metadata = {}
        self.item.save(update_fields=("metadata",))
        class MissingDurationProvider(FakeProvider):
            def probe(inner_self, source_url, timeout=None):
                return ProviderProbe(inner_self.name, source_url, "native", "Title", None, "Verified Artist", evidence={})

        self.item.metadata = {}
        self.item.save(update_fields=("metadata",))
        candidate = acquire_candidate(self.queue, provider_name="fake-missing", provider=MissingDurationProvider(self.low_audio))
        self.assertEqual(candidate.state, MediaCandidate.State.REVIEW_REQUIRED)
        self.assertEqual(candidate.duration_comparison["status"], "missing_expected")

    def test_quality_ranking_uses_observed_bitrate_not_provider_claims(self):
        low = probe_audio(self.low_audio)
        high = probe_audio(self.high_audio)
        self.assertGreater(high["measured_bitrate_bps"], low["measured_bitrate_bps"])
        low_rank = quality_rank({**low, "advertised_bitrate_bps": 9999999}, {"provenance_confidence": 98})
        high_rank = quality_rank({**high, "advertised_bitrate_bps": 320000}, {"provenance_confidence": 90})
        low_candidate = self._candidate("fixture-low")
        low_candidate.state = MediaCandidate.State.READY
        low_candidate.quality_rank = low_rank
        low_candidate.observed_facts = low
        low_candidate.save()
        high_candidate = self._candidate("fixture-high")
        high_candidate.state = MediaCandidate.State.READY
        high_candidate.quality_rank = high_rank
        high_candidate.observed_facts = high
        high_candidate.save()
        self.assertEqual(best_ready_candidate(self.match.track).pk, high_candidate.pk)

    def test_format_aware_mp3_and_mp4_tag_and_artwork_readback(self):
        mp3_prepared = Path(self.temp.name) / "prepared.mp3"
        report = prepare_tagged_copy(self.low_audio, mp3_prepared, {
            "title": "هیچ‌کس راه", "artists": ["هیچ‌کس"], "album": "راه", "release_date": "2025-05-01", "track_number": 2, "disc_number": 1,
        }, artwork_path=self.cover)
        self.assertEqual(report["artwork"]["state"], "embedded")
        self.assertTrue(report["readback"]["artwork_read_back"])
        self.assertEqual(readback_tags(mp3_prepared, "هیچ‌کس راه", ["هیچ‌کس"], "راه", "@RapFaDrop", True)["title_matches"], True)
        self.assertEqual(validate_artwork(self.cover)["format"], "JPEG")

        m4a = Path(self.temp.name) / "fixture.m4a"
        subprocess.run([
            "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=500:duration=30", "-c:a", "aac", "-b:a", "96k", "-y", str(m4a),
        ], check=True, timeout=30)
        mp4_prepared = Path(self.temp.name) / "prepared.m4a"
        mp4_report = prepare_tagged_copy(m4a, mp4_prepared, {"title": "Road", "artists": ["Artist"], "album": "Road"})
        self.assertEqual(mp4_report["readback"]["title_matches"], True)
        self.assertEqual(mp4_report["unsupported_fields"], [])
        self.assertIn("author_url", mp4_report["mapped_fields"])

    @override_settings(MEDIA_CHANNEL_TAG_FIELDS=frozenset({"comments"}))
    def test_channel_tag_policy_only_writes_configured_fields(self):
        prepared = Path(self.temp.name) / "policy.mp3"
        report = prepare_tagged_copy(self.low_audio, prepared, {
            "title": "Road", "artists": ["Artist"], "album": "Road",
        })
        self.assertEqual(report["mapped_fields"][-1], "comments")
        self.assertEqual(report["unsupported_fields"], [])
        self.assertEqual(report["readback"]["album_suffix_matches"], True)

    def test_ytdlp_provider_is_anonymous_bounded_and_soundcloud_only(self):
        provider = YtDlpProvider()
        self.assertTrue(provider.can_handle("https://soundcloud.com/artist/song"))
        self.assertFalse(provider.can_handle("https://open.spotify.com/track/abc"))
        self.assertFalse(provider.can_handle("https://soundcloud.com/artist/sets/album"))
        error = ProviderError("https://media.example/file?token=secret").args[0]
        self.assertNotIn("secret", error)

    @override_settings(MEDIA_PROVIDER_ORDER=("unregistered", "yt-dlp"))
    def test_configured_provider_order_selects_first_registered_provider(self):
        candidate = request_candidate(self.queue)
        self.assertEqual(candidate.provider, "yt-dlp")
        self.assertEqual(candidate.state, MediaCandidate.State.CANDIDATE)

    def test_authenticated_admin_upload_uses_same_pipeline_and_records_actor(self):
        admin = get_user_model().objects.create_superuser("media-admin", "media@example.test", "test-only")
        candidate = self._candidate("manual")
        anonymous = self.client.get(f"/admin/media_pipeline/mediacandidate/{candidate.pk}/manual-upload/")
        self.assertEqual(anonymous.status_code, 302)
        self.client.force_login(admin)
        detail = self.client.get(f"/admin/media_pipeline/mediacandidate/{candidate.pk}/change/")
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Upload validated audio")
        with self.low_audio.open("rb") as stream:
            audio = SimpleUploadedFile("upload.mp3", stream.read(), content_type="audio/mpeg")
        art = SimpleUploadedFile("cover.jpg", self.cover.read_bytes(), content_type="image/jpeg")
        response = self.client.post(f"/admin/media_pipeline/mediacandidate/{candidate.pk}/manual-upload/", {
            "audio_file": audio,
            "artwork_file": art,
            "artwork_source_url": "https://soundcloud.com/artist/song/artwork?token=must-not-persist",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        candidate.refresh_from_db()
        self.assertEqual(candidate.state, MediaCandidate.State.READY)
        self.assertEqual(candidate.created_by, None)
        self.assertEqual(candidate.provenance["uploaded_by_id"], admin.pk)
        self.assertNotIn("token=", str(candidate.provenance))
        self.assertTrue(candidate.audit_events.filter(actor=admin, action="manual_upload_received").exists())
        self.assertTrue(candidate.audit_events.filter(actor=admin, action="candidate_ready").exists())

    def test_ready_candidate_is_immutable_and_duplicate_hash_does_not_duplicate_prepared_file(self):
        provider = FakeProvider(self.low_audio)
        first = acquire_candidate(self.queue, provider_name=provider.name, provider=provider)
        self.assertEqual(first.state, MediaCandidate.State.READY)
        second_match = SourceMatch.objects.create(
            source_item=self._another_source_item(), release=self.match.release, track=self.match.track,
            confidence=98, evidence={}, matching_method="fixture", state=SourceMatch.State.MATCHED,
        )
        second = MediaCandidate.objects.create(track=self.match.track, release=self.match.release, source_match=second_match, provider="fake-second")
        attempt = MediaAttempt.objects.create(candidate=second, provider=second.provider, started_at=timezone.now())
        from .services import _accept_audio_file
        result = _accept_audio_file(second, attempt, self.low_audio, expected=30, now=timezone.now())
        first.refresh_from_db()
        self.assertEqual(result.state, MediaCandidate.State.READY)
        self.assertEqual(result.sha256, first.sha256)
        self.assertEqual(result.prepared_path, first.prepared_path)
        self.assertEqual(Path(first.prepared_path).exists(), True)
        self.assertEqual(len(list(self.media_root.glob("track-*/candidate-*/prepared-*"))), 1)
        from .services import process_manual_upload, MediaRequestError
        with self.low_audio.open("rb") as stream:
            with self.assertRaises(MediaRequestError):
                process_manual_upload(first, SimpleUploadedFile("x.mp3", stream.read()), actor=get_user_model().objects.create_user("operator"))

    def test_retagging_same_raw_recording_prepares_new_policy_instead_of_sharing_stale_tags(self):
        from .tagging import CHANNEL_FIELDS
        from .services import _accept_audio_file
        with override_settings(MEDIA_CHANNEL_TAG_FIELDS={'comments', 'encoded_by', 'author_url'}):
            first = acquire_candidate(self.queue, provider_name='fixture-retag', provider=FakeProvider(self.low_audio))
        second = MediaCandidate.objects.create(track=first.track, release=first.release, source_match=first.source_match, provider='manual')
        attempt = MediaAttempt.objects.create(candidate=second, provider='policy-retag', started_at=timezone.now())
        with override_settings(MEDIA_CHANNEL_TAG_FIELDS=CHANNEL_FIELDS):
            second = _accept_audio_file(second, attempt, Path(first.candidate_path), expected=30, share_prepared=False)
        self.assertEqual(first.sha256, second.sha256)
        self.assertNotEqual(first.prepared_path, second.prepared_path)
        self.assertTrue(CHANNEL_FIELDS <= set(second.preparation_report['mapped_fields']))
        self.assertTrue(second.preparation_report['readback']['channel_fields_read_back'])
        self.assertTrue(Path(first.prepared_path).is_file())

    def _another_source_item(self):
        return SourceItem.objects.create(
            platform="soundcloud", native_item_id="another-media-id", source=self.source,
            title=self.item.title, canonical_url="https://soundcloud.com/hichkasofficial/another-song",
            source_release_at=self.item.source_release_at, first_observed_at=timezone.now(), metadata={"duration": 30.0},
        )


@skipUnless(connection.vendor == "postgresql", "Media acquisition concurrency test requires PostgreSQL row locks")
class ConcurrentMediaTests(TransactionTestCase):
    reset_sequences = True

    def test_concurrent_candidate_requests_run_provider_once(self):
        with tempfile.TemporaryDirectory(prefix="rapfadrop-media-concurrency-") as temp:
            root = Path(temp)
            audio_path = root / "valid.mp3"
            MediaPipelineTests._make_audio(audio_path, 30, 64)
            artist = Artist.objects.create(official_name="Concurrent Media Artist", enabled=True)
            source = ArtistSource.objects.create(artist=artist, platform="soundcloud", enabled=True, verification="verified")
            item = SourceItem.objects.create(
                platform="soundcloud", native_item_id="concurrent-media", source=source,
                title="Concurrent Song", canonical_url="https://soundcloud.com/artist/concurrent-song",
                first_observed_at=timezone.now(), metadata={"duration": 30.0},
            )
            self.assertEqual(ingest_source_item(item), "queued")
            queue_id = ProcessingQueueItem.objects.get(track=item.identity_match.track).pk
            provider = FakeProvider(audio_path, delay=0.2)
            results = []
            errors = []

            def run_once():
                connections.close_all()
                try:
                    queue = ProcessingQueueItem.objects.get(pk=queue_id)
                    results.append(acquire_candidate(queue, provider_name=provider.name, provider=provider).state)
                except Exception as exc:
                    errors.append(exc)
                finally:
                    connections.close_all()

            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(run_once) for _ in range(2)]
                for future in futures:
                    future.result()
            self.assertEqual(errors, [])
            self.assertTrue(all(state in {MediaCandidate.State.READY, MediaCandidate.State.DOWNLOADING} for state in results))
            self.assertIn(MediaCandidate.State.READY, results)
            self.assertEqual(provider.probe_calls, 1)
            self.assertEqual(provider.download_calls, 1)
            self.assertEqual(MediaCandidate.objects.count(), 1)
            self.assertEqual(MediaAttempt.objects.count(), 1)
