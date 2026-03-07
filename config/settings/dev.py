from .base import *  # noqa: F401, F403

DEBUG = True

SECRET_KEY = SECRET_KEY or "django-insecure-dev-only-key-do-not-use-in-production"  # noqa: F405

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}
