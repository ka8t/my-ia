"""
Fixtures pour les tests Admin Documents.

Execution: docker-compose exec app python -m pytest tests/admin_documents/ -v
"""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import User, Document, DocumentVisibility
from app.features.auth.config import SECRET


@pytest.fixture(scope="session")
def event_loop():
    """Event loop unique."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def app():
    """App FastAPI avec NullPool pour tests."""
    from app.main import app as fastapi_app
    import app.db as db_module

    original_engine = db_module.engine
    original_session_maker = db_module.async_session_maker

    test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

    db_module.engine = test_engine
    db_module.async_session_maker = test_session_maker

    yield fastapi_app

    await test_engine.dispose()
    db_module.engine = original_engine
    db_module.async_session_maker = original_session_maker


@pytest_asyncio.fixture(scope="function")
async def async_client(app):
    """Client HTTP async."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(scope="module")
async def admin_token():
    """Token JWT pour un admin."""
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


@pytest_asyncio.fixture(scope="module")
async def user_token():
    """Token JWT pour un utilisateur non-admin."""
    engine = create_async_engine(settings.database_url, pool_size=1, max_overflow=0)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Chercher un utilisateur non-admin
        result = await session.execute(
            select(User).where(User.role_id != 1, User.is_active == True).limit(1)
        )
        user = result.scalar_one_or_none()
        if not user:
            # Si pas d'utilisateur non-admin, prendre n'importe quel utilisateur
            result = await session.execute(
                select(User).where(User.is_active == True).limit(1)
            )
            user = result.scalar_one_or_none()
        if not user:
            await engine.dispose()
            pytest.skip("Aucun utilisateur actif dans la DB")
        user_id = str(user.id)

    await engine.dispose()

    payload = {
        "sub": user_id,
        "aud": ["fastapi-users:auth"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


@pytest.fixture
def admin_headers(admin_token):
    """Headers d'authentification admin."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def user_headers(user_token):
    """Headers d'authentification utilisateur."""
    return {"Authorization": f"Bearer {user_token}"}


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Session DB pour tests unitaires."""
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_document(db_session: AsyncSession) -> Document:
    """Cree un document de test."""
    # Recuperer un utilisateur
    result = await db_session.execute(
        select(User).where(User.is_active == True).limit(1)
    )
    user = result.scalar_one_or_none()
    if not user:
        pytest.skip("Aucun utilisateur actif")

    doc = Document(
        user_id=user.id,
        filename=f"admin_test_{uuid4().hex[:8]}.pdf",
        file_hash=f"admin_hash_{uuid4().hex[:16]}",
        file_size=2048,
        file_type="application/pdf",
        chunk_count=3,
        current_version=1,
        visibility=DocumentVisibility.PUBLIC,
        is_indexed=True,
    )
    db_session.add(doc)
    await db_session.flush()
    await db_session.refresh(doc)
    return doc
