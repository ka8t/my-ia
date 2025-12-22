# MY-IA API - Dockerfile optimisé pour architecture modulaire
# Python 3.12 requis pour compatibilité unstructured
FROM python:3.12-slim

WORKDIR /code

# Installation des dépendances système pour ingestion avancée v2
RUN apt-get update && apt-get install -y \
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
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copier les requirements d'abord (pour cache Docker)
COPY requirements.txt ./

# Installer les dépendances Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier tout le code de l'application
COPY . /code/app/

# Définir le PYTHONPATH pour que Python trouve le module 'app'
ENV PYTHONPATH=/code

EXPOSE 8080

# Healthcheck pour Docker
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Lancer l'application avec le bon chemin de module
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
