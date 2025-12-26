"""
Tests pour Admin Conversations

Tests de la gestion avancee des conversations par l'admin.
Execution: docker-compose exec app python -m pytest tests/admin/test_admin_conversations.py -v
"""
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.features.admin.conversations.service import ConversationAdminService


# =============================================================================
# TESTS LIST CONVERSATIONS
# =============================================================================

class TestAdminConversationList:
    """Tests liste des conversations"""

    @pytest.mark.asyncio
    async def test_list_conversations(self, db_session: AsyncSession):
        """Test liste des conversations"""
        conversations, total = await ConversationAdminService.get_conversations(
            db=db_session,
            limit=10,
            offset=0
        )

        assert isinstance(conversations, list)
        assert isinstance(total, int)
        assert total >= 0

    @pytest.mark.asyncio
    async def test_list_conversations_pagination(self, db_session: AsyncSession):
        """Test pagination des conversations"""
        # Page 1
        convs_p1, total = await ConversationAdminService.get_conversations(
            db=db_session,
            limit=5,
            offset=0
        )

        # Page 2
        convs_p2, _ = await ConversationAdminService.get_conversations(
            db=db_session,
            limit=5,
            offset=5
        )

        if total > 5:
            assert len(convs_p1) > 0
            # Les IDs doivent etre differents
            ids_p1 = {c["id"] for c in convs_p1}
            ids_p2 = {c["id"] for c in convs_p2}
            assert ids_p1.isdisjoint(ids_p2)


# =============================================================================
# TESTS GET CONVERSATION DETAILS
# =============================================================================

class TestAdminConversationDetails:
    """Tests details d'une conversation"""

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(self, db_session: AsyncSession):
        """Test conversation non trouvee"""
        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await ConversationAdminService.get_conversation_detail(
                db=db_session,
                conversation_id=fake_id
            )

        assert exc_info.value.status_code == 404


# =============================================================================
# TESTS DELETE CONVERSATION
# =============================================================================

class TestAdminConversationDelete:
    """Tests suppression de conversation"""

    @pytest.mark.asyncio
    async def test_delete_nonexistent_conversation(self, db_session: AsyncSession):
        """Test suppression conversation inexistante"""
        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await ConversationAdminService.delete_conversation(
                db=db_session,
                conversation_id=fake_id
            )

        assert exc_info.value.status_code == 404


# =============================================================================
# TESTS EDGE CASES
# =============================================================================

class TestAdminConversationEdgeCases:
    """Tests cas limites conversations"""

    @pytest.mark.asyncio
    async def test_empty_conversation_list(self, db_session: AsyncSession):
        """Test liste potentiellement vide"""
        conversations, total = await ConversationAdminService.get_conversations(
            db=db_session,
            limit=10,
            offset=99999  # Offset tres grand
        )

        assert conversations == []

    @pytest.mark.asyncio
    async def test_filter_by_nonexistent_user(self, db_session: AsyncSession):
        """Test filtre par utilisateur inexistant"""
        fake_user_id = uuid.uuid4()

        conversations, total = await ConversationAdminService.get_conversations(
            db=db_session,
            user_id=fake_user_id,
            limit=10,
            offset=0
        )

        assert total == 0
        assert conversations == []


# =============================================================================
# TESTS ARCHIVE/UNARCHIVE
# =============================================================================

class TestAdminConversationArchive:
    """Tests archivage de conversation par admin"""

    @pytest.mark.asyncio
    async def test_archive_nonexistent_conversation(self, db_session: AsyncSession):
        """Test archivage conversation inexistante"""
        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await ConversationAdminService.archive_conversation(
                db=db_session,
                conversation_id=fake_id
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_unarchive_nonexistent_conversation(self, db_session: AsyncSession):
        """Test desarchivage conversation inexistante"""
        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await ConversationAdminService.unarchive_conversation(
                db=db_session,
                conversation_id=fake_id
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_archive_conversation_success(
        self, db_session: AsyncSession, admin_user_id: uuid.UUID
    ):
        """Test archivage d'une conversation avec succes"""
        from app.features.conversations.service import ConversationService
        from app.features.conversations.schemas import ConversationCreate

        # Creer une conversation
        data = ConversationCreate(title="Admin Archive Test", mode_id=1)
        conversation = await ConversationService.create_conversation(
            db_session, admin_user_id, data
        )
        assert conversation.archived_at is None

        # Archiver via admin service
        result = await ConversationAdminService.archive_conversation(
            db_session, conversation.id
        )

        assert result is not None
        assert result["id"] == conversation.id
        assert result["archived_at"] is not None

    @pytest.mark.asyncio
    async def test_unarchive_conversation_success(
        self, db_session: AsyncSession, admin_user_id: uuid.UUID
    ):
        """Test desarchivage d'une conversation avec succes"""
        from app.features.conversations.service import ConversationService
        from app.features.conversations.schemas import ConversationCreate

        # Creer et archiver une conversation
        data = ConversationCreate(title="Admin Unarchive Test", mode_id=1)
        conversation = await ConversationService.create_conversation(
            db_session, admin_user_id, data
        )
        await ConversationAdminService.archive_conversation(
            db_session, conversation.id
        )

        # Desarchiver via admin service
        result = await ConversationAdminService.unarchive_conversation(
            db_session, conversation.id
        )

        assert result is not None
        assert result["id"] == conversation.id
        assert result["archived_at"] is None

    @pytest.mark.asyncio
    async def test_list_includes_archived_at(self, db_session: AsyncSession):
        """Test que la liste inclut archived_at"""
        conversations, _ = await ConversationAdminService.get_conversations(
            db=db_session,
            limit=1,
            offset=0
        )

        if conversations:
            # Verifier que archived_at est present dans le dict
            assert "archived_at" in conversations[0]
