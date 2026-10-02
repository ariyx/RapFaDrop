import json
import os
import subprocess
import sys

from django.test import SimpleTestCase

from config.scheduling import beat_schedule


class PublicationScheduleTests(SimpleTestCase):
    def test_switch_combinations_exclude_publication_unless_explicitly_live(self):
        for publication, telegram, mode in ((False, True, "test"), (True, False, "test"), (True, True, "disabled")):
            self.assertEqual(list(beat_schedule(publication, telegram, mode)), ["poll-due-artist-sources"])
        self.assertIn("publication-recovery-and-correction-deletion", beat_schedule(True, True, "test"))

    def test_real_lazy_celery_settings_and_stale_beat_state_cannot_emit_disabled_publication(self):
        # A separate process reproduces lazy configuration loading and persistent
        # beat state from a previously publication-enabled run, using no real broker.
        code = '''
import json,shelve,tempfile
from datetime import timedelta
from unittest.mock import patch
from celery.beat import PersistentScheduler,ScheduleEntry
from config.celery import app
assert list(app.conf.beat_schedule)==["poll-due-artist-sources"]
app.conf.broker_url="memory://"
with tempfile.TemporaryDirectory() as directory:
 path=directory+"/schedule"
 with shelve.open(path) as state:
  state["entries"]={"publication-recovery-and-correction-deletion":ScheduleEntry(name="publication-recovery-and-correction-deletion",task="publication.tasks.process_due_publications",schedule=30,app=app)}
  state["tz"]=app.conf.timezone;state["utc_enabled"]=app.conf.enable_utc;state["__version__"]="5.6.3"
 scheduler=PersistentScheduler(app=app,schedule_filename=path)
 assert "publication-recovery-and-correction-deletion" not in scheduler.schedule
 for entry in scheduler.schedule.values():entry.last_run_at=app.now()-timedelta(seconds=120)
 with patch.object(scheduler,"apply_async") as publish:
  scheduler.tick()
  assert publish.call_count==1
  tasks=[c.args[0].task for c in publish.call_args_list]
  assert tasks==["sources.tasks.poll_due_artist_sources"]
 scheduler.close()
 print(json.dumps(tasks))
'''
        env = {**os.environ, "RAPFADROP_PUBLICATION_WORKER_ENABLED": "false", "RAPFADROP_TELEGRAM_LIVE_ENABLED": "true", "RAPFADROP_TELEGRAM_MODE": "test"}
        result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), ["sources.tasks.poll_due_artist_sources"])
