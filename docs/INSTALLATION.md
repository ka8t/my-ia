# Guide d'Installation MY-IA

Guide complet pour installer et déployer MY-IA sur votre infrastructure.

## Prérequis

### Matériel Recommandé

**Configuration Minimale (CPU uniquement)** :
- CPU : 4 cores minimum
- RAM : 8 GB minimum (12 GB recommandé)
- Stockage : 20 GB libre
- Performances : 1-3 minutes par requête

**Configuration Optimale (avec GPU)** :
- CPU : 4+ cores
- RAM : 16 GB+
- GPU : NVIDIA avec 8 GB+ VRAM (CUDA) ou Apple Silicon M1/M2 (Metal)
- Stockage : 30 GB libre
- Performances : 5-30 secondes par requête

### Logiciels Requis

- **Docker** : version 20.10+
- **Docker Compose** : version 2.0+
- **Git** : pour cloner le projet
- **curl** : pour les tests

## Installation Rapide

### 1. Cloner le Projet

```bash
git clone https://github.com/votre-repo/my-ia.git
cd my-ia
```

### 2. Configuration

Créez un fichier `.env` à la racine du projet :

```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer les variables
nano .env
```

Variables importantes :

```env
# Modèles LLM
MODEL_NAME=llama3.2:1b       # Modèle compact et rapide
# MODEL_NAME=mistral:7b      # Plus puissant mais plus lent
EMBED_MODEL=nomic-embed-text

# Sécurité
API_KEY=changez-moi-en-production

# N8N
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=changez-moi
```

### 3. Lancement avec Script

**Linux/Mac** :
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

**Windows** :
```cmd
scripts\setup.bat
```

Le script va :
1. Créer les volumes Docker
2. Lancer tous les services
3. Télécharger les modèles LLM
4. Ingérer les données d'exemple
5. Tester l'installation

### 4. Vérification

```bash
# Vérifier l'état des services
docker compose ps

# Tester l'API
curl http://localhost:8080/health
```

## Installation Manuelle

Si vous préférez installer étape par étape :

### Étape 1 : Lancer les Services

```bash
docker compose up -d
```

Services démarrés :
- **PostgreSQL** : Port 5432 (interne)
- **N8N** : Port 5678
- **ChromaDB** : Port 8000
- **Ollama** : Port 11434
- **FastAPI** : Port 8080

### Étape 2 : Télécharger les Modèles

```bash
# Modèle LLM principal (choisir l'un des deux)
docker exec my-ia-ollama ollama pull llama3.2:1b    # Rapide (1.3 GB)
# docker exec my-ia-ollama ollama pull mistral:7b  # Puissant (4.4 GB)

# Modèle d'embeddings (requis)
docker exec my-ia-ollama ollama pull nomic-embed-text
```

**Temps de téléchargement** :
- llama3.2:1b : ~2-5 minutes
- mistral:7b : ~10-20 minutes
- nomic-embed-text : ~1 minute

### Étape 3 : Ingérer les Données

```bash
# Indexer les documents dans ChromaDB
docker compose exec app python ingest.py
```

Cela va :
- Lire les fichiers dans `/datasets`
- Générer les embeddings
- Stocker dans ChromaDB

### Étape 4 : Tester

```bash
# Test sans RAG
curl -X POST http://localhost:8080/test \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-me-in-production' \
  -d '{"query":"Bonjour"}'

# Test avec RAG
curl -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: change-me-in-production' \
  -d '{"query":"Comment installer MY-IA?"}'
```

## Configuration Avancée

### Changer de Modèle LLM

Éditez `docker-compose.yml` :

```yaml
app:
  environment:
    - MODEL_NAME=mistral:7b  # ou llama3.2:1b
```

Puis :

```bash
# Télécharger le nouveau modèle
docker exec my-ia-ollama ollama pull mistral:7b

# Redémarrer l'app
docker compose restart app
```

### Augmenter les Timeouts

Pour les modèles lents sur CPU, les timeouts sont déjà configurés à 600 secondes (10 minutes).

Si besoin, éditez `app/main.py` :

```python
async with httpx.AsyncClient(timeout=900.0) as client:  # 15 minutes
```

### Activer le GPU

**NVIDIA GPU (Linux)** :

```yaml
# docker-compose.yml
services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

**Apple Silicon (Mac)** :

Le GPU est automatiquement utilisé via Metal.

## Ajouter des Données

### Formats Supportés

MY-IA supporte 3 formats de documents :

1. **Markdown** (`.md`) - Recommandé
2. **Texte** (`.txt`)
3. **JSONL** (`.jsonl`) - Format structuré

### Ajouter un Document

```bash
# Créer votre document
echo "# Mon Document
Contenu de mon document..." > datasets/mon-doc.md

# Réindexer
docker compose exec app python ingest.py
```

### Format JSONL

```jsonl
{"text": "Contenu du document 1", "metadata": {"source": "doc1.md", "tags": ["tag1", "tag2"]}}
{"text": "Contenu du document 2", "metadata": {"source": "doc2.md", "tags": ["tag3"]}}
```

Voir [datasets/README.md](../datasets/README.md) pour plus de détails.

## Accès aux Services

Une fois installé, accédez aux interfaces :

- **API FastAPI** : http://localhost:8080
- **Documentation API** : http://localhost:8080/docs
- **N8N** : http://localhost:5678
  - User : `admin`
  - Password : Celui défini dans `.env`
- **Prometheus Metrics** : http://localhost:8080/metrics

## Désinstallation

Pour supprimer complètement MY-IA :

```bash
# Arrêter et supprimer les conteneurs
docker compose down

# Supprimer les volumes (ATTENTION : perte de données)
docker compose down -v

# Supprimer les images
docker rmi my-ia_app chromadb/chroma ollama/ollama n8nio/n8n
```

## Prochaines Étapes

- [Guide d'Utilisation](USAGE.md) - Apprendre à utiliser MY-IA
- [Documentation API](API.md) - Référence des endpoints
- [Dépannage](TROUBLESHOOTING.md) - Résoudre les problèmes courants

## Support

Problèmes d'installation ? Consultez :
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- [Issues GitHub](https://github.com/votre-repo/my-ia/issues)
