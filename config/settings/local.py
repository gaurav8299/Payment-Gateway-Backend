import sys

from .base import *  # noqa: F403, F405

DEBUG = True

ALLOWED_HOSTS = ["*"]

# In local environment, use console backend for email if not specified
EMAIL_BACKEND = config(  # noqa: F405
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)

# In local host development, default to LocMemCache and eager Celery unless Redis is explicitly configured
CACHES = {
    "default": {
        "BACKEND": config(  # noqa: F405
            "CACHE_BACKEND",
            default="django.core.cache.backends.locmem.LocMemCache",
        ),
        "LOCATION": "unique-local-cache",
    }
}

if "pytest" in sys.modules or "test" in sys.argv:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "test_db.sqlite3",  # noqa: F405
        }
    }
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

