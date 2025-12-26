"""
Tests unitaires pour DocumentRepository.

Execution: docker-compose exec app python -m pytest tests/documents/test_repository.py -v
"""

import pytest
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentVisibility, User
from app.features.documents.repository import DocumentRepository


pytestmark = pytest.mark.asyncio


class TestDocumentRepositoryRead:
    """Tests pour les operations de lecture."""

    async def test_get_by_id(self, db_session: AsyncSession, test_document: Document):
        """Recupere un document par ID."""
        repo = DocumentRepository(db_session)
        result = await repo.get_by_id(test_document.id)
        
        assert result is not None
        assert result.id == test_document.id
        assert result.filename == test_document.filename

    async def test_get_by_id_not_found(self, db_session: AsyncSession):
        """Retourne None si document non trouve."""
        repo = DocumentRepository(db_session)
        result = await repo.get_by_id(uuid4())
        
        assert result is None

    async def test_get_user_document(
        self, db_session: AsyncSession, test_user: User, test_document: Document
    ):
        """Recupere un document appartenant a un utilisateur."""
        repo = DocumentRepository(db_session)
        result = await repo.get_user_document(test_user.id, test_document.id)
        
        assert result is not None
        assert result.user_id == test_user.id

    async def test_get_user_document_wrong_user(
        self, db_session: AsyncSession, test_document: Document
    ):
        """Retourne None si le document n'appartient pas a l'utilisateur."""
        repo = DocumentRepository(db_session)
        result = await repo.get_user_document(uuid4(), test_document.id)
        
        assert result is None

    async def test_get_by_id_with_versions(
        self, db_session: AsyncSession, test_document: Document
    ):
        """Recupere un document avec ses versions."""
        repo = DocumentRepository(db_session)
        result = await repo.get_by_id_with_versions(test_document.id)
        
        assert result is not None
        assert len(result.versions) >= 1


class TestDocumentRepositoryList:
    """Tests pour les operations de listing."""

    async def test_list_user_documents(
        self, db_session: AsyncSession, test_user: User, test_document: Document
    ):
        """Liste les documents d'un utilisateur."""
        repo = DocumentRepository(db_session)
        documents, total = await repo.list_user_documents(test_user.id)
        
        assert total >= 1
        assert any(d.id == test_document.id for d in documents)

    async def test_list_user_documents_with_visibility_filter(
        self, db_session: AsyncSession, test_user: User, private_document: Document
    ):
        """Filtre par visibilite."""
        repo = DocumentRepository(db_session)
        
        # Filtre private
        docs, total = await repo.list_user_documents(
            test_user.id, visibility="private"
        )
        
        assert all(d.visibility == DocumentVisibility.PRIVATE for d in docs)

    async def test_list_user_documents_pagination(
        self, db_session: AsyncSession, test_user: User
    ):
        """Pagination fonctionne."""
        repo = DocumentRepository(db_session)
        
        # Page 1
        docs_p1, total = await repo.list_user_documents(
            test_user.id, page=1, page_size=1
        )
        
        # Si plusieurs documents, verifier la pagination
        if total > 1:
            docs_p2, _ = await repo.list_user_documents(
                test_user.id, page=2, page_size=1
            )
            assert docs_p1[0].id != docs_p2[0].id

    async def test_list_user_documents_empty(self, db_session: AsyncSession):
        """Retourne liste vide pour utilisateur sans documents."""
        repo = DocumentRepository(db_session)
        docs, total = await repo.list_user_documents(uuid4())
        
        assert docs == []
        assert total == 0


class TestDocumentRepositorySearch:
    """Tests pour la recherche."""

    async def test_search_user_documents(
        self, db_session: AsyncSession, test_user: User, test_document: Document
    ):
        """Recherche par nom de fichier."""
        repo = DocumentRepository(db_session)
        results = await repo.search_user_documents(
            test_user.id, query="test_document"
        )
        
        assert len(results) >= 1
        assert any(d.id == test_document.id for d in results)

    async def test_search_user_documents_case_insensitive(
        self, db_session: AsyncSession, test_user: User, test_document: Document
    ):
        """Recherche insensible a la casse."""
        repo = DocumentRepository(db_session)
        results = await repo.search_user_documents(
            test_user.id, query="TEST_DOCUMENT"
        )
        
        assert len(results) >= 1

    async def test_search_user_documents_no_results(
        self, db_session: AsyncSession, test_user: User
    ):
        """Retourne liste vide si aucun resultat."""
        repo = DocumentRepository(db_session)
        results = await repo.search_user_documents(
            test_user.id, query="zzz_nonexistent_xyz"
        )
        
        assert results == []


class TestDocumentRepositoryWrite:
    """Tests pour les operations d'ecriture."""

    async def test_create_document(self, db_session: AsyncSession, test_user: User):
        """Cree un nouveau document."""
        repo = DocumentRepository(db_session)
        
        doc = Document(
            user_id=test_user.id,
            filename="new_doc.pdf",
            file_hash=f"new_hash_{uuid4().hex[:16]}",
            file_size=2048,
            file_type="application/pdf",
            visibility=DocumentVisibility.PUBLIC,
        )
        
        created = await repo.create(doc)
        
        assert created.id is not None
        assert created.filename == "new_doc.pdf"

    async def test_update_document(
        self, db_session: AsyncSession, test_document: Document
    ):
        """Met a jour un document."""
        repo = DocumentRepository(db_session)
        
        test_document.filename = "updated_name.pdf"
        updated = await repo.update(test_document)
        
        assert updated.filename == "updated_name.pdf"

    async def test_update_visibility(
        self, db_session: AsyncSession, test_document: Document
    ):
        """Change la visibilite d'un document."""
        repo = DocumentRepository(db_session)
        
        updated = await repo.update_visibility(test_document, "private")
        
        assert updated.visibility == DocumentVisibility.PRIVATE

    async def test_delete_document(
        self, db_session: AsyncSession, test_user: User
    ):
        """Supprime un document."""
        repo = DocumentRepository(db_session)
        
        # Creer un document a supprimer
        doc = Document(
            user_id=test_user.id,
            filename="to_delete.pdf",
            file_hash=f"delete_hash_{uuid4().hex[:16]}",
            file_size=100,
            file_type="application/pdf",
            visibility=DocumentVisibility.PUBLIC,
        )
        created = await repo.create(doc)
        doc_id = created.id
        
        # Supprimer
        result = await repo.delete(created)
        
        assert result is True
        
        # Verifier suppression
        found = await repo.get_by_id(doc_id)
        assert found is None


class TestDocumentRepositoryVersions:
    """Tests pour les versions de documents."""

    async def test_list_versions(
        self, db_session: AsyncSession, test_document: Document
    ):
        """Liste les versions d'un document."""
        repo = DocumentRepository(db_session)
        versions = await repo.list_versions(test_document.id)
        
        assert len(versions) >= 1
        assert versions[0].document_id == test_document.id

    async def test_get_version(
        self, db_session: AsyncSession, test_document: Document
    ):
        """Recupere une version specifique."""
        repo = DocumentRepository(db_session)
        version = await repo.get_version(test_document.id, 1)
        
        assert version is not None
        assert version.version_number == 1

    async def test_get_version_not_found(
        self, db_session: AsyncSession, test_document: Document
    ):
        """Retourne None si version non trouvee."""
        repo = DocumentRepository(db_session)
        version = await repo.get_version(test_document.id, 999)
        
        assert version is None

    async def test_get_latest_version(
        self, db_session: AsyncSession, test_document: Document
    ):
        """Recupere la derniere version."""
        repo = DocumentRepository(db_session)
        latest = await repo.get_latest_version(test_document.id)
        
        assert latest is not None
        assert latest.version_number == test_document.current_version
