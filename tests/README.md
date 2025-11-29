# Tests MY-IA

Ce répertoire contient tous les tests automatisés pour le projet MY-IA.

## Structure

```
tests/
├── conftest.py                    # Fixtures pytest globales
├── test_api_endpoints.py          # Tests des endpoints API
├── test_utility_functions.py      # Tests des fonctions utilitaires
├── test_ingest.py                 # Tests du système d'ingestion (à venir)
├── test_integration.py            # Tests d'intégration end-to-end (à venir)
└── README.md                      # Ce fichier
```

## Installation

Installer les dépendances de test :

```bash
pip install -r requirements-test.txt
```

## Lancer les tests

### Tous les tests

```bash
pytest
```

### Tests unitaires seulement

```bash
pytest -m unit
```

### Tests d'intégration seulement

```bash
pytest -m integration
```

### Tests d'un fichier spécifique

```bash
pytest tests/test_api_endpoints.py
```

### Tests d'une classe spécifique

```bash
pytest tests/test_api_endpoints.py::TestChatEndpoint
```

### Tests d'une fonction spécifique

```bash
pytest tests/test_api_endpoints.py::TestChatEndpoint::test_chat_with_valid_api_key
```

### Avec coverage

```bash
pytest --cov=app --cov-report=html
```

Le rapport HTML sera généré dans `htmlcov/index.html`.

### Tests en parallèle (plus rapide)

```bash
pip install pytest-xdist
pytest -n auto
```

### Tests avec output détaillé

```bash
pytest -v
pytest -vv  # Encore plus détaillé
```

### Arrêter au premier échec

```bash
pytest -x
```

### Mode watch (relance automatiquement quand le code change)

```bash
pip install pytest-watch
ptw
```

## Markers disponibles

Les tests sont marqués avec des catégories :

- `@pytest.mark.unit` - Tests unitaires rapides
- `@pytest.mark.integration` - Tests d'intégration avec services externes
- `@pytest.mark.slow` - Tests lents (> 1s)
- `@pytest.mark.api` - Tests des endpoints API
- `@pytest.mark.ingest` - Tests du système d'ingestion
- `@pytest.mark.rag` - Tests du système RAG

### Exemples d'utilisation des markers

```bash
# Tous les tests API
pytest -m api

# Tous les tests sauf les lents
pytest -m "not slow"

# Tests unitaires ET API
pytest -m "unit and api"

# Tests d'intégration OU lents
pytest -m "integration or slow"
```

## Configuration

La configuration de pytest est dans `pytest.ini` à la racine du projet.

Options importantes :
- `--cov-fail-under=70` : Échec si coverage < 70%
- `--tb=short` : Tracebacks courts pour meilleure lisibilité
- `-v` : Mode verbose par défaut

## Fixtures disponibles

Voir `conftest.py` pour la liste complète. Principales fixtures :

### Clients
- `client` : TestClient FastAPI synchrone
- `async_client` : httpx.AsyncClient pour tests async

### Données de test
- `sample_chat_request` : Requête chat valide
- `sample_document_text` : Texte de document pour tests d'ingestion
- `sample_embeddings` : Vecteur d'embeddings simulé
- `mock_chroma_results` : Résultats ChromaDB mockés
- `mock_ollama_response` : Réponse Ollama mockée

### Mocks
- `mock_ollama_embeddings` : Mock de get_embeddings()
- `mock_chroma_search` : Mock de search_context()
- `mock_ollama_generate` : Mock de generate_response()

### Configuration
- `test_api_key` : Clé API de test
- `test_ollama_host` : URL Ollama de test
- `test_chroma_host` : URL ChromaDB de test

## Écrire de nouveaux tests

### Template de test unitaire

```python
import pytest

@pytest.mark.unit
class TestMyFeature:
    """Tests pour ma fonctionnalité"""

    def test_feature_works(self, client, test_api_key):
        """Vérifie que la fonctionnalité fonctionne"""
        response = client.get("/my-endpoint", headers={"X-API-Key": test_api_key})

        assert response.status_code == 200
        assert "expected_field" in response.json()
```

### Template de test async

```python
import pytest

@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncFeature:
    """Tests pour fonctionnalité async"""

    async def test_async_function(self, mocker):
        """Vérifie une fonction async"""
        from app.main import my_async_function

        result = await my_async_function("test")

        assert result is not None
```

### Template de test d'intégration

```python
import pytest

@pytest.mark.integration
@pytest.mark.slow
class TestIntegration:
    """Tests d'intégration avec services externes"""

    async def test_end_to_end_workflow(self, async_client, test_api_key):
        """Test du workflow complet"""
        # Ingestion
        # ...

        # Query
        response = await async_client.post(
            "/chat",
            json={"query": "Test"},
            headers={"X-API-Key": test_api_key}
        )

        assert response.status_code == 200
```

## Bonnes pratiques

1. **Nommer clairement les tests** : Le nom doit décrire ce qui est testé
   - ✅ `test_chat_endpoint_rejects_invalid_api_key`
   - ❌ `test_1`

2. **Un test = une assertion principale**
   - Tester une seule chose par test
   - Utiliser des asserts multiples si nécessaire pour la même chose

3. **Utiliser les fixtures** : Éviter la duplication de code
   - Créer des fixtures réutilisables dans `conftest.py`

4. **Mocker les dépendances externes**
   - Ollama, ChromaDB, etc. doivent être mockés en tests unitaires
   - Tests d'intégration peuvent utiliser les vrais services

5. **Documenter les tests complexes**
   - Ajouter des docstrings expliquant le scénario

6. **Isoler les tests**
   - Chaque test doit être indépendant
   - Utiliser `autouse=True` fixtures pour reset l'état

## Debugging

### Afficher les prints pendant les tests

```bash
pytest -s
```

### Entrer en mode debug avec pdb

```bash
pytest --pdb
```

Ou ajouter dans le code :
```python
import pdb; pdb.set_trace()
```

### Voir les variables locales en cas d'échec

```bash
pytest -l
```

### Augmenter la verbosité des logs

```bash
pytest --log-cli-level=DEBUG
```

## CI/CD

Les tests sont exécutés automatiquement via GitHub Actions à chaque push/PR.

Voir `.github/workflows/tests.yml` pour la configuration.

## Coverage

Le coverage minimum requis est de 70%.

Vérifier le coverage actuel :
```bash
pytest --cov=app --cov-report=term-missing
```

Identifier les lignes non couvertes :
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Ressources

- [Documentation pytest](https://docs.pytest.org/)
- [Documentation pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Documentation pytest-mock](https://pytest-mock.readthedocs.io/)
- [Guide coverage.py](https://coverage.readthedocs.io/)
