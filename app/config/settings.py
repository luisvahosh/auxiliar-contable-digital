"""
Configuración Django — Auxiliar Contable Digital.
Regla 12-factor (PLAN.md §4): TODO lo configurable viene de variables de
entorno vía .env. Nada de rutas, claves ni credenciales quemadas en código.
"""
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga .env desde la raíz de app/ (no versionado; ver .env.example)
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]  # obligatoria: falla ruidoso si no existe

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "axes",  # rate limiting de login (PLAN.md §12)
    # Apps del producto
    "core",
    "causacion",
    "conciliacion",
    "calendario",
    "cierre",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.AccesoPorEmpresaMiddleware",  # acceso cerrado por defecto (§12)
    "axes.middleware.AxesMiddleware",
]

# Autenticación y protección de login (PLAN.md §12)
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",  # debe ir primero
    "django.contrib.auth.backends.ModelBackend",
]
AXES_FAILURE_LIMIT = int(os.environ.get("AXES_INTENTOS_MAXIMOS", "5"))
AXES_COOLOFF_TIME = 1  # horas de bloqueo tras agotar los intentos
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",  # compatibilidad
]

LOGIN_URL = "core:login"
LOGIN_REDIRECT_URL = "core:inicio"
LOGOUT_REDIRECT_URL = "core:login"

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Base de datos: DATABASE_URL en .env.
# Desarrollo día 1: sqlite. Meta (PLAN.md): PostgreSQL + pgvector —
# cambiar DATABASE_URL a postgres://... cuando esté instalado; nada más cambia.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True  # cifras contables legibles: 2.380.000

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Soportes subidos (fotos de facturas físicas, P1.10). Configurable por .env.
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("DJANGO_MEDIA_ROOT", BASE_DIR / "media"))

# Correo (alertas tributarias P6.2). En desarrollo: consola; en producción,
# cambiar backend y credenciales SMTP por .env.
EMAIL_BACKEND = os.environ.get("DJANGO_EMAIL_BACKEND",
                               "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.environ.get("DJANGO_FROM_EMAIL", "alertas@auxiliar.local")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
