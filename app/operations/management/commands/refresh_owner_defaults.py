from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max
from operations.models import OperatorSettings
from publication.captions import DEFAULT_CONFIG
from publication.models import CaptionTemplate

OLD_ROWS = ['music_video_url', 'platforms', 'album_post_url', 'original_track_post_url']
OLD_TAGS = {'comments', 'encoded_by', 'author_url'}
NEW_TAGS = ['subtitle', 'comments', 'album_artist_suffix', 'album_suffix', 'publisher', 'encoded_by', 'author_url', 'copyright', 'composers', 'conductors', 'initial_key']
AUDIO_KINDS = {'single_audio', 'album_track_audio', 'archive_audio', 'edition'}


def known_audio_default(config):
    old = {k: v for k, v in DEFAULT_CONFIG.items() if k not in {'audio_layout', 'archive_header', 'brand_label', 'brand_url'}}
    for rows in (old['rows'], OLD_ROWS):
        for footer in ('t.me/RapFaDrop', '@RapFaDrop'):
            for heading in ('Previously released from this album:', 'پیش‌تر از این آلبوم منتشر شده:'):
                allowed = {**old, 'rows': rows, 'intro_footer': footer, 'prior_heading': heading, 'archive_header': 'ARCHIVE'}
                if all(k in allowed and allowed[k] == v for k, v in config.items()):
                    return True
    return False


class Command(BaseCommand):
    help = 'Version known legacy defaults; preserve customized templates/settings. No Telegram calls.'

    @transaction.atomic
    def handle(self, *args, **options):
        changed, custom = [], []
        for kind in CaptionTemplate.objects.filter(enabled=True).values_list('kind', flat=True).distinct():
            # Audio-only task: introduction/notification/correction versions are untouched.
            if kind not in AUDIO_KINDS:
                continue
            template = CaptionTemplate.objects.filter(kind=kind, enabled=True).order_by('-version').first()
            if template.config.get('audio_layout') == 'compact':
                continue
            if known_audio_default(template.config):
                version = CaptionTemplate.objects.filter(kind=kind).aggregate(v=Max('version'))['v'] + 1
                CaptionTemplate.objects.create(kind=kind, version=version, config=DEFAULT_CONFIG)
                CaptionTemplate.objects.filter(pk=template.pk).update(enabled=False)
                changed.append(kind)
            else:
                custom.append({'id': template.pk, 'kind': kind, 'reason': 'Customized template retained; compact audio design requires owner review'})
        setting = OperatorSettings.objects.filter(pk=1).first()
        tags_changed = bool(setting and set(setting.tag_fields) == OLD_TAGS)
        if tags_changed:
            setting.tag_fields = NEW_TAGS
            setting.version += 1
            setting.save(update_fields=['tag_fields', 'version', 'updated_at'])
        self.stdout.write(str({'new_caption_versions': changed, 'custom_templates_retained': custom, 'tag_defaults_migrated': tags_changed}))
