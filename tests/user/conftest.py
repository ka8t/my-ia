"""
Fixtures pour les tests modules utilisateur

IMPORTANT: Utilise PostgreSQL du container Docker, PAS SQLite.
Les modeles utilisent UUID PostgreSQL non compatible SQLite.

Execution: docker-compose exec app python -m pytest tests/user/ -v
"""
import uuid
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool


# =============================================================================
# EVENT LOOP
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Event loop unique pour la session de tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# APPLICATION FIXTURE
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def app():
    """Application FastAPI avec engine de test isolé."""
    from app.core.config import settings
    from app.main import app as fastapi_app
    import app.db as db_module

    original_engine = db_module.engine
    original_session_maker = db_module.async_session_maker

    test_engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool
    )
    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

    db_module.engine = test_engine
    db_module.async_session_maker = test_session_maker

    yield fastapi_app

    await test_engine.dispose()
    db_module.engine = original_engine
    db_module.async_session_maker = original_session_maker


@pytest_asyncio.fixture(scope="function")
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Client HTTP async pour les tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Session DB connectée au PostgreSQL Docker."""
    from app.core.config import settings

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
# AUTHENTIFICATION FIXTURES - Utilisateur normal (pas admin)
# =============================================================================

@pytest_asyncio.fixture(scope="module")
async def user_token() -> str:
    """
    Génère un token JWT pour un utilisateur normal.
    Utilise un utilisateur existant ou en crée un.
    Scope=module pour éviter de recréer à chaque test.
    """
    import jwt
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from passlib.context import CryptContext
    from app.core.config import settings
    from app.models import User
    from app.features.auth.config import SECRET

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Créer une session DB séparée
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
        # Chercher un utilisateur normal actif
        result = await session.execute(
            select(User).where(
                User.role_id == 2,
                User.is_active == True
            ).limit(1)
        )
        user = result.scalar_one_or_none()

        if not user:
            # Créer un utilisateur de test permanent
            user = User(
                email="test_user_permanent@test.local",
                username="test_user_permanent",
                hashed_password=pwd_context.hash("TestUser123!"),
                first_name="Test",
                last_name="User Permanent",
                role_id=2,
                is_active=True,
                is_verified=True,
                is_superuser=False
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        user_id = str(user.id)

    await engine.dispose()

    # Générer le token JWT
    payload = {
        "sub": user_id,
        "aud": ["fastapi-users:auth"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


@pytest_asyncio.fixture(scope="module")
async def user_headers(user_token: str) -> dict:
    """Headers HTTP avec token utilisateur normal."""
    return {"Authorization": f"Bearer {user_token}"}


@pytest_asyncio.fixture(scope="module")
async def user_id() -> uuid.UUID:
    """Récupère l'ID de l'utilisateur de test."""
    from sqlalchemy import select
    from app.core.config import settings
    from app.models import User

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
        result = await session.execute(
            select(User).where(
                User.role_id == 2,
                User.is_active == True
            ).limit(1)
        )
        user = result.scalar_one_or_none()
        uid = user.id if user else None

    await engine.dispose()

    if not uid:
        pytest.skip("Aucun utilisateur de test dans la DB")

    return uid


# =============================================================================
# FIXTURES DE DONNÉES DE TEST
# =============================================================================

@pytest.fixture
def sample_conversation_data() -> dict:
    """Données pour créer une conversation de test."""
    return {
        "title": f"Test Conversation {uuid.uuid4().hex[:8]}",
        "mode_id": 1
    }


@pytest.fixture
def sample_chat_request() -> dict:
    """Données pour une requête de chat."""
    return {
        "query": "Bonjour, comment ça va ?"
    }
