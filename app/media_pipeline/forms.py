from urllib.parse import urlsplit, urlunsplit

from django import forms

from .models import MediaCandidate


class ManualMediaUploadForm(forms.Form):
    audio_file = forms.FileField()
    artwork_file = forms.FileField(required=False)
    artwork_source_url = forms.URLField(required=False, max_length=1000, help_text="Required when artwork is supplied; record the official page where it was observed.")

    def clean_artwork_source_url(self):
        value = self.cleaned_data.get("artwork_source_url", "").strip()
        if value:
            parts = urlsplit(value)
            if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
                raise forms.ValidationError("Artwork provenance must be a credential-free HTTPS URL.")
            return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        return ""

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("artwork_file") and not cleaned.get("artwork_source_url"):
            self.add_error("artwork_source_url", "Record the official artwork source URL.")
        return cleaned


class MediaCandidateAdminForm(forms.ModelForm):
    class Meta:
        model = MediaCandidate
        fields = ("source_match", "provider")

    def clean_source_match(self):
        match = self.cleaned_data["source_match"]
        if not match.track_id or not match.release_id or match.confidence < 90 or match.state not in {"matched", "approved", "corrected"}:
            raise forms.ValidationError("Choose a confidently identified track/release source match.")
        return match
