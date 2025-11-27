# MY-IA - IA Personnelle avec Ollama + N8N

Stack complète d'IA conversationnelle avec interface web et automatisation de workflows :
- 💬 **Interface Web** : Chat moderne type ChatGPT/Claude
- 🤖 **Ollama** : Serveur LLM local
- 🗄️ **ChromaDB** : Base vectorielle pour RAG
- ⚡ **FastAPI** : API REST pour l'IA
- 🔄 **N8N** : Automatisation de workflows
- 🐘 **PostgreSQL** : Base de données pour N8N

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
| **PostgreSQL** | 5432 | Base de données N8N | localhost:5432 |

### Identifiants par défaut

⚠️ **À CHANGER EN PRODUCTION!**

- **N8N**: admin / change-me-in-production
- **PostgreSQL**: n8n / n8n_password
- **API**: Header `X-API-Key: change-me-in-production`

## 📖 Documentation

### Ajouter vos données

1. Placez vos fichiers dans `./datasets/`:
   - Formats supportés: `.jsonl`, `.md`, `.txt`, `.pdf`, `.html`
   
2. Lancez l'ingestion:
```bash
docker compose exec app python ingest.py
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

## 🛠️ Commandes utiles

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
├── docker-compose.yml      # 5 services configurés
├── app/
│   ├── main.py            # API FastAPI (CORS activé pour N8N)
│   ├── ingest.py          # Ingestion de données
│   └── prompts/           # System prompts
├── datasets/              # Vos données
│   └── examples/          # Exemples fournis
├── n8n/
│   ├── workflows/         # Workflows N8N exportés
│   └── README.md          # Doc workflows
├── scripts/
│   ├── setup.sh           # Setup automatique
│   ├── backup.sh          # Backup complet (incluant N8N)
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
