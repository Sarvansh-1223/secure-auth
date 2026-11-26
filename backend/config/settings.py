"""
Django settings.

Every secret / environment-specific value comes from environment variables
(or a local, git-ignored ``backend/.env`` file). Nothing sensitive is hardcoded.
See ``.env.example`` and ``scripts/make_env.py``.
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------
DEBUG = env.bool("DEBUG", default=False)
SECRET_KEY = env("SECRET_KEY")  # required, no default on purpose
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Secret used to HMAC OTPs and identifiers (a "pepper"). Kept separate from
# SECRET_KEY so that rotating one doesn't silently affect the other.
AUTH_PEPPER = env("AUTH_PEPPER")  # required

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "corsheaders",
    "rest_framework",
    "core",
    "accounts",
    "otp",
    "sessions_app",
    "webauthn_app",
    "security",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "core.middleware.ApiSecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
AUTH_USER_MODEL = "accounts.User"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"

TEMPLATES = []  # API only

# --------------------------------------------------------------------------
# Database (MySQL by default; SQLite only for local tests via DB_ENGINE=sqlite)
# --------------------------------------------------------------------------
DB_ENGINE = env("DB_ENGINE", default="mysql")
if DB_ENGINE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": env("DB_NAME", default=str(BASE_DIR / "db.sqlite3")),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env("DB_NAME", default="secure_auth"),
            "USER": env("DB_USER", default="secure_auth"),
            "PASSWORD": env("DB_PASSWORD"),
            "HOST": env("DB_HOST", default="127.0.0.1"),
            "PORT": env("DB_PORT", default="3306"),
            "CONN_MAX_AGE": 60,
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_ALL_TABLES'",
                "isolation_level": "read committed",
            },
        }
    }

# --------------------------------------------------------------------------
# Cache (rate limiting, resend cooldowns). Use Redis in any multi-process setup.
# --------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# --------------------------------------------------------------------------
# HTTP security: cookies, CSRF, CORS, headers
# --------------------------------------------------------------------------
COOKIE_SECURE = env.bool("COOKIE_SECURE", default=not DEBUG)
SESSION_COOKIE_NAME_AUTH = "sa_session"   # opaque server-side session token
DEVICE_COOKIE_NAME = "sa_device"          # long-lived device identifier
COOKIE_SAMESITE = env("COOKIE_SAMESITE", default="Lax")

CSRF_COOKIE_SECURE = COOKIE_SECURE
CSRF_COOKIE_SAMESITE = COOKIE_SAMESITE
CSRF_COOKIE_HTTPONLY = False  # SPA reads token via /auth/csrf JSON anyway
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://localhost:5173"])

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:5173"])
CORS_ALLOW_CREDENTIALS = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_PROXY_SSL_HEADER = (
        ("HTTP_X_FORWARDED_PROTO", "https") if env.bool("TRUST_PROXY", default=False) else None
    )

# Only trust X-Forwarded-For when running behind a proxy you control.
TRUST_PROXY = env.bool("TRUST_PROXY", default=False)

# --------------------------------------------------------------------------
# Authentication policy (all configurable)
# --------------------------------------------------------------------------
OTP_LENGTH = 6
OTP_TTL_SECONDS = env.int("OTP_TTL_SECONDS", default=300)              # 5 minutes
OTP_RESEND_COOLDOWN_SECONDS = env.int("OTP_RESEND_COOLDOWN_SECONDS", default=30)
OTP_MAX_SENDS_PER_HOUR = env.int("OTP_MAX_SENDS_PER_HOUR", default=5)
OTP_MAX_ATTEMPTS_PER_CODE = env.int("OTP_MAX_ATTEMPTS_PER_CODE", default=5)

LOCKOUT_MAX_FAILURES = env.int("LOCKOUT_MAX_FAILURES", default=5)
LOCKOUT_DURATION_SECONDS = env.int("LOCKOUT_DURATION_SECONDS", default=3600)  # exactly 1 hour
# Defence-in-depth: failures from one IP (any account) inside the window.
IP_FAILURE_LIMIT = env.int("IP_FAILURE_LIMIT", default=30)
IP_FAILURE_WINDOW_SECONDS = env.int("IP_FAILURE_WINDOW_SECONDS", default=900)

SESSION_IDLE_TIMEOUT_SECONDS = env.int("SESSION_IDLE_TIMEOUT_SECONDS", default=1800)
SESSION_ABSOLUTE_TIMEOUT_SECONDS = env.int("SESSION_ABSOLUTE_TIMEOUT_SECONDS", default=43200)
SESSION_TOUCH_INTERVAL_SECONDS = 30

MIN_REGISTRATION_AGE_YEARS = env.int("MIN_REGISTRATION_AGE_YEARS", default=13)
MAX_REGISTRATION_AGE_YEARS = 120

# --------------------------------------------------------------------------
# WebAuthn
# --------------------------------------------------------------------------
WEBAUTHN_RP_ID = env("WEBAUTHN_RP_ID", default="localhost")
WEBAUTHN_RP_NAME = env("WEBAUTHN_RP_NAME", default="Secure Auth")
WEBAUTHN_ORIGINS = env.list("WEBAUTHN_ORIGINS", default=["http://localhost:5173"])
WEBAUTHN_CHALLENGE_TTL_SECONDS = 120

# --------------------------------------------------------------------------
# OTP delivery
# --------------------------------------------------------------------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Secure Auth <no-reply@example.com>")

SMS_PROVIDER = env("SMS_PROVIDER", default="console")  # console | twilio
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN", default="")
TWILIO_FROM_NUMBER = env("TWILIO_FROM_NUMBER", default="")

# --------------------------------------------------------------------------
# Django REST Framework
# --------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["sessions_app.authentication.ServerSessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "register": env("THROTTLE_REGISTER", default="10/hour"),
        "otp_request": env("THROTTLE_OTP_REQUEST", default="10/hour"),
        "credential_check": env("THROTTLE_CREDENTIAL_CHECK", default="30/minute"),
        "webauthn": env("THROTTLE_WEBAUTHN", default="30/minute"),
        "status": env("THROTTLE_STATUS", default="60/minute"),
    },
    "NUM_PROXIES": 1 if TRUST_PROXY else 0,
    "UNAUTHENTICATED_USER": None,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
