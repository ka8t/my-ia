"""
Fixtures pour les tests Admin

IMPORTANT: Utilise PostgreSQL du container Docker, PAS SQLite.
Les modeles utilisent UUID PostgreSQL non compatible SQLite.

Execution: docker-compose exec app python -m pytest tests/admin/ -v
"""
import os
import uuid
import asyncio
from typing import AsyncGenerator, List
from datetime import datetime

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Configuration pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


# =============================================================================
# CONFIGURATION ASYNCIO - Event Loop pour toutes les fixtures
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """
    Cree un event loop unique pour toute la session de tests.
    Resout les conflits asyncpg avec pytest-asyncio.
    Compatible avec fixtures scope=module et scope=function.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# APPLICATION FIXTURE - avec engine de test isolé
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def app():
    """
    Fixture de l'application FastAPI avec engine de test isolé.
    Crée un nouvel engine pour chaque test pour éviter les conflits asyncpg.
    """
    from app.core.config import settings
    from app.main import app as fastapi_app
    import app.db as db_module

    # Sauvegarder l'engine original
    original_engine = db_module.engine
    original_session_maker = db_module.async_session_maker

    # Créer un nouvel engine avec pool_class=NullPool pour éviter les conflits
    from sqlalchemy.pool import NullPool
    test_engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool  # Pas de pool = pas de conflit
    )
    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

    # Remplacer dans le module db
    db_module.engine = test_engine
    db_module.async_session_maker = test_session_maker

    yield fastapi_app

    # Restaurer l'engine original et fermer l'engine de test
    await test_engine.dispose()
    db_module.engine = original_engine
    db_module.async_session_maker = original_session_maker


@pytest_asyncio.fixture(scope="function")
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """
    Client HTTP async pour les tests.
    Utilise ASGITransport pour communiquer directement avec l'app.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# =============================================================================
# DATABASE FIXTURES - PostgreSQL Docker
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Session de base de donnees connectee au PostgreSQL Docker.
    Cree une nouvelle connexion pour eviter les conflits d'event loop.
    """
    from app.core.config import settings

    # Creer un engine et session independants pour les tests
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True
    )

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()

    await engine.dispose()


# =============================================================================
# AUTHENTIFICATION FIXTURES
# =============================================================================

@pytest_asyncio.fixture(scope="module")
async def admin_token() -> str:
    """
    Génère un token JWT pour un admin directement (sans HTTP).
    Utilise sa propre session DB séparée pour éviter le conflit asyncpg.
    Scope=module pour éviter de recréer le token à chaque test.
    """
    import jwt
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.core.config import settings
    from app.models import User
    from app.features.auth.config import SECRET

    # Créer une session DB séparée pour cette fixture uniquement
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=1,
        max_overflow=0
    )
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_factory() as session:
        # Chercher un admin dans la DB
        result = await session.execute(
            select(User).where(User.role_id == 1, User.is_active == True).limit(1)
        )
        admin = result.scalar_one_or_none()

        if not admin:
            await engine.dispose()
            pytest.skip("Aucun compte admin actif dans la DB")

        admin_id = str(admin.id)

    # Fermer l'engine AVANT de retourner le token
    await engine.dispose()

    # Générer le token JWT directement
    payload = {
        "sub": admin_id,
        "aud": ["fastapi-users:auth"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    token = jwt.encode(payload, SECRET, algorithm="HS256")

    return token


@pytest_asyncio.fixture(scope="module")
async def admin_headers(admin_token: str) -> dict:
    """Headers HTTP avec token admin"""
    return {"Authorization": f"Bearer {admin_token}"}


# =============================================================================
# FIXTURES UTILISATEURS DE TEST
# =============================================================================

@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    """
    Recupere ou cree un utilisateur admin pour les tests.
    """
    from sqlalchemy import select
    from app.models import User

    # Chercher un admin existant
    result = await db_session.execute(
        select(User).where(User.role_id == 1).limit(1)
    )
    admin = result.scalar_one_or_none()

    if admin:
        return admin

    pytest.skip("Aucun utilisateur admin dans la DB")


@pytest_asyncio.fixture
async def admin_user_id(db_session: AsyncSession) -> uuid.UUID:
    """
    Recupere l'ID d'un utilisateur admin pour les tests.
    """
    from sqlalchemy import select
    from app.models import User

    result = await db_session.execute(
        select(User).where(User.role_id == 1).limit(1)
    )
    admin = result.scalar_one_or_none()

    if admin:
        return admin.id

    pytest.skip("Aucun utilisateur admin dans la DB")


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> AsyncGenerator:
    """
    Cree un utilisateur de test temporaire.
    Supprime apres le test.
    """
    from app.models import User
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    unique_id = uuid.uuid4().hex[:8]

    user = User(
        email=f"testuser_{unique_id}@test.local",
        username=f"testuser_{unique_id}",
        hashed_password=pwd_context.hash("Test123!"),
        full_name="Test User",
        role_id=2,  # user role
        is_active=True,
        is_verified=True,
        is_superuser=False
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    yield user

    # Cleanup
    try:
        await db_session.delete(user)
        await db_session.commit()
    except Exception:
        await db_session.rollback()


@pytest_asyncio.fixture
async def multiple_users(db_session: AsyncSession) -> AsyncGenerator[List, None]:
    """
    Cree plusieurs utilisateurs de test.
    Supprime apres le test.
    Note: Cree les users un par un pour eviter le probleme de sentinel UUID.
    """
    from app.models import User
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    users = []

    for i in range(5):
        unique_id = uuid.uuid4().hex[:8]
        user = User(
            email=f"multiuser_{unique_id}@test.local",
            username=f"multiuser_{unique_id}",
            hashed_password=pwd_context.hash("Test123!"),
            full_name=f"Test User {i}",
            role_id=2,
            is_active=True,
            is_verified=(i % 2 == 0),
            is_superuser=False
        )
        db_session.add(user)
        # Commit un par un pour eviter le batch insert avec UUID
        await db_session.commit()
        await db_session.refresh(user)
        users.append(user)

    yield users

    # Cleanup
    for user in users:
        try:
            await db_session.delete(user)
            await db_session.commit()
        except Exception:
            await db_session.rollback()


# =============================================================================
# FIXTURES ROLES ET MODES
# =============================================================================

@pytest_asyncio.fixture
async def test_roles(db_session: AsyncSession):
    """
    Verifie que les roles existent.
    """
    from sqlalchemy import select
    from app.models import Role

    result = await db_session.execute(select(Role))
    roles = result.scalars().all()

    if not roles:
        pytest.skip("Aucun role dans la DB - executer les migrations")

    return roles


@pytest_asyncio.fixture
async def test_conversation_modes(db_session: AsyncSession):
    """
    Verifie que les modes de conversation existent.
    """
    from sqlalchemy import select
    from app.models import ConversationMode

    result = await db_session.execute(select(ConversationMode))
    modes = result.scalars().all()

    if not modes:
        pytest.skip("Aucun mode de conversation dans la DB")

    return modes


# =============================================================================
# FIXTURES DONNEES DE TEST
# =============================================================================

@pytest.fixture
def sample_user_data() -> dict:
    """Donnees pour creer un utilisateur de test"""
    unique_id = uuid.uuid4().hex[:8]
    return {
        "email": f"sampleuser_{unique_id}@test.local",
        "username": f"sampleuser_{unique_id}",
        "password": "SampleUser123!",
        "full_name": "Sample User",
        "role_id": 2,
        "is_active": True,
        "is_verified": False
    }


@pytest.fixture
def sample_conversation_data() -> dict:
    """Donnees pour creer une conversation de test"""
    return {
        "title": f"Test Conversation {uuid.uuid4().hex[:8]}",
        "mode_id": 1
    }
