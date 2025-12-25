"""
Service Conversations

Logique métier pour la gestion des conversations utilisateur.
"""
import uuid
import logging
from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation, Message
from app.features.conversations.repository import ConversationRepository, MessageRepository
from app.features.conversations.schemas import (
    ConversationCreate,
    ConversationUpdate,
    ConversationRead,
    ConversationDetail,
    MessageRead,
    MessageCreate,
    ChatResponse
)
from app.common.utils.chroma import search_context
from app.common.utils.ollama import generate_response
from app.features.chat.service import CHATBOT_SYSTEM_PROMPT, ASSISTANT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class ConversationService:
    """Service pour la gestion des conversations"""

    @staticmethod
    async def list_conversations(
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[ConversationRead], int]:
        """
        Liste les conversations de l'utilisateur.

        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            limit: Nombre max de résultats
            offset: Décalage pour pagination

        Returns:
            Tuple (liste des conversations, total)
        """
        conversations, total = await ConversationRepository.list_by_user(
            db, user_id, limit, offset
        )

        items = []
        for conv in conversations:
            messages_count = await ConversationRepository.count_messages(db, conv.id)
            items.append(ConversationRead(
                id=conv.id,
                title=conv.title,
                mode_id=conv.mode_id,
                mode_name=conv.mode.name if conv.mode else None,
                messages_count=messages_count,
                created_at=conv.created_at,
                updated_at=conv.updated_at
            ))

        return items, total

    @staticmethod
    async def get_conversation(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[ConversationDetail]:
        """
        Récupère une conversation avec ses messages.

        Args:
            db: Session de base de données
            conversation_id: ID de la conversation
            user_id: ID de l'utilisateur

        Returns:
            Détails de la conversation ou None
        """
        conversation = await ConversationRepository.get_by_id(
            db, conversation_id, user_id
        )

        if not conversation:
            return None

        messages = [
            MessageRead(
                id=msg.id,
                sender_type=msg.sender_type,
                content=msg.content,
                sources=msg.sources,
                created_at=msg.created_at
            )
            for msg in conversation.messages
        ]

        return ConversationDetail(
            id=conversation.id,
            title=conversation.title,
            mode_id=conversation.mode_id,
            mode_name=conversation.mode.name if conversation.mode else None,
            messages=messages,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )

    @staticmethod
    async def create_conversation(
        db: AsyncSession,
        user_id: uuid.UUID,
        data: ConversationCreate
    ) -> ConversationRead:
        """
        Crée une nouvelle conversation.

        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            data: Données de création

        Returns:
            Conversation créée
        """
        conversation = await ConversationRepository.create(
            db,
            user_id=user_id,
            title=data.title,
            mode_id=data.mode_id
        )

        logger.info(f"Conversation created: {conversation.id} for user {user_id}")

        return ConversationRead(
            id=conversation.id,
            title=conversation.title,
            mode_id=conversation.mode_id,
            mode_name=conversation.mode.name if conversation.mode else None,
            messages_count=0,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )

    @staticmethod
    async def update_conversation(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        data: ConversationUpdate
    ) -> Optional[ConversationRead]:
        """
        Met à jour une conversation.

        Args:
            db: Session de base de données
            conversation_id: ID de la conversation
            user_id: ID de l'utilisateur
            data: Données de mise à jour

        Returns:
            Conversation mise à jour ou None
        """
        conversation = await ConversationRepository.get_by_id(
            db, conversation_id, user_id
        )

        if not conversation:
            return None

        updated = await ConversationRepository.update(
            db, conversation, title=data.title
        )

        messages_count = await ConversationRepository.count_messages(db, updated.id)

        logger.info(f"Conversation updated: {conversation_id}")

        return ConversationRead(
            id=updated.id,
            title=updated.title,
            mode_id=updated.mode_id,
            mode_name=updated.mode.name if updated.mode else None,
            messages_count=messages_count,
            created_at=updated.created_at,
            updated_at=updated.updated_at
        )

    @staticmethod
    async def delete_conversation(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """
        Supprime une conversation.

        Args:
            db: Session de base de données
            conversation_id: ID de la conversation
            user_id: ID de l'utilisateur

        Returns:
            True si supprimée, False sinon
        """
        deleted = await ConversationRepository.delete(db, conversation_id, user_id)

        if deleted:
            logger.info(f"Conversation deleted: {conversation_id}")

        return deleted

    @staticmethod
    async def add_message(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        data: MessageCreate
    ) -> Optional[MessageRead]:
        """
        Ajoute un message à une conversation.

        Args:
            db: Session de base de données
            conversation_id: ID de la conversation
            user_id: ID de l'utilisateur propriétaire
            data: Données du message

        Returns:
            Message créé ou None si conversation non trouvée
        """
        # Vérifier que la conversation appartient à l'utilisateur
        conversation = await ConversationRepository.get_by_id(
            db, conversation_id, user_id
        )

        if not conversation:
            return None

        message = await MessageRepository.create(
            db,
            conversation_id=conversation_id,
            sender_type=data.sender_type,
            content=data.content,
            sources=data.sources
        )

        return MessageRead(
            id=message.id,
            sender_type=message.sender_type,
            content=message.content,
            sources=message.sources,
            created_at=message.created_at
        )

    @staticmethod
    async def get_or_create_conversation(
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: Optional[str],
        title: str = "Nouvelle conversation",
        mode_id: int = 1
    ) -> Conversation:
        """
        Récupère ou crée une conversation basée sur session_id.

        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            session_id: ID de session (peut être un UUID de conversation)
            title: Titre par défaut si création
            mode_id: Mode de conversation

        Returns:
            Conversation existante ou nouvelle
        """
        # Si session_id est fourni et valide, essayer de récupérer la conversation
        if session_id:
            try:
                conv_id = uuid.UUID(session_id)
                existing = await ConversationRepository.get_by_id(db, conv_id, user_id)
                if existing:
                    return existing
            except (ValueError, TypeError):
                pass

        # Créer une nouvelle conversation
        return await ConversationRepository.create(
            db, user_id=user_id, title=title, mode_id=mode_id
        )

    @staticmethod
    async def chat_and_save(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        query: str
    ) -> Optional[ChatResponse]:
        """
        Envoie un message, génère une réponse RAG et sauvegarde les deux.

        Args:
            db: Session de base de données
            conversation_id: ID de la conversation
            user_id: ID de l'utilisateur
            query: Question de l'utilisateur

        Returns:
            ChatResponse avec les messages sauvegardés ou None si conversation non trouvée
        """
        # Vérifier que la conversation appartient à l'utilisateur
        conversation = await ConversationRepository.get_by_id(
            db, conversation_id, user_id
        )

        if not conversation:
            return None

        # Sauvegarder le message utilisateur
        user_message = await MessageRepository.create(
            db,
            conversation_id=conversation_id,
            sender_type="user",
            content=query
        )

        # Choisir le prompt selon le mode
        if conversation.mode and conversation.mode.name == "assistant":
            system_prompt = ASSISTANT_SYSTEM_PROMPT
        else:
            system_prompt = CHATBOT_SYSTEM_PROMPT

        # Recherche de contexte RAG
        context = await search_context(query)

        # Générer la réponse
        response_text = await generate_response(
            query,
            system_prompt,
            context,
            stream=False
        )

        # Préparer les sources
        sources = None
        if context:
            sources = {
                "items": [
                    {"source": ctx.get("metadata", {}).get("source", "Unknown")}
                    for ctx in context
                ]
            }

        # Sauvegarder la réponse assistant
        assistant_message = await MessageRepository.create(
            db,
            conversation_id=conversation_id,
            sender_type="assistant",
            content=response_text,
            sources=sources
        )

        logger.info(f"Chat saved in conversation {conversation_id}")

        return ChatResponse(
            response=response_text,
            sources=[{"source": ctx.get("metadata", {}).get("source", "Unknown")} for ctx in context] if context else None,
            user_message=MessageRead(
                id=user_message.id,
                sender_type=user_message.sender_type,
                content=user_message.content,
                sources=user_message.sources,
                created_at=user_message.created_at
            ),
            assistant_message=MessageRead(
                id=assistant_message.id,
                sender_type=assistant_message.sender_type,
                content=assistant_message.content,
                sources=assistant_message.sources,
                created_at=assistant_message.created_at
            )
        )
