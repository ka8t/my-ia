# Tests d'Intégration MY-IA

Ce document explique comment configurer et exécuter les tests d'intégration end-to-end.

## Prérequis

Les tests d'intégration nécessitent que les services suivants soient **en cours d'exécution** :

### 1. Ollama
```bash
# Vérifier qu'Ollama est en cours
curl http://localhost:11434/api/tags

# Démarrer Ollama si nécessaire
ollama serve

# Télécharger les modèles requis
ollama pull mistral:7b
ollama pull nomic-embed-text
```

### 2. ChromaDB
```bash
# Avec Docker Compose (recommandé)
docker compose up -d chroma

# Vérifier que ChromaDB est accessible
curl http://localhost:8000/api/v1/heartbeat
```

### 3. API MY-IA (optionnel)
```bash
# Si vous testez l'API déployée
docker compose up -d app
```

## Configuration

### Variables d'environnement

Les tests utilisent ces variables (définies dans `conftest.py`) :

```bash
export OLLAMA_HOST="http://localhost:11434"
export CHROMA_HOST="http://localhost:8000"
export API_KEY="test-api-key-12345"
export MODEL_NAME="mistral:7b"
export EMBED_MODEL="nomic-embed-text"
```

### Données de test

Pour les tests d'ingestion, vous pouvez créer des documents dans `datasets/` :

```bash
mkdir -p datasets
echo "# Test Document\n\nCe document teste le RAG." > datasets/test.md
```

## Exécution des tests

### Tous les tests d'intégration

```bash
pytest -m integration -v
```

### Tests d'intégration avec output détaillé

```bash
pytest -m integration -v -s
```

### Tests spécifiques

```bash
# Workflow complet
pytest tests/test_integration.py::TestEndToEndWorkflow -v

# Streaming
pytest tests/test_integration.py::TestStreamingWorkflow -v

# Performance
pytest tests/test_integration.py::TestPerformance -v
```

### Avec timeout custom

```bash
pytest -m integration -v --timeout=300
```

## Structure des tests

### TestEndToEndWorkflow
- `test_complete_rag_workflow` : Test du workflow complet RAG
- `test_assistant_mode_workflow` : Test du mode Assistant

**Ce qui est testé :**
1. Health check des services
2. Requête /chat avec API key
3. Vérification de la réponse
4. Vérification des sources retournées

### TestStreamingWorkflow
- `test_chat_streaming_e2e` : Test du streaming de bout en bout

**Ce qui est testé :**
1. Initiation du stream
2. Réception de chunks NDJSON
3. Accumulation de la réponse
4. Flag "done" final

### TestIngestionWorkflow
- `test_ingest_and_query_workflow` : Test ingestion → query

**Ce qui est testé :**
1. Existence de documents dans ChromaDB
2. Requête utilisant les documents
3. Sources dans la réponse

### TestErrorHandling
- `test_invalid_query_handling` : Query invalide
- `test_missing_api_key` : Sans API key
- `test_invalid_api_key` : Mauvaise API key

**Ce qui est testé :**
- Codes d'erreur appropriés (401, 422)
- Messages d'erreur corrects

### TestPerformance
- `test_chat_response_time` : Temps de réponse
- `test_concurrent_requests` : Requêtes concurrentes

**Ce qui est testé :**
- Temps de réponse < 2 minutes
- Support de requêtes concurrentes

### TestServicesIntegration
- `test_ollama_connection` : Connexion Ollama
- `test_chromadb_connection` : Connexion ChromaDB

**Ce qui est testé :**
- Accessibilité des services
- Endpoints de health check

## Debugging

### Logs détaillés

```bash
pytest -m integration -v -s --log-cli-level=DEBUG
```

### Capturer les prints

```bash
pytest -m integration -v -s
```

### Mode interactif en cas d'échec

```bash
pytest -m integration -v --pdb
```

## Problèmes courants

### ❌ "Ollama non disponible"

**Solution :**
```bash
# Vérifier qu'Ollama tourne
ps aux | grep ollama

# Démarrer Ollama
ollama serve

# Vérifier l'accessibilité
curl http://localhost:11434/api/tags
```

### ❌ "ChromaDB non disponible"

**Solution :**
```bash
# Vérifier le conteneur
docker ps | grep chroma

# Redémarrer ChromaDB
docker compose restart chroma

# Vérifier les logs
docker compose logs chroma
```

### ❌ "Timeout lors des tests"

**Causes possibles :**
- Modèle Ollama trop lent pour le hardware
- Ollama n'a pas de GPU
- Modèle non téléchargé

**Solutions :**
```bash
# Augmenter le timeout
pytest -m integration -v --timeout=600

# Utiliser un modèle plus petit
export MODEL_NAME="tinyllama"
ollama pull tinyllama

# Vérifier que le modèle est chargé
ollama list
```

### ❌ "Tests échouent mais services fonctionnent"

**Debug :**
```bash
# Tester manuellement l'API
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-api-key-12345" \
  -d '{"query":"Test","session_id":"debug"}'

# Vérifier les logs
docker compose logs app
```

## Métriques de performance

Les tests de performance affichent des métriques :

```
⏱️  Temps de réponse: 12.34s
🚦 Requêtes rate limited: 5/35
```

Ces métriques peuvent varier selon :
- Le hardware (CPU, RAM, GPU)
- Le modèle utilisé
- La charge du système

## CI/CD

Dans un environnement CI/CD, vous pouvez :

### Option 1 : Utiliser des services réels

```yaml
services:
  ollama:
    image: ollama/ollama
  chromadb:
    image: chromadb/chroma
```

### Option 2 : Mocker les services

```bash
# Exécuter seulement les tests unitaires en CI
pytest -m "not integration" -v
```

### Option 3 : Tests d'intégration conditionnels

```bash
# Skip si services non disponibles
pytest -m integration -v --skip-if-services-down
```

## Bonnes pratiques

1. **Isoler les tests** : Chaque test doit être indépendant
2. **Nettoyer après** : Supprimer les données de test créées
3. **Timeouts généreux** : Les tests d'intégration peuvent être lents
4. **Skip si services down** : Utiliser `pytest.skip()` si services indisponibles
5. **Logs clairs** : Afficher des messages utiles en cas d'échec

## Exemple de workflow complet

```bash
# 1. Démarrer les services
docker compose up -d ollama chroma

# 2. Attendre qu'ils soient prêts
sleep 10

# 3. Télécharger les modèles
docker compose exec ollama ollama pull mistral:7b
docker compose exec ollama ollama pull nomic-embed-text

# 4. Optionnel : Ingérer des documents de test
docker compose exec app python app/ingest.py

# 5. Lancer les tests
pytest -m integration -v

# 6. Nettoyer
docker compose down
```

## Monitoring des tests

Vous pouvez monitorer les tests avec :

```bash
# Génération de rapport HTML
pytest -m integration -v --html=report.html --self-contained-html

# Génération de rapport JSON
pytest -m integration -v --json-report --json-report-file=report.json
```

## Ressources

- [Documentation Ollama](https://ollama.ai/docs)
- [Documentation ChromaDB](https://docs.trychroma.com/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
