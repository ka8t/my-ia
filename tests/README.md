# Tests MY-IA v2.0

Suite de tests pour MY-IA avec support des fonctionnalités v2.0.

## 📋 Structure des tests

```
tests/
├── conftest.py                    # Configuration pytest et fixtures globales
├── fixtures/                      # Données de test
│   ├── documents/                # Fichiers de test (TXT, PDF, DOCX, etc.)
│   ├── images/                   # Images pour tests OCR
│   └── generate_test_files.py   # Script de génération de fixtures
│
├── test_api_endpoints.py         # Tests de tous les endpoints API
├── test_ingest_v2.py             # Tests système d'ingestion v2.0
└── README.md                     # Ce fichier
```

## 🚀 Démarrage rapide

### 1. Installation des dépendances de test

```bash
# Installer pytest et dépendances
pip install pytest pytest-asyncio pytest-mock pytest-cov httpx

# Installer les dépendances pour générer les fixtures
pip install reportlab python-docx openpyxl python-pptx Pillow
```

### 2. Générer les fichiers de test

```bash
# Générer tous les fichiers de test (PDF, DOCX, XLSX, PPTX, images)
cd tests/fixtures
python generate_test_files.py
```

### 3. Lancer les tests

```bash
# Tous les tests
pytest

# Tests avec verbosité
pytest -v

# Tests avec couverture de code
pytest --cov=app --cov-report=html

# Tests spécifiques
pytest tests/test_api_endpoints.py      # Tests API
pytest tests/test_ingest_v2.py          # Tests ingestion v2

# Tests par marker
pytest -m api                           # Seulement tests API
pytest -m ingest_v2                     # Seulement tests ingestion v2
pytest -m unit                          # Seulement tests unitaires
pytest -m integration                   # Seulement tests d'intégration
```

## 🏷️ Markers disponibles

- `@pytest.mark.unit` - Tests unitaires (rapides)
- `@pytest.mark.integration` - Tests d'intégration (plus lents)
- `@pytest.mark.slow` - Tests lents
- `@pytest.mark.ingest_v2` - Tests système d'ingestion v2.0
- `@pytest.mark.api` - Tests endpoints API
- `@pytest.mark.upload_v2` - Tests endpoint /upload/v2
- `@pytest.mark.smoke` - Tests de fumée critiques

## 📦 Fixtures disponibles

Voir `conftest.py` pour la liste complète des fixtures.

Principaux fixtures :
- `client` - Client FastAPI de test (avec API key configurée)
- `test_api_key` - Clé API de test
- `test_ollama_host` - URL Ollama de test
- `test_chroma_host` - URL ChromaDB de test

## 🧪 Tests par endpoint

### API Endpoints (`test_api_endpoints.py`)

Tous les endpoints de l'application sont testés:
- `GET /health` - Santé de l'application
- `GET /metrics` - Métriques Prometheus
- `GET /` - Endpoint racine
- `POST /chat` - Chat avec RAG
- `POST /assistant` - Mode assistant
- `POST /chat/stream` - Chat streaming
- `POST /test` - Test sans RAG
- `POST /upload` - Upload v1 (legacy)
- `POST /upload/stream` - Upload avec streaming v1
- `POST /upload/v2` - Upload v2 avec Unstructured

### Ingestion v2.0 (`test_ingest_v2.py`)

Tests pour le système d'ingestion avancé:
- **DocumentDeduplicator** - Hash et détection de duplicates
- **MetadataExtractor** - Extraction de métadonnées enrichies
- **SemanticChunker** - Découpage sémantique avec LangChain
- **DocumentParser** - Parsing multi-format avec Unstructured
- **EmbeddingGenerator** - Génération d'embeddings
- **AdvancedIngestionPipeline** - Pipeline complet d'ingestion

## 📊 Couverture de code

```bash
# Générer le rapport HTML
pytest --cov=app --cov-report=html

# Ouvrir le rapport
open htmlcov/index.html
```

## 🔧 Configuration

Le fichier `pytest.ini` contient la configuration par défaut:
- Couverture de code minimale: 20%
- Rapports: HTML + terminal
- Markers: strict mode activé

## 💡 Notes

- **Python 3.13**: Les tests utilisent des mocks pour ChromaDB et Unstructured car ces librairies ne sont pas compatibles avec Python 3.13
- **Ollama**: Les tests API qui nécessitent Ollama acceptent soit 200 (succès) soit 500 (Ollama indisponible)
- **ChromaDB**: Les tests d'intégration nécessitent ChromaDB en cours d'exécution

---

Pour plus de détails, voir la documentation dans chaque fichier de test.
