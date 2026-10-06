import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-development-only")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [value.strip() for value in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if value.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "diagnostics",
    "sources",
    "releases",
    "media_pipeline",
    "publication",
    "operations",
    "archive_collection",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.environ.get("POSTGRES_DB", "rapfadrop"),
    "USER": os.environ.get("POSTGRES_USER", "rapfadrop"),
    "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
    "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
    "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    "CONN_MAX_AGE": 60,
}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "/admin/login/"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MEDIA_ROOT = Path(os.environ.get("RAPFADROP_MEDIA_ROOT", "/tmp/rapfadrop-media"))
MEDIA_MAX_UPLOAD_BYTES = int(os.environ.get("RAPFADROP_MEDIA_MAX_UPLOAD_BYTES", "104857600"))
MEDIA_DOWNLOAD_TIMEOUT_SECONDS = int(os.environ.get("RAPFADROP_MEDIA_DOWNLOAD_TIMEOUT_SECONDS", "240"))
MEDIA_FFPROBE_TIMEOUT_SECONDS = int(os.environ.get("RAPFADROP_MEDIA_FFPROBE_TIMEOUT_SECONDS", "30"))
MEDIA_EXPECTED_DURATION_TOLERANCE_SECONDS = float(os.environ.get("RAPFADROP_MEDIA_EXPECTED_DURATION_TOLERANCE_SECONDS", "5"))
MEDIA_TRUNCATION_RATIO = float(os.environ.get("RAPFADROP_MEDIA_TRUNCATION_RATIO", "0.9"))
MEDIA_CHANNEL_TAG = os.environ.get("RAPFADROP_MEDIA_CHANNEL_TAG", "@RapFaDrop")
MEDIA_AUTHOR_URL = os.environ.get("RAPFADROP_MEDIA_AUTHOR_URL", "https://t.me/RapFaDrop")
MEDIA_MAX_ARTWORK_BYTES = int(os.environ.get("RAPFADROP_MEDIA_MAX_ARTWORK_BYTES", str(8 * 1024 * 1024)))
MEDIA_ALLOWED_AUDIO_EXTENSIONS = tuple(
    value.strip().lower() if value.strip().startswith(".") else f".{value.strip().lower()}"
    for value in os.environ.get("RAPFADROP_MEDIA_ALLOWED_AUDIO_EXTENSIONS", "mp3,m4a,mp4,aac,flac,ogg,opus,wav,aiff,aif").split(",")
    if value.strip()
)
MEDIA_CHANNEL_TAG_FIELDS = frozenset(
    value.strip().lower()
    for value in os.environ.get("RAPFADROP_MEDIA_CHANNEL_TAG_FIELDS", "subtitle,comments,album_artist_suffix,album_suffix,publisher,encoded_by,author_url,copyright,composers,conductors,initial_key").split(",")
    if value.strip()
)
MEDIA_YOUTUBE_COOKIES_FILE = os.environ.get('RAPFADROP_MEDIA_YOUTUBE_COOKIES_FILE', '')
MEDIA_YOUTUBE_JS_RUNTIME = os.environ.get('RAPFADROP_MEDIA_YOUTUBE_JS_RUNTIME', '')
MEDIA_PROVIDER_ORDER = tuple(
    value.strip()
    for value in os.environ.get("RAPFADROP_MEDIA_PROVIDER_ORDER", "yt-dlp").split(",")
    if value.strip()
)
SPOTIFY_MEDIA_BRIDGE_ENABLED = os.environ.get("RAPFADROP_SPOTIFY_MEDIA_BRIDGE_ENABLED", "false").lower() == "true"

TELEGRAM_MODE = os.environ.get("RAPFADROP_TELEGRAM_MODE", "disabled")
TELEGRAM_LIVE_ENABLED = os.environ.get("RAPFADROP_TELEGRAM_LIVE_ENABLED", "false").lower() == "true"
TELEGRAM_BOT_TOKEN = os.environ.get("RAPFADROP_TELEGRAM_BOT_TOKEN", "")
if os.environ.get("RAPFADROP_TELEGRAM_BOT_TOKEN_FILE"):
    _bot_file = Path(os.environ["RAPFADROP_TELEGRAM_BOT_TOKEN_FILE"])
    if _bot_file.is_symlink() or not _bot_file.is_file() or _bot_file.stat().st_mode & 0o077:
        raise ValueError("Protected bot credential file required")
    TELEGRAM_BOT_TOKEN = _bot_file.read_text().strip()
TELEGRAM_TEST_CHAT_ID = os.environ.get("RAPFADROP_TELEGRAM_TEST_CHAT_ID", "")
TELEGRAM_REVIEW_CHAT_ID = os.environ.get("RAPFADROP_TELEGRAM_REVIEW_CHAT_ID", "")
TELEGRAM_PRODUCTION_CHAT_ID = os.environ.get("RAPFADROP_TELEGRAM_PRODUCTION_CHAT_ID", "")
TELEGRAM_TIMEOUT_SECONDS = int(os.environ.get("RAPFADROP_TELEGRAM_TIMEOUT_SECONDS", "60"))
PUBLICATION_WORKER_ENABLED = os.environ.get("RAPFADROP_PUBLICATION_WORKER_ENABLED", "false").lower() == "true"
FRESH_PIPELINE_ENABLED = os.environ.get("RAPFADROP_FRESH_PIPELINE_ENABLED", "false").lower() == "true"
FRESH_INDEPENDENT_UPLOADERS_ENABLED = os.environ.get('RAPFADROP_FRESH_INDEPENDENT_UPLOADERS_ENABLED', 'false').lower() == 'true'
FRESH_SPOTSAVER_ENABLED = os.environ.get('RAPFADROP_FRESH_SPOTSAVER_ENABLED', 'false').lower() == 'true'
FRESH_FEED_DISCOVERY_ENABLED = os.environ.get('RAPFADROP_FRESH_FEED_DISCOVERY_ENABLED', 'false').lower() == 'true'
FRESH_FEED_DISCOVERY_CONCURRENCY = int(os.environ.get('RAPFADROP_FRESH_FEED_DISCOVERY_CONCURRENCY','2'))
TELEGRAM_EXPECTED_BOT_ID = int(os.environ.get("RAPFADROP_TELEGRAM_EXPECTED_BOT_ID", "0"))
PUBLICATION_ALBUM_HOLD_SECONDS = int(os.environ.get("RAPFADROP_PUBLICATION_ALBUM_HOLD_SECONDS", "900"))
PUBLICATION_CORRECTION_DELETE_SECONDS = int(os.environ.get("RAPFADROP_PUBLICATION_CORRECTION_DELETE_SECONDS", "600"))
PUBLICATION_CORRECTION_TEXT = os.environ.get("RAPFADROP_PUBLICATION_CORRECTION_TEXT", "Audio file updated.")

CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = None
CELERY_TASK_IGNORE_RESULT = True
CELERY_TIMEZONE = "UTC"
from .scheduling import beat_schedule

CELERY_BEAT_SCHEDULE = beat_schedule(PUBLICATION_WORKER_ENABLED, TELEGRAM_LIVE_ENABLED, TELEGRAM_MODE, SPOTIFY_MEDIA_BRIDGE_ENABLED, FRESH_PIPELINE_ENABLED)
if FRESH_FEED_DISCOVERY_ENABLED:
    CELERY_BEAT_SCHEDULE['independent-upload-discovery']={'task':'releases.tasks.poll_independent_uploads','schedule':5.0,'options':{'queue':'fresh-discovery-v1','expires':5}}
CELERY_TASK_ROUTES = {
    "sources.tasks.poll_due_artist_sources": {"queue": "spotify-pilot"},
    "releases.tasks.process_fresh_releases": {"queue": "fresh-media-v1"},
    "publication.tasks.process_due_publications": {"queue": "fresh-publication-v1"},
}

# The adapter is selected explicitly; existing installations stay unavailable.
SPOTIFY_DISCOVERY_MODE = os.environ.get("RAPFADROP_SPOTIFY_DISCOVERY_MODE", "unavailable")
