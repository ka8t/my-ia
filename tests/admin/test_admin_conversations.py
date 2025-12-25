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
