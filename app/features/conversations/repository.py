"""
Repository Conversations

Opérations de base de données pour les conversations utilisateur.
"""
import uuid
from typing import Optional, List, Tuple

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Conversation, Message, ConversationMode


class ConversationRepository:
    """Repository pour les opérations CRUD sur les conversations"""

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Conversation]:
        """
        Récupère une conversation par son ID pour un utilisateur donné.

        Args:
            db: Session de base de données
            conversation_id: ID de la conversation
            user_id: ID de l'utilisateur propriétaire

        Returns:
            Conversation ou None si non trouvée
        """
        result = await db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .options(selectinload(Conversation.mode))
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_user(
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Conversation], int]:
        """
        Liste les conversations d'un utilisateur avec pagination.

        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            limit: Nombre max de résultats
            offset: Décalage pour la pagination

        Returns:
            Tuple (liste des conversations, total)
        """
        # Compte total
        count_query = select(func.count()).select_from(Conversation).where(
            Conversation.user_id == user_id
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Liste paginée avec le mode et le nombre de messages
        query = (
            select(Conversation)
            .options(selectinload(Conversation.mode))
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(query)
        conversations = list(result.scalars().all())

        return conversations, total

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: uuid.UUID,
        title: str,
        mode_id: int = 1
    ) -> Conversation:
        """
        Crée une nouvelle conversation.

        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            title: Titre de la conversation
            mode_id: ID du mode de conversation

        Returns:
            Conversation créée
        """
        conversation = Conversation(
            user_id=user_id,
            title=title,
            mode_id=mode_id
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

        # Charger le mode pour le retour
        await db.refresh(conversation, ["mode"])
        return conversation

    @staticmethod
    async def update(
        db: AsyncSession,
        conversation: Conversation,
        title: Optional[str] = None
    ) -> Conversation:
        """
        Met à jour une conversation.

        Args:
            db: Session de base de données
            conversation: Conversation à modifier
            title: Nouveau titre (optionnel)

        Returns:
            Conversation mise à jour
        """
        if title is not None:
            conversation.title = title

        await db.commit()
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def delete(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """
        Supprime une conversation et ses messages.

        Args:
            db: Session de base de données
            conversation_id: ID de la conversation
            user_id: ID de l'utilisateur propriétaire

        Returns:
            True si supprimée, False si non trouvée
        """
        result = await db.execute(
            delete(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def count_messages(
        db: AsyncSession,
        conversation_id: uuid.UUID
    ) -> int:
        """
        Compte le nombre de messages dans une conversation.

        Args:
            db: Session de base de données
            conversation_id: ID de la conversation

        Returns:
            Nombre de messages
        """
        result = await db.execute(
            select(func.count()).select_from(Message).where(
                Message.conversation_id == conversation_id
            )
        )
        return result.scalar() or 0


class MessageRepository:
    """Repository pour les opérations sur les messages"""

    @staticmethod
    async def create(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        sender_type: str,
        content: str,
        sources: Optional[dict] = None
    ) -> Message:
        """
        Crée un nouveau message.

        Args:
            db: Session de base de données
            conversation_id: ID de la conversation
            sender_type: 'user' ou 'assistant'
            content: Contenu du message
            sources: Sources RAG (optionnel)

        Returns:
            Message créé
        """
        message = Message(
            conversation_id=conversation_id,
            sender_type=sender_type,
            content=content,
            sources=sources
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    @staticmethod
    async def list_by_conversation(
        db: AsyncSession,
        conversation_id: uuid.UUID
    ) -> List[Message]:
        """
        Liste les messages d'une conversation.

        Args:
            db: Session de base de données
            conversation_id: ID de la conversation

        Returns:
            Liste des messages ordonnés par date
        """
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        return list(result.scalars().all())
