"""
Fixtures pour les tests de la feature Documents.

Execution: docker-compose exec app python -m pytest tests/documents/ -v
"""

import asyncio
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models import User, Document, DocumentVersion, DocumentVisibility


@pytest.fixture(scope="session")
def event_loop():
    """Event loop unique pour eviter conflits."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


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
async def test_user(db_session: AsyncSession) -> User:
    """Recupere un utilisateur de test existant."""
    result = await db_session.execute(
        select(User).where(User.is_active == True).limit(1)
    )
    user = result.scalar_one_or_none()
    if not user:
        pytest.skip("Aucun utilisateur actif dans la DB")
    return user


@pytest_asyncio.fixture(scope="function")
async def test_document(db_session: AsyncSession, test_user: User) -> Document:
    """Cree un document de test."""
    doc = Document(
        user_id=test_user.id,
        filename="test_document.pdf",
        file_hash=f"test_hash_{uuid4().hex[:16]}",
        file_size=1024,
        file_type="application/pdf",
        file_path=f"{test_user.id}/test_doc/v1_test.pdf",
        chunk_count=5,
        current_version=1,
        visibility=DocumentVisibility.PUBLIC,
        is_indexed=True,
    )
    db_session.add(doc)
    await db_session.flush()
    await db_session.refresh(doc)
    
    # Creer une version
    version = DocumentVersion(
        document_id=doc.id,
        version_number=1,
        file_path=doc.file_path,
        file_size=doc.file_size,
        file_hash=doc.file_hash,
        chunk_count=doc.chunk_count,
        created_by=test_user.id,
    )
    db_session.add(version)
    await db_session.flush()
    
    return doc


@pytest_asyncio.fixture(scope="function")
async def private_document(db_session: AsyncSession, test_user: User) -> Document:
    """Cree un document prive de test."""
    doc = Document(
        user_id=test_user.id,
        filename="private_doc.txt",
        file_hash=f"private_hash_{uuid4().hex[:16]}",
        file_size=512,
        file_type="text/plain",
        file_path=f"{test_user.id}/private_doc/v1_private.txt",
        chunk_count=2,
        current_version=1,
        visibility=DocumentVisibility.PRIVATE,
        is_indexed=True,
    )
    db_session.add(doc)
    await db_session.flush()
    await db_session.refresh(doc)
    return doc
