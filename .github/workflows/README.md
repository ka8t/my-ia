# CI/CD Workflows

Ce répertoire contient les workflows GitHub Actions pour MY-IA.

## Workflows disponibles

### 🧪 tests.yml

Workflow principal qui exécute tous les tests et checks de qualité.

**Déclenché sur:**
- Push sur `main` ou `develop`
- Pull requests vers `main` ou `develop`

**Jobs:**

1. **Lint & Format Check**
   - Vérification du formatage (Black)
   - Vérification de l'ordre des imports (isort)
   - Linting du code (Flake8)

2. **Unit Tests**
   - Tests unitaires sur Python 3.10, 3.11, 3.12
   - Génération du rapport de coverage
   - Upload vers Codecov

3. **Integration Tests**
   - Démarrage de ChromaDB en service
   - Installation d'Ollama
   - Pull des modèles (tinyllama pour rapidité)
   - Exécution des tests d'intégration

4. **Docker Build Test**
   - Build de l'image app
   - Build de l'image frontend
   - Cache pour optimisation

5. **Security Scan**
   - Scan des dépendances (Safety)
   - Analyse de sécurité du code (Bandit)

6. **Coverage Report**
   - Génération du rapport HTML
   - Upload comme artifact
   - Commentaire sur PR avec coverage

## Configuration requise

### Secrets GitHub

Aucun secret requis pour les tests de base.

Optionnel pour coverage:
- `CODECOV_TOKEN` : Token Codecov (si compte privé)

### Variables d'environnement

Les workflows utilisent ces variables:

```yaml
OLLAMA_HOST: http://localhost:11434
CHROMA_HOST: http://localhost:8000
MODEL_NAME: tinyllama  # Modèle léger pour CI
EMBED_MODEL: nomic-embed-text
```

## Optimisations

### Cache

Les workflows utilisent le cache GitHub Actions pour:
- Packages pip Python
- Layers Docker (buildx cache)

Cela accélère significativement les builds suivants.

### Modèles

Pour le CI, on utilise `tinyllama` au lieu de `mistral:7b`:
- Plus rapide à télécharger (~600MB vs ~4GB)
- Plus rapide à exécuter
- Suffisant pour valider la logique

## Statut des checks

### Checks obligatoires

Pour qu'un PR soit mergeable:
- ✅ Lint doit passer
- ✅ Unit tests doivent passer
- ✅ Docker build doit réussir

### Checks informatifs

Ces checks peuvent échouer sans bloquer:
- ℹ️ Integration tests (services peuvent être instables)
- ℹ️ Security scan (warnings seulement)
- ℹ️ Coverage (informatif)

## Timeouts

| Job | Timeout | Raison |
|-----|---------|--------|
| Lint | 5 min | Rapide |
| Unit Tests | 10 min | Tests mockés |
| Integration Tests | 20 min | Pull modèles + tests réels |
| Docker Build | 15 min | Multi-stage builds |
| Security | 5 min | Scans rapides |

## Exemples de sortie

### ✅ Succès

```
✓ Lint & Format Check (1m 23s)
✓ Unit Tests - Python 3.11 (2m 45s)
✓ Integration Tests (8m 12s)
✓ Docker Build Test (4m 56s)
✓ Security Scan (1m 08s)
✓ Coverage Report (2m 33s)
```

### ❌ Échec

```
✓ Lint & Format Check (1m 23s)
✗ Unit Tests - Python 3.11 (2m 45s)
  → 3 tests failed in test_api_endpoints.py
✓ Docker Build Test (4m 56s)
```

## Debugging

### Voir les logs détaillés

1. Aller sur l'onglet "Actions" du repo
2. Cliquer sur le workflow run
3. Cliquer sur le job qui a échoué
4. Voir les logs détaillés de chaque step

### Re-runner un job

1. Aller sur le workflow run
2. Cliquer "Re-run jobs"
3. Choisir "Re-run failed jobs" ou "Re-run all jobs"

### Logs locaux vs CI

Les workflows utilisent les mêmes commandes que localement:

```bash
# Local
pytest -m unit -v

# CI
- run: pytest -m unit -v
```

## Ajout de nouveaux workflows

### Template de base

```yaml
name: Mon Workflow

on:
  push:
    branches: [ main ]

jobs:
  mon-job:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: |
          pip install -r requirements.txt
          # Vos commandes
```

### Bonnes pratiques

1. **Nommer clairement** : Nom de job descriptif
2. **Cacher les dépendances** : Utiliser `actions/cache`
3. **Fail-fast matrix** : `fail-fast: false` pour tester toutes les versions
4. **Timeouts** : Définir `timeout-minutes`
5. **Artifacts** : Uploader les rapports importants

## Notifications

### Échec de workflow

Par défaut, GitHub envoie un email au:
- Auteur du commit qui a causé l'échec
- Mainteneurs du repo

### Configuration Slack (optionnel)

Ajouter un step de notification:

```yaml
- name: Notify Slack
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    webhook-url: ${{ secrets.SLACK_WEBHOOK }}
```

## Métriques

### Durée moyenne

Sur hardware GitHub Actions standard:

| Job | Durée typique |
|-----|---------------|
| Lint | ~1-2 min |
| Unit Tests | ~2-3 min |
| Integration | ~8-12 min |
| Docker Build | ~4-6 min |
| Security | ~1-2 min |

**Total: ~20-30 minutes**

### Optimisations possibles

- ✅ Cache pip (économie: 30-60s)
- ✅ Cache Docker (économie: 2-4 min)
- ✅ Parallélisation des jobs
- ⏳ Self-hosted runners (plus rapides)

## Troubleshooting

### "Ollama download timeout"

Augmenter le timeout:
```yaml
- run: ollama pull tinyllama
  timeout-minutes: 15  # Au lieu de 10
```

### "ChromaDB not accessible"

Vérifier le health check:
```yaml
services:
  chromadb:
    options: >-
      --health-cmd "curl -f http://localhost:8000/api/v1/heartbeat"
      --health-interval 10s
```

### "Tests pass locally but fail in CI"

Causes communes:
- Chemins de fichiers absolus vs relatifs
- Variables d'environnement manquantes
- Services non démarrés
- Différences Python version

Debug:
```yaml
- run: |
    echo "Python: $(python --version)"
    echo "Env: $OLLAMA_HOST"
    curl -v http://localhost:11434/api/tags
```

## Ressources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Available Actions](https://github.com/marketplace?type=actions)
