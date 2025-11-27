# Guide de Contribution MY-IA

Merci de votre intérêt pour contribuer à MY-IA ! Ce guide vous aidera à démarrer.

## Table des Matières

- [Code de Conduite](#code-de-conduite)
- [Comment Contribuer](#comment-contribuer)
- [Configuration de l'Environnement](#configuration-de-lenvironnement)
- [Standards de Code](#standards-de-code)
- [Process de Pull Request](#process-de-pull-request)
- [Idées de Contributions](#idées-de-contributions)

---

## Code de Conduite

En participant à ce projet, vous acceptez de respecter notre code de conduite :

- Soyez respectueux et professionnel
- Acceptez les critiques constructives
- Concentrez-vous sur ce qui est le mieux pour la communauté
- Faites preuve d'empathie envers les autres membres

---

## Comment Contribuer

### Signaler un Bug

1. **Vérifier les issues existantes** : https://github.com/votre-repo/my-ia/issues
2. **Créer une nouvelle issue** avec :
   - Titre clair et descriptif
   - Description détaillée du problème
   - Étapes pour reproduire
   - Comportement attendu vs actuel
   - Logs et captures d'écran si pertinent
   - Environnement (OS, Docker version, etc.)

### Proposer une Nouvelle Fonctionnalité

1. **Créer une issue** de type "Feature Request"
2. **Décrire** :
   - Le problème que cela résout
   - La solution proposée
   - Les alternatives considérées
   - Impact sur l'existant

### Améliorer la Documentation

La documentation est aussi importante que le code !

- Corriger les fautes
- Clarifier les explications
- Ajouter des exemples
- Traduire dans d'autres langues

---

## Configuration de l'Environnement

### 1. Fork et Clone

```bash
# Fork le projet sur GitHub
# Puis cloner votre fork
git clone https://github.com/votre-username/my-ia.git
cd my-ia
```

### 2. Installer les Dépendances

```bash
# Lancer l'environnement de développement
docker compose up -d

# Télécharger les modèles
docker exec my-ia-ollama ollama pull llama3.2:1b
docker exec my-ia-ollama ollama pull nomic-embed-text
```

### 3. Créer une Branche

```bash
git checkout -b feature/ma-nouvelle-fonctionnalite
# ou
git checkout -b fix/correction-bug-123
```

---

## Standards de Code

### Python

**Style** : Suivre [PEP 8](https://pep8.org/)

**Formatage** :
```bash
# Installer black et flake8
pip install black flake8

# Formater le code
black app/

# Vérifier le style
flake8 app/
```

**Conventions** :
- Maximum 88 caractères par ligne (black)
- Type hints pour les fonctions publiques
- Docstrings pour les fonctions et classes

**Exemple** :
```python
async def generate_response(
    query: str,
    system_prompt: str,
    context: Optional[List[Dict[str, Any]]] = None,
    stream: bool = False
) -> str:
    """
    Génère une réponse via Ollama.

    Args:
        query: Question de l'utilisateur
        system_prompt: Prompt système à utiliser
        context: Contexte RAG optionnel
        stream: Activer le streaming

    Returns:
        La réponse générée par le LLM

    Raises:
        HTTPException: Si erreur lors de la génération
    """
    # ...
```

### Tests

**Ajouter des tests** pour toutes les nouvelles fonctionnalités.

```python
# tests/test_main.py
import pytest
from app.main import app

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
```

**Exécuter les tests** :
```bash
docker compose exec app pytest
```

### Documentation

- **Markdown** pour tous les documents
- **Docstrings** pour le code Python
- **Commentaires** pour les parties complexes uniquement

---

## Process de Pull Request

### 1. Avant de Soumettre

**Checklist** :
- [ ] Le code suit les standards (PEP 8)
- [ ] Les tests passent
- [ ] La documentation est à jour
- [ ] Les commits sont clairs et descriptifs
- [ ] La branche est à jour avec `main`

**Formater et tester** :
```bash
# Formater
black app/

# Linter
flake8 app/

# Tests
docker compose exec app pytest

# Build
docker compose build app
```

### 2. Commits

**Format** : Suivre [Conventional Commits](https://www.conventionalcommits.org/)

```bash
# Exemples
git commit -m "feat: add streaming support for /assistant endpoint"
git commit -m "fix: correct timeout handling in generate_response"
git commit -m "docs: update API.md with new endpoints"
git commit -m "refactor: simplify ChromaDB connection logic"
git commit -m "test: add tests for rate limiting"
```

**Types** :
- `feat`: Nouvelle fonctionnalité
- `fix`: Correction de bug
- `docs`: Documentation uniquement
- `style`: Formatage (pas de changement de code)
- `refactor`: Refactoring (ni feat ni fix)
- `test`: Ajout ou modification de tests
- `chore`: Maintenance (dépendances, config, etc.)

### 3. Soumettre la PR

```bash
git push origin feature/ma-nouvelle-fonctionnalite
```

Sur GitHub :
1. Créer une Pull Request
2. Remplir le template
3. Lier l'issue concernée

**Template PR** :
```markdown
## Description
Brève description de ce que fait cette PR

## Type de Changement
- [ ] Bug fix
- [ ] Nouvelle fonctionnalité
- [ ] Breaking change
- [ ] Documentation

## Tests
- [ ] Tests ajoutés/mis à jour
- [ ] Tous les tests passent

## Checklist
- [ ] Code formaté (black)
- [ ] Lint OK (flake8)
- [ ] Documentation à jour
- [ ] Commit message clair
```

### 4. Review

- Soyez patient et réceptif aux commentaires
- Répondez aux questions
- Faites les modifications demandées
- Re-push sur la même branche

---

## Idées de Contributions

### Fonctionnalités Prioritaires

**Backend** :
- [ ] Support de modèles multimodaux (images)
- [ ] Système de cache pour les embeddings
- [ ] WebSocket pour le streaming
- [ ] Authentification OAuth2
- [ ] Multi-tenancy (plusieurs utilisateurs)

**RAG** :
- [ ] Support de PDF, DOCX, XLSX
- [ ] Chunking intelligent (semantic splitting)
- [ ] Reranking des résultats
- [ ] Metadata filtering avancé
- [ ] Hybrid search (BM25 + embeddings)

**Infrastructure** :
- [ ] Kubernetes manifests
- [ ] Helm chart
- [ ] CI/CD GitHub Actions
- [ ] Tests d'intégration automatisés
- [ ] Monitoring avec Grafana

**Documentation** :
- [ ] Tutoriels vidéo
- [ ] Exemples d'intégration (React, Vue, etc.)
- [ ] Traductions (EN, ES, DE)
- [ ] Architecture decision records (ADRs)

### Quick Wins (Faciles)

- Corriger les fautes de frappe
- Améliorer les messages d'erreur
- Ajouter des exemples dans la doc
- Créer des scripts utilitaires
- Améliorer les logs

### Bonnes Premières Issues

Cherchez le label `good first issue` sur GitHub :
https://github.com/votre-repo/my-ia/labels/good%20first%20issue

---

## Architecture du Projet

```
my-ia/
├── app/                      # Application FastAPI
│   ├── main.py              # API principale
│   ├── ingest.py            # Ingestion de données
│   ├── prompts/             # System prompts
│   └── requirements.txt
│
├── datasets/                 # Données pour RAG
│   ├── examples/
│   └── procedures/
│
├── docs/                     # Documentation
│   ├── INSTALLATION.md
│   ├── API.md
│   ├── TROUBLESHOOTING.md
│   └── CONTRIBUTING.md
│
├── scripts/                  # Scripts utilitaires
│   ├── setup.sh
│   ├── test.sh
│   ├── backup.sh
│   └── restore.sh
│
├── tests/                    # Tests
│   └── test_main.py
│
├── docker-compose.yml        # Configuration Docker
└── README.md                 # Documentation principale
```

---

## Stack Technique

- **Backend** : Python 3.11, FastAPI, Pydantic
- **LLM** : Ollama (llama3.2, mistral)
- **Vector DB** : ChromaDB
- **Embeddings** : nomic-embed-text
- **Automation** : N8N
- **Database** : PostgreSQL (pour N8N)
- **Monitoring** : Prometheus
- **Rate Limiting** : slowapi

---

## Questions ?

- **Discord** : (à créer)
- **Issues** : https://github.com/votre-repo/my-ia/issues
- **Discussions** : https://github.com/votre-repo/my-ia/discussions

Merci de contribuer à MY-IA ! 🚀
