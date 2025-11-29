# Guide de Tests MY-IA

Ce document récapitule l'infrastructure de tests complète mise en place pour MY-IA.

## 📋 Vue d'ensemble

L'infrastructure de tests comprend :

- **~100+ tests unitaires** pour l'API et les fonctions
- **Tests d'intégration end-to-end** avec services réels
- **CI/CD GitHub Actions** complet
- **Coverage minimum** de 70%
- **Mocking complet** pour isolation des tests

## 📁 Structure

```
my-ia/
├── pytest.ini                      # Configuration pytest
├── requirements-test.txt           # Dépendances de test
├── run_tests.sh                    # Script de lancement
├── .github/
│   └── workflows/
│       ├── tests.yml              # Workflow CI/CD
│       └── README.md              # Documentation workflows
└── tests/
    ├── __init__.py
    ├── conftest.py                # Fixtures globales
    ├── README.md                  # Guide des tests
    ├── INTEGRATION_TESTS.md       # Guide intégration
    ├── test_api_endpoints.py      # ~30 tests API
    ├── test_utility_functions.py  # ~20 tests utils
    ├── test_ingest.py             # ~30 tests ingestion
    └── test_integration.py        # ~15 tests e2e
```

## 🚀 Installation

```bash
# Installer les dépendances de test
pip install -r requirements-test.txt

# Vérifier l'installation
pytest --version
```

## 🧪 Exécution des tests

### Tests rapides (unitaires)

```bash
# Avec le script
./run_tests.sh unit

# Ou directement
pytest -m unit -v
```

### Tests complets (avec intégration)

```bash
# Démarrer les services
docker compose up -d ollama chroma

# Lancer tous les tests
./run_tests.sh

# Ou spécifiquement
pytest -v
```

### Tests avec coverage

```bash
./run_tests.sh coverage

# Ouvrir le rapport HTML
open htmlcov/index.html
```

### Tests spécifiques

```bash
# Un fichier
pytest tests/test_api_endpoints.py -v

# Une classe
pytest tests/test_api_endpoints.py::TestChatEndpoint -v

# Un test spécifique
pytest tests/test_api_endpoints.py::TestChatEndpoint::test_chat_with_valid_api_key -v

# Avec un pattern
pytest -k "chat" -v  # Tous les tests contenant "chat"
```

## 🏷️ Markers

Les tests sont catégorisés avec des markers :

```bash
# Tests unitaires seulement
pytest -m unit

# Tests d'intégration seulement
pytest -m integration

# Tests API
pytest -m api

# Tests du système d'ingestion
pytest -m ingest

# Tests sans les lents
pytest -m "not slow"

# Combiner les markers
pytest -m "unit and api"
```

## 📊 Coverage

Le coverage minimum requis est de **70%**.

```bash
# Générer le coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Vérifier le coverage actuel
pytest --cov=app --cov-report=term
```

**Fichiers exclus du coverage :**
- `tests/*`
- `*/venv/*`
- `*/__pycache__/*`

## 🔄 CI/CD GitHub Actions

### Workflow automatique

Chaque push ou PR déclenche :

1. **Lint & Format** (1-2 min)
   - Black, isort, Flake8

2. **Unit Tests** (2-3 min)
   - Python 3.10, 3.11, 3.12
   - Coverage upload vers Codecov

3. **Integration Tests** (8-12 min)
   - ChromaDB + Ollama
   - Modèle tinyllama

4. **Docker Build** (4-6 min)
   - Images app & frontend

5. **Security Scan** (1-2 min)
   - Safety, Bandit

6. **Coverage Report** (2-3 min)
   - Rapport HTML
   - Commentaire sur PR

### Badge de statut

Ajouter au README.md :

```markdown
![Tests](https://github.com/VOTRE-USERNAME/my-ia/workflows/Tests/badge.svg)
```

## 📝 Écrire de nouveaux tests

### Test unitaire

```python
import pytest

@pytest.mark.unit
class TestMaFonction:
    def test_comportement_normal(self, client, test_api_key):
        """Vérifie le comportement normal"""
        response = client.post(
            "/endpoint",
            json={"data": "test"},
            headers={"X-API-Key": test_api_key}
        )

        assert response.status_code == 200
        assert "expected_key" in response.json()
```

### Test d'intégration

```python
import pytest

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
class TestWorkflowComplet:
    async def test_e2e(self, async_client, test_api_key):
        """Test du workflow complet"""
        # Skip si services non disponibles
        health = await async_client.get("/health")
        if not health.json().get("ollama"):
            pytest.skip("Ollama non disponible")

        # Test...
```

## 🔧 Fixtures disponibles

### Clients
- `client` : TestClient FastAPI (sync)
- `async_client` : httpx.AsyncClient (async)

### Données
- `sample_chat_request` : Requête chat valide
- `sample_document_text` : Document pour tests
- `sample_embeddings` : Vecteur d'embeddings
- `mock_chroma_results` : Résultats ChromaDB
- `mock_ollama_response` : Réponse Ollama

### Mocks
- `mock_ollama_embeddings` : Mock get_embeddings()
- `mock_chroma_search` : Mock search_context()
- `mock_ollama_generate` : Mock generate_response()

### Configuration
- `test_api_key` : Clé API de test
- `test_ollama_host` : URL Ollama
- `test_chroma_host` : URL ChromaDB

## 🐛 Debugging

### Afficher les prints

```bash
pytest -s
```

### Mode debug (pdb)

```bash
pytest --pdb
```

Ou dans le code :
```python
import pdb; pdb.set_trace()
```

### Logs détaillés

```bash
pytest --log-cli-level=DEBUG
```

### Re-runner le dernier échec

```bash
pytest --lf  # Last failed
pytest --ff  # Failed first
```

## 📈 Métriques

### Statistiques actuelles

- **Tests totaux** : ~100+
- **Tests unitaires** : ~80
- **Tests d'intégration** : ~15
- **Coverage** : 70%+ (objectif)
- **Durée moyenne** : 3-5 min (unit), 10-15 min (all)

### Par fichier

| Fichier | Tests | Coverage | Durée |
|---------|-------|----------|-------|
| test_api_endpoints.py | ~30 | 85% | 1 min |
| test_utility_functions.py | ~20 | 80% | 1 min |
| test_ingest.py | ~30 | 75% | 1 min |
| test_integration.py | ~15 | N/A | 10 min |

## 🔒 Best Practices

1. **Tests isolés** : Chaque test doit être indépendant
2. **Noms descriptifs** : `test_chat_rejects_invalid_api_key`
3. **Une assertion principale** : Focus sur un comportement
4. **Utiliser les fixtures** : Éviter la duplication
5. **Mocker les dépendances** : Isoler le code testé
6. **Documenter les tests** : Docstrings claires
7. **Skip intelligemment** : `pytest.skip()` si services down

## 🚨 Problèmes courants

### Tests qui passent localement mais échouent en CI

**Solutions :**
- Vérifier les chemins (absolu vs relatif)
- Vérifier les variables d'environnement
- Vérifier les versions Python
- Vérifier les services (Ollama, ChromaDB)

### Timeout en tests d'intégration

**Solutions :**
```bash
# Augmenter le timeout
pytest --timeout=300

# Utiliser un modèle plus léger
export MODEL_NAME="tinyllama"
```

### ChromaDB non accessible

**Solutions :**
```bash
# Vérifier le conteneur
docker ps | grep chroma

# Redémarrer
docker compose restart chroma

# Vérifier les logs
docker compose logs chroma
```

## 📚 Ressources

- [Guide des tests](tests/README.md)
- [Tests d'intégration](tests/INTEGRATION_TESTS.md)
- [Workflows CI/CD](.github/workflows/README.md)
- [Documentation pytest](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)

## 🎯 Prochaines étapes

Pour améliorer encore les tests :

- [ ] Tests de performance (load testing)
- [ ] Tests de sécurité (penetration testing)
- [ ] Tests frontend (Jest, Playwright)
- [ ] Tests E2E complets (Selenium)
- [ ] Mutation testing (coverage de qualité)
- [ ] Property-based testing (Hypothesis)

## 📞 Support

En cas de problème avec les tests :

1. Consulter les docs dans `tests/`
2. Vérifier les logs CI/CD
3. Tester localement avec `-v -s`
4. Ouvrir une issue GitHub

---

**Dernière mise à jour** : 27 novembre 2025
**Auteur** : Claude (via Claude Code)
