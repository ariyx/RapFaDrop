from dataclasses import dataclass

from django import forms
from django.conf import settings

from publication.captions import render_caption
from publication.models import CaptionTemplate
from publication.gateway import TargetBlocked, guard_target

from .models import OperatorSettings


class OperatorSettingsForm(forms.ModelForm):
    tag_fields = forms.MultipleChoiceField(choices=(), required=False)
    correction_delete_seconds = forms.IntegerField(min_value=60, max_value=86400, initial=600)

    class Meta:
        model = OperatorSettings
        fields = ("tag_fields", "correction_delete_seconds", "notification_mode", "notification_target")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = sorted(set(settings.MEDIA_CHANNEL_TAG_FIELDS))
        self.fields["tag_fields"].choices = [(name, name) for name in allowed]
        self.fields["tag_fields"].initial = (self.instance.tag_fields if self.instance and self.instance.pk else allowed)

    def clean_tag_fields(self):
        values = self.cleaned_data["tag_fields"]
        allowed = set(settings.MEDIA_CHANNEL_TAG_FIELDS)
        if set(values) - allowed:
            raise forms.ValidationError("Only documented tag fields are supported.")
        return sorted(set(values))

    def clean_notification_target(self):
        value = self.cleaned_data["notification_target"].strip()
        if value and not value.lstrip("-").isdigit():
            raise forms.ValidationError("Use a numeric isolated test-chat ID; usernames are not accepted.")
        if value:
            try:
                guard_target(value)
            except TargetBlocked as exc:
                raise forms.ValidationError("Production channel targets are not allowed here.") from exc
        return value

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("notification_mode") == "test_only" and not cleaned.get("notification_target"):
            self.add_error("notification_target", "A numeric isolated test target is required for test-only mode.")
        return cleaned


class TemplatePreviewForm(forms.Form):
    template = forms.ModelChoiceField(queryset=CaptionTemplate.objects.all())

    def preview(self):
        template = self.cleaned_data["template"]
        kind = template.kind
        fixtures = {
            "single_audio": {"title": "نمونهٔ آهنگ", "artists": ["هنرمند نمونه"], "features": ["مهمان"], "release_type": "single", "spotify_url": "https://open.spotify.com/track/fixture", "soundcloud_url": "https://soundcloud.com/artist/fixture"},
            "album_intro": {"title": "نمونهٔ آلبوم", "artists": ["هنرمند نمونه"], "features": [], "release_type": "album", "previous_singles": [{"title": "تک‌آهنگ قبلی", "url": "https://t.me/RapFaDrop/123"}]},
        }
        context = fixtures.get(kind, fixtures["single_audio"])
        rendered = render_caption(kind, context, template.config)
        omitted = []
        if kind != "album_intro":
            config = template.config or {}
            labels = {**{"music_video_url": "Music Video", "spotify_url": "Spotify", "soundcloud_url": "SoundCloud", "album_post_url": "Album", "original_track_post_url": "Original"}, **config.get("labels", {})}
            for row in config.get("rows", ["music_video_url", "platforms", "album_post_url", "original_track_post_url"]):
                included = any(context.get(name) for name in ("spotify_url", "soundcloud_url")) if row == "platforms" else bool(row in labels and context.get(row))
                if not included:
                    omitted.append(row)
        return CaptionPreview(rendered.html, rendered.overflow, tuple(omitted))


@dataclass(frozen=True)
class CaptionPreview:
    html: str
    overflow: tuple
    omitted_rows: tuple
