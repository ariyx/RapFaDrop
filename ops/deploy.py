#!/usr/bin/env python3
"""Deploy an exact server-tested commit, with an encrypted restore-verified backup."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import urllib.request

import backup


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('sha')
    parser.add_argument('--tested-marker', required=True)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{40}', args.sha) or backup.private(args.tested_marker).read_text().strip() != args.sha:
        raise ValueError('Exact tested SHA marker required')
    c = json.loads(backup.private(backup.CONFIG).read_text())
    checkout = c['checkout']
    if backup.run(['git', '-C', checkout, 'status', '--porcelain']).strip():
        raise ValueError('Deployment checkout must be clean')
    backup.run(['git', '-C', checkout, 'fetch', 'origin', 'main'])
    backup.run(['git', '-C', checkout, 'cat-file', '-e', args.sha + '^{commit}'])
    with (Path(c['backup_dir']) / '.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        artifact = backup.create(c, 'pre-deploy-' + args.sha)
        backup.restore_drill(c, artifact)
        backup.upload(c, artifact)
        services = list(c.get('production_services') or ['beat', 'worker'])
        backup.compose(c, 'stop', '-t', '180', *services)
        backup.run(['git', '-C', checkout, 'checkout', args.sha])
        backup.compose(c, 'config', '--quiet')
        backup.compose(c, 'build', 'web')
        backup.compose(c, 'run', '--rm', '--no-deps', 'web', 'python', 'manage.py', 'migrate', '--noinput')
        backup.compose(c, 'run', '--rm', '--no-deps', 'web', 'python', 'manage.py', 'refresh_owner_defaults')
        backup.compose(c, 'up', '-d', '--no-deps', '--no-build', '--wait', '--wait-timeout', '90', *list(c.get('production_services') or ['web', 'worker', 'beat']))
        for command in [('check',), ('migrate', '--check'), ('makemigrations', '--check', '--dry-run')]:
            backup.compose(c, 'exec', '-T', 'web', 'python', 'manage.py', *command)
        backup.guard(c)
        with urllib.request.urlopen('http://91.107.178.12:8000/health/', timeout=15) as response:
            health = json.load(response)
        if health != {'status': 'ok', 'database': 'ok'}:
            raise ValueError('Health verification failed')
        print(json.dumps({'deployed_sha': args.sha, 'verified_predeploy_backup': str(artifact), 'health': health, 'safety': 'protected runtime roles verified'}))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'error': str(exc) if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__, 'recovery': 'Use retained predeployment backup; inspect stopped services before restarting'}))
        raise SystemExit(1)
