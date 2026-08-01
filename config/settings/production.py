from .base import *  # noqa: F403, F405

DEBUG = False

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = config(  # noqa: F405
    "SECURE_SSL_REDIRECT", default=True, cast=bool
)
SESSION_COOKIE_SECURE = config(  # noqa: F405
    "SESSION_COOKIE_SECURE", default=True, cast=bool
)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=True, cast=bool)  # noqa: F405
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
