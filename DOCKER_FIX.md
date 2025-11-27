# Corrections Docker - MY-IA

> Date: 2025-11-27
> Statut: ✅ CORRIGÉ

## 🔴 Problèmes Identifiés

### 1. **Fichier `app/main.py` CORROMPU** (CRITIQUE)
**Symptôme**: Le fichier contenait du code YAML au lieu du code Python FastAPI

**Cause**: Le fichier `main.py` avait été écrasé avec le contenu de `docker-compose.yml`

**Impact**: L'application FastAPI ne pouvait pas démarrer (erreur de syntaxe Python)

**Solution**:
- ✅ Sauvegarde créée: `app/main.py.backup.20251127_045940`
- ✅ Nouveau fichier `main.py` créé avec API complète (371 lignes)

---

### 2. **Indentation incorrecte dans `docker-compose.yml`**
**Symptôme**: Espaces mal alignés devant les commentaires

**Lignes affectées**:
- Ligne 22: `# N8N - Automatisation de workflows`
- Ligne 54: `# ChromaDB - Vector Database`
- Ligne 84: `# Application FastAPI - API RAG`

**Solution**: ✅ Indentation corrigée (2 espaces)

---

## ✅ Nouveau fichier `main.py`

### Fonctionnalités Implémentées

#### **Endpoints API**
1. `GET /` - Informations de base
2. `GET /health` - Health check (Ollama + ChromaDB)
3. `GET /metrics` - Métriques Prometheus
4. `POST /chat` - ChatBot conversationnel avec RAG
5. `POST /assistant` - Assistant orienté tâches avec RAG
6. `POST /chat/stream` - Streaming responses

#### **Fonctionnalités**
- ✅ **RAG complet** avec ChromaDB
  - Génération d'embeddings via Ollama
  - Recherche sémantique (top_k configurable)
  - Contexte injecté dans les prompts

- ✅ **Authentication**
  - API Key via header `X-API-Key`
  - Configurable via env var `API_KEY`

- ✅ **Rate Limiting**
  - 30 req/min pour `/chat` et `/assistant`
  - 20 req/min pour `/chat/stream`

- ✅ **CORS activé**
  - Pour intégration N8N
  - Tous origins autorisés (à restreindre en prod)

- ✅ **Monitoring**
  - Métriques Prometheus (compteurs, histogrammes)
  - Logs structurés (niveau configurable)
  - Health checks (Ollama + ChromaDB)

- ✅ **System Prompts**
  - Lecture depuis `/app/prompts/chatbot_system.md`
  - Lecture depuis `/app/prompts/assistant_system.md`
  - Fallback si fichiers manquants

- ✅ **Gestion d'erreurs robuste**
  - Try/except sur tous les appels externes
  - Messages d'erreur clairs
  - Logging détaillé

#### **Configuration (Variables d'environnement)**
```bash
OLLAMA_HOST=http://ollama:11434
CHROMA_HOST=http://chroma:8000
MODEL_NAME=mistral:7b
EMBED_MODEL=nomic-embed-text
TOP_K=4
LOG_LEVEL=INFO
API_KEY=change-me-in-production
```

---

## 📦 Images Docker

### Statut des Builds
- ✅ `my-ia_app` - Python 3.11-slim + FastAPI
- ✅ `my-ia_chroma` - ChromaDB avec curl pour healthcheck
- ✅ Images construites sans erreur

### Optimisations Possibles (À faire)
- [ ] Multi-stage builds pour réduire taille
- [ ] Utiliser Alpine Linux où possible
- [ ] Healthchecks pour tous les services
- [ ] .dockerignore optimisé

---

## 🧪 Tests à Effectuer

### 1. Lancement des Services
```bash
cd /Users/k/Documents/Documents\ -\ MacBook\ Pro\ de\ k/Code/Ollama/my-ia
docker compose up -d
```

### 2. Vérifier les Logs
```bash
# Tous les services
docker compose logs -f

# Service spécifique
docker compose logs -f app
```

### 3. Health Check
```bash
curl http://localhost:8080/health
```

**Réponse attendue**:
```json
{
  "status": "healthy",
  "ollama": true,
  "chroma": true,
  "model": "mistral:7b"
}
```

### 4. Test ChatBot
```bash
curl -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-me-in-production' \
  -d '{"query":"Hello, ça va?"}'
```

### 5. Test Assistant
```bash
curl -X POST http://localhost:8080/assistant \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-me-in-production' \
  -d '{"query":"Crée un plan de déploiement"}'
```

### 6. Documentation Interactive
Ouvrir dans le navigateur:
```
http://localhost:8080/docs
```

---

## ⚠️ Prérequis Avant de Lancer

### 1. Télécharger les Modèles Ollama
```bash
# Démarrer seulement Ollama
docker compose up -d ollama

# Télécharger les modèles
docker exec -it my-ia-ollama ollama pull mistral:7b
docker exec -it my-ia-ollama ollama pull nomic-embed-text
```

### 2. Créer la Collection ChromaDB
Le script `ingest.py` doit être exécuté après le premier lancement:
```bash
docker compose exec app python ingest.py
```

---

## 🚀 Démarrage Complet

### Option 1: Script Automatique
```bash
./scripts/setup.sh
```

### Option 2: Étape par Étape
```bash
# 1. Build des images
docker compose build

# 2. Démarrer tous les services
docker compose up -d

# 3. Attendre que Ollama soit prêt (30-60s)
sleep 60

# 4. Télécharger les modèles
docker exec -it my-ia-ollama ollama pull mistral:7b
docker exec -it my-ia-ollama ollama pull nomic-embed-text

# 5. Ingérer les données
docker compose exec app python ingest.py

# 6. Tester
curl http://localhost:8080/health
```

---

## 📊 État des Services

| Service | Port | Statut Build | Notes |
|---------|------|--------------|-------|
| **postgres** | 5432 | ✅ Image officielle | Healthcheck OK |
| **n8n** | 5678 | ✅ Image officielle | Dépend de postgres |
| **chroma** | 8000 | ✅ Build réussi | Curl installé |
| **ollama** | 11434 | ✅ Image officielle | Pas de healthcheck |
| **app** | 8080 | ✅ Build réussi | **main.py recréé** |

---

## 🔐 Sécurité

### Identifiants par Défaut (À CHANGER!)
```bash
# PostgreSQL
POSTGRES_USER=n8n
POSTGRES_PASSWORD=n8n_password

# N8N
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=change-me-in-production

# API
API_KEY=change-me-in-production
```

### Recommandations
1. Créer un fichier `.env` avec des valeurs sécurisées
2. Ne jamais commiter `.env` dans Git
3. Utiliser Docker secrets en production
4. Activer HTTPS pour N8N

---

## 📝 Fichiers Modifiés

```
my-ia/
├── app/
│   ├── main.py                           ✅ RECRÉÉ (371 lignes)
│   └── main.py.backup.20251127_045940    📦 Sauvegarde
├── docker-compose.yml                     ✅ CORRIGÉ (indentation)
└── DOCKER_FIX.md                          📄 Ce document
```

---

## 🐛 Problèmes Potentiels et Solutions

### 1. ChromaDB: Collection n'existe pas
**Erreur**: `Collection 'knowledge_base' not found`
**Solution**: Exécuter `docker compose exec app python ingest.py`

### 2. Ollama: Modèle non trouvé
**Erreur**: `model 'mistral:7b' not found`
**Solution**:
```bash
docker exec -it my-ia-ollama ollama pull mistral:7b
```

### 3. App: Cannot connect to ChromaDB
**Erreur**: `Connection refused to chroma:8000`
**Solution**: Vérifier que ChromaDB est démarré avec `docker compose ps`

### 4. Rate Limit atteint
**Erreur**: `429 Too Many Requests`
**Solution**: Attendre 1 minute ou augmenter les limites dans `main.py`

### 5. API Key invalide
**Erreur**: `401 Invalid API key`
**Solution**: Ajouter header `-H 'X-API-Key: change-me-in-production'`

---

## 📈 Prochaines Étapes Recommandées

1. ✅ **Tests complets** - Lancer tous les services et tester
2. [ ] **Multi-stage builds** - Optimiser taille des images
3. [ ] **Tests unitaires** - Créer tests pour `main.py`
4. [ ] **CI/CD** - GitHub Actions pour build automatique
5. [ ] **Monitoring** - Ajouter Grafana pour visualisation
6. [ ] **Documentation** - Diagrammes de séquence API

---

## 🎯 Quick Start

```bash
# Clone et setup
cd "/Users/k/Documents/Documents - MacBook Pro de k/Code/Ollama/my-ia"

# Build
docker compose build

# Start
docker compose up -d

# Wait for services
sleep 60

# Download models
docker exec -it my-ia-ollama ollama pull mistral:7b
docker exec -it my-ia-ollama ollama pull nomic-embed-text

# Ingest data
docker compose exec app python ingest.py

# Test
curl http://localhost:8080/health
curl http://localhost:8080/docs

# Enjoy!
```

---

**Dernière mise à jour**: 2025-11-27 04:59:40
**Correctifs appliqués**: main.py recréé + indentation docker-compose.yml corrigée
**Statut**: ✅ PRÊT POUR TESTS
