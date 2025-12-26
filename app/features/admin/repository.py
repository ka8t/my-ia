"""
Repository Admin

Opérations de base de données pour l'administration.
"""
import uuid
import logging
from typing import Optional, List, Type, TypeVar, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, desc

from app.models import (
    User, Role, ConversationMode, ResourceType, AuditAction,
    UserPreference, Conversation, Message, Document, Session, AuditLog
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class AdminRepository:
    """Repository pour les opérations d'administration"""

    # ========================================================================
    # Opérations génériques CRUD
    # ========================================================================

    @staticmethod
    async def get_all(
        db: AsyncSession,
        model: Type[T],
        limit: int = 50,
        offset: int = 0,
        order_by: Any = None
    ) -> List[T]:
        """Récupère tous les éléments d'un modèle"""
        query = select(model)
        if order_by is not None:
            query = query.order_by(order_by)
        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        model: Type[T],
        id: Any
    ) -> Optional[T]:
        """Récupère un élément par ID"""
        result = await db.execute(select(model).where(model.id == id))
        return result.scalar_one_or_none()

    @staticmethod
    async def count(db: AsyncSession, model: Type[T]) -> int:
        """Compte le nombre d'éléments"""
        result = await db.execute(select(func.count(model.id)))
        return result.scalar()

    @staticmethod
    async def delete_by_id(db: AsyncSession, model: Type[T], id: Any) -> bool:
        """Supprime un élément par ID"""
        item = await AdminRepository.get_by_id(db, model, id)
        if not item:
            return False

        await db.delete(item)
        await db.commit()
        return True

    # ========================================================================
    # Audit Logs
    # ========================================================================

    @staticmethod
    async def get_audit_logs(
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None,
        action_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AuditLog]:
        """Récupère les logs d'audit avec filtres"""
        query = select(AuditLog).order_by(desc(AuditLog.created_at))

        if user_id:
            query = query.where(AuditLog.user_id == user_id)

        if action_name:
            # Récupérer l'action_id depuis le nom
            action_result = await db.execute(
                select(AuditAction).where(AuditAction.name == action_name)
            )
            action_obj = action_result.scalar_one_or_none()
            if action_obj:
                query = query.where(AuditLog.action_id == action_obj.id)

        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        return result.scalars().all()

    # ========================================================================
    # Conversations
    # ========================================================================

    @staticmethod
    async def get_conversations(
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None,
        mode_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Conversation]:
        """Récupère les conversations avec filtres"""
        query = select(Conversation).order_by(Conversation.updated_at.desc())

        if user_id:
            query = query.where(Conversation.user_id == user_id)
        if mode_id:
            query = query.where(Conversation.mode_id == mode_id)

        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        return result.scalars().all()

    # ========================================================================
    # Messages
    # ========================================================================

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        conversation_id: Optional[uuid.UUID] = None,
        sender_type: Optional[str] = None,
        include_deleted: bool = False,
        deleted_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Message]:
        """
        Récupère les messages avec filtres.

        Args:
            db: Session de base de données
            conversation_id: Filtrer par conversation
            sender_type: Filtrer par type d'expéditeur
            include_deleted: Inclure les messages supprimés
            deleted_only: Ne montrer que les messages supprimés
            limit: Limite de résultats
            offset: Décalage pour pagination

        Returns:
            Liste des messages
        """
        query = select(Message).order_by(Message.created_at.desc())

        if conversation_id:
            query = query.where(Message.conversation_id == conversation_id)
        if sender_type:
            query = query.where(Message.sender_type == sender_type)

        # Gestion des messages supprimés
        if deleted_only:
            query = query.where(Message.deleted_at.isnot(None))
        elif not include_deleted:
            query = query.where(Message.deleted_at.is_(None))

        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def hard_delete_message(
        db: AsyncSession,
        message_id: uuid.UUID
    ) -> bool:
        """
        Supprime physiquement un message (admin uniquement).

        Args:
            db: Session de base de données
            message_id: ID du message

        Returns:
            True si supprimé, False sinon
        """
        result = await db.execute(
            delete(Message).where(Message.id == message_id)
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def restore_message(
        db: AsyncSession,
        message_id: uuid.UUID
    ) -> Optional[Message]:
        """
        Restaure un message supprimé (soft delete).

        Args:
            db: Session de base de données
            message_id: ID du message

        Returns:
            Message restauré ou None
        """
        result = await db.execute(
            select(Message).where(Message.id == message_id)
        )
        message = result.scalar_one_or_none()

        if message and message.deleted_at is not None:
            message.deleted_at = None
            await db.commit()
            await db.refresh(message)
            return message

        return None

    # ========================================================================
    # Documents
    # ========================================================================

    @staticmethod
    async def get_documents(
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None,
        file_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Document]:
        """Récupère les documents avec filtres"""
        query = select(Document).order_by(Document.created_at.desc())

        if user_id:
            query = query.where(Document.user_id == user_id)
        if file_type:
            query = query.where(Document.file_type == file_type)

        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        return result.scalars().all()

    # ========================================================================
    # Sessions
    # ========================================================================

    @staticmethod
    async def get_sessions(
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Session]:
        """Récupère les sessions avec filtres"""
        from datetime import datetime

        query = select(Session).order_by(Session.created_at.desc())

        if user_id:
            query = query.where(Session.user_id == user_id)
        if active_only:
            query = query.where(Session.expires_at > datetime.utcnow())

        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def revoke_all_user_sessions(
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> int:
        """Révoque toutes les sessions d'un utilisateur"""
        count_result = await db.execute(
            select(func.count(Session.id)).where(Session.user_id == user_id)
        )
        count = count_result.scalar()

        await db.execute(delete(Session).where(Session.user_id == user_id))
        await db.commit()

        return count
