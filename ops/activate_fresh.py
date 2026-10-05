#!/usr/bin/env python3
"""Explicit owner-authorized activation on the existing protected server."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import urllib.request
import backup

ROOT = Path('/var/lib/rapfadrop-operations')
OVERLAY = ROOT / 'fresh-production.compose.yaml'
ROLES = {'web':'metadata', 'worker':'metadata', 'beat':'scheduler', 'fresh-media':'metadata', 'fresh-publication':'publisher'}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('sha')
    parser.add_argument('--tested-marker', required=True)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{40}', args.sha) or backup.private(args.tested_marker).read_text().strip() != args.sha:
        raise ValueError('Exact tested SHA required')
    c = json.loads(backup.private(backup.CONFIG).read_text())
    if backup.run(['git','-C',c['checkout'],'rev-parse','HEAD']).decode().strip() != args.sha:
        raise ValueError('Deployed SHA differs from tested commit')
    if c.get('production_services'):
        raise ValueError('Already activated; use durable pause/resume commands instead')
    auth = ROOT / 'youtube-auth'
    cookie = backup.private(auth/'worker-cookies.txt')
    runtime = auth/'runtime'
    if not (runtime/'deno').is_file():
        raise ValueError('Verified standard YouTube runtime missing')
    credentials = json.loads(backup.private(ROOT/'popular-collection.json').read_text())
    if credentials['expected_bot_id'] != 8697681226:
        raise ValueError('Protected bot identity mismatch')
    token = backup.private(credentials['token_file'])
    with (Path(c['backup_dir'])/'.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = backup.create(c, 'before-fresh-production-configuration')
        backup.restore_drill(c, before)
        backup.upload(c, before)
        private_root = ROOT/'fresh-auth'
        private_root.mkdir(mode=0o700, exist_ok=True)
        bot_file = private_root/'bot-token'
        shutil.copyfile(token, bot_file)
        bot_file.chmod(0o600)
        os.chown(bot_file,1000,1000)
        # The old generic Redis envelopes are preserved. Fresh worker queues
        # must be empty before their first authorized consumers are started.
        for queue in ('fresh-media-v1','fresh-publication-v1'):
            length = backup.run(['docker','exec','rapfadrop-redis-1','redis-cli','-p','56379','LLEN',queue]).decode().strip()
            if length != '0':
                raise ValueError('Unexpected dormant fresh-worker envelopes; activation stopped')
        common = {'RAPFADROP_SPOTIFY_DISCOVERY_MODE':'spotifyscraper','RAPFADROP_FRESH_PIPELINE_ENABLED':'true',
            'RAPFADROP_SPOTIFY_MEDIA_BRIDGE_ENABLED':'true', 'RAPFADROP_TELEGRAM_MODE':'disabled',
            'RAPFADROP_TELEGRAM_LIVE_ENABLED':'false', 'RAPFADROP_PUBLICATION_WORKER_ENABLED':'false',
            'RAPFADROP_TELEGRAM_PRODUCTION_CHAT_ID':backup.PRODUCTION_CHAT, 'RAPFADROP_TELEGRAM_EXPECTED_BOT_ID':'8697681226'}
        live = {**common,'RAPFADROP_TELEGRAM_MODE':'production','RAPFADROP_TELEGRAM_LIVE_ENABLED':'true',
            'RAPFADROP_PUBLICATION_WORKER_ENABLED':'true','RAPFADROP_TELEGRAM_PRODUCTION_CHAT_ID':backup.PRODUCTION_CHAT,
            'RAPFADROP_TELEGRAM_EXPECTED_BOT_ID':'8697681226'}
        def worker(queue, environment, memory):
            return {'image':'rapfadrop-web:latest','restart':'unless-stopped','network_mode':'host',
                'env_file':c['checkout']+'/.env','environment':environment,'mem_limit':memory,'cpus':0.6,
                'pids_limit':160,'volumes':['media_data:/var/lib/rapfadrop/media'],
                'command':['celery','-A','config.celery:app','worker','-Q',queue,'--concurrency=1','--pool=solo',
                    '--loglevel=INFO','--without-gossip','--without-mingle','--hostname='+queue+'@%h']}
        media = worker('fresh-media-v1',{**common,'RAPFADROP_MEDIA_YOUTUBE_COOKIES_FILE':'/run/youtube/cookies.txt',
            'RAPFADROP_MEDIA_YOUTUBE_JS_RUNTIME':'deno:/runtime/deno','DENO_DIR':'/tmp/deno'},'384m')
        media['volumes'] += [str(cookie)+':/run/youtube/cookies.txt:ro',str(runtime)+':/runtime:ro']
        publisher = worker('fresh-publication-v1',{**live,'RAPFADROP_TELEGRAM_BOT_TOKEN_FILE':'/run/production-bot-token'},'256m')
        publisher['volumes'] += [str(bot_file)+':/run/production-bot-token:ro']
        overlay = {'services':{
            'web':{'environment':common},
            'worker':{'environment':common,'command':worker('spotify-pilot',common,'256m')['command'],'mem_limit':'256m','cpus':0.5},
            'beat':{'environment':live,'command':['celery','-A','config.celery:app','beat','--loglevel=INFO',
                '--schedule=/tmp/fresh-production-beat','--max-interval=5'],'mem_limit':'192m','cpus':0.3},
            'fresh-media':media,'fresh-publication':publisher}}
        OVERLAY.write_text(json.dumps(overlay, indent=2))
        OVERLAY.chmod(0o600)
        current = {**c, 'compose_files':[*c['compose_files'],str(OVERLAY)]}
        backup.compose(current,'config','--quiet')
        # Read-only Bot API preflight and manifest. Durable control defaults paused.
        verification = backup.compose(current,'run','--rm','--no-deps','-T','fresh-publication','python','manage.py','shell','-c',
            "from publication.gateway import TelegramGateway; print(TelegramGateway()._guard_live('-1004311149640'))").decode()
        if "('-1004311149640', 'RapFaDrop')" not in verification and "('-1004311149640', 'rapfadrop')" not in verification:
            raise ValueError('Exact production read-only preflight failed')
        manifest = backup.compose(current,'run','--rm','--no-deps','-T','fresh-publication','python','manage.py','fresh_pipeline','manifest').decode()
        backup.compose(c,'stop','-t','180','beat','worker')
        backup.compose(current,'up','-d','--no-deps','--no-build','--wait','--wait-timeout','90',*ROLES)
        current['production_services'] = ROLES
        current['protected_files'] = list(dict.fromkeys([*c['protected_files'],str(OVERLAY),str(bot_file),str(cookie)]))
        backup.write_json(ROOT/'backup-before-fresh.json',c)
        backup.write_json(backup.CONFIG,current)
        backup.guard(current)
        armed = backup.create(current,'fresh-production-armed-durably-paused')
        backup.restore_drill(current,armed)
        backup.upload(current,armed)
        backup.compose(current,'exec','-T','fresh-publication','python','manage.py','fresh_pipeline','resume')
        with urllib.request.urlopen('http://91.107.178.12:8000/health/',timeout=15) as response:
            health=json.load(response)
        if health != {'status':'ok','database':'ok'}:
            backup.compose(current,'exec','-T','fresh-publication','python','manage.py','fresh_pipeline','pause')
            raise ValueError('Activation health failed; publication durably paused')
        print(json.dumps({'deployed_sha':args.sha,'before_configuration_backup':str(before),'armed_backup':str(armed),
            'channel':backup.PRODUCTION_CHAT,'bot_id':8697681226,'health':health,'roles':ROLES,
            'manifest_status':manifest,'activation':'resumed; scoped fresh workers only'}))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'error':str(exc) if isinstance(exc,ValueError) else type(exc).__name__,
                          'recovery':'Retained backups; inspect durable pause state and protected configuration before retry'}))
        raise SystemExit(1)
