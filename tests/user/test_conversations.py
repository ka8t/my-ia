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
