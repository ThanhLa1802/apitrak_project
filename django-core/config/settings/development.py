from config.settings.base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]
CORS_ALLOW_CREDENTIALS = True

# WhiteNoise: auto-discover static files from STATICFILES_DIRS / installed apps
# when STATIC_ROOT hasn't been populated by collectstatic yet.
WHITENOISE_USE_FINDERS = True
