"""Configuration Django du projet Le Grand Cinéma.

Les valeurs propres à chaque environnement (dev, preprod, prod) ne sont
jamais écrites ici : elles sont lues dans les variables d'environnement.
En local, elles viennent du fichier .env (non versionné, modèle dans
.env.example). Sur Azure, elles sont fournies au conteneur à partir du
coffre-fort de secrets (Key Vault, H-05).
"""

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
    # Modules métier de l'architecture du B1 (modules M1 à M6)
    "accounts",  # M6 Administration (EPIC 9)
    "programme",  # M1 Programme et séances (EPIC 1 et 6)
    "booking",  # M2 Réservation et stock de places (EPIC 2 et 7)
    "payment",  # M3 Paiement (EPIC 3)
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
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
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
