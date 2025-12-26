"""
Tests pour l'archivage des conversations

Execution: docker-compose exec app python -m pytest tests/user/test_conversations_archive.py -v
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


# =============================================================================
# TESTS ENDPOINTS HTTP
# =============================================================================

class TestArchiveEndpoints:
    """Tests des endpoints /conversations/{id}/archive et /unarchive"""

    async def test_archive_requires_auth(self, async_client: AsyncClient):
        """Archive sans auth retourne 401"""
        fake_id = str(uuid.uuid4())
        response = await async_client.post(f"/conversations/{fake_id}/archive")
        assert response.status_code == 401

    async def test_unarchive_requires_auth(self, async_client: AsyncClient):
        """Unarchive sans auth retourne 401"""
        fake_id = str(uuid.uuid4())
        response = await async_client.post(f"/conversations/{fake_id}/unarchive")
        assert response.status_code == 401

    async def test_archive_conversation_not_found(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Archive d'une conversation inexistante retourne 404"""
        fake_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/conversations/{fake_id}/archive",
            headers=user_headers
        )
        assert response.status_code == 404

    async def test_unarchive_conversation_not_found(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Unarchive d'une conversation inexistante retourne 404"""
        fake_id = str(uuid.uuid4())
        response = await async_client.post(
            f"/conversations/{fake_id}/unarchive",
            headers=user_headers
        )
        assert response.status_code == 404

    async def test_archive_conversation_success(
        self,
        async_client: AsyncClient,
        user_headers: dict,
        sample_conversation_data: dict
    ):
        """Archivage d'une conversation avec succes"""
        # Creer une conversation
        create_response = await async_client.post(
            "/conversations",
            json=sample_conversation_data,
            headers=user_headers
        )
        assert create_response.status_code == 201
        conversation_id = create_response.json()["id"]

        # Archiver
        response = await async_client.post(
            f"/conversations/{conversation_id}/archive",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conversation_id
        assert data["archived_at"] is not None

    async def test_unarchive_conversation_success(
        self,
        async_client: AsyncClient,
        user_headers: dict,
        sample_conversation_data: dict
    ):
        """Desarchivage d'une conversation avec succes"""
        # Creer une conversation
        create_response = await async_client.post(
            "/conversations",
            json=sample_conversation_data,
            headers=user_headers
        )
        assert create_response.status_code == 201
        conversation_id = create_response.json()["id"]

        # Archiver d'abord
        archive_response = await async_client.post(
            f"/conversations/{conversation_id}/archive",
            headers=user_headers
        )
        assert archive_response.status_code == 200
        assert archive_response.json()["archived_at"] is not None

        # Desarchiver
        response = await async_client.post(
            f"/conversations/{conversation_id}/unarchive",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conversation_id
        assert data["archived_at"] is None

    async def test_list_includes_archived_at(
        self,
        async_client: AsyncClient,
        user_headers: dict,
        sample_conversation_data: dict
    ):
        """La liste des conversations inclut le champ archived_at"""
        # Creer une conversation
        create_response = await async_client.post(
            "/conversations",
            json=sample_conversation_data,
            headers=user_headers
        )
        assert create_response.status_code == 201

        # Lister
        response = await async_client.get(
            "/conversations/",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        # Verifier que archived_at est present dans le schema
        first_item = data["items"][0]
        assert "archived_at" in first_item

    async def test_archived_conversations_still_accessible(
        self,
        async_client: AsyncClient,
        user_headers: dict,
        sample_conversation_data: dict
    ):
        """Une conversation archivee reste accessible par son ID"""
        # Creer une conversation
        create_response = await async_client.post(
            "/conversations",
            json=sample_conversation_data,
            headers=user_headers
        )
        assert create_response.status_code == 201
        conversation_id = create_response.json()["id"]

        # Archiver
        await async_client.post(
            f"/conversations/{conversation_id}/archive",
            headers=user_headers
        )

        # Verifier qu'elle est toujours accessible
        response = await async_client.get(
            f"/conversations/{conversation_id}",
            headers=user_headers
        )
        assert response.status_code == 200
        assert response.json()["id"] == conversation_id


# =============================================================================
# TESTS SERVICE
# =============================================================================

class TestArchiveService:
    """Tests du service d'archivage"""

    async def test_archive_conversation_service(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test archivage via service"""
        from app.features.conversations.service import ConversationService
        from app.features.conversations.schemas import ConversationCreate

        # Creer conversation
        data = ConversationCreate(title="Archive Test", mode_id=1)
        conversation = await ConversationService.create_conversation(
            db_session, user_id, data
        )
        assert conversation.archived_at is None

        # Archiver
        result = await ConversationService.archive_conversation(
            db_session, conversation.id, user_id
        )

        assert result is not None
        assert result.id == conversation.id
        assert result.archived_at is not None

    async def test_unarchive_conversation_service(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test desarchivage via service"""
        from app.features.conversations.service import ConversationService
        from app.features.conversations.schemas import ConversationCreate

        # Creer et archiver
        data = ConversationCreate(title="Unarchive Test", mode_id=1)
        conversation = await ConversationService.create_conversation(
            db_session, user_id, data
        )
        archived = await ConversationService.archive_conversation(
            db_session, conversation.id, user_id
        )
        assert archived.archived_at is not None

        # Desarchiver
        result = await ConversationService.unarchive_conversation(
            db_session, conversation.id, user_id
        )

        assert result is not None
        assert result.id == conversation.id
        assert result.archived_at is None

    async def test_archive_nonexistent_conversation_service(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test archivage conversation inexistante via service"""
        from app.features.conversations.service import ConversationService

        fake_id = uuid.uuid4()
        result = await ConversationService.archive_conversation(
            db_session, fake_id, user_id
        )

        assert result is None

    async def test_unarchive_nonexistent_conversation_service(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test desarchivage conversation inexistante via service"""
        from app.features.conversations.service import ConversationService

        fake_id = uuid.uuid4()
        result = await ConversationService.unarchive_conversation(
            db_session, fake_id, user_id
        )

        assert result is None

    async def test_list_includes_archived_at_service(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test que list_conversations retourne archived_at"""
        from app.features.conversations.service import ConversationService
        from app.features.conversations.schemas import ConversationCreate

        # Creer une conversation
        data = ConversationCreate(title="List Archive Test", mode_id=1)
        await ConversationService.create_conversation(db_session, user_id, data)

        # Lister
        items, total = await ConversationService.list_conversations(
            db_session, user_id, limit=10, offset=0
        )

        assert len(items) > 0
        # Verifier que archived_at est un attribut (meme si None)
        assert hasattr(items[0], 'archived_at')


# =============================================================================
# TESTS REPOSITORY
# =============================================================================

class TestArchiveRepository:
    """Tests du repository d'archivage"""

    async def test_archive_repository(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test archivage via repository"""
        from app.features.conversations.repository import ConversationRepository

        # Creer conversation
        conversation = await ConversationRepository.create(
            db_session,
            user_id=user_id,
            title="Repo Archive Test",
            mode_id=1
        )
        assert conversation.archived_at is None

        # Archiver
        result = await ConversationRepository.archive(
            db_session, conversation.id, user_id
        )

        assert result is not None
        assert result.id == conversation.id
        assert result.archived_at is not None

    async def test_unarchive_repository(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test desarchivage via repository"""
        from app.features.conversations.repository import ConversationRepository

        # Creer et archiver
        conversation = await ConversationRepository.create(
            db_session,
            user_id=user_id,
            title="Repo Unarchive Test",
            mode_id=1
        )
        await ConversationRepository.archive(
            db_session, conversation.id, user_id
        )

        # Desarchiver
        result = await ConversationRepository.unarchive(
            db_session, conversation.id, user_id
        )

        assert result is not None
        assert result.id == conversation.id
        assert result.archived_at is None

    async def test_archive_wrong_user_repository(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test archivage avec mauvais user_id via repository"""
        from app.features.conversations.repository import ConversationRepository

        # Creer conversation
        conversation = await ConversationRepository.create(
            db_session,
            user_id=user_id,
            title="Wrong User Test",
            mode_id=1
        )

        # Essayer d'archiver avec un autre user_id
        fake_user_id = uuid.uuid4()
        result = await ConversationRepository.archive(
            db_session, conversation.id, fake_user_id
        )

        assert result is None
