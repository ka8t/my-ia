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


class TestDocumentsVisibilityEndpoints:
    """Tests des endpoints de visibilité /documents/{id}/visibility"""

    async def test_update_visibility_requires_auth(self, async_client: AsyncClient):
        """Changement de visibilité sans auth retourne 401"""
        fake_id = str(uuid.uuid4())
        response = await async_client.patch(
            f"/documents/{fake_id}/visibility",
            json={"visibility": "private"}
        )
        assert response.status_code == 401

    async def test_update_visibility_document_not_found(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Changement de visibilité sur document inexistant retourne 404"""
        fake_id = str(uuid.uuid4())
        response = await async_client.patch(
            f"/documents/{fake_id}/visibility",
            json={"visibility": "private"},
            headers=user_headers
        )
        assert response.status_code == 404

    async def test_update_visibility_invalid_value(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Visibilité invalide retourne 422"""
        fake_id = str(uuid.uuid4())
        response = await async_client.patch(
            f"/documents/{fake_id}/visibility",
            json={"visibility": "invalid_value"},
            headers=user_headers
        )
        assert response.status_code == 422


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


class TestDocumentsVisibilityService:
    """Tests du service de visibilité des documents"""

    async def test_update_visibility_document_not_found(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Changement de visibilité sur document inexistant lève 404"""
        from app.features.documents.service import DocumentService
        from fastapi import HTTPException

        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await DocumentService.update_visibility(
                db_session, fake_id, user_id, "private"
            )

        assert exc_info.value.status_code == 404

    async def test_update_visibility_invalid_value(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Valeur de visibilité invalide lève 400"""
        from app.features.documents.service import DocumentService
        from fastapi import HTTPException

        # On crée un document temporaire pour tester
        from app.models import Document

        test_doc = Document(
            user_id=user_id,
            filename="test_visibility.txt",
            file_hash=f"testhash_{uuid.uuid4().hex[:16]}",
            file_size=100,
            file_type="text/plain",
            chunk_count=1,
            # visibility utilise la valeur par defaut 'public' de la colonne
            is_indexed=True
        )
        db_session.add(test_doc)
        await db_session.commit()
        await db_session.refresh(test_doc)

        try:
            with pytest.raises(HTTPException) as exc_info:
                await DocumentService.update_visibility(
                    db_session, test_doc.id, user_id, "invalid"
                )
            assert exc_info.value.status_code == 400
        finally:
            # Cleanup
            await db_session.delete(test_doc)
            await db_session.commit()

    async def test_update_visibility_success(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Changement de visibilité réussi"""
        from app.features.documents.service import DocumentService
        from app.models import Document, DocumentVisibility

        # Créer un document de test (visibility utilise default 'public')
        test_doc = Document(
            user_id=user_id,
            filename="test_visibility_success.txt",
            file_hash=f"testhash_{uuid.uuid4().hex[:16]}",
            file_size=100,
            file_type="text/plain",
            chunk_count=1,
            is_indexed=True
        )
        db_session.add(test_doc)
        await db_session.commit()
        await db_session.refresh(test_doc)

        try:
            # Changer de public à private
            result = await DocumentService.update_visibility(
                db_session, test_doc.id, user_id, "private"
            )

            assert result is not None
            assert result.visibility == "private"

            # Vérifier en base
            await db_session.refresh(test_doc)
            assert test_doc.visibility == DocumentVisibility.PRIVATE
        finally:
            # Cleanup
            await db_session.delete(test_doc)
            await db_session.commit()

    async def test_update_visibility_same_value(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Changement vers la même visibilité lève 400"""
        from app.features.documents.service import DocumentService
        from app.models import Document, DocumentVisibility
        from fastapi import HTTPException

        # Créer un document de test (visibility utilise default 'public')
        test_doc = Document(
            user_id=user_id,
            filename="test_visibility_same.txt",
            file_hash=f"testhash_{uuid.uuid4().hex[:16]}",
            file_size=100,
            file_type="text/plain",
            chunk_count=1,
            is_indexed=True
        )
        db_session.add(test_doc)
        await db_session.commit()
        await db_session.refresh(test_doc)

        try:
            with pytest.raises(HTTPException) as exc_info:
                await DocumentService.update_visibility(
                    db_session, test_doc.id, user_id, "public"
                )
            assert exc_info.value.status_code == 400
            assert "déjà" in exc_info.value.detail.lower()
        finally:
            # Cleanup
            await db_session.delete(test_doc)
            await db_session.commit()
