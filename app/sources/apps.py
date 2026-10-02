from django.apps import AppConfig
import logging


class SourcesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sources"

    def ready(self):
        from .adapters import SpotifyAdapter
        logging.getLogger(__name__).warning("Spotify discovery status: %s", SpotifyAdapter.status())

