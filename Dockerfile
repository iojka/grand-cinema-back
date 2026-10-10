# Image Docker de l'API Le Grand Cinéma (Azure Container Apps, H-02)
FROM python:3.14-slim

# Pas de fichiers .pyc, et les logs sont affichés tout de suite
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dépendances en premier : Docker garde cette étape en cache tant que
# requirements.txt ne change pas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Fichiers statiques (admin, Swagger) servis par WhiteNoise.
# Valeurs factices : collectstatic ne se connecte pas à la base.
RUN SECRET_KEY=build DATABASE_URL=sqlite:///build.db \
    python manage.py collectstatic --noinput

# Sécurité : l'application ne tourne pas en root
RUN useradd --create-home app
USER app

EXPOSE 8000

# Au démarrage : migrations puis serveur Gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 2"]
