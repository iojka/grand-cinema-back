"""Configuration Django du projet Le Grand Cinéma

Les valeurs propres à chaque environnement (dev, preprod, prod) ne sont
jamais écrites ici : elles sont lues dans les variables d'environnement.
En local, elles viennent du fichier .env (non versionné, modèle dans
.env.example). Sur Azure, elles sont fournies au conteneur à partir du
coffre-fort de secrets (Key Vault, H-05)
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",  # appels du front hébergé sur un autre domaine (H-01)
    "drf_spectacular",  # documentation OpenAPI / Swagger de l'API
    # Modules métier de l'architecture du B1 (modules M1 à M6)
    "accounts",  # M6 Administration (EPIC 9)
    "programme",  # M1 Programme et séances (EPIC 1 et 6)
    "booking",  # M2 Réservation et stock de places (EPIC 2 et 7)
    "payment",  # M3 Paiement (EPIC 3)
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise : sert les fichiers statiques (admin, Swagger) en production
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    # CORS : doit être placé avant CommonMiddleware
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

# Base de données : PostgreSQL 16 dans tous les environnements, car le
# verrouillage des lignes est indispensable contre la double vente.
# Exemple local :
#   postgres://grandcinema:grandcinema@localhost:5433/grandcinema
# Exemple Azure (connexion chiffrée obligatoire) :
#   postgres://<user>:<mdp>@<serveur>.postgres.database.azure.com:5432/
#   grandcinema?sslmode=require
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)

# Comptes du back office : modèle personnalisé (connexion par e-mail,
# 4 rôles de l'US 9.1). Il doit être déclaré avant la 1re migration.
AUTH_USER_MODEL = "accounts.User"
# Connexion avec verrouillage après 5 échecs (US 9.1)
AUTHENTICATION_BACKENDS = ["accounts.backends.LockoutBackend"]

VALIDATORS_MODULE = "django.contrib.auth.password_validation"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"{VALIDATORS_MODULE}.UserAttributeSimilarityValidator"},
    {
        # US 9.1 : un mot de passe de moins de 12 caractères est refusé
        "NAME": f"{VALIDATORS_MODULE}.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": f"{VALIDATORS_MODULE}.CommonPasswordValidator"},
    {"NAME": f"{VALIDATORS_MODULE}.NumericPasswordValidator"},
]

# Langues : français par défaut, anglais (NF2)
LANGUAGE_CODE = "fr"
LANGUAGES = [("fr", "Français"), ("en", "English")]
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Fichiers statiques compressés par WhiteNoise (collectstatic)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# API REST (Django REST Framework)
REST_FRAMEWORK = {
    # Sécurité par défaut (moindre privilège) : toute route exige d'être
    # connecté, sauf celles déclarées publiques explicitement
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Jeton JWT pour le front (en-tête Authorization: Bearer ...) ;
    # session pour l'interface Swagger quand on est connecté à l'admin
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination.PageNumberPagination"
    ),
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# Jetons JWT : durée limitée, comme dans le cours (US 9.1)
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=3),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}

# Journalisation des connexions (US 9.1), affichée dans la console :
# sur Azure, ces lignes arrivent dans Log Analytics (H-06)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"accounts": {"handlers": ["console"], "level": "INFO"}},
}

# Documentation de l'API (OpenAPI 3, interface Swagger sur /api/docs/)
SPECTACULAR_SETTINGS = {
    "TITLE": "API Le Grand Cinéma",
    "DESCRIPTION": (
        "API de réservation du Grand Cinéma : programme, plan de salle, "
        "réservations, paiement, billets, guichet et pilotage."
    ),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Paiement Stripe (US 3.1) : clés du mode test, lues dans .env ou dans
# les secrets Azure, jamais écrites dans le code
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")
# Adresse du front : retour du spectateur après la page Stripe
FRONT_URL = env("FRONT_URL", default="http://localhost:5173")

# Emails (US 3.3) : affichés dans la console, donc dans les journaux du
# conteneur sur Azure. Un vrai envoi demanderait Azure Communication
# Services (H-07), non déployé pour l'examen
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = "Le Grand Cinéma <billetterie@legrandcinema.test>"

# CORS : seules les adresses du front listées ici peuvent appeler l'API
# (local : serveur de développement React ; Azure : Static Web Apps)
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS", default=["http://localhost:5173"]
)

# Préproduction et production : Azure termine le HTTPS avant le
# conteneur et le signale par l'en-tête X-Forwarded-Proto.
# Les cookies ne passent qu'en HTTPS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
