import sys

from .base import *  # noqa: F403, F405

DEBUG = True

ALLOWED_HOSTS = ["*"]

# In local environment, use console backend for email if not specified
EMAIL_BACKEND = config(  # noqa: F405
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)

# SQLite test database and LocMemCache override when running pytest locally on host
if "pytest" in sys.modules or "test" in sys.argv:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "test_db.sqlite3",  # noqa: F405
        }
    }
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-pytest-cache",
        }
    }
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
