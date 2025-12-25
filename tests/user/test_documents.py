"""
Tests pour le module Documents utilisateur

Execution: docker-compose exec app python -m pytest tests/user/test_documents.py -v
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


class TestDocumentsEndpoints:
    """Tests des endpoints /documents"""

    async def test_list_documents_requires_auth(self, async_client: AsyncClient):
        """Liste des documents sans auth retourne 401"""
        response = await async_client.get("/documents/")
        assert response.status_code == 401

    async def test_list_documents(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Liste des documents avec auth"""
        response = await async_client.get("/documents/", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_get_document_not_found(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Récupération d'un document inexistant retourne 404"""
        fake_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/documents/{fake_id}",
            headers=user_headers
        )
        assert response.status_code == 404

    async def test_delete_document_not_found(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Suppression d'un document inexistant retourne 404"""
        fake_id = str(uuid.uuid4())
        response = await async_client.delete(
            f"/documents/{fake_id}",
            headers=user_headers
        )
        assert response.status_code == 404

    async def test_pagination(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Test de la pagination des documents"""
        response = await async_client.get(
            "/documents/?limit=5&offset=0",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 0


class TestDocumentsService:
    """Tests du service Documents"""

    async def test_list_documents_service(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test liste via service"""
        from app.features.documents.service import DocumentService

        items, total = await DocumentService.list_documents(
            db_session, user_id, limit=10, offset=0
        )

        assert isinstance(items, list)
        assert isinstance(total, int)
        assert total >= 0

    async def test_get_document_not_found_service(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test récupération document inexistant via service"""
        from app.features.documents.service import DocumentService

        fake_id = uuid.uuid4()
        result = await DocumentService.get_document(db_session, fake_id, user_id)

        assert result is None

    async def test_delete_document_not_found_service(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test suppression document inexistant via service"""
        from app.features.documents.service import DocumentService

        fake_id = uuid.uuid4()
        result = await DocumentService.delete_document(db_session, fake_id, user_id)

        assert result is False
