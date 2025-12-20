# MY-IA - IA Personnelle avec Ollama + N8N

Stack complète d'IA conversationnelle avec interface web moderne et automatisation de workflows :
- 💬 **Interface Web** : Chat moderne type ChatGPT/Claude avec streaming en temps réel
- 🤖 **Ollama** : Serveur LLM local (Mistral, Llama, etc.)
- 🗄️ **ChromaDB** : Base vectorielle pour RAG (Retrieval Augmented Generation)
- ⚡ **FastAPI** : API REST pour l'IA avec rate limiting et métriques
- 🔄 **N8N** : Automatisation de workflows
- 🐘 **PostgreSQL** : Base de données pour N8N

## ✨ Nouveautés v2.0 - Système d'Ingestion Avancé

🚀 **Nouvelle architecture d'ingestion avec les meilleurs outils open-source 2025 :**
- 📚 **13 formats supportés** (vs 5) : PDF, DOCX, XLSX, PPTX, TXT, MD, HTML, images avec OCR
- 🧠 **Chunking sémantique** avec LangChain (respecte la structure des documents)
- 🔍 **Parsing intelligent** avec Unstructured.io (détection de tables, titres)
- ♻️ **Déduplication automatique** (hash SHA256, pas de réindexation inutile)
- 📊 **Métadonnées enrichies** (11 champs vs 1)
- 🖼️ **OCR intégré** (Tesseract pour images et PDFs scannés)
- ⚡ **Hot reload activé** - Modifiez le code sans rebuild !

👉 **[Voir la documentation complète](docs/INGESTION_V2.md)** | **[Changelog détaillé](docs/CHANGELOG_INGESTION_V2.md)**

## 🚀 Démarrage rapide

```bash
# 1. Lancer la configuration initiale (tout automatique!)
./scripts/setup.sh

# 2. Accéder aux interfaces
# Interface Chat:  http://localhost:3000  ⭐ NOUVEAU!
# API IA:          http://localhost:8080
# N8N:             http://localhost:5678
```

## 📋 Prérequis

- Docker 24.0+
- docker-compose 2.0+
- 8 GB RAM minimum (16 GB recommandé)
- 30 GB d'espace disque (incluant PostgreSQL et N8N)

## 🏗️ Architecture

```
┌─────────────┐
│  Frontend   │ (Interface Web Chat)
│   Nginx     │
└──────┬──────┘
       │
┌──────▼──────┐     ┌──────────────┐     ┌─────────────┐
│   FastAPI   │────▶│   ChromaDB   │     │   Ollama    │
│     App     │     │ (Vector DB)  │     │    (LLM)    │
└─────────────┘     └──────────────┘     └─────────────┘
      │                                          │
      │         ┌──────────────┐                 │
      └────────▶│     N8N      │◀────────────────┘
                │ (Automation) │
                └──────┬───────┘
                       │
                ┌──────▼───────┐
                │  PostgreSQL  │
                └──────────────┘
```

## 📚 Services déployés

| Service | Port | Description | URL |
|---------|------|-------------|-----|
| **Interface Chat** | 3000 | Interface web moderne type ChatGPT | http://localhost:3000 |
| **API** | 8080 | Interface IA avec RAG | http://localhost:8080 |
| **N8N** | 5678 | Automatisation de workflows | http://localhost:5678 |
| **Ollama** | 11434 | Serveur LLM | http://localhost:11434 |
| **ChromaDB** | 8000 | Base de données vectorielle | http://localhost:8000 |
| **PostgreSQL** | 5432 | Base de données N8N | Interne (exposé sur demande) |

### Identifiants par défaut

⚠️ **À CHANGER EN PRODUCTION!**

- **N8N**: admin / change-me-in-production
- **PostgreSQL**: n8n / n8n_password (Database: n8n)
- **API**: Header `X-API-Key: change-me-in-production`

### Note sur le premier démarrage

Si N8N ne démarre pas correctement (erreur de connexion DB), vous devrez peut-être créer la base de données manuellement :
```bash
docker exec my-ia-postgres createdb -U n8n n8n
```

## 📖 Documentation

### 📚 Guides disponibles

| Document | Description |
|----------|-------------|
| **[DEV_WORKFLOW.md](docs/DEV_WORKFLOW.md)** | 🔥 **À lire en premier !** Guide de développement avec hot reload |
| **[INGESTION_V2.md](docs/INGESTION_V2.md)** | Système d'ingestion avancé v2.0 (multi-formats, OCR, chunking sémantique) |
| **[CHANGELOG_INGESTION_V2.md](docs/CHANGELOG_INGESTION_V2.md)** | Détails techniques des nouveautés v2.0 |
| **[TODO.md](docs/TODO.md)** | Roadmap et tâches en cours |
| **[API.md](docs/API.md)** | Documentation complète de l'API REST |
| **[INSTALLATION.md](docs/INSTALLATION.md)** | Guide d'installation détaillé |
| **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** | Résolution de problèmes |
| **[TESTING.md](docs/TESTING.md)** | Tests et validation |
| **[CONTRIBUTING.md](docs/CONTRIBUTING.md)** | Guide de contribution |

### Ajouter vos données (v2 - Nouveau !)

**Via l'interface web :**
1. Accédez à http://localhost:3000
2. Cliquez sur "Ajouter documents"
3. Uploadez vos fichiers (PDF, DOCX, XLSX, PPTX, images, etc.)
4. L'indexation est automatique avec déduplication !

**En ligne de commande :**
1. Placez vos fichiers dans `./datasets/`
   - **Formats supportés v2** : PDF, DOCX, XLSX, PPTX, TXT, MD, HTML, JSONL, CSV, PNG, JPG

2. Lancez l'ingestion avancée :
```bash
# Système v2 (recommandé) avec chunking sémantique et OCR
docker compose exec app python ingest_v2.py

# Ancien système (legacy)
docker compose exec app python ingest.py
```

**API Upload :**
```bash
# Upload avec parsing avancé
curl -X POST http://localhost:8080/upload/v2 \
  -H "X-API-Key: change-me-in-production" \
  -F "file=@document.pdf"

# Upload haute résolution (meilleure qualité)
curl -X POST "http://localhost:8080/upload/v2?parsing_strategy=hi_res" \
  -H "X-API-Key: change-me-in-production" \
  -F "file=@complex_document.pdf"
```

### Créer des workflows N8N

1. Accédez à N8N: http://localhost:5678
2. Connectez-vous avec les identifiants
3. Consultez `./n8n/README.md` pour des exemples
4. Importez le workflow d'exemple: `./n8n/workflows/example-ai-processor.json`

### Exemples de workflows

- **Email Auto-responder** : Répondre aux emails avec l'IA
- **Document Processor** : Analyser et résumer des documents
- **Slack Bot** : Assistant IA dans Slack
- **Customer Support** : Automatiser le support client
- **Content Generator** : Générer du contenu automatiquement

## 🎯 Endpoints API

### ChatBot
```bash
curl -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -d '{"query":"Comment déployer ?"}'
```

### Assistant (orienté tâches)
```bash
curl -X POST http://localhost:8080/assistant \
  -H 'Content-Type: application/json' \
  -d '{"query":"Prépare un runbook de rollback"}'
```

### Streaming
```bash
curl -N -X POST http://localhost:8080/chat/stream \
  -H 'Content-Type: application/json' \
  -d '{"query":"Explique le RAG"}'
```

### Documentation complète
http://localhost:8080/docs

## 👨‍💻 Développement

### Hot Reload activé ⚡

**Modifiez le code sans rebuild !** Le serveur FastAPI redémarre automatiquement (2-3 secondes).

```bash
# Démarrer les services
docker compose up -d

# Modifier le code Python (app/*.py)
nano app/main.py
nano app/ingest_v2.py

# Voir le reload automatique
docker compose logs -f app
# → INFO: Detected file change... Reloading...
# → INFO: Application startup complete.

# Tester immédiatement !
curl http://localhost:8080/health
```

**Quand rebuild ?**
- ✅ **Jamais** pour les modifications Python
- ❌ **Seulement** pour nouvelles dépendances ou changements Docker

👉 **[Guide complet de développement](docs/DEV_WORKFLOW.md)**

### Workflow recommandé

1. **Modifier** le code dans `app/`
2. **Observer** les logs : `docker compose logs -f app`
3. **Tester** (reload auto en 2-3s)
4. **Itérer** jusqu'à satisfaction

## 🛠️ Commandes utiles

### Développement
```bash
# Logs en temps réel
docker compose logs -f app

# Restart rapide (2s)
docker compose restart app

# Shell dans le container
docker compose exec app bash

# Tester l'ingestion v2
docker compose exec app python ingest_v2.py
```

### Production
```bash
# Voir les logs
docker compose logs -f

# Logs d'un service spécifique
docker compose logs -f n8n

# Redémarrer un service
docker compose restart app

# Arrêter tout
docker compose down

# Backup complet
./scripts/backup.sh

# Restauration
./scripts/restore.sh ./backups/20240115-143022

# Tests
./scripts/test.sh

# Télécharger un nouveau modèle
docker exec -it $(docker ps -qf name=ollama) ollama pull mistral:7b

# Accéder à la base PostgreSQL
docker compose exec postgres psql -U n8n n8n
```

## 🔐 Sécurité (Production)

### 1. Changer les mots de passe

Éditez `docker-compose.yml`:
```yaml
environment:
  - POSTGRES_PASSWORD=<strong-password>
  - N8N_BASIC_AUTH_PASSWORD=<strong-password>
  - API_KEY=<strong-api-key>
```

### 2. Configurer HTTPS pour N8N

```yaml
n8n:
  environment:
    - N8N_PROTOCOL=https
    - N8N_HOST=your-domain.com
    - N8N_PORT=443
```

### 3. Limiter l'accès réseau

Modifier les `ports` en `expose` pour les services internes.

## 📊 Monitoring

- **Métriques Prometheus**: http://localhost:8080/metrics
- **Health check API**: http://localhost:8080/health
- **N8N Executions**: Interface N8N > Executions

## 💡 Exemples d'intégration N8N + IA

### 1. Webhook AI Processor
```javascript
// Node HTTP Request dans N8N
{
  "method": "POST",
  "url": "http://app:8080/chat",
  "body": {
    "query": "{{$json.question}}",
    "session_id": "n8n-{{$workflow.id}}"
  }
}
```

### 2. Email Auto-Response
1. Trigger: Email reçu
2. HTTP Request: Appel /chat avec le contenu de l'email
3. Gmail: Envoyer la réponse

### 3. Document Summarizer
1. Trigger: Fichier ajouté dans Google Drive
2. HTTP Request: Télécharger et envoyer à /assistant
3. Google Drive: Sauvegarder le résumé

## 🐛 Dépannage

### Service ne démarre pas
```bash
docker compose logs <service>
docker compose ps
docker compose restart <service>
```

### N8N ne se connecte pas à PostgreSQL
```bash
# Vérifier que PostgreSQL est "healthy"
docker compose ps postgres

# Vérifier les logs
docker compose logs postgres
docker compose logs n8n
```

### Reset complet de N8N
```bash
docker compose down
docker volume rm my-ia_n8n-data my-ia_postgres-data
docker compose up -d
```

### Réponses IA hors sujet
- Augmenter `TOP_K` dans docker-compose.yml
- Améliorer la qualité des données sources
- Réindexer: `docker compose exec app python ingest.py`

## 📝 Structure du projet

```
my-ia/
├── docker-compose.yml      # 6 services (+ frontend)
├── README.md              # Ce fichier
├── app/
│   ├── main.py            # API FastAPI + endpoints /upload/v2
│   ├── ingest.py          # Ingestion legacy (v1)
│   ├── ingest_v2.py       # ✨ Ingestion avancée v2 (Unstructured + LangChain)
│   ├── requirements.txt   # Dépendances Python
│   ├── Dockerfile         # Image avec hot reload activé
│   └── prompts/           # System prompts (chatbot, assistant)
├── frontend/              # Interface web Chat
│   ├── index.html         # UI moderne type ChatGPT
│   ├── js/app.js          # Logic avec upload v2
│   ├── css/styles.css     # Styles dark/light mode
│   └── Dockerfile         # Nginx Alpine
├── datasets/              # Vos données sources
│   ├── examples/          # Exemples fournis
│   └── procedures/        # Documentation procédures
├── docs/                  # 📚 Documentation complète
│   ├── DEV_WORKFLOW.md    # 🔥 Guide développement (hot reload)
│   ├── INGESTION_V2.md    # Nouveau système d'ingestion
│   ├── CHANGELOG_INGESTION_V2.md  # Détails techniques v2
│   ├── TODO.md            # Roadmap et tâches
│   ├── API.md             # Documentation API REST
│   ├── INSTALLATION.md    # Installation détaillée
│   ├── TROUBLESHOOTING.md # Résolution problèmes
│   ├── TESTING.md         # Tests et validation
│   └── CONTRIBUTING.md    # Guide contribution
├── n8n/
│   ├── workflows/         # Workflows N8N exportés
│   └── README.md          # Doc workflows
├── scripts/
│   ├── setup.sh           # Setup automatique complet
│   ├── backup.sh          # Backup (N8N + ChromaDB + code)
│   ├── restore.sh         # Restauration
│   └── test.sh            # Tests système
└── backups/               # Sauvegardes automatiques
```

## 🤝 Cas d'usage

### Support Client Automatisé
1. Client envoie un email
2. N8N reçoit l'email via Gmail Trigger
3. API IA analyse la question et génère une réponse
4. N8N envoie la réponse par email
5. Si complexe, créer un ticket dans Jira

### Génération de Rapports
1. N8N déclenché quotidiennement (Cron)
2. Récupère les données (Google Sheets, DB)
3. API Assistant génère le rapport
4. Envoie par email ou Slack

### Documentation Interactive
1. Webhook reçoit une question
2. API effectue le RAG sur la documentation
3. Retourne une réponse contextuelle
4. Log dans PostgreSQL pour analytics

## 🔗 Ressources

- [Documentation Ollama](https://ollama.ai/docs)
- [ChromaDB Docs](https://docs.trychroma.com/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [N8N Documentation](https://docs.n8n.io/)
- [N8N Community Workflows](https://n8n.io/workflows/)

## 📄 Licence

MIT

---

**Note**: Ce projet combine le meilleur de l'IA locale (Ollama + RAG) avec l'automatisation (N8N) pour créer des workflows intelligents sans dépendre de services cloud payants.
