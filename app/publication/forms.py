from django import forms
from django.core.exceptions import ValidationError

from .captions import DEFAULT_CONFIG
from .models import CaptionTemplate


class CaptionTemplateForm(forms.ModelForm):
    class Meta:
        model = CaptionTemplate
        fields = ("kind", "version", "config", "enabled")

    def clean_config(self):
        value = self.cleaned_data["config"]
        if not isinstance(value, dict) or set(value) - set(DEFAULT_CONFIG):
            raise ValidationError("Template config contains unsupported fields.")
        rows = value.get("rows", DEFAULT_CONFIG["rows"])
        labels = value.get("labels", DEFAULT_CONFIG["labels"])
        allowed_rows = {"music_video_url", "platforms", "album_post_url", "original_track_post_url"}
        allowed_labels = set(DEFAULT_CONFIG["labels"])
        if not isinstance(rows, list) or set(rows) - allowed_rows:
            raise ValidationError("Template contains unknown or unsupported row variables.")
        if not isinstance(labels, dict) or set(labels) - allowed_labels or any(not isinstance(v, str) or len(v) > 80 for v in labels.values()):
            raise ValidationError("Template labels must use documented caption values.")
        for key in set(value) - {"rows", "labels"}:
            if not isinstance(value[key], str) or len(value[key]) > 200:
                raise ValidationError("Caption text values must be plain strings up to 200 characters.")
        return value

    def clean(self):
        cleaned = super().clean()
        allowed_kinds = {"single_audio", "album_intro", "album_track_audio", "archive_audio", "edition", "overflow", "correction", "notification"}
        if cleaned.get("kind") not in allowed_kinds:
            self.add_error("kind", "Choose a documented publication template kind.")
        if not self.instance.pk and cleaned.get("enabled"):
            self.add_error("enabled", "Create templates disabled, preview them, then activate from the operator panel.")
        if self.instance.pk:
            old = CaptionTemplate.objects.get(pk=self.instance.pk)
            if (old.kind, old.version, old.config, old.enabled) != (cleaned.get("kind"), cleaned.get("version"), cleaned.get("config"), cleaned.get("enabled")):
                raise ValidationError("Caption templates are versioned. Add a new version instead of editing an existing one.")
        return cleaned
