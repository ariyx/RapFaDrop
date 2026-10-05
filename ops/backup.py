#!/usr/bin/env python3
"""Root-only host operator tool. No Django/Celery dispatch or music gateway."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import uuid

CONFIG = Path('/var/lib/rapfadrop-operations/backup.json')
CHAT = '-1004475982526'
PRODUCTION_CHAT = '-1004311149640'
PART_SIZE = 45_000_000


class DefiniteUploadError(RuntimeError):
    pass


def run(args, *, data=None):
    result = subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError('Command failed: ' + str(args[0]))  # Never leak subprocess secrets.
    return result.stdout


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def private(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
        raise ValueError('Protected regular file required')
    return path


def write_json(path, data):
    target = Path(path)
    temporary = target.with_suffix(target.suffix + '.tmp')
    with temporary.open('w') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
    temporary.chmod(0o600)
    temporary.replace(target)


def compose(c, *args):
    command = ['docker', 'compose', '-p', 'rapfadrop']
    for file in c['compose_files']:
        command += ['-f', file]
    return run(command + list(args))


def pg(*args, data=None):
    return run(['docker', 'exec', '-i', 'rapfadrop-postgres-1', *args], data=data)


def sql(db, query):
    return pg('psql', '-U', 'rapfadrop', '-p', '55432', '-d', db, '-X', '-At', '-v', 'ON_ERROR_STOP=1', '-c', query).decode().strip()


def snapshot(db):
    tables = sql(db, "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
    result = {}
    for table in tables:
        if not re.fullmatch(r'[a-z0-9_]+', table):
            raise ValueError('Unexpected table name')
        rows = sql(db, f'SELECT row_to_json(t)::text FROM public."{table}" t ORDER BY row_to_json(t)::text').encode()
        result[table] = {'count': int(sql(db, f'SELECT count(*) FROM public."{table}"')), 'sha256': hashlib.sha256(rows).hexdigest()}
    schema = pg('pg_dump', '-U', 'rapfadrop', '-p', '55432', '-d', db, '--schema-only', '--no-owner', '--no-acl').decode()
    # pg_dump 17 random restrict tokens are not schema differences.
    schema = '\n'.join(line for line in schema.splitlines() if not line.startswith(('\\restrict', '\\unrestrict', '--')))
    return {'tables': result, 'schema_sha256': hashlib.sha256(schema.encode()).hexdigest()}


def guard(c):
    if c.get('backup_chat_id') != CHAT or c.get('backup_chat_id') == c.get('production_chat_id') or c.get('production_chat_id') != PRODUCTION_CHAT:
        raise ValueError('Dedicated backup target required; no fallback')
    roles = c.get('production_services')
    if roles and roles != {'web':'metadata', 'worker':'metadata', 'beat':'scheduler', 'fresh-media':'metadata', 'fresh-publication':'publisher'}:
        raise ValueError('Exact approved production service roles required')
    for name in (roles or ['web', 'worker', 'beat']):
        info = json.loads(run(['docker', 'inspect', f'rapfadrop-{name}-1']))[0]
        env = dict(value.split('=', 1) for value in info['Config']['Env'])
        required = {'RAPFADROP_SPOTIFY_MEDIA_BRIDGE_ENABLED': 'false', 'RAPFADROP_TELEGRAM_MODE': 'disabled', 'RAPFADROP_TELEGRAM_LIVE_ENABLED': 'false', 'RAPFADROP_PUBLICATION_WORKER_ENABLED': 'false'}
        if roles:
            live_role = roles[name] in {'publisher', 'scheduler'}
            required.update({'RAPFADROP_SPOTIFY_MEDIA_BRIDGE_ENABLED':'true',
                'RAPFADROP_FRESH_PIPELINE_ENABLED':'true', 'RAPFADROP_TELEGRAM_MODE':'production' if live_role else 'disabled',
                'RAPFADROP_TELEGRAM_LIVE_ENABLED':'true' if live_role else 'false',
                'RAPFADROP_PUBLICATION_WORKER_ENABLED':'true' if live_role else 'false'})
            if live_role:
                required.update({'RAPFADROP_TELEGRAM_PRODUCTION_CHAT_ID':PRODUCTION_CHAT, 'RAPFADROP_TELEGRAM_EXPECTED_BOT_ID':'8697681226'})
        if any(env.get(key) != value for key, value in required.items()):
            raise ValueError('Protected runtime safety switches differ from approved roles')


def key(c, *, create=False):
    target = Path(c['identity_file'])
    if not target.exists() and create:
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        run(['age-keygen', '-o', str(target)])
        target.chmod(0o600)
    return private(target)


def create(c, reason):
    guard(c)
    identity = key(c, create=True)
    root = Path(c['backup_dir'])
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    if shutil.disk_usage(root).free < 1024 ** 3:
        raise ValueError('At least 1 GiB free required')
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dest = root / f'rapfadrop-{stamp}-{uuid.uuid4().hex[:8]}.tar.age'
    with tempfile.TemporaryDirectory(prefix='.stage-', dir=root) as temporary:
        stage = Path(temporary)
        runtime_services = list(c.get('production_services') or ['beat', 'worker', 'web'])
        compose(c, 'stop', '-t', '180', *runtime_services)
        try:
            manifest = {'utc': stamp, 'reason': reason, 'application_sha': run(['git', '-C', c['checkout'], 'rev-parse', 'HEAD']).decode().strip(), 'snapshot': snapshot('rapfadrop'), 'runtime': {'postgres': sql('rapfadrop', 'SHOW server_version'), 'docker': run(['docker', '--version']).decode().strip(), 'python': run(['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'python', 'rapfadrop-web', '--version']).decode().strip()}, 'migrations': sql('rapfadrop', 'SELECT app,name FROM django_migrations ORDER BY app,name')}
            (stage / 'database.dump').write_bytes(pg('pg_dump', '-U', 'rapfadrop', '-p', '55432', '-d', 'rapfadrop', '--format=custom'))
            manifest['runtime']['age'] = run(['age', '--version']).decode().strip()
            manifest['runtime']['image_id'] = json.loads(run(['docker', 'inspect', 'rapfadrop-web-1']))[0]['Image']
            (stage / 'runtime-packages.txt').write_bytes(run(['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'python', 'rapfadrop-web', '-m', 'pip', 'freeze']))
            (stage / 'ffmpeg-version.txt').write_bytes(run(['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'ffmpeg', 'rapfadrop-web', '-version']))
            config = stage / 'protected'
            config.mkdir(mode=0o700)
            manifest['restore_paths'] = {}
            for index, original in enumerate(c['protected_files']):
                source = Path(original)
                if source.resolve() == identity.resolve():
                    raise ValueError('Recovery identity must never enter archive')
                if source.is_symlink() or not source.is_file():
                    raise ValueError('Missing protected deployment file')
                name = f'{index:02d}-{source.name}'
                shutil.copyfile(source, config / name)
                manifest['restore_paths']['protected/' + name] = str(source)
            shutil.copyfile(Path(__file__).with_name('BACKUP_RESTORE.md'), stage / 'RESTORE.md')
            shutil.copyfile(Path(__file__), stage / 'backup.py')
            manifest['files'] = {str(p.relative_to(stage)): digest(p) for p in stage.rglob('*') if p.is_file()}
            write_json(stage / 'manifest.json', manifest)
        finally:
            compose(c, 'up', '-d', '--no-deps', '--no-build', *runtime_services)
        archive = stage / 'backup.tar'
        with tarfile.open(archive, 'w') as tar:
            for file in stage.rglob('*'):
                if file.is_file() and file != archive:
                    tar.add(file, arcname=str(file.relative_to(stage)), recursive=False)
        recipient = run(['age-keygen', '-y', str(identity)]).decode().strip()
        run(['age', '-r', recipient, '-o', str(dest), str(archive)])
    dest.chmod(0o600)
    state = {'utc': stamp, 'sha256': digest(dest), 'bytes': dest.stat().st_size, 'application_sha': manifest['application_sha'], 'upload': 'pending', 'restore_verified': False}
    write_json(str(dest) + '.json', state)
    return dest


def unpack(c, artifact, stage):
    artifact = private(artifact)
    state = json.loads(Path(str(artifact) + '.json').read_text())
    if digest(artifact) != state['sha256']:
        raise ValueError('Encrypted archive checksum mismatch')
    archive = stage / 'decrypted.tar'
    run(['age', '-d', '-i', str(key(c)), '-o', str(archive), str(artifact)])
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        if any(not m.isfile() or Path(m.name).is_absolute() or '..' in Path(m.name).parts for m in members):
            raise ValueError('Unsafe archive member')
        if len({m.name for m in members}) != len(members):
            raise ValueError('Duplicate archive members')
        tar.extractall(stage, filter='data')
    manifest = json.loads((stage / 'manifest.json').read_text())
    actual = {str(p.relative_to(stage)) for p in stage.rglob('*') if p.is_file()} - {'decrypted.tar', 'manifest.json'}
    if actual != set(manifest['files']) or any(digest(stage / name) != value for name, value in manifest['files'].items()):
        raise ValueError('Archive integrity mismatch')
    return manifest


def restore_drill(c, artifact):
    name = 'rfd_restore_' + uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix='.restore-', dir=c['backup_dir']) as directory:
        stage = Path(directory)
        manifest = unpack(c, artifact, stage)
        pg('createdb', '-U', 'rapfadrop', '-p', '55432', '-T', 'template0', name)
        try:
            pg('pg_restore', '-U', 'rapfadrop', '-p', '55432', '-d', name, '--exit-on-error', '--single-transaction', '--no-owner', '--no-acl', data=(stage / 'database.dump').read_bytes())
            observed = snapshot(name)
            if observed != manifest['snapshot']:
                raise ValueError('Restore schema/content differs')
        finally:
            pg('dropdb', '-U', 'rapfadrop', '-p', '55432', name)
    state_path = Path(str(artifact) + '.json')
    state = json.loads(state_path.read_text())
    state.update(restore_verified=True, restore_utc=dt.datetime.now(dt.timezone.utc).isoformat(), restored_tables=len(observed['tables']))
    write_json(state_path, state)
    return state


def api(c, method, fields, file=None):
    token = private(c['token_file']).read_text().strip()
    if not token:
        raise ValueError('Backup credential missing')
    boundary = uuid.uuid4().hex
    chunks = []
    for name, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    if file:
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="{file.name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + file.read_bytes() + b'\r\n')
    chunks.append(f'--{boundary}--\r\n'.encode())
    request = urllib.request.Request(f'https://api.telegram.org/bot{token}/{method}', data=b''.join(chunks), headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                result = json.load(response)
        except urllib.error.HTTPError as exc:
            try:
                result = json.loads(exc.read(16384))
            except Exception:
                raise RuntimeError('Backup Telegram outcome uncertain; reconcile before retry') from None
        except Exception:
            raise RuntimeError('Backup Telegram request failed; reconcile uncertain send before retry') from None
        if result.get('ok') is True:
            return result['result']
        if result.get('ok') is False and result.get('error_code') == 429:
            delay = int(result.get('parameters', {}).get('retry_after', 1))
            if attempt == 0 and 0 <= delay <= 30:
                time.sleep(delay)
                continue
        if result.get('ok') is False and 400 <= int(result.get('error_code', 0)) < 500:
            raise DefiniteUploadError('Telegram definitively rejected backup request; local artifact retained')
        raise RuntimeError('Backup Telegram outcome uncertain; reconcile before retry')


def split(artifact, directory):
    parts = []
    with artifact.open('rb') as source:
        while data := source.read(PART_SIZE):
            part = directory / f'{artifact.name}.part{len(parts)+1:04d}'
            part.write_bytes(data)
            part.chmod(0o600)
            parts.append(part)
    return parts


def upload(c, artifact, *, reconcile=False):
    guard(c)
    state_path = Path(str(artifact) + '.json')
    state = json.loads(state_path.read_text())
    if state.get('upload') == 'complete':
        return state
    if state.get('upload') == 'uncertain' and not reconcile:
        raise ValueError('Reconcile backup channel first; explicit --reconciled-absent required')
    if digest(artifact) != state['sha256']:
        raise ValueError('Backup checksum mismatch')
    chat = api(c, 'getChat', {'chat_id': c['backup_chat_id']})
    if str(chat.get('id')) != CHAT or chat.get('type') != 'channel':
        raise ValueError('Exact backup channel verification failed')
    with tempfile.TemporaryDirectory(prefix='.upload-', dir=c['backup_dir']) as directory:
        parts = split(artifact, Path(directory))
        index = {'archive': artifact.name, 'sha256': state['sha256'], 'bytes': state['bytes'], 'parts': [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in parts], 'reassemble': 'Concatenate numbered parts in order, verify archive SHA256, then age-decrypt using separate recovery identity.'}
        index_path = Path(directory) / (artifact.name + '.manifest.json')
        write_json(index_path, index)
        files = parts + [index_path]
        state.setdefault('messages', [])
        for file in files:
            if any(m['name'] == file.name for m in state['messages']):
                continue
            state.update(upload='uncertain', pending_file=file.name)
            write_json(state_path, state)  # Durable intent before network request.
            try:
                result = api(c, 'sendDocument', {'chat_id': CHAT, 'caption': 'RapFaDrop BACKUP — encrypted recovery artifact; retain. ' + file.name}, file)
            except DefiniteUploadError:
                state.update(upload='failed', pending_file=None)
                write_json(state_path, state)
                raise
            if str(result.get('chat', {}).get('id')) != CHAT:
                raise ValueError('Backup response target mismatch')
            state['messages'].append({'name': file.name, 'message_id': result['message_id'], 'file_id': result['document']['file_id'], 'sha256': digest(file), 'bytes': file.stat().st_size})
            state.update(upload='partial', pending_file=None)
            write_json(state_path, state)
        state['upload'] = 'complete'
        write_json(state_path, state)
    return state


def readback(c, artifact):
    state_path = Path(str(artifact) + '.json')
    state = json.loads(state_path.read_text())
    token = private(c['token_file']).read_text().strip()
    for message in state['messages']:
        if message['bytes'] > 20_000_000:
            message['readback'] = 'blocked: hosted Bot API download limit 20MB'
            continue
        file = api(c, 'getFile', {'file_id': message['file_id']})
        try:
            with urllib.request.urlopen(f'https://api.telegram.org/file/bot{token}/{file["file_path"]}', timeout=120) as response:
                content = response.read(20_000_001)
        except Exception:
            raise RuntimeError('Backup readback failed') from None
        if hashlib.sha256(content).hexdigest() != message['sha256']:
            raise ValueError('Telegram backup readback mismatch')
        message['readback'] = 'sha256 matched'
    write_json(state_path, state)
    return state


def retained(states, daily=7, weekly=4):
    usable = sorted([(p, s) for p, s in states if s.get('restore_verified')], key=lambda pair: pair[1]['utc'], reverse=True)
    keep, days, weeks = set(), set(), set()
    for p, s in usable:
        date = dt.datetime.strptime(s['utc'], '%Y%m%dT%H%M%SZ').date()
        day, week = str(date), date.isocalendar()[:2]
        if day not in days and len(days) < daily:
            keep.add(p); days.add(day)
        if week not in weeks and len(weeks) < weekly:
            keep.add(p); weeks.add(week)
    if usable:
        keep.add(usable[0][0])  # Never remove last restore-verified artifact.
    keep.update(p for p, s in states if not s.get('restore_verified') or s.get('upload') != 'complete')
    return keep


def retention(c):
    states = [(p, json.loads(Path(str(p) + '.json').read_text())) for p in Path(c['backup_dir']).glob('rapfadrop-*.tar.age')]
    keep = retained(states, c.get('daily_retention', 7), c.get('weekly_retention', 4))
    for path, state in states:
        if path not in keep:
            # Safe receipts (hashes, upload/readback state, message IDs) outlive artifacts.
            path.unlink()
    return {'retained': len(keep), 'removed': len(states)-len(keep), 'telegram_retention': 'manual; no deletion'}


def production_restore(c, artifact, confirmation):
    if confirmation != 'RESTORE-RAPFADROP-PRODUCTION':
        raise ValueError('Explicit production confirmation phrase required')
    guard(c)
    restore_drill(c, artifact)
    # This includes a new tested recovery point before any destructive production work.
    before = create(c, 'pre-production-restore')
    restore_drill(c, before)
    with tempfile.TemporaryDirectory(prefix='.prod-restore-', dir=c['backup_dir']) as directory:
        stage = Path(directory)
        manifest = unpack(c, artifact, stage)
        current = run(['git', '-C', c['checkout'], 'rev-parse', 'HEAD']).decode().strip()
        if current != manifest['application_sha']:
            raise ValueError('Deploy the archived SHA first, with workers stopped; do not run newer code against restored schema')
        compose(c, 'stop', '-t', '180', *list(c.get('production_services') or ['beat', 'worker', 'web']))
        # Deliberately leave dispatch stopped on success or failure; operator verifies before restart.
        pg('dropdb', '-U', 'rapfadrop', '-p', '55432', '--force', 'rapfadrop')
        pg('createdb', '-U', 'rapfadrop', '-p', '55432', '-T', 'template0', 'rapfadrop')
        pg('pg_restore', '-U', 'rapfadrop', '-p', '55432', '-d', 'rapfadrop', '--exit-on-error', '--single-transaction', '--no-owner', '--no-acl', data=(stage / 'database.dump').read_bytes())
        if snapshot('rapfadrop') != manifest['snapshot']:
            raise ValueError('Production restore verification failed; services remain stopped')
    return {'restored': str(artifact), 'pre_restore_backup': str(before), 'services': 'stopped; protected configs must be reviewed separately before explicit restart'}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['create', 'check', 'restore-drill', 'upload', 'readback', 'retention', 'daily', 'restore-production'])
    parser.add_argument('artifact', nargs='?')
    parser.add_argument('--config', default=str(CONFIG))
    parser.add_argument('--reason', default='manual')
    parser.add_argument('--reconciled-absent', action='store_true')
    parser.add_argument('--confirm', default='')
    args = parser.parse_args()
    try:
        c = json.loads(private(args.config).read_text())
        Path(c['backup_dir']).mkdir(parents=True, exist_ok=True, mode=0o700)
        with (Path(c['backup_dir']) / '.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            artifact = Path(args.artifact) if args.artifact else None
            if args.command in {'create', 'daily'}:
                artifact = create(c, args.reason)
                result = {'artifact': str(artifact)}
                if args.command == 'daily':
                    restore_drill(c, artifact)
                    upload(c, artifact)
                    result.update(retention(c))
            elif args.command in {'check', 'restore-drill'}:
                result = restore_drill(c, artifact)
            elif args.command == 'upload':
                result = upload(c, artifact, reconcile=args.reconciled_absent)
            elif args.command == 'readback':
                result = readback(c, artifact)
            elif args.command == 'retention':
                result = retention(c)
            else:
                result = production_restore(c, artifact, args.confirm)
            print(json.dumps(result, indent=2))
    except Exception as exc:
        print(json.dumps({'error': str(exc) if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__, 'local_backups': 'retained'}))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
