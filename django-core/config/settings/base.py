"""
Base settings shared across all environments.
"""
import os
import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# ── GeoDjango / GDAL (Windows) ────────────────────────────────────────────────
# On Windows with Anaconda, GDAL and its dependency DLLs (proj, curl, zlib…)
# live in <conda_env>/Library/bin. Python's DLL loader must know about this
# directory BEFORE any GDAL import or it crashes with 0xC06D007F.
# Set CONDA_ENV_PATH in .env to the Library\bin folder of your conda env.
import sys
if sys.platform == "win32":
    _conda_bin = env("CONDA_ENV_PATH", default="")
    if _conda_bin:
        import ctypes
        os.add_dll_directory(_conda_bin)        # Python 3.8+ DLL search path
        os.environ["PATH"] = _conda_bin + os.pathsep + os.environ.get("PATH", "")

_gdal_path = env("GDAL_LIBRARY_PATH", default="")
_geos_path = env("GEOS_LIBRARY_PATH", default="")
_proj_path = env("PROJ_LIBRARY_PATH", default="")
if _gdal_path:
    GDAL_LIBRARY_PATH = _gdal_path
if _geos_path:
    GEOS_LIBRARY_PATH = _geos_path
if _proj_path:
    PROJ_LIBRARY_PATH = _proj_path

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

# ── Application ───────────────────────────────────────────────────────────────

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "rest_framework",
    "rest_framework_gis",
    "channels",
]

LOCAL_APPS = [
    "apps.organizations",
    "apps.assets",
    "apps.devices",
    "apps.geofences",
    "apps.tracking",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
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

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ASGI_APPLICATION = "config.asgi.application"

# ── Database (PostGIS) ────────────────────────────────────────────────────────

DATABASES = {
    "default": env.db("DATABASE_URL", engine="django.contrib.gis.db.backends.postgis"),
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Cache (Redis) ─────────────────────────────────────────────────────────────

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "MAX_ENTRIES": 10000,
        },
    }
}

# ── Channels (WebSocket) ──────────────────────────────────────────────────────

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

# ── Celery ────────────────────────────────────────────────────────────────────

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_ROUTES = {
    "apps.devices.tasks.write_cold_storage": {"queue": "cold_write"},
    "apps.devices.tasks.evaluate_geofences": {"queue": "geofences"},
}
CELERY_BEAT_SCHEDULER = "celery.beat:PersistentScheduler"

# ── Django REST Framework ─────────────────────────────────────────────────────

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "device_telemetry": "60/min",
    },
    "DEFAULT_PAGINATION_CLASS": "config.pagination.CreatedAtCursorPagination",
    "PAGE_SIZE": 100,
}

CURSOR_PAGINATION_ORDERING = "-created_at"

# ── Internationalisation ──────────────────────────────────────────────────────

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# ── SimpleJWT ─────────────────────────────────────────────────────────────────

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
}
