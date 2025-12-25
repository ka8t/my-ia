# Tests Admin - Documentation Technique

## Statut actuel (2025-12-25)

```
93 tests collectes
93 PASSED  ✓
0  FAILED  ✗
0  ERRORS  ✗
0  SKIPPED
```

### Corrections appliquées (v3 - FINAL)
1. `rate_limit_admin` ajouté dans `app/core/config.py`
2. `date=` corrigé en `day=` dans `dashboard/service.py:280`
3. Endpoint `/admin/dashboard` corrigé en `/admin/dashboard/overview`
4. Fixture `admin_token` génère JWT directement (évite conflit HTTP/DB)
5. Fixture `app` utilise `NullPool` pour isoler les connexions par test
6. Test `test_get_role_by_id` corrigé en `test_roles_contains_admin_role`

**Commande d'execution:**
```bash
docker-compose exec app python -m pytest tests/admin/ -v
```

---

## Table des matieres

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture des tests](#architecture-des-tests)
3. [Execution des tests](#execution-des-tests)
4. [Configuration technique](#configuration-technique)
5. [Plan de tests par module](#plan-de-tests-par-module)
6. [Erreurs connues et solutions](#erreurs-connues-et-solutions)
7. [Bonnes pratiques](#bonnes-pratiques)

---

## Vue d'ensemble

Les tests admin couvrent les 6 sous-modules de l'administration :

| Module | Service | Description |
|--------|---------|-------------|
| `users` | `AdminUserService` | CRUD utilisateurs, roles, statuts |
| `dashboard` | `DashboardService` | Statistiques et metriques |
| `bulk` | `BulkService` | Operations en masse |
| `export` | `ExportService` | Export CSV/JSON |
| `conversations` | `ConversationAdminService` | Gestion conversations |
| `config` | `ConfigService` | Configuration runtime |

### Contrainte technique importante

**Les modeles SQLAlchemy utilisent `UUID` PostgreSQL** qui n'est pas compatible avec SQLite.
Les tests doivent donc s'executer avec une vraie base PostgreSQL (via Docker).

---

## Architecture des tests

```
tests/
├── conftest.py                    # Fixtures globales (API client)
└── admin/
    ├── __init__.py
    ├── conftest.py                # Fixtures admin (DB session, users)
    ├── test_integration_admin.py  # Tests HTTP endpoints
    ├── test_admin_users_crud.py   # Tests CRUD utilisateurs
    ├── test_admin_users_security.py # Tests securite
    ├── test_admin_dashboard.py    # Tests statistiques
    ├── test_admin_bulk.py         # Tests operations masse
    ├── test_admin_export.py       # Tests export
    ├── test_admin_conversations.py # Tests conversations
    └── test_admin_config.py       # Tests configuration
```

### Types de tests

1. **Tests unitaires** : Testent les services avec mocks de la DB
2. **Tests d'integration** : Testent les services avec vraie DB PostgreSQL
3. **Tests HTTP** : Testent les endpoints via `httpx.AsyncClient`

---

## Execution des tests

### Prerequis

- Docker Compose en cours d'execution
- Containers `my-ia-app` et `my-ia-postgres` up

### Commandes d'execution

#### Dans Docker (recommande)

```bash
# Tous les tests admin
docker-compose exec app python -m pytest tests/admin/ -v

# Un seul fichier
docker-compose exec app python -m pytest tests/admin/test_admin_users_crud.py -v

# Une seule classe
docker-compose exec app python -m pytest tests/admin/test_admin_users_crud.py::TestAdminUserService -v

# Un seul test
docker-compose exec app python -m pytest tests/admin/test_admin_users_crud.py::TestAdminUserService::test_create_user -v

# Avec couverture
docker-compose exec app python -m pytest tests/admin/ -v --cov=app.features.admin --cov-report=html

# Tests rapides (sans slow)
docker-compose exec app python -m pytest tests/admin/ -v -m "not slow"

# Afficher les logs
docker-compose exec app python -m pytest tests/admin/ -v --log-cli-level=INFO
```

#### Depuis l'hote (copie prealable necessaire)

```bash
# Copier les tests dans le container
docker cp tests/admin my-ia-app:/code/tests/

# Executer
docker-compose exec -T app python -m pytest tests/admin/ -v --tb=short
```

### Container cible

| Container | Nom | Usage |
|-----------|-----|-------|
| Application | `my-ia-app` | Execution pytest |
| Database | `my-ia-postgres` | PostgreSQL pour tests |
| ChromaDB | `my-ia-chroma` | Tests RAG (optionnel) |

---

## Configuration technique

### Fichier `tests/admin/conftest.py`

```python
"""
Fixtures pour les tests Admin

IMPORTANT: Utilise PostgreSQL du container Docker, PAS SQLite.
Les modeles utilisent UUID PostgreSQL non compatible SQLite.
"""
import os
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Configuration asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop_policy():
    """Politique event loop par defaut"""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


# =============================================================================
# DATABASE FIXTURES - Utilise PostgreSQL Docker
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Session DB connectee au PostgreSQL Docker.
    Utilise la meme connexion que l'app.
    """
    from app.core.deps import get_db

    async for session in get_db():
        yield session


# =============================================================================
# APPLICATION FIXTURES
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def app():
    """Application FastAPI"""
    from app.main import app as fastapi_app
    yield fastapi_app


@pytest_asyncio.fixture(scope="function")
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Client HTTP async pour tests endpoints"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# =============================================================================
# AUTHENTIFICATION FIXTURES
# =============================================================================

@pytest_asyncio.fixture
async def admin_token(async_client: AsyncClient) -> str:
    """Token JWT admin pour tests authentifies"""
    accounts = [
        {"username": "admin@myia.local", "password": "admin123"},
        {"username": "test@example.com", "password": "password123"},
    ]

    for creds in accounts:
        response = await async_client.post(
            "/auth/jwt/login",
            data=creds,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if response.status_code == 200:
            return response.json().get("access_token", "")

    pytest.skip("Aucun compte admin disponible")


@pytest.fixture
def admin_headers(admin_token: str) -> dict:
    """Headers avec token admin"""
    return {"Authorization": f"Bearer {admin_token}"}
```

### Variables d'environnement requises

```bash
# Dans le container app (deja configure via docker-compose)
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/myia
```

---

## Plan de tests par module

### 1. AdminUserService (`test_admin_users_crud.py`)

| Test | Methode | Description |
|------|---------|-------------|
| `test_get_users` | `get_users()` | Liste avec pagination |
| `test_get_users_filter_role` | `get_users(role_id=)` | Filtre par role |
| `test_get_users_filter_active` | `get_users(is_active=)` | Filtre par statut |
| `test_get_users_search` | `get_users(search=)` | Recherche texte |
| `test_get_user_details` | `get_user_details()` | Details utilisateur |
| `test_get_user_not_found` | `get_user_details()` | 404 si inexistant |
| `test_create_user` | `create_user()` | Creation utilisateur |
| `test_create_user_duplicate` | `create_user()` | 409 si email existe |
| `test_update_user` | `update_user()` | Mise a jour |
| `test_change_role` | `change_role()` | Changement de role |
| `test_change_status` | `change_status()` | Activation/desactivation |
| `test_reset_password` | `reset_password()` | Reset mot de passe |
| `test_delete_user` | `delete_user()` | Suppression |

### 2. AdminUserService Securite (`test_admin_users_security.py`)

| Test | Description |
|------|-------------|
| `test_cannot_delete_self` | Admin ne peut pas se supprimer |
| `test_cannot_deactivate_self` | Admin ne peut pas se desactiver |
| `test_cannot_demote_self` | Admin ne peut pas se retrograder |
| `test_cannot_delete_last_admin` | Protection dernier admin |
| `test_cannot_demote_last_admin` | Protection dernier admin |

### 3. DashboardService (`test_admin_dashboard.py`)

| Test | Methode | Description |
|------|---------|-------------|
| `test_get_overview` | `get_overview()` | Vue complete |
| `test_get_user_stats` | `get_user_stats()` | Stats utilisateurs |
| `test_get_conversation_stats` | `get_conversation_stats()` | Stats conversations |
| `test_get_document_stats` | `get_document_stats()` | Stats documents |
| `test_get_system_stats` | `get_system_stats()` | Stats systeme |
| `test_get_usage_daily` | `get_usage_daily()` | Usage quotidien |
| `test_get_trends` | `get_trends()` | Tendances |

### 4. BulkService (`test_admin_bulk.py`)

| Test | Methode | Description |
|------|---------|-------------|
| `test_activate_users` | `activate_users()` | Activation en masse |
| `test_deactivate_users` | `deactivate_users()` | Desactivation en masse |
| `test_change_users_role` | `change_users_role()` | Changement role masse |
| `test_delete_users` | `delete_users()` | Suppression masse |
| `test_delete_conversations` | `delete_conversations()` | Suppression conversations |
| `test_delete_requires_confirm` | Tous | confirm=True obligatoire |
| `test_partial_success` | Tous | Resultat partiel OK |

### 5. ConversationAdminService (`test_admin_conversations.py`)

| Test | Methode | Description |
|------|---------|-------------|
| `test_get_conversations` | `get_conversations()` | Liste paginee |
| `test_filter_by_user` | `get_conversations(user_id=)` | Filtre user |
| `test_filter_by_mode` | `get_conversations(mode_id=)` | Filtre mode |
| `test_get_conversation_detail` | `get_conversation_detail()` | Details + messages |
| `test_delete_conversation` | `delete_conversation()` | Suppression |
| `test_delete_user_conversations` | `delete_user_conversations()` | Suppr. toutes convs user |
| `test_export_conversation` | `export_conversation()` | Export JSON |

### 6. ConfigService (`test_admin_config.py`)

| Test | Methode | Description |
|------|---------|-------------|
| `test_get_system_config` | `get_system_config()` | Config complete |
| `test_get_rag_config` | `get_rag_config()` | Config RAG |
| `test_get_timeouts_config` | `get_timeouts_config()` | Config timeouts |
| `test_update_rag_config` | `update_rag_config()` | Modification RAG |
| `test_update_timeouts_config` | `update_timeouts_config()` | Modification timeouts |
| `test_reload_config` | `reload_config()` | Reset runtime |
| `test_sensitive_not_exposed` | `get_system_config()` | Pas de secrets exposes |

### 7. Tests HTTP Integration (`test_integration_admin.py`)

| Test | Endpoint | Description |
|------|----------|-------------|
| `test_*_requires_auth` | `/admin/*` | 401 sans token |
| `test_list_users` | `GET /admin/users` | Liste users |
| `test_dashboard` | `GET /admin/dashboard` | Dashboard |
| `test_roles` | `GET /admin/roles` | Liste roles |
| `test_audit` | `GET /admin/audit` | Logs audit |
| `test_config` | `GET /admin/config` | Configuration |
| `test_conversations` | `GET /admin/conversations` | Conversations |

---

## Erreurs connues et solutions

### Erreur 1: UUID incompatible SQLite

```
sqlalchemy.exc.UnsupportedCompilationError:
Compiler can't render element of type UUID
```

**Cause** : Les modeles utilisent `sqlalchemy.dialects.postgresql.UUID`

**Solution** : Executer les tests dans Docker avec PostgreSQL

```bash
# CORRECT
docker-compose exec app python -m pytest tests/admin/ -v

# INCORRECT (SQLite local)
python -m pytest tests/admin/ -v
```

### Erreur 2: Event loop asyncpg

```
asyncpg.exceptions.InterfaceError:
cannot perform operation: another operation is in progress
```

**Cause** : Conflit entre TestClient (sync) et asyncpg (async)

**Solution** : Utiliser `httpx.AsyncClient` avec `ASGITransport`

```python
# CORRECT
from httpx import AsyncClient, ASGITransport

async with AsyncClient(
    transport=ASGITransport(app=app),
    base_url="http://test"
) as client:
    response = await client.get("/admin/users")

# INCORRECT
from fastapi.testclient import TestClient
client = TestClient(app)  # Conflit avec asyncpg
```

### Erreur 3: Methodes inexistantes

```
AttributeError: 'AdminUserRepository' has no attribute 'get_users'
```

**Cause** : Les tests appelaient des methodes qui n'existent pas

**Solution** : Verifier les vraies signatures dans les services

```python
# CORRECT
AdminUserService.get_users(db, limit=10, offset=0)

# INCORRECT
AdminUserRepository.get_users(db)  # N'existe pas
```

### Erreur 4: Token admin non valide

```
pytest.skip("Impossible d'obtenir un token admin")
```

**Cause** : Aucun compte admin avec credentials connus

**Solution** : Creer/verifier un compte admin dans la DB

```sql
-- Dans PostgreSQL Docker
UPDATE "user"
SET hashed_password = '$2b$12$...' -- bcrypt hash de 'admin123'
WHERE email = 'admin@myia.local';
```

---

## Bonnes pratiques

### 1. Isolation des tests

```python
@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Cree un user de test, supprime apres"""
    user = User(email=f"test_{uuid.uuid4().hex[:8]}@test.com", ...)
    db_session.add(user)
    await db_session.commit()

    yield user

    await db_session.delete(user)
    await db_session.commit()
```

### 2. Marqueurs pytest

```python
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    """Test async"""
    pass

@pytest.mark.slow
async def test_heavy_operation():
    """Test lent"""
    pass

@pytest.mark.integration
async def test_full_flow():
    """Test integration"""
    pass
```

### 3. Assertions claires

```python
# CORRECT
assert response.status_code == 200, f"Expected 200, got {response.status_code}"
assert "items" in data, "Response should contain 'items'"

# INCORRECT
assert response.status_code == 200
assert "items" in data
```

### 4. Nettoyage des donnees

```python
@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_data(db_session: AsyncSession):
    """Nettoie les donnees de test apres chaque test"""
    yield

    # Supprimer les users de test
    await db_session.execute(
        delete(User).where(User.email.like("test_%@test.com"))
    )
    await db_session.commit()
```

---

## Maintenance

### Mise a jour des tests

Lors de modifications des services admin :

1. Verifier les signatures des methodes dans les fichiers service
2. Mettre a jour les tests correspondants
3. Executer tous les tests avant commit

### Ajout de nouveaux tests

1. Creer le fichier dans `tests/admin/`
2. Importer les fixtures depuis `conftest.py`
3. Suivre la convention de nommage `test_<module>_<fonction>.py`
4. Documenter dans cette page

---

*Document genere le 2025-12-25*
*Auteur: KL*
