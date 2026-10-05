#!/usr/bin/env python3
"""SSH-only durable control; no queue purge or history reset."""
import argparse
import json
import backup


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('status','pause','resume'))
    args=parser.parse_args()
    c=json.loads(backup.private(backup.CONFIG).read_text())
    if not c.get('production_services'):
        raise ValueError('Production fresh pipeline has not been configured')
    backup.guard(c)
    if args.action=='resume':
        backup.compose(c,'run','--rm','--no-deps','-T','fresh-publication','python','manage.py','shell','-c',
            "from publication.gateway import TelegramGateway; TelegramGateway()._guard_live('-1004311149640')")
    print(backup.compose(c,'run','--rm','--no-deps','-T','fresh-publication','python','manage.py',
        'fresh_pipeline',args.action).decode())


if __name__=='__main__':
    main()
