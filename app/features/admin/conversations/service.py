"""
Service Admin Conversations

Logique métier pour la gestion avancée des conversations.
"""
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete
from sqlalchemy.orm import joinedload
from fastapi import HTTPException

from app.models import Conversation, Message, User, ConversationMode

logger = logging.getLogger(__name__)


class ConversationAdminService:
    """Service pour la gestion admin des conversations"""

    # ========================================================================
    # LECTURE
    # ========================================================================

    @staticmethod
    async def get_conversations(
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None,
        mode_id: Optional[int] = None,
        search: Optional[str] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Récupère les conversations avec filtres et pagination.

        Returns:
            Tuple (liste de conversations enrichies, total)
        """
        # Requête de base avec jointures
        base_query = select(Conversation).options(
            joinedload(Conversation.user),
            joinedload(Conversation.mode)
        )

        # Application des filtres
        conditions = []
        if user_id:
            conditions.append(Conversation.user_id == user_id)
        if mode_id:
            conditions.append(Conversation.mode_id == mode_id)
        if search:
            conditions.append(Conversation.title.ilike(f"%{search}%"))
        if created_after:
            conditions.append(Conversation.created_at >= created_after)
        if created_before:
            conditions.append(Conversation.created_at <= created_before)

        if conditions:
            base_query = base_query.where(and_(*conditions))

        # Comptage total
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Requête paginée
        paginated_query = (
            base_query
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(paginated_query)
        conversations = result.scalars().unique().all()

        # Enrichir avec le comptage des messages
        conversations_data = []
        for conv in conversations:
            msg_count_result = await db.execute(
                select(func.count(Message.id)).where(Message.conversation_id == conv.id)
            )
            messages_count = msg_count_result.scalar() or 0

            conversations_data.append({
                "id": conv.id,
                "user_id": conv.user_id,
                "user_email": conv.user.email if conv.user else "",
                "title": conv.title,
                "mode_id": conv.mode_id,
                "mode_name": conv.mode.name if conv.mode else "",
                "messages_count": messages_count,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
                "archived_at": conv.archived_at
            })

        return conversations_data, total

    @staticmethod
    async def get_conversation_detail(
        db: AsyncSession,
        conversation_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Récupère les détails d'une conversation avec ses messages.

        Args:
            db: Session de base de données
            conversation_id: UUID de la conversation

        Returns:
            Dictionnaire avec conversation et messages

        Raises:
            HTTPException 404 si la conversation n'existe pas
        """
        # Récupérer la conversation
        query = select(Conversation).options(
            joinedload(Conversation.user),
            joinedload(Conversation.mode),
            joinedload(Conversation.messages)
        ).where(Conversation.id == conversation_id)

        result = await db.execute(query)
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Formater les messages
        messages = [
            {
                "id": msg.id,
                "sender_type": msg.sender_type,
                "content": msg.content,
                "sources": msg.sources,
                "created_at": msg.created_at
            }
            for msg in sorted(conversation.messages, key=lambda m: m.created_at)
        ]

        return {
            "id": conversation.id,
            "user_id": conversation.user_id,
            "user_email": conversation.user.email if conversation.user else "",
            "title": conversation.title,
            "mode_id": conversation.mode_id,
            "mode_name": conversation.mode.name if conversation.mode else "",
            "messages_count": len(messages),
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
            "archived_at": conversation.archived_at,
            "messages": messages
        }

    # ========================================================================
    # SUPPRESSION
    # ========================================================================

    @staticmethod
    async def delete_conversation(
        db: AsyncSession,
        conversation_id: uuid.UUID
    ) -> bool:
        """
        Supprime une conversation et ses messages.

        Args:
            db: Session de base de données
            conversation_id: UUID de la conversation

        Returns:
            True si supprimée

        Raises:
            HTTPException 404 si la conversation n'existe pas
        """
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        await db.delete(conversation)
        await db.commit()

        logger.info(f"Conversation deleted: {conversation_id}")
        return True

    @staticmethod
    async def delete_user_conversations(
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> int:
        """
        Supprime toutes les conversations d'un utilisateur.

        Args:
            db: Session de base de données
            user_id: UUID de l'utilisateur

        Returns:
            Nombre de conversations supprimées

        Raises:
            HTTPException 404 si l'utilisateur n'existe pas
        """
        # Vérifier que l'utilisateur existe
        user_result = await db.execute(select(User).where(User.id == user_id))
        if not user_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="User not found")

        # Compter avant suppression
        count_result = await db.execute(
            select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
        )
        count = count_result.scalar() or 0

        # Supprimer
        await db.execute(
            delete(Conversation).where(Conversation.user_id == user_id)
        )
        await db.commit()

        logger.info(f"Deleted {count} conversations for user {user_id}")
        return count

    # ========================================================================
    # EXPORT
    # ========================================================================

    @staticmethod
    async def export_conversation(
        db: AsyncSession,
        conversation_id: uuid.UUID
    ) -> str:
        """
        Exporte une conversation complète en JSON.

        Args:
            db: Session de base de données
            conversation_id: UUID de la conversation

        Returns:
            JSON string de la conversation

        Raises:
            HTTPException 404 si la conversation n'existe pas
        """
        detail = await ConversationAdminService.get_conversation_detail(
            db, conversation_id
        )

        export_data = {
            "conversation": {
                "id": str(detail["id"]),
                "user_id": str(detail["user_id"]),
                "user_email": detail["user_email"],
                "title": detail["title"],
                "mode": detail["mode_name"],
                "created_at": detail["created_at"].isoformat(),
                "updated_at": detail["updated_at"].isoformat()
            },
            "messages": [
                {
                    "id": str(msg["id"]),
                    "sender": msg["sender_type"],
                    "content": msg["content"],
                    "sources": msg["sources"],
                    "timestamp": msg["created_at"].isoformat()
                }
                for msg in detail["messages"]
            ],
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "messages_count": detail["messages_count"]
        }

        return json.dumps(export_data, indent=2, ensure_ascii=False)

    # ========================================================================
    # ARCHIVAGE
    # ========================================================================

    @staticmethod
    async def archive_conversation(
        db: AsyncSession,
        conversation_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Archive une conversation (admin peut archiver n'importe quelle conversation).

        Args:
            db: Session de base de données
            conversation_id: UUID de la conversation

        Returns:
            Dictionnaire avec la conversation mise à jour

        Raises:
            HTTPException 404 si la conversation n'existe pas
        """
        result = await db.execute(
            select(Conversation).options(
                joinedload(Conversation.user),
                joinedload(Conversation.mode)
            ).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        conversation.archived_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(conversation)

        logger.info(f"Conversation archived by admin: {conversation_id}")

        return {
            "id": conversation.id,
            "user_id": conversation.user_id,
            "user_email": conversation.user.email if conversation.user else "",
            "title": conversation.title,
            "mode_id": conversation.mode_id,
            "mode_name": conversation.mode.name if conversation.mode else "",
            "archived_at": conversation.archived_at,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at
        }

    @staticmethod
    async def unarchive_conversation(
        db: AsyncSession,
        conversation_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Désarchive une conversation (admin peut désarchiver n'importe quelle conversation).

        Args:
            db: Session de base de données
            conversation_id: UUID de la conversation

        Returns:
            Dictionnaire avec la conversation mise à jour

        Raises:
            HTTPException 404 si la conversation n'existe pas
        """
        result = await db.execute(
            select(Conversation).options(
                joinedload(Conversation.user),
                joinedload(Conversation.mode)
            ).where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        conversation.archived_at = None
        await db.commit()
        await db.refresh(conversation)

        logger.info(f"Conversation unarchived by admin: {conversation_id}")

        return {
            "id": conversation.id,
            "user_id": conversation.user_id,
            "user_email": conversation.user.email if conversation.user else "",
            "title": conversation.title,
            "mode_id": conversation.mode_id,
            "mode_name": conversation.mode.name if conversation.mode else "",
            "archived_at": conversation.archived_at,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at
        }
