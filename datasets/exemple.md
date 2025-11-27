# Documentation MY-IA

## Qu'est-ce que MY-IA?

MY-IA est une plateforme d'intelligence artificielle conversationnelle auto-hébergée. Elle combine plusieurs technologies pour offrir une expérience RAG (Retrieval-Augmented Generation) complète.

## Architecture

L'architecture de MY-IA repose sur 5 services Docker:

1. **PostgreSQL** - Base de données relationnelle pour N8N
2. **N8N** - Plateforme d'automatisation de workflows
3. **ChromaDB** - Base de données vectorielle pour le RAG
4. **Ollama** - Serveur de modèles de langage local
5. **FastAPI** - API REST pour l'interface utilisateur

## Modèles Supportés

MY-IA supporte plusieurs modèles LLM via Ollama:

- **llama3.2:1b** - Modèle compact (1.3 GB), rapide, idéal pour CPU
- **mistral:7b** - Modèle puissant (4.4 GB), nécessite 4.5 GB RAM minimum
- **nomic-embed-text** - Modèle d'embeddings (274 MB) pour la recherche sémantique

## Endpoints API

L'API FastAPI expose plusieurs endpoints:

- `GET /health` - Vérification de l'état des services
- `GET /metrics` - Métriques Prometheus
- `POST /chat` - ChatBot conversationnel avec RAG
- `POST /assistant` - Assistant orienté tâches
- `POST /chat/stream` - Streaming des réponses

## Configuration

Les variables d'environnement importantes:

- `OLLAMA_HOST` - URL du serveur Ollama (défaut: http://ollama:11434)
- `CHROMA_HOST` - URL de ChromaDB (défaut: http://chroma:8000)
- `MODEL_NAME` - Nom du modèle LLM à utiliser
- `EMBED_MODEL` - Modèle pour les embeddings
- `API_KEY` - Clé d'authentification API

## Installation

Pour déployer MY-IA:

```bash
# Cloner le projet
git clone https://github.com/votre-repo/my-ia

# Lancer les services
docker compose up -d

# Télécharger les modèles
docker exec my-ia-ollama ollama pull llama3.2:1b
docker exec my-ia-ollama ollama pull nomic-embed-text

# Ingérer les données
docker compose exec app python ingest_fixed.py
```

## Performances

Les temps de réponse dépendent du matériel:

- **CPU uniquement**: 1-3 minutes par requête
- **GPU (CUDA)**: 5-15 secondes par requête
- **GPU (M1/M2 Metal)**: 10-30 secondes par requête

## Sécurité

Points de sécurité à configurer en production:

1. Changer l'API_KEY par défaut
2. Configurer HTTPS avec un reverse proxy (nginx)
3. Modifier les mots de passe N8N et PostgreSQL
4. Restreindre les CORS à votre domaine
5. Activer le rate limiting strictement
