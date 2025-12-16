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

