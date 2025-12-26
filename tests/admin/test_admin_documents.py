"""
Tests pour les endpoints Admin Documents (deindex, reindex, visibility)

Execution: docker-compose exec app python -m pytest tests/admin/test_admin_documents.py -v
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


class TestAdminDocumentsEndpoints:
    """Tests des endpoints /admin/documents"""

    async def test_get_documents_requires_admin(self, async_client: AsyncClient):
        """Liste des documents sans auth retourne 401"""
        response = await async_client.get("/admin/documents")
        assert response.status_code == 401

    async def test_get_documents_with_admin(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Liste des documents avec auth admin"""
        response = await async_client.get("/admin/documents", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestAdminDocumentsDeindexEndpoints:
    """Tests des endpoints /admin/documents/{id}/deindex"""

    async def test_deindex_requires_admin(self, async_client: AsyncClient):
        """Deindex sans auth retourne 401"""
        fake_id = str(uuid.uuid4())
        response = await async_client.post(f"/admin/documents/{fake_id}/deindex")
        assert response.status_code == 401

    async def test_deindex_document_not_found(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Deindex sur document inexistant retourne 404"""
        fake_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/admin/documents/{fake_id}/deindex",
            headers=admin_headers
        )
        assert response.status_code == 404


class TestAdminDocumentsReindexEndpoints:
    """Tests des endpoints /admin/documents/{id}/reindex"""

    async def test_reindex_requires_admin(self, async_client: AsyncClient):
        """Reindex sans auth retourne 401"""
        fake_id = str(uuid.uuid4())
        response = await async_client.post(f"/admin/documents/{fake_id}/reindex")
        assert response.status_code == 401

    async def test_reindex_document_not_found(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Reindex sur document inexistant retourne 404"""
        fake_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/admin/documents/{fake_id}/reindex",
            headers=admin_headers
        )
        assert response.status_code == 404


class TestAdminDocumentsVisibilityEndpoints:
    """Tests des endpoints /admin/documents/{id}/visibility"""

    async def test_update_visibility_requires_admin(self, async_client: AsyncClient):
        """Changement visibilité sans auth retourne 401"""
        fake_id = str(uuid.uuid4())
        response = await async_client.patch(
            f"/admin/documents/{fake_id}/visibility",
            params={"visibility": "private"}
        )
        assert response.status_code == 401

    async def test_update_visibility_document_not_found(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Changement visibilité sur document inexistant retourne 404"""
        fake_id = str(uuid.uuid4())
        response = await async_client.patch(
            f"/admin/documents/{fake_id}/visibility",
            params={"visibility": "private"},
            headers=admin_headers
        )
        assert response.status_code == 404


class TestAdminDocumentsService:
    """Tests du service Admin pour les documents"""

    async def test_deindex_document_not_found(
        self, db_session: AsyncSession
    ):
        """Deindex sur document inexistant lève 404"""
        from app.features.admin.service import AdminService
        from fastapi import HTTPException

        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await AdminService.deindex_document(db_session, fake_id)

        assert exc_info.value.status_code == 404

    async def test_reindex_document_not_found(
        self, db_session: AsyncSession
    ):
        """Reindex sur document inexistant lève 404"""
        from app.features.admin.service import AdminService
        from fastapi import HTTPException

        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await AdminService.reindex_document(db_session, fake_id)

        assert exc_info.value.status_code == 404

    async def test_deindex_already_deindexed(
        self, db_session: AsyncSession, admin_user_id: uuid.UUID
    ):
        """Deindex d'un document déjà désindexé lève 400"""
        from app.features.admin.service import AdminService
        from app.models import Document, DocumentVisibility
        from fastapi import HTTPException

        # Créer un document déjà désindexé
        test_doc = Document(
            user_id=admin_user_id,
            filename="test_already_deindexed.txt",
            file_hash=f"testhash_{uuid.uuid4().hex[:16]}",
            file_size=100,
            file_type="text/plain",
            chunk_count=1,
            visibility=DocumentVisibility.PUBLIC,
            is_indexed=False  # Déjà désindexé
        )
        db_session.add(test_doc)
        await db_session.commit()
        await db_session.refresh(test_doc)

        try:
            with pytest.raises(HTTPException) as exc_info:
                await AdminService.deindex_document(db_session, test_doc.id)
            assert exc_info.value.status_code == 400
            assert "already deindexed" in exc_info.value.detail.lower()
        finally:
            await db_session.delete(test_doc)
            await db_session.commit()

    async def test_reindex_already_indexed(
        self, db_session: AsyncSession, admin_user_id: uuid.UUID
    ):
        """Reindex d'un document déjà indexé lève 400"""
        from app.features.admin.service import AdminService
        from app.models import Document, DocumentVisibility
        from fastapi import HTTPException

        # Créer un document déjà indexé
        test_doc = Document(
            user_id=admin_user_id,
            filename="test_already_indexed.txt",
            file_hash=f"testhash_{uuid.uuid4().hex[:16]}",
            file_size=100,
            file_type="text/plain",
            chunk_count=1,
            visibility=DocumentVisibility.PUBLIC,
            is_indexed=True  # Déjà indexé
        )
        db_session.add(test_doc)
        await db_session.commit()
        await db_session.refresh(test_doc)

        try:
            with pytest.raises(HTTPException) as exc_info:
                await AdminService.reindex_document(db_session, test_doc.id)
            assert exc_info.value.status_code == 400
            assert "already indexed" in exc_info.value.detail.lower()
        finally:
            await db_session.delete(test_doc)
            await db_session.commit()

    async def test_deindex_success(
        self, db_session: AsyncSession, admin_user_id: uuid.UUID
    ):
        """Deindex réussi"""
        from app.features.admin.service import AdminService
        from app.models import Document, DocumentVisibility

        # Créer un document indexé
        test_doc = Document(
            user_id=admin_user_id,
            filename="test_deindex_success.txt",
            file_hash=f"testhash_{uuid.uuid4().hex[:16]}",
            file_size=100,
            file_type="text/plain",
            chunk_count=1,
            visibility=DocumentVisibility.PUBLIC,
            is_indexed=True
        )
        db_session.add(test_doc)
        await db_session.commit()
        await db_session.refresh(test_doc)

        try:
            result = await AdminService.deindex_document(db_session, test_doc.id)

            assert result is not None
            assert result.is_indexed is False

            # Vérifier en base
            await db_session.refresh(test_doc)
            assert test_doc.is_indexed is False
        finally:
            await db_session.delete(test_doc)
            await db_session.commit()

    async def test_reindex_success(
        self, db_session: AsyncSession, admin_user_id: uuid.UUID
    ):
        """Reindex réussi"""
        from app.features.admin.service import AdminService
        from app.models import Document, DocumentVisibility

        # Créer un document désindexé
        test_doc = Document(
            user_id=admin_user_id,
            filename="test_reindex_success.txt",
            file_hash=f"testhash_{uuid.uuid4().hex[:16]}",
            file_size=100,
            file_type="text/plain",
            chunk_count=1,
            visibility=DocumentVisibility.PUBLIC,
            is_indexed=False
        )
        db_session.add(test_doc)
        await db_session.commit()
        await db_session.refresh(test_doc)

        try:
            result = await AdminService.reindex_document(db_session, test_doc.id)

            assert result is not None
            assert result.is_indexed is True

            # Vérifier en base
            await db_session.refresh(test_doc)
            assert test_doc.is_indexed is True
        finally:
            await db_session.delete(test_doc)
            await db_session.commit()

    async def test_update_visibility_as_admin(
        self, db_session: AsyncSession, admin_user_id: uuid.UUID
    ):
        """Admin peut changer la visibilité de n'importe quel document"""
        from app.features.admin.service import AdminService
        from app.models import Document, DocumentVisibility

        # Créer un document d'un autre utilisateur (simulé avec admin_user_id)
        test_doc = Document(
            user_id=admin_user_id,
            filename="test_admin_visibility.txt",
            file_hash=f"testhash_{uuid.uuid4().hex[:16]}",
            file_size=100,
            file_type="text/plain",
            chunk_count=1,
            visibility=DocumentVisibility.PUBLIC,
            is_indexed=True
        )
        db_session.add(test_doc)
        await db_session.commit()
        await db_session.refresh(test_doc)

        try:
            # L'admin peut changer la visibilité (is_admin=True)
            result = await AdminService.update_document_visibility(
                db=db_session,
                document_id=test_doc.id,
                visibility="private",
                user_id=admin_user_id,
                is_admin=True
            )

            assert result is not None
            assert result.visibility == DocumentVisibility.PRIVATE

            # Vérifier en base
            await db_session.refresh(test_doc)
            assert test_doc.visibility == DocumentVisibility.PRIVATE
        finally:
            await db_session.delete(test_doc)
            await db_session.commit()
