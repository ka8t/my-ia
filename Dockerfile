# MY-IA API - Dockerfile optimisé pour MacBook Pro 2015
# Python 3.12 requis pour compatibilité unstructured
FROM python:3.12-slim

WORKDIR /code

# Installation des dépendances système pour ingestion avancée v2
# Optimisé : combine tout en une seule couche + nettoyage agressif
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    poppler-utils \
    libmagic1 \
    libgl1 \
    libglib2.0-0 \
    pandoc \
    libjpeg-dev \
    libpng-dev \
    # Build dependencies (seront supprimés après)
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copier les requirements d'abord (pour cache Docker)
COPY requirements.txt ./

# Installer les dépendances Python (sans cleanup qui masque les erreurs)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Nettoyer les caches Python séparément (pour ne pas masquer les erreurs d'installation)
RUN rm -rf /root/.cache/pip && \
    find /usr/local/lib/python3.12 -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true

# Copier tout le code de l'application
COPY ./app /code/app/

# Définir le PYTHONPATH pour que Python trouve le module 'app'
ENV PYTHONPATH=/code

EXPOSE 8080

# Healthcheck pour Docker
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Lancer l'application avec le bon chemin de module
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
