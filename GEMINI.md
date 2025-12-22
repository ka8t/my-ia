IMPORTANT : SUIT CES RÈGLES À CHAQUE ÉTAPE DE GÉNÉRATION DE CODE. Relis ce fichier au début de chaque session. Appliquez systématiquement cette structure modulaire, scalable et maintenable pour tous les projets Python/FastAPI.

# Context : Projet "MY-IA API"


## Description
Application de Chatbot RAG avec gestion administrative poussée, authentification et observabilité.

## Stack Technique
- **Framework :** FastAPI (Python 3.10+)
- **Database (Relationnelle) :** PostgreSQL (via SQLAlchemy 2.0 + AsyncPG)
- **Database (Vectorielle) :** ChromaDB (Client persistant)
- **LLM / Embeddings :** Ollama (Mistral, Nomic-embed-text)
- **Auth :** FastAPI Users (JWT Strategy)
- **Ingestion :** Pipeline personnalisé (Unstructured.io + LangChain semantic chunking)
- **Monitoring :** Prometheus Client, SlowAPI (Rate Limiting)

## Architecture & Structure (Cible)
projet/
├── main.py              # SEULEMENT: app = FastAPI(); app.include_router(...)
├── Dockerfile           # Multi-stage
├── docker-compose.yml   # DB/Redis/Celery
├── app/
│   ├── core/config.py   # pydantic-settings (.env)
│   ├── core/deps.py     # get_db(), get_redis()
│   ├── common/          # Librairies partagées UNIQUEMENT
│   │   ├── utils/       # validators, loggers
│   │   ├── exceptions/  # Custom HTTPException
│   │   └── schemas/     # Base Pydantic models
│   └── features/        # UNE feature = 1 dossier
│       ├── user/
│       │   ├── router.py     # @router.get/post ONLY
│       │   ├── service.py    # Business logic
│       │   ├── repository.py # DB ops
│       │   └── models.py     # SQLAlchemy + Pydantic
│       └── auth/             # Même structure
├── tests/              # Pytest >80% coverage
└── docs/


Ce projet est en cours de migration d'un `main.py` monolithique vers une architecture modulaire :
- `/app/routers` : Définition des endpoints (fichiers séparés par domaine : `chat.py`, `admin.py`, `auth.py`).
- `/app/services` : Logique métier pure (ex: `ChatService`, `IngestionService`).
- `/app/models` : Modèles SQLAlchemy.
- `/app/schemas` : Modèles Pydantic (DTOs).
- `/app/core` : Configuration, Sécurité, Dépendances globales.


Vérification Finale
À CHAQUE réponse de code, confirmer :
✅ Structure features/ respectée
✅ Type hints partout
✅ Tests unitaires écrits
✅ Docstrings présentes
# ✅ Logger utilisé (pas print)
# ✅ Dependencies injectées (si utilisée)


## Conventions de Nommage
- Variables/Fonctions : `snake_case`
- Classes : `PascalCase`
- Constantes : `UPPER_CASE`

Ce fichier gemini.md doit être la référence ABSOLUE pour tous vos projets Python. Relis-le systématiquement au début de chaque génération de code.