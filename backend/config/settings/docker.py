"""
Docker-friendly settings: production-like, but without forced HTTPS redirects.
"""

from .base import *  # noqa: F403

DEBUG = False

# Allow docker-compose defaults to "localhost,127.0.0.1,frontend"
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "frontend"])  # noqa: F405

# In-container deployments are often behind a reverse proxy; don't force HTTPS.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# CORS/CSRF for the bundled nginx frontend.
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:8080"])  # noqa: F405
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost:8080"])  # noqa: F405

# Email: the containers have no SMTP server; Django's default SMTP backend
# would hard-fail on localhost:25. Console by default — set the EMAIL_* env
# vars (documented in .env.prod.example) to point at a real provider when
# outbound mail is wanted (E4).
EMAIL_BACKEND = env(  # noqa: F405
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", default=587)  # noqa: F405
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)  # noqa: F405
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")  # noqa: F405
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")  # noqa: F405
DEFAULT_FROM_EMAIL = env(  # noqa: F405
    "DEFAULT_FROM_EMAIL", default="noreply@heritageplatform.ddns.net"
)

