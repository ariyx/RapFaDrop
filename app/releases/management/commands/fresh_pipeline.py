import json
from collections import Counter
from django.core.management.base import BaseCommand
from releases.models import FreshControl, FreshDispatch, FreshProviderBackoff
from releases.fresh import build_manifest, process_due


class Command(BaseCommand):
    help = 'Durable fresh-release control; never dispatches the popular backlog.'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=('manifest', 'status', 'pause', 'resume', 'process'))

    def handle(self, *args, **options):
        action = options['action']
        if action in {'pause', 'resume'}:
            FreshControl.objects.update_or_create(name='production', defaults={'paused':action == 'pause'})
        if action == 'manifest':
            self.stdout.write(json.dumps(build_manifest()))
        if action == 'process':
            self.stdout.write(json.dumps(process_due()))
        self.stdout.write(json.dumps({'paused':not FreshControl.objects.filter(name='production', paused=False).exists(),
            'counts':dict(Counter(FreshDispatch.objects.values_list('disposition', flat=True))),
            'post_baseline':list(FreshDispatch.objects.exclude(disposition='excluded').values('id', 'source_item__title',
                'source_item__native_item_id', 'disposition', 'processing_state', 'reason', 'release_id', 'attempts', 'due_at')),
            'provider_backoff':list(FreshProviderBackoff.objects.values())}, default=str))
