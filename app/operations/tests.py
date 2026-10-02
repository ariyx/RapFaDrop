from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse
from unittest.mock import patch

from sources.models import Artist, ArtistSource
from sources.models import SourceItem
from releases.models import CanonicalRelease, IdentityAuditEvent, ProcessingQueueItem, ReviewItem, SourceMatch, Track
from media_pipeline.models import MediaCandidate
from publication.captions import DEFAULT_CONFIG, render_caption
from publication.models import CaptionTemplate, Publication, PublicationAttempt, PublicationAuditEvent, PublicationChannel
from publication.forms import CaptionTemplateForm

from .models import OperatorActionRequest, OperatorAuditEvent
from .services import OPERATOR_GROUP, configure_operator_group


class OperatorPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.artist = Artist.objects.create(official_name="Artist", aliases=["هنرمند نمونه", "هنرمند"])
        cls.source = ArtistSource.objects.create(artist=cls.artist, platform="soundcloud", canonical_url="https://soundcloud.com/artist")
        cls.group = configure_operator_group()
        User = get_user_model()
        cls.admin_one = User.objects.create_user("operator-one", password="a-long-test-password")
        cls.admin_two = User.objects.create_user("operator-two", password="a-long-test-password")
        cls.admin_one.is_staff = cls.admin_two.is_staff = True
        cls.admin_one.save(); cls.admin_two.save()
        cls.admin_one.groups.add(cls.group); cls.admin_two.groups.add(cls.group)

    def test_login_role_and_persian_alias_search(self):
        self.assertEqual(self.client.get(reverse("operations:dashboard")).status_code, 302)
        self.client.force_login(self.admin_one)
        response = self.client.get(reverse("operations:dashboard"), {"q": "هنرمند نمونه"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "هنرمند نمونه")
        denied = get_user_model().objects.create_user("ordinary", password="a-long-test-password", is_staff=True)
        self.client.force_login(denied)
        self.assertEqual(self.client.get(reverse("operations:dashboard")).status_code, 403)
        self.assertFalse(self.group.permissions.filter(codename__startswith="delete_").exists())

    def test_csrf_and_equal_role_source_actions_audited(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin_one)
        url = reverse("operations:source_action", args=(self.source.pk, "verify"))
        self.assertEqual(client.post(url).status_code, 403)
        page = client.get(reverse("operations:dashboard"))
        token = page.cookies["csrftoken"].value
        self.assertEqual(client.post(url, {"notes": "Official artist profile verified"}, HTTP_X_CSRFTOKEN=token).status_code, 302)
        self.source.refresh_from_db()
        self.assertEqual(self.source.verification, ArtistSource.Verification.VERIFIED)
        Artist.objects.filter(pk=self.artist.pk).update(enabled=True)
        ArtistSource.objects.filter(pk=self.source.pk).update(enabled=True)
        client.force_login(self.admin_two)
        baseline_url = reverse("operations:source_action", args=(self.source.pk, "baseline"))
        token = client.get(reverse("operations:dashboard")).cookies["csrftoken"].value
        self.assertEqual(client.post(baseline_url, HTTP_X_CSRFTOKEN=token).status_code, 302)
        self.assertEqual(OperatorActionRequest.objects.count(), 1)
        self.assertFalse(self.source.baseline_runs.exists())
        self.assertTrue(OperatorAuditEvent.objects.filter(action="source_baseline_requested", actor=self.admin_two).exists())

    def test_enable_unverified_warns_without_changing_source(self):
        self.client.force_login(self.admin_one)
        response = self.client.post(reverse("operations:source_action", args=(self.source.pk, "enable")), follow=True)
        self.assertContains(response, "must be verified")
        self.source.refresh_from_db()
        self.assertFalse(self.source.enabled)

    def test_settings_reject_unlisted_tag_fields_and_audit_valid_values(self):
        self.client.force_login(self.admin_one)
        response = self.client.post(reverse("operations:settings"), {"tag_fields": ["not_a_tag"], "correction_delete_seconds": 600})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(OperatorAuditEvent.objects.filter(action="settings_updated").exists())

    def test_settings_version_controls_m4_and_rejects_production_notification_target(self):
        self.client.force_login(self.admin_one)
        data = {"tag_fields": ["comments"], "correction_delete_seconds": 900, "notification_mode": "disabled", "notification_target": ""}
        self.assertEqual(self.client.post(reverse("operations:settings"), data).status_code, 302)
        from operations.services import active_correction_delete_seconds, active_media_tag_fields
        self.assertEqual(active_correction_delete_seconds(600), 900)
        self.assertEqual(active_media_tag_fields({"publisher"}), frozenset({"comments"}))
        bad = {**data, "notification_mode": "test_only", "notification_target": "@RapFaDrop"}
        response = self.client.post(reverse("operations:settings"), bad)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(OperatorAuditEvent.objects.filter(action="settings_updated").exists())

    def test_reset_another_admin_does_not_audit_password(self):
        self.client.force_login(self.admin_one)
        response = self.client.post(reverse("operations:password_reset", args=(self.admin_two.pk,)), {"new_password": "replacement-secret-12345"})
        self.assertEqual(response.status_code, 302)
        event = OperatorAuditEvent.objects.get(action="admin_password_reset")
        self.assertNotIn("replacement-secret", str(event.before) + str(event.after))
        self.admin_two.refresh_from_db()
        self.assertTrue(self.admin_two.check_password("replacement-secret-12345"))

    def test_review_requeue_uses_m2_service_and_is_audited(self):
        item = SourceItem.objects.create(platform="soundcloud", native_item_id="source-1", source=self.source, title="Title", first_observed_at=__import__("django.utils.timezone", fromlist=["now"]).now())
        release = CanonicalRelease.objects.create(title="Title", release_type="single")
        track = Track.objects.create(official_title="Title", normalized_title="title")
        match = SourceMatch.objects.create(source_item=item, release=release, track=track, matching_method="test", state=SourceMatch.State.REVIEW_REQUIRED)
        review = ReviewItem.objects.create(source_item=item, source_match=match, category=ReviewItem.Category.MANUAL, reason="Needs review", state=ReviewItem.State.APPROVED)
        self.client.force_login(self.admin_one)
        response = self.client.post(reverse("operations:review_action", args=(review.pk, "requeue")), {"resolution": "Second look"})
        self.assertEqual(response.status_code, 302)
        review.refresh_from_db()
        self.assertEqual(review.state, ReviewItem.State.REQUEUED)
        self.assertTrue(IdentityAuditEvent.objects.filter(review_item=review, action="review_requeued", actor=self.admin_one).exists())
        self.assertTrue(OperatorAuditEvent.objects.filter(action="review_requeue", actor=self.admin_one).exists())

    def test_review_approval_creates_queue_through_m2_service(self):
        item = SourceItem.objects.create(platform="soundcloud", native_item_id="source-approve", source=self.source, title="Title", first_observed_at=__import__("django.utils.timezone", fromlist=["now"]).now())
        release = CanonicalRelease.objects.create(title="Title", release_type="single")
        track = Track.objects.create(official_title="Title", normalized_title="title")
        match = SourceMatch.objects.create(source_item=item, release=release, track=track, matching_method="test", state=SourceMatch.State.REVIEW_REQUIRED)
        review = ReviewItem.objects.create(source_item=item, source_match=match, category=ReviewItem.Category.MANUAL, reason="Needs review")
        self.client.force_login(self.admin_one)
        response = self.client.post(reverse("operations:review_action", args=(review.pk, "approve")), {"resolution": "Evidence checked"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ProcessingQueueItem.objects.filter(track=track).count(), 1)

    @patch("operations.views.retry_candidate")
    def test_media_retry_route_uses_m3_service_without_exposing_paths(self, retry):
        item = SourceItem.objects.create(platform="soundcloud", native_item_id="source-media", source=self.source, title="Title", first_observed_at=__import__("django.utils.timezone", fromlist=["now"]).now())
        release = CanonicalRelease.objects.create(title="Title", release_type="single")
        track = Track.objects.create(official_title="Title", normalized_title="title")
        match = SourceMatch.objects.create(source_item=item, release=release, track=track, matching_method="test", state=SourceMatch.State.MATCHED, confidence=95)
        candidate = MediaCandidate.objects.create(track=track, release=release, source_match=match, provider="yt-dlp", candidate_path="/private/example")
        retry.return_value = candidate
        self.client.force_login(self.admin_one)
        response = self.client.post(reverse("operations:media_retry", args=(candidate.pk,)))
        self.assertEqual(response.status_code, 302)
        retry.assert_called_once_with(candidate)
        event = OperatorAuditEvent.objects.get(action="media_retry")
        self.assertNotIn("/private/example", str(event.before) + str(event.after))
        candidate.last_error = "failed at /private/example?token=secret"
        candidate.save(update_fields=("last_error",))
        detail = self.client.get(f"/admin/media_pipeline/mediacandidate/{candidate.pk}/change/")
        self.assertEqual(detail.status_code, 200)
        self.assertNotContains(detail, "/private/example")
        self.assertNotContains(detail, "token=secret")

    def test_publication_retry_schedules_only_definite_failure_without_gateway_call(self):
        from django.utils import timezone
        channel = PublicationChannel.objects.create(target="-1001234567890")
        publication = Publication.objects.create(channel=channel, identity_key="retry-fixture", kind=Publication.Kind.SINGLE, state=Publication.State.RETRY_WAIT)
        attempt = PublicationAttempt.objects.create(publication=publication, operation="send_audio", operation_key="initial", state=PublicationAttempt.State.FAILED, error="safe fixture failure", started_at=timezone.now())
        self.client.force_login(self.admin_one)
        response = self.client.post(reverse("operations:publication_retry", args=(publication.pk,)))
        self.assertEqual(response.status_code, 302)
        publication.refresh_from_db()
        self.assertLessEqual(publication.retry_due_at, timezone.now())
        self.assertTrue(PublicationAuditEvent.objects.filter(publication=publication, attempt=attempt, action="operator_retry_scheduled", actor=self.admin_one).exists())
        self.assertTrue(OperatorAuditEvent.objects.filter(action="publication_retry_requested", actor=self.admin_one).exists())

    def test_template_form_rejects_unknown_variables_and_marker_is_safe(self):
        form = CaptionTemplateForm(data={"kind": "album_intro", "version": 99, "enabled": "on", "config": '{"rows":["arbitrary_python"]}'})
        self.assertFalse(form.is_valid())
        rendered = render_caption("album_intro", {"title": "Album", "artists": ["Artist"], "release_type": "LP", "previous_singles": [{"title": "Single", "url": "https://t.me/RapFaDrop/1"}]})
        self.assertIn("›", rendered.html)
        self.assertNotIn("•", rendered.html)

    def test_caption_preview_escapes_markup_and_reports_omitted_conditional_rows(self):
        template = CaptionTemplate.objects.create(kind="single_audio", version=1, config={**DEFAULT_CONFIG, "header": "<unsafe>"}, enabled=False)
        self.client.force_login(self.admin_one)
        response = self.client.post(reverse("operations:template_preview"), {"template": template.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "&amp;lt;unsafe&amp;gt;")
        self.assertContains(response, "music_video_url")
        self.assertNotContains(response, "<unsafe>")
        template.refresh_from_db()
        self.assertIsNotNone(template.previewed_at)
        response = self.client.post(reverse("operations:template_activate", args=(template.pk,)))
        self.assertEqual(response.status_code, 302)
        template.refresh_from_db()
        self.assertTrue(template.enabled)
        self.assertTrue(OperatorAuditEvent.objects.filter(action="caption_template_activated", actor=self.admin_one).exists())

    def test_panel_omits_sensitive_provider_errors_and_paths(self):
        self.source.last_error = "https://provider.invalid/?token=secret"
        self.source.save(update_fields=("last_error",))
        self.client.force_login(self.admin_one)
        response = self.client.get(reverse("operations:dashboard"))
        self.assertNotContains(response, "provider.invalid")
        self.assertNotContains(response, "token=secret")
