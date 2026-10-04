import datetime as dt
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import backup


class BackupTests(unittest.TestCase):
    def test_age_authentication_and_file_checksums(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            identity = root / 'identity'
            backup.run(['age-keygen', '-o', str(identity)])
            identity.chmod(0o600)
            source = root / 'source'; source.mkdir()
            (source / 'database.dump').write_bytes(b'bounded test dump')
            backup.write_json(source / 'manifest.json', {'files': {'database.dump': backup.digest(source / 'database.dump')}})
            tarpath = root / 'archive.tar'
            with tarfile.open(tarpath, 'w') as tar:
                for file in source.iterdir(): tar.add(file, arcname=file.name)
            artifact = root / 'test.tar.age'
            recipient = backup.run(['age-keygen', '-y', str(identity)]).decode().strip()
            backup.run(['age', '-r', recipient, '-o', str(artifact), str(tarpath)])
            artifact.chmod(0o600)
            backup.write_json(str(artifact) + '.json', {'sha256': backup.digest(artifact)})
            stage = root / 'stage'; stage.mkdir()
            backup.unpack({'identity_file': str(identity)}, artifact, stage)
            self.assertEqual((stage / 'database.dump').read_bytes(), b'bounded test dump')
            data = bytearray(artifact.read_bytes()); data[-5] ^= 1; artifact.write_bytes(data)
            backup.write_json(str(artifact) + '.json', {'sha256': backup.digest(artifact)})
            other = root / 'tampered'; other.mkdir()
            with self.assertRaises(RuntimeError): backup.unpack({'identity_file': str(identity)}, artifact, other)

    def test_retention_seven_daily_four_weekly_last_usable_and_incomplete(self):
        start = dt.datetime(2026, 10, 4)
        states = [(Path(str(i)), {'utc': (start-dt.timedelta(days=i)).strftime('%Y%m%dT%H%M%SZ'), 'restore_verified': True, 'upload': 'complete'}) for i in range(40)]
        keep = backup.retained(states)
        self.assertTrue(all(Path(str(i)) in keep for i in range(7)))
        weeks = {(start-dt.timedelta(days=int(str(p)))).isocalendar()[:2] for p in keep}
        self.assertEqual(len(weeks), 4)
        self.assertIn(states[0][0], backup.retained(states, 0, 0))
        states.append((Path('pending'), {'utc': '20251001T000000Z', 'restore_verified': False, 'upload': 'uncertain'}))
        self.assertIn(Path('pending'), backup.retained(states))

    def test_upload_failure_preserves_artifact_and_durable_uncertainty(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / 'backup.age'; artifact.write_bytes(b'encrypted fixture'); artifact.chmod(0o600)
            backup.write_json(str(artifact)+'.json', {'sha256': backup.digest(artifact), 'bytes': artifact.stat().st_size, 'upload': 'pending'})
            def api(c, method, fields, file=None):
                if method == 'getChat': return {'id': int(backup.CHAT), 'type': 'channel'}
                raise RuntimeError('Network failure')
            with patch.object(backup, 'guard'), patch.object(backup, 'api', side_effect=api):
                with self.assertRaises(RuntimeError): backup.upload({'backup_dir': directory, 'backup_chat_id': backup.CHAT}, artifact)
                with self.assertRaises(ValueError): backup.upload({'backup_dir': directory}, artifact)
            self.assertTrue(artifact.exists())
            self.assertEqual(json.loads(Path(str(artifact)+'.json').read_text())['upload'], 'uncertain')

    def test_split_reassembles_identically(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); file = root/'encrypted'; file.write_bytes(b'0123456789'*5)
            with patch.object(backup, 'PART_SIZE', 13): parts = backup.split(file, root)
            self.assertEqual(b''.join(p.read_bytes() for p in parts), file.read_bytes())
            self.assertTrue(all(p.stat().st_size <= 13 for p in parts))

    def test_definite_rejection_can_retry_without_blind_duplicate_send(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / 'backup.age'; artifact.write_bytes(b'encrypted'); artifact.chmod(0o600)
            backup.write_json(str(artifact)+'.json', {'sha256': backup.digest(artifact), 'bytes': artifact.stat().st_size, 'upload': 'pending'})
            def rejected(c, method, fields, file=None):
                if method == 'getChat': return {'id': int(backup.CHAT), 'type': 'channel'}
                raise backup.DefiniteUploadError('rejected')
            with patch.object(backup, 'guard'), patch.object(backup, 'api', side_effect=rejected):
                with self.assertRaises(backup.DefiniteUploadError): backup.upload({'backup_dir': directory, 'backup_chat_id': backup.CHAT}, artifact)
            self.assertEqual(json.loads(Path(str(artifact)+'.json').read_text())['upload'], 'failed')
            with patch.object(backup, 'guard'), patch.object(backup, 'api', side_effect=rejected):
                with self.assertRaises(backup.DefiniteUploadError): backup.upload({'backup_dir': directory, 'backup_chat_id': backup.CHAT}, artifact)

    def test_retention_preserves_durable_upload_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=[]
            for index, stamp in enumerate(['20261004T010000Z','20261004T020000Z']):
                artifact=Path(directory)/f'rapfadrop-{index}.tar.age'
                artifact.write_bytes(b'fixture')
                backup.write_json(str(artifact)+'.json', {'utc':stamp,'restore_verified':True,'upload':'complete','messages':[{'message_id':40+index}]})
                paths.append(artifact)
            backup.retention({'backup_dir':directory})
            self.assertFalse(paths[0].exists())
            self.assertTrue(paths[1].exists())
            self.assertEqual(json.loads(Path(str(paths[0])+'.json').read_text())['messages'][0]['message_id'],40)

    def test_production_restore_without_explicit_phrase_cannot_mutate(self):
        with patch.object(backup, 'pg') as pg:
            with self.assertRaises(ValueError): backup.production_restore({}, Path('archive'), '')
            pg.assert_not_called()

    def test_restore_drill_failure_drops_only_its_isolated_database(self):
        with tempfile.TemporaryDirectory() as directory:
            def unpack(c, artifact, stage):
                (stage/'database.dump').write_bytes(b'fixture')
                return {'snapshot': {}}
            def pg(*args, **kwargs):
                self.assertNotEqual(args[-1], 'rapfadrop')
                if args[0] == 'pg_restore': raise RuntimeError('invalid dump')
            with patch.object(backup, 'unpack', side_effect=unpack), patch.object(backup, 'pg', side_effect=pg) as mocked:
                with self.assertRaises(RuntimeError): backup.restore_drill({'backup_dir': directory}, Path('artifact'))
                self.assertEqual(mocked.call_args.args[0], 'dropdb')
                self.assertTrue(mocked.call_args.args[-1].startswith('rfd_restore_'))


if __name__ == '__main__': unittest.main()
