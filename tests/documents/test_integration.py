"""
Tests d'integration HTTP pour les endpoints Documents.

Execution: docker-compose exec app python -m pytest tests/documents/test_integration.py -v
"""

import asyncio
import io
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


pytestmark = pytest.mark.asyncio


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
async def user_token():
    """Token JWT pour un utilisateur actif."""
    engine = create_async_engine(settings.database_url, pool_size=1, max_overflow=0)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
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
def auth_headers(user_token):
    """Headers d'authentification."""
    return {"Authorization": f"Bearer {user_token}"}


class TestDocumentsListEndpoint:
    """Tests pour GET /api/user/documents"""

    async def test_list_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401."""
        response = await async_client.get("/api/user/documents")
        assert response.status_code == 401

    async def test_list_documents(self, async_client: AsyncClient, auth_headers: dict):
        """Liste les documents avec auth."""
        response = await async_client.get(
            "/api/user/documents", headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    async def test_list_with_pagination(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Pagination fonctionne."""
        response = await async_client.get(
            "/api/user/documents?page=1&page_size=5", headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    async def test_list_with_visibility_filter(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Filtre par visibilite."""
        response = await async_client.get(
            "/api/user/documents?visibility=public", headers=auth_headers
        )
        
        assert response.status_code == 200


class TestDocumentsSearchEndpoint:
    """Tests pour GET /api/user/documents/search"""

    async def test_search_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401."""
        response = await async_client.get("/api/user/documents/search?q=test")
        assert response.status_code == 401

    async def test_search_requires_query(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Requiert un parametre q."""
        response = await async_client.get(
            "/api/user/documents/search", headers=auth_headers
        )
        assert response.status_code == 422  # Validation error

    async def test_search_min_length(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Query doit avoir au moins 2 caracteres."""
        response = await async_client.get(
            "/api/user/documents/search?q=a", headers=auth_headers
        )
        assert response.status_code == 422

    async def test_search_success(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Recherche avec succes."""
        response = await async_client.get(
            "/api/user/documents/search?q=test", headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "query" in data


class TestDocumentsStatsEndpoint:
    """Tests pour GET /api/user/documents/stats"""

    async def test_stats_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401."""
        response = await async_client.get("/api/user/documents/stats")
        assert response.status_code == 401

    async def test_stats_success(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Recupere les stats avec succes."""
        response = await async_client.get(
            "/api/user/documents/stats", headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "used_bytes" in data
        assert "file_count" in data
        assert "quota_bytes" in data
        assert "quota_used_percent" in data


class TestDocumentsUploadEndpoint:
    """Tests pour POST /api/user/documents"""

    async def test_upload_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401."""
        response = await async_client.post("/api/user/documents")
        assert response.status_code == 401

    async def test_upload_requires_file(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Requiert un fichier."""
        response = await async_client.post(
            "/api/user/documents", headers=auth_headers
        )
        assert response.status_code == 422

    async def test_upload_success(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Upload un fichier avec succes."""
        # Creer un fichier de test
        file_content = f"Test content {uuid4().hex}".encode()
        files = {
            "file": (f"test_{uuid4().hex[:8]}.txt", io.BytesIO(file_content), "text/plain")
        }
        
        response = await async_client.post(
            "/api/user/documents",
            headers=auth_headers,
            files=files,
            data={"visibility": "private"},
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["filename"].startswith("test_")
        assert data["version"] == 1


class TestDocumentsDetailEndpoint:
    """Tests pour GET /api/user/documents/{id}"""

    async def test_detail_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401."""
        response = await async_client.get(f"/api/user/documents/{uuid4()}")
        assert response.status_code == 401

    async def test_detail_not_found(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Retourne 404 si document non trouve."""
        response = await async_client.get(
            f"/api/user/documents/{uuid4()}", headers=auth_headers
        )
        assert response.status_code == 404


class TestDocumentsUpdateEndpoint:
    """Tests pour PATCH /api/user/documents/{id}"""

    async def test_update_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401."""
        response = await async_client.patch(
            f"/api/user/documents/{uuid4()}",
            json={"visibility": "private"},
        )
        assert response.status_code == 401


class TestDocumentsDeleteEndpoint:
    """Tests pour DELETE /api/user/documents/{id}"""

    async def test_delete_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401."""
        response = await async_client.delete(f"/api/user/documents/{uuid4()}")
        assert response.status_code == 401

    async def test_delete_not_found(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Retourne 404 si document non trouve."""
        response = await async_client.delete(
            f"/api/user/documents/{uuid4()}", headers=auth_headers
        )
        assert response.status_code == 404


class TestDocumentsDownloadEndpoint:
    """Tests pour GET /api/user/documents/{id}/download"""

    async def test_download_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401."""
        response = await async_client.get(f"/api/user/documents/{uuid4()}/download")
        assert response.status_code == 401

    async def test_download_not_found(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Retourne 404 si document non trouve."""
        response = await async_client.get(
            f"/api/user/documents/{uuid4()}/download", headers=auth_headers
        )
        assert response.status_code == 404
