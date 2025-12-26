"""
Tests pour les endpoints Admin Messages (soft/hard delete)

Execution: docker-compose exec app python -m pytest tests/admin/test_admin_messages.py -v
"""
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Message, Conversation, User

pytestmark = pytest.mark.asyncio


# =============================================================================
# FIXTURES
# =============================================================================

@pytest_asyncio.fixture
async def test_conversation_with_messages(db_session: AsyncSession, admin_user: User):
    """
    Cree une conversation avec des messages pour les tests.
    Inclut des messages soft-deleted.
    """
    # Creer une conversation
    conversation = Conversation(
        user_id=admin_user.id,
        title=f"Test Conv Messages {uuid.uuid4().hex[:8]}",
        mode_id=1
    )
    db_session.add(conversation)
    await db_session.commit()
    await db_session.refresh(conversation)

    # Creer des messages (un par un pour eviter probleme UUID batch)
    messages = []

    # Message user normal
    msg1 = Message(
        conversation_id=conversation.id,
        sender_type="user",
        content="Message utilisateur normal"
    )
    db_session.add(msg1)
    await db_session.commit()
    await db_session.refresh(msg1)
    messages.append(msg1)

    # Message assistant normal
    msg2 = Message(
        conversation_id=conversation.id,
        sender_type="assistant",
        content="Reponse assistant normale"
    )
    db_session.add(msg2)
    await db_session.commit()
    await db_session.refresh(msg2)
    messages.append(msg2)

    # Message user soft-deleted
    msg3 = Message(
        conversation_id=conversation.id,
        sender_type="user",
        content="Message utilisateur supprime",
        deleted_at=datetime.now(timezone.utc)
    )
    db_session.add(msg3)
    await db_session.commit()
    await db_session.refresh(msg3)
    messages.append(msg3)

    # Message assistant soft-deleted
    msg4 = Message(
        conversation_id=conversation.id,
        sender_type="assistant",
        content="Reponse assistant supprimee",
        deleted_at=datetime.now(timezone.utc)
    )
    db_session.add(msg4)
    await db_session.commit()
    await db_session.refresh(msg4)
    messages.append(msg4)

    yield {"conversation": conversation, "messages": messages}

    # Cleanup
    try:
        for msg in messages:
            try:
                await db_session.delete(msg)
                await db_session.commit()
            except Exception:
                await db_session.rollback()
        await db_session.delete(conversation)
        await db_session.commit()
    except Exception:
        await db_session.rollback()


# =============================================================================
# TESTS ENDPOINT GET /admin/messages
# =============================================================================

class TestAdminMessagesEndpoint:
    """Tests pour GET /admin/messages avec filtres"""

    async def test_get_messages_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401"""
        response = await async_client.get("/admin/messages")
        assert response.status_code == 401

    async def test_get_messages_default_excludes_deleted(
        self,
        async_client: AsyncClient,
        admin_headers: dict,
        test_conversation_with_messages
    ):
        """Par defaut, les messages supprimes ne sont pas inclus"""
        conv_id = test_conversation_with_messages["conversation"].id
        response = await async_client.get(
            f"/admin/messages?conversation_id={conv_id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Seulement les 2 messages non supprimes
        non_deleted = [m for m in data if m.get("deleted_at") is None]
        assert len(non_deleted) == 2

    async def test_get_messages_with_include_deleted(
        self,
        async_client: AsyncClient,
        admin_headers: dict,
        test_conversation_with_messages
    ):
        """include_deleted=true retourne tous les messages"""
        conv_id = test_conversation_with_messages["conversation"].id
        response = await async_client.get(
            f"/admin/messages?conversation_id={conv_id}&include_deleted=true",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Tous les 4 messages
        assert len(data) == 4


# =============================================================================
# TESTS ENDPOINT GET /admin/messages/deleted
# =============================================================================

class TestAdminDeletedMessagesEndpoint:
    """Tests pour GET /admin/messages/deleted"""

    async def test_get_deleted_messages_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401"""
        response = await async_client.get("/admin/messages/deleted")
        assert response.status_code == 401

    async def test_get_deleted_messages_only(
        self,
        async_client: AsyncClient,
        admin_headers: dict,
        test_conversation_with_messages
    ):
        """Retourne uniquement les messages supprimes"""
        conv_id = test_conversation_with_messages["conversation"].id
        response = await async_client.get(
            f"/admin/messages/deleted?conversation_id={conv_id}",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Seulement les 2 messages supprimes
        assert len(data) == 2
        for msg in data:
            assert msg.get("deleted_at") is not None


# =============================================================================
# TESTS ENDPOINT DELETE /admin/messages/{id} (hard delete)
# =============================================================================

class TestAdminHardDeleteMessage:
    """Tests pour DELETE /admin/messages/{message_id}"""

    async def test_hard_delete_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401"""
        fake_id = uuid.uuid4()
        response = await async_client.delete(f"/admin/messages/{fake_id}")
        assert response.status_code == 401

    async def test_hard_delete_not_found(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """Message inexistant retourne 404"""
        fake_id = uuid.uuid4()
        response = await async_client.delete(
            f"/admin/messages/{fake_id}",
            headers=admin_headers
        )
        assert response.status_code == 404

    async def test_hard_delete_success(
        self,
        async_client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
        admin_user: User
    ):
        """Hard delete supprime physiquement le message"""
        # Creer une conversation et un message temporaire
        conversation = Conversation(
            user_id=admin_user.id,
            title="Conv pour hard delete",
            mode_id=1
        )
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        message = Message(
            conversation_id=conversation.id,
            sender_type="user",
            content="Message a supprimer physiquement"
        )
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)
        message_id = message.id

        # Hard delete
        response = await async_client.delete(
            f"/admin/messages/{message_id}",
            headers=admin_headers
        )
        assert response.status_code == 204

        # Verifier que le message n'existe plus
        result = await db_session.execute(
            select(Message).where(Message.id == message_id)
        )
        assert result.scalar_one_or_none() is None

        # Cleanup conversation
        await db_session.delete(conversation)
        await db_session.commit()


# =============================================================================
# TESTS ENDPOINT POST /admin/messages/{id}/restore
# =============================================================================

class TestAdminRestoreMessage:
    """Tests pour POST /admin/messages/{message_id}/restore"""

    async def test_restore_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401"""
        fake_id = uuid.uuid4()
        response = await async_client.post(f"/admin/messages/{fake_id}/restore")
        assert response.status_code == 401

    async def test_restore_not_found(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """Message inexistant retourne 404"""
        fake_id = uuid.uuid4()
        response = await async_client.post(
            f"/admin/messages/{fake_id}/restore",
            headers=admin_headers
        )
        assert response.status_code == 404

    async def test_restore_not_deleted_returns_404(
        self,
        async_client: AsyncClient,
        admin_headers: dict,
        test_conversation_with_messages
    ):
        """Message non supprime retourne 404"""
        # Prendre un message non supprime
        messages = test_conversation_with_messages["messages"]
        non_deleted = [m for m in messages if m.deleted_at is None][0]

        response = await async_client.post(
            f"/admin/messages/{non_deleted.id}/restore",
            headers=admin_headers
        )
        assert response.status_code == 404
        assert "not deleted" in response.json()["detail"]

    async def test_restore_success(
        self,
        async_client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
        admin_user: User
    ):
        """Restore annule le soft delete"""
        # Creer une conversation et un message soft-deleted
        conversation = Conversation(
            user_id=admin_user.id,
            title="Conv pour restore",
            mode_id=1
        )
        db_session.add(conversation)
        await db_session.commit()
        await db_session.refresh(conversation)

        message = Message(
            conversation_id=conversation.id,
            sender_type="user",
            content="Message a restaurer",
            deleted_at=datetime.now(timezone.utc)
        )
        db_session.add(message)
        await db_session.commit()
        await db_session.refresh(message)
        message_id = message.id

        # Restore
        response = await async_client.post(
            f"/admin/messages/{message_id}/restore",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(message_id)
        assert data["deleted_at"] is None

        # Cleanup
        await db_session.delete(message)
        await db_session.delete(conversation)
        await db_session.commit()
