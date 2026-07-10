"""
Django base settings for Heritage Platform project.
"""

from pathlib import Path
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False)
)

# Read .env file if it exists
environ.Env.read_env(BASE_DIR / '.env')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY also signs JWT access/refresh tokens (SimpleJWT falls back to it
# when SIGNING_KEY is unset), so a predictable key means anyone can forge tokens
# for any user. We therefore only allow the throw-away insecure default in DEBUG:
# outside DEBUG a missing SECRET_KEY is a hard error (fail closed) rather than a
# silent fall-back to a public, committed key.
if DEBUG:
    SECRET_KEY = env(
        'SECRET_KEY',
        default='django-insecure-pwlzd#&b6fu7fqnbrver$ov^(f2ppw(p7ms*kv4+6y02(shvhq',
    )
else:
    SECRET_KEY = env('SECRET_KEY')  # raises ImproperlyConfigured if unset

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

# Application definition

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',  # GeoDjango for PostGIS support
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',  # API documentation
    'modeltranslation',  # Multilingual support
]

PROJECT_APPS = [
    'apps.users',
    'apps.cities',
    'apps.heritage',
    'apps.education',
    'apps.routes',
    'apps.contributions',
    'apps.gamification',
    'apps.moderation',
    'apps.ai_services.apps.AiServicesConfig',
    'apps.notifications',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + PROJECT_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS middleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # i18n middleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': env.db('DATABASE_URL', default='sqlite:///db.sqlite3'),
}

# For PostGIS support
DATABASES['default']['ENGINE'] = 'django.contrib.gis.db.backends.postgis'

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = []

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'es'  # Default to Spanish

LANGUAGES = [
    ('es', 'Español'),
    ('en', 'English'),
]

# Server-wide timezone (env-overridable). Note: AI-usage day buckets and any
# timezone.localdate() aggregation follow this global setting; City.timezone
# is informational/display-only and deliberately NOT applied to aggregation.
TIME_ZONE = env('DJANGO_TIME_ZONE', default='America/Guayaquil')

USE_I18N = True
USE_TZ = True

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Modeltranslation default language
MODELTRANSLATION_DEFAULT_LANGUAGE = 'es'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# JWT Configuration
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# API Documentation (drf-spectacular)
SPECTACULAR_SETTINGS = {
    'TITLE': 'Heritage Platform API',
    'DESCRIPTION': 'API for participatory digital platform for cultural heritage management',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# CORS settings (will be configured per environment)
CORS_ALLOW_ALL_ORIGINS = False

# The SPA sends the active city on every request; the default allow-list of
# django-cors-headers does not include custom headers, so preflights from the
# Vite dev server (:5173 → :8000) would fail without this.
from corsheaders.defaults import default_headers

CORS_ALLOW_HEADERS = (*default_headers, 'x-city')

# AI configuration. The active provider, model and prompts live in ai.yaml
# (path below). Provider API keys are read from the environment by the AI config
# loader via the `api_key_env` declared in ai.yaml (e.g. GEMINI_API_KEY) and are
# NEVER stored in the YAML. We read GEMINI_API_KEY here so django-environ loads
# it from .env into the process environment where the loader can see it.
AI_CONFIG_PATH = env("AI_CONFIG_PATH", default=str(BASE_DIR / "config" / "ai.yaml"))
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")

# Route geometry / walking-directions provider. OFF by default: with
# ROUTING_PROVIDER=straight_line, route paths are simple polylines through the
# stops and no external service is called. Set ROUTING_PROVIDER=osrm + OSRM_URL
# (e.g. http://osrm:5000) to snap paths to streets with turn-by-turn + real ETA;
# an unreachable OSRM degrades to the straight-line fallback (never breaks a save).
ROUTING_PROVIDER = env("ROUTING_PROVIDER", default="straight_line")
OSRM_URL = env("OSRM_URL", default="")
ROUTING_TIMEOUT_SECONDS = env.int("ROUTING_TIMEOUT_SECONDS", default=8)
ROUTING_WALKING_SPEED_MPS = env.float("ROUTING_WALKING_SPEED_MPS", default=1.3)
# Radius (metres) within which a geolocated check-in is considered "at" the stop.
ROUTE_CHECKIN_RADIUS_M = env.int("ROUTE_CHECKIN_RADIUS_M", default=100)

# F.3 — test-run fast path. The default PBKDF2 hasher deliberately burns
# ~100ms per hash, and nearly every test setUp calls create_user(); across the
# suite that hashing dominated wall-clock time. MD5 is plenty for throwaway
# test credentials. Applies only under `manage.py test` — every real run keeps
# the production hasher.
import sys  # noqa: E402

if len(sys.argv) > 1 and sys.argv[1] == "test":
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
