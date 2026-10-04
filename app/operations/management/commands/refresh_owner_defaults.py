from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max
from operations.models import OperatorSettings
from publication.captions import DEFAULT_CONFIG
from publication.models import CaptionTemplate

OLD_ROWS = ['music_video_url', 'platforms', 'album_post_url', 'original_track_post_url']
OLD_TAGS = {'comments', 'encoded_by', 'author_url'}
NEW_TAGS = ['subtitle', 'comments', 'album_artist_suffix', 'album_suffix', 'publisher', 'encoded_by', 'author_url', 'copyright', 'composers', 'conductors', 'initial_key']


class Command(BaseCommand):
    help = 'Version known legacy defaults; preserve customized templates/settings. No Telegram calls.'

    @transaction.atomic
    def handle(self, *args, **options):
        changed, custom = [], []
        for kind in CaptionTemplate.objects.filter(enabled=True).values_list('kind', flat=True).distinct():
            template = CaptionTemplate.objects.filter(kind=kind, enabled=True).order_by('-version').first()
            legacy = {**DEFAULT_CONFIG, 'rows': OLD_ROWS, 'intro_footer': '@RapFaDrop', 'prior_heading': 'پیش‌تر از این آلبوم منتشر شده:'}
            effective = {**legacy, **template.config}
            if effective == legacy:
                version = CaptionTemplate.objects.filter(kind=kind).aggregate(v=Max('version'))['v'] + 1
                CaptionTemplate.objects.create(kind=kind, version=version, config=DEFAULT_CONFIG)
                CaptionTemplate.objects.filter(pk=template.pk).update(enabled=False)
                changed.append(kind)
            elif template.config.get('prior_heading') == 'پیش‌تر از این آلبوم منتشر شده:':
                version = CaptionTemplate.objects.filter(kind=kind).aggregate(v=Max('version'))['v'] + 1
                CaptionTemplate.objects.create(kind=kind, version=version, config={**template.config, 'prior_heading': DEFAULT_CONFIG['prior_heading']})
                CaptionTemplate.objects.filter(pk=template.pk).update(enabled=False)
                changed.append(kind)
            elif effective.get('rows', [])[-1:] != ['platforms'] or effective.get('intro_footer') != 't.me/RapFaDrop':
                custom.append({'id': template.pk, 'kind': kind, 'reason': 'Customized template retained; ordering/footer requires owner review'})
        setting = OperatorSettings.objects.filter(pk=1).first()
        tags_changed = bool(setting and set(setting.tag_fields) == OLD_TAGS)
        if tags_changed:
            setting.tag_fields = NEW_TAGS
            setting.version += 1
            setting.save(update_fields=['tag_fields', 'version', 'updated_at'])
        self.stdout.write(str({'new_caption_versions': changed, 'custom_templates_retained': custom, 'tag_defaults_migrated': tags_changed}))
