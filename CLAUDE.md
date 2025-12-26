IMPORTANT : SUIT CES RÈGLES À CHAQUE ÉTAPE DE GÉNÉRATION DE CODE. Relis ce fichier au début de chaque session. Appliquez systématiquement cette structure modulaire, scalable et maintenable pour tous les projets Python/FastAPI.

# Context : Projet "MY-IA API"
Je suis sous Macos Monterey. MacBook Pro 2015.
Intel core I5 2,7 
256 Go SSD interne
1 Go SSD externe
Je veux utiliser le minimum de ressources pour créer l'application et doit donc optimiser les ressources.

## Interaction
Tu dois toujours t'adresser à moi en Français

## Description
Application de Chatbot RAG avec gestion administrative poussée, authentification et observabilité.

## Stack Technique
- **Framework :** FastAPI (Python 3.10+)
- **Database (Relationnelle) :** PostgreSQL (via SQLAlchemy 2.0 + AsyncPG)
- **Database (Vectorielle) :** ChromaDB (HttpClient)
- **LLM / Embeddings :** Ollama (Mistral, Nomic-embed-text)
- **Auth :** FastAPI Users (JWT Strategy)
- **Ingestion :** Pipeline personnalisé (Unstructured.io + LangChain semantic chunking)
- **Monitoring :** Prometheus Client, SlowAPI (Rate Limiting)


NE JAMais mettre de logique métier dans main.py ou router.py.

Ce projet a migré d'un `main.py` monolithique vers une architecture modulaire.
Chaque feature est découpée comme suit
exemple dans le dossier `/app`
```
app/
├── main.py                        # Point d'entrée minimal
├── core/                          # Configuration centralisée
│   ├── config.py                  # pydantic-settings
│   └── deps.py                    # Injection de dépendances
├── common/                        # Code partagé
│   ├── utils/
│   │   ├── chroma.py              # search_context()
│   │   └── ollama.py              # get_embeddings(), generate_response()
│   ├── exceptions/http.py         # Custom HTTP exceptions
│   ├── schemas/base.py            # Base Pydantic models
│   └── metrics.py                 # Métriques Prometheus centralisées
└── features/                      # 🎯 Architecture modulaire
    ├── health/                    # ✅ Health check & metrics
    │   ├── router.py
    │   └── service.py
    ├── chat/                      # ✅ Chat conversationnel RAG
    │   ├── router.py
    │   ├── service.py
    │   └── schemas.py
    ├── ingestion/                 # ✅ Upload documents
    │   ├── router.py
    │   ├── service.py
    │   └── schemas.py
    ├── audit/                     # ✅ Audit logs
    │   ├── service.py
    │   └── repository.py
    └── admin/                     # ✅ CRUD admin (20+ endpoints)
        ├── router.py
        ├── service.py
        └── repository.py
```

### Pattern Feature (Standard Appliqué)

Chaque feature suit le pattern **Router → Service → Repository** :

```python
features/[nom]/
├── router.py       # FastAPI endpoints ONLY (GET/POST/PATCH/DELETE)
├── service.py      # Business logic (async)
├── repository.py   # Database operations (optionnel)
└── schemas.py      # Pydantic DTOs (optionnel)
```

Les documents Markdown (sauf README) doivent être stockés dans le dossier /docs
à la racine et organisés par type de documentation
- Générale
    - cahier des charges
    - évolutions
    - todos ...
- technique
    - installation
    - déploiement
    - maintenance ...

Les tests doivent être stockés dans le dossier /tests
à la racine et organisés de manière à pouvoir les exécuter individuellement ou tout l'ensemble.

## Contraintes Tests Unitaires

### Execution obligatoire dans Docker
```bash
# CORRECT - dans le container
docker-compose exec app python -m pytest tests/[module]/ -v

# INCORRECT - en local (incompatibilité UUID PostgreSQL/SQLite)
python -m pytest tests/
```

### Structure des tests
```
tests/
├── conftest.py              # Fixtures globales (si necessaire)
└── [feature]/
    ├── __init__.py
    ├── conftest.py          # Fixtures specifiques au module
    ├── test_[module]_xxx.py # Tests unitaires (Service direct)
    └── test_integration_[module].py  # Tests HTTP endpoints
```

### Fixtures OBLIGATOIRES dans conftest.py

```python
import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

# Event loop unique pour eviter conflits asyncpg
@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

# Session DB pour tests unitaires (Services)
@pytest_asyncio.fixture(scope="function")
async def db_session():
    from app.core.config import settings
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()
    await engine.dispose()

# App avec NullPool pour tests HTTP (OBLIGATOIRE pour eviter conflits asyncpg)
@pytest_asyncio.fixture(scope="function")
async def app():
    from app.core.config import settings
    from app.main import app as fastapi_app
    import app.db as db_module

    original_engine = db_module.engine
    original_session_maker = db_module.async_session_maker

    # NullPool = pas de pool = pas de conflit entre tests
    test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

    db_module.engine = test_engine
    db_module.async_session_maker = test_session_maker

    yield fastapi_app

    await test_engine.dispose()
    db_module.engine = original_engine
    db_module.async_session_maker = original_session_maker

# Token JWT genere DIRECTEMENT (pas via HTTP - evite conflit DB)
@pytest_asyncio.fixture(scope="module")
async def admin_token():
    import jwt
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.core.config import settings
    from app.models import User
    from app.features.auth.config import SECRET

    engine = create_async_engine(settings.database_url, pool_size=1, max_overflow=0)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.role_id == 1, User.is_active == True).limit(1)
        )
        admin = result.scalar_one_or_none()
        if not admin:
            await engine.dispose()
            pytest.skip("Aucun admin actif dans la DB")
        admin_id = str(admin.id)

    await engine.dispose()

    payload = {
        "sub": admin_id,
        "aud": ["fastapi-users:auth"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")
```

### Erreurs a eviter

| Erreur | Cause | Solution |
|--------|-------|----------|
| `UUID not supported` | SQLite en local | Executer dans Docker avec PostgreSQL |
| `another operation in progress` | Pool de connexions partage | Utiliser `NullPool` dans fixture `app` |
| `sentinel values mismatch` | Batch insert UUID | Commit un par un, pas en batch |
| `fixture not found` | Mauvais nom | Utiliser `db_session` (pas `test_db_session`) |
| Token HTTP echoue | Conflit DB lors du login | Generer JWT directement avec `jwt.encode()` |
| 404 sur endpoint | Mauvais chemin | Verifier le routeur avant d'ecrire le test |

### Template test unitaire (Service)

```python
"""
Tests pour [Module] Service
Execution: docker-compose exec app python -m pytest tests/[module]/ -v
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.[module].service import MonService

class TestMonService:
    @pytest.mark.asyncio
    async def test_ma_fonction(self, db_session: AsyncSession):
        """Description du test"""
        result = await MonService.ma_methode(db_session, param=valeur)
        assert result is not None
```

### Template test integration (HTTP)

```python
"""
Tests HTTP pour [Module]
Execution: docker-compose exec app python -m pytest tests/[module]/ -v
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

class TestMonEndpoint:
    async def test_endpoint_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401"""
        response = await async_client.get("/api/endpoint")
        assert response.status_code == 401

    async def test_endpoint_with_auth(self, async_client: AsyncClient, admin_headers: dict):
        """Endpoint avec auth retourne 200"""
        response = await async_client.get("/api/endpoint", headers=admin_headers)
        assert response.status_code == 200
```

### AVANT d'ecrire des tests
1. **Lire le router.py** pour connaitre les vrais endpoints (chemins exacts)
2. **Lire le service.py** pour connaitre les vraies signatures des methodes
3. **Lire les schemas.py** pour connaitre les vrais noms des champs Pydantic
4. **Verifier que les fixtures existent** dans conftest.py
5. **Ne JAMAIS utiliser SQLite** pour les tests (UUID PostgreSQL incompatible)
6. **Toujours utiliser NullPool** pour les tests d'integration HTTP


Vérification Finale
À CHAQUE réponse de code, confirmer :
✅ Structure features/ respectée
✅ main.py minimal 
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
1. **DRY** Pas de duplication de code qui viole le principe DRY (Don't Repeat Yourself).
2. **Asynchronisme :** Tout doit être `async/await`, surtout les appels DB et HTTP (Ollama).
3. **Typage :** Utiliser `typing` (List, Optional, Dict) et Pydantic strictement.
4. **Erreurs :** Toujours wrapper les appels externes dans des `try/except` avec logging approprié.
5. **Dépendances :** Utiliser l'injection de dépendance de FastAPI (`Depends()`) plutôt que des imports globaux.
6. **Admin :** Les routes admin doivent toujours vérifier le rôle `superuser` ou `admin`.
7. **Commit :** Indiquer KL comme auteur. Ne JAMAIS ajouter de références à Claude, Claude Code, ou Co-Authored-By dans les messages de commit.

## Conventions de Nommage
- Variables/Fonctions : `snake_case`
- Classes : `PascalCase`
- Constantes : `UPPER_CASE`

Pour les containers docker, on ne doit pas redémarrer ou les reconstruire si il y a un changement de code mais uniquement si cela est nécessaire, ajout/modification de libs systèmes, dépendances ....

Ne prends jamais d'initiatives d'optimisatations sans me présenter le pour et le contre. Sachant que le plus important est la maintenabilité, la clarté, la scalabilité.

Tu dois toujoujours suggérer les meilleurs pratiques de codage.

Tu dois toujours vérifier les dépendances et les conflits possibles entre elles.

Tu dois à chaque création ou modification de fichier que les lines-ending ne sont pas au format Windows.

Tu ne dois jamais nommer les champs d'une table avec le nom d'un type existant (ex: Date)

Tu dois toujours utiliser les contraintes techniques actuelles (os, docker, bdd ... ) pour créer et modifier les tests unitaires.

A chaque modification de code ou fonctionnalité frontend ou backend,  tu dois mettre à jour les tests unitaires et leurs dépendances si le backend est modifié et ensuite les tester.

Quand tu dois tester unitairement, demande moi toujours si je veux que je teste l'ensemble ou ce qui vient d'^tre créé ou modifié.

A chaque fonctionnalité pour un utilisateur, l'admin doit aussi pouvoir y accéder.



Ce fichier CLAUDE.md doit être la référence ABSOLUE pour tous vos projets Python. Relisez-le systématiquement au début de chaque génération de code.