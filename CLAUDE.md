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

NE JAMais mettre de logique métier dans main.py ou router.py.

Ce projet est en cours de migration d'un `main.py` monolithique vers une architecture modulaire :
- `/app/routers` : Définition des endpoints (fichiers séparés par domaine : `chat.py`, `admin.py`, `auth.py`).
- `/app/services` : Logique métier pure (ex: `ChatService`, `IngestionService`).
- `/app/models` : Modèles SQLAlchemy.
- `/app/schemas` : Modèles Pydantic (DTOs).
- `/app/core` : Configuration, Sécurité, Dépendances globales.

Si la migration est terminée :
Vérification Finale
À CHAQUE réponse de code, confirmer :
✅ Structure features/ respectée
✅ main.py minimal (<50 lignes)
✅ Type hints partout
✅ Tests unitaires écrits
✅ Docstrings présentes
✅ Logger utilisé (pas print)
✅ Dependencies injectées (si utilisée)

## Améliorations : Modulaire, Scalable, Maintenable
1. Découpage des Routes (Modularité)
Actuellement, plus de 60% de ton fichier main.py est occupé par les routes /admin. Action : Crée un dossier routers/ et déplace le code.
2. Injection de Dépendances (Scalabilité & Testabilité)
Tu utilises des variables globales comme chroma_client ou ingestion_pipeline initialisées au début du fichier. Problème : Si la connexion échoue au démarrage, toute l'app plante. Difficile à tester (mocker). Solution : Utilise lru_cache ou le système de dépendance FastAPI.
3. Gestion asynchrone de l'ingestion (Performance)
La route /upload fait : await ingestion_pipeline.ingest_file(...). Problème : Si le fichier est gros, la requête HTTP va timeout (le client attendra indéfiniment). Cela bloque un "worker" FastAPI. Solution : Utiliser BackgroundTasks de FastAPI (simple) ou Celery (robuste).
4. Generic Repository Pattern (Maintenabilité)
Les routes Admin (get_roles, create_role, update_role, etc.) répètent la même logique CRUD 10 fois. Solution : Crée une classe générique.

## Directives de Code
1. **Asynchronisme :** Tout doit être `async/await`, surtout les appels DB et HTTP (Ollama).
2. **Typage :** Utiliser `typing` (List, Optional, Dict) et Pydantic strictement.
3. **Erreurs :** Toujours wrapper les appels externes dans des `try/except` avec logging approprié.
4. **Dépendances :** Utiliser l'injection de dépendance de FastAPI (`Depends()`) plutôt que des imports globaux.
5. **Admin :** Les routes admin doivent toujours vérifier le rôle `superuser` ou `admin`.

## Conventions de Nommage
- Variables/Fonctions : `snake_case`
- Classes : `PascalCase`
- Constantes : `UPPER_CASE`

Ce fichier CLAUDE.md doit être la référence ABSOLUE pour tous vos projets Python. Relisez-le systématiquement au début de chaque génération de code.