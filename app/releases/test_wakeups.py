from unittest.mock import patch
from django.db import transaction
from django.test import TestCase, override_settings
from .wakeups import wake_media, wake_publication


@override_settings(FRESH_PIPELINE_ENABLED=True, SPOTIFY_MEDIA_BRIDGE_ENABLED=True)
class FreshWakeupTests(TestCase):
    def test_handoffs_wait_for_commit_and_use_separate_queues(self):
        with patch('releases.tasks.process_fresh_releases.apply_async') as media, patch('publication.tasks.process_due_publications.apply_async') as publication:
            with self.captureOnCommitCallbacks(execute=True):
                wake_media()
                wake_publication()
                media.assert_not_called()
                publication.assert_not_called()
            media.assert_called_once_with(queue='fresh-media-v1', expires=60)
            publication.assert_called_once_with(queue='fresh-publication-v1', expires=60)

    def test_rollback_does_not_dispatch(self):
        with patch('releases.tasks.process_fresh_releases.apply_async') as media:
            with self.captureOnCommitCallbacks(execute=True):
                try:
                    with transaction.atomic():
                        wake_media()
                        raise ValueError('rolled back')
                except ValueError:
                    pass
            media.assert_not_called()

    def test_broker_failure_does_not_invalidate_committed_discovery(self):
        with patch('releases.tasks.process_fresh_releases.apply_async', side_effect=ConnectionError('offline')):
            with self.assertLogs(level='ERROR'):
                with self.captureOnCommitCallbacks(execute=True):
                    wake_media()

    @override_settings(FRESH_PIPELINE_ENABLED=False)
    def test_disabled_pipeline_enqueues_nothing(self):
        with patch('releases.tasks.process_fresh_releases.apply_async') as media, patch('publication.tasks.process_due_publications.apply_async') as publication:
            with self.captureOnCommitCallbacks(execute=True):
                wake_media()
                wake_publication()
            media.assert_not_called()
            publication.assert_not_called()
