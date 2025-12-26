"""
Fixtures pour les tests Geo

Execution: docker-compose exec app python -m pytest tests/geo/ -v
"""
import asyncio
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


# =============================================================================
# CONFIGURATION ASYNCIO
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Event loop unique pour toute la session de tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# APPLICATION FIXTURE
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def app():
    """Application FastAPI avec engine de test isole."""
    from app.core.config import settings
    from app.main import app as fastapi_app
    import app.db as db_module
    from sqlalchemy.pool import NullPool

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
    """Session de base de donnees connectee au PostgreSQL Docker."""
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
# AUTHENTIFICATION FIXTURES
# =============================================================================

@pytest_asyncio.fixture(scope="module")
async def admin_token() -> str:
    """Genere un token JWT pour un admin directement."""
    import jwt
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.core.config import settings
    from app.models import User
    from app.features.auth.config import SECRET

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
            select(User).where(User.role_id == 1, User.is_active == True).limit(1)
        )
        admin = result.scalar_one_or_none()

        if not admin:
            await engine.dispose()
            pytest.skip("Aucun compte admin actif dans la DB")

        admin_id = str(admin.id)

    await engine.dispose()

    payload = {
        "sub": admin_id,
        "aud": ["fastapi-users:auth"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


@pytest_asyncio.fixture(scope="module")
async def admin_headers(admin_token: str) -> dict:
    """Headers HTTP avec token admin."""
    return {"Authorization": f"Bearer {admin_token}"}
