"""
Tests pour le module Conversations utilisateur

Execution: docker-compose exec app python -m pytest tests/user/test_conversations.py -v
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


class TestConversationsEndpoints:
    """Tests des endpoints /conversations"""

    async def test_list_conversations_requires_auth(self, async_client: AsyncClient):
        """Liste des conversations sans auth retourne 401"""
        response = await async_client.get("/conversations/")
        assert response.status_code == 401

    async def test_list_conversations_empty(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Liste des conversations retourne liste (peut être vide)"""
        response = await async_client.get("/conversations/", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_create_conversation(
        self,
        async_client: AsyncClient,
        user_headers: dict,
        sample_conversation_data: dict
    ):
        """Création d'une conversation"""
        response = await async_client.post(
            "/conversations",
            json=sample_conversation_data,
            headers=user_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_conversation_data["title"]
        assert data["mode_id"] == sample_conversation_data["mode_id"]
        assert "id" in data
        assert "created_at" in data

    async def test_get_conversation(
        self,
        async_client: AsyncClient,
        user_headers: dict,
        sample_conversation_data: dict
    ):
        """Récupération d'une conversation"""
        # Créer d'abord
        create_response = await async_client.post(
            "/conversations",
            json=sample_conversation_data,
            headers=user_headers
        )
        assert create_response.status_code == 201
        conversation_id = create_response.json()["id"]

        # Récupérer
        response = await async_client.get(
            f"/conversations/{conversation_id}",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conversation_id
        assert "messages" in data
        assert isinstance(data["messages"], list)

    async def test_get_conversation_not_found(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Récupération d'une conversation inexistante retourne 404"""
        fake_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/conversations/{fake_id}",
            headers=user_headers
        )
        assert response.status_code == 404

    async def test_update_conversation(
        self,
        async_client: AsyncClient,
        user_headers: dict,
        sample_conversation_data: dict
    ):
        """Mise à jour du titre d'une conversation"""
        # Créer
        create_response = await async_client.post(
            "/conversations",
            json=sample_conversation_data,
            headers=user_headers
        )
        conversation_id = create_response.json()["id"]

        # Modifier
        new_title = "Nouveau titre de conversation"
        response = await async_client.patch(
            f"/conversations/{conversation_id}",
            json={"title": new_title},
            headers=user_headers
        )
        assert response.status_code == 200
        assert response.json()["title"] == new_title

    async def test_delete_conversation(
        self,
        async_client: AsyncClient,
        user_headers: dict,
        sample_conversation_data: dict
    ):
        """Suppression d'une conversation"""
        # Créer
        create_response = await async_client.post(
            "/conversations",
            json=sample_conversation_data,
            headers=user_headers
        )
        conversation_id = create_response.json()["id"]

        # Supprimer
        response = await async_client.delete(
            f"/conversations/{conversation_id}",
            headers=user_headers
        )
        assert response.status_code == 204

        # Vérifier suppression
        get_response = await async_client.get(
            f"/conversations/{conversation_id}",
            headers=user_headers
        )
        assert get_response.status_code == 404

    async def test_add_message_to_conversation(
        self,
        async_client: AsyncClient,
        user_headers: dict,
        sample_conversation_data: dict
    ):
        """Ajout d'un message à une conversation"""
        # Créer conversation
        create_response = await async_client.post(
            "/conversations",
            json=sample_conversation_data,
            headers=user_headers
        )
        conversation_id = create_response.json()["id"]

        # Ajouter message
        message_data = {
            "sender_type": "user",
            "content": "Ceci est un message de test"
        }
        response = await async_client.post(
            f"/conversations/{conversation_id}/messages",
            json=message_data,
            headers=user_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sender_type"] == "user"
        assert data["content"] == message_data["content"]
        assert "response_time" in data
        assert data["response_time"] is None  # Pas de response_time fourni

    async def test_add_message_with_response_time(
        self,
        async_client: AsyncClient,
        user_headers: dict,
        sample_conversation_data: dict
    ):
        """Ajout d'un message avec temps de réponse"""
        # Créer conversation
        create_response = await async_client.post(
            "/conversations",
            json=sample_conversation_data,
            headers=user_headers
        )
        conversation_id = create_response.json()["id"]

        # Ajouter message avec response_time
        message_data = {
            "sender_type": "assistant",
            "content": "Réponse de l'assistant",
            "response_time": 2.5
        }
        response = await async_client.post(
            f"/conversations/{conversation_id}/messages",
            json=message_data,
            headers=user_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["sender_type"] == "assistant"
        assert data["response_time"] == 2.5

    async def test_get_conversation_with_response_times(
        self,
        async_client: AsyncClient,
        user_headers: dict,
        sample_conversation_data: dict
    ):
        """Récupération d'une conversation avec response_time dans les messages"""
        # Créer conversation
        create_response = await async_client.post(
            "/conversations",
            json=sample_conversation_data,
            headers=user_headers
        )
        conversation_id = create_response.json()["id"]

        # Ajouter message user
        await async_client.post(
            f"/conversations/{conversation_id}/messages",
            json={"sender_type": "user", "content": "Question", "response_time": 0.0},
            headers=user_headers
        )

        # Ajouter message assistant avec response_time
        await async_client.post(
            f"/conversations/{conversation_id}/messages",
            json={"sender_type": "assistant", "content": "Réponse", "response_time": 3.2},
            headers=user_headers
        )

        # Récupérer la conversation
        response = await async_client.get(
            f"/conversations/{conversation_id}",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 2
        assert data["messages"][0]["response_time"] == 0.0
        assert data["messages"][1]["response_time"] == 3.2

    async def test_pagination(
        self,
        async_client: AsyncClient,
        user_headers: dict
    ):
        """Test de la pagination des conversations"""
        # Créer plusieurs conversations
        for i in range(3):
            await async_client.post(
                "/conversations",
                json={"title": f"Pagination Test {i}", "mode_id": 1},
                headers=user_headers
            )

        # Test pagination
        response = await async_client.get(
            "/conversations/?limit=2&offset=0",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 2
        assert data["offset"] == 0
        assert len(data["items"]) <= 2


class TestConversationsService:
    """Tests du service Conversations"""

    async def test_create_conversation_service(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test création via service"""
        from app.features.conversations.service import ConversationService
        from app.features.conversations.schemas import ConversationCreate

        data = ConversationCreate(title="Test Service", mode_id=1)
        result = await ConversationService.create_conversation(db_session, user_id, data)

        assert result is not None
        assert result.title == "Test Service"
        assert result.mode_id == 1

    async def test_list_conversations_service(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test liste via service"""
        from app.features.conversations.service import ConversationService

        items, total = await ConversationService.list_conversations(
            db_session, user_id, limit=10, offset=0
        )

        assert isinstance(items, list)
        assert isinstance(total, int)
        assert total >= 0

    async def test_get_conversation_service(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test récupération via service"""
        from app.features.conversations.service import ConversationService
        from app.features.conversations.schemas import ConversationCreate

        # Créer
        data = ConversationCreate(title="Get Test", mode_id=1)
        created = await ConversationService.create_conversation(db_session, user_id, data)

        # Récupérer
        result = await ConversationService.get_conversation(
            db_session, created.id, user_id
        )

        assert result is not None
        assert result.id == created.id
        assert result.title == "Get Test"

    async def test_add_message_service(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test ajout message via service"""
        from app.features.conversations.service import ConversationService
        from app.features.conversations.schemas import ConversationCreate, MessageCreate

        # Créer conversation
        conv_data = ConversationCreate(title="Message Test", mode_id=1)
        conversation = await ConversationService.create_conversation(
            db_session, user_id, conv_data
        )

        # Ajouter message sans response_time
        msg_data = MessageCreate(sender_type="user", content="Hello")
        result = await ConversationService.add_message(
            db_session, conversation.id, user_id, msg_data
        )

        assert result is not None
        assert result.sender_type == "user"
        assert result.content == "Hello"
        assert result.response_time is None

    async def test_add_message_with_response_time_service(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test ajout message avec response_time via service"""
        from app.features.conversations.service import ConversationService
        from app.features.conversations.schemas import ConversationCreate, MessageCreate

        # Créer conversation
        conv_data = ConversationCreate(title="Response Time Test", mode_id=1)
        conversation = await ConversationService.create_conversation(
            db_session, user_id, conv_data
        )

        # Ajouter message avec response_time
        msg_data = MessageCreate(
            sender_type="assistant",
            content="Response with time",
            response_time=4.25
        )
        result = await ConversationService.add_message(
            db_session, conversation.id, user_id, msg_data
        )

        assert result is not None
        assert result.sender_type == "assistant"
        assert result.response_time == 4.25

    async def test_get_conversation_includes_response_time_service(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test que get_conversation retourne les response_time"""
        from app.features.conversations.service import ConversationService
        from app.features.conversations.schemas import ConversationCreate, MessageCreate

        # Créer conversation avec messages
        conv_data = ConversationCreate(title="Full Test", mode_id=1)
        conversation = await ConversationService.create_conversation(
            db_session, user_id, conv_data
        )

        # Ajouter messages
        await ConversationService.add_message(
            db_session, conversation.id, user_id,
            MessageCreate(sender_type="user", content="Q1", response_time=0.0)
        )
        await ConversationService.add_message(
            db_session, conversation.id, user_id,
            MessageCreate(sender_type="assistant", content="A1", response_time=2.8)
        )

        # Récupérer et vérifier
        result = await ConversationService.get_conversation(
            db_session, conversation.id, user_id
        )

        assert result is not None
        assert len(result.messages) == 2
        assert result.messages[0].response_time == 0.0
        assert result.messages[1].response_time == 2.8
