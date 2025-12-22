"""
Service Admin

Logique métier pour l'administration.
"""
import uuid
import logging
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException

from app.models import (
    User, Role, ConversationMode, ResourceType, AuditAction,
    UserPreference, Conversation, Message, Document, Session, AuditLog
)
from app.features.admin.repository import AdminRepository
from app.core.deps import get_chroma_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class AdminService:
    """Service pour les opérations d'administration"""

    # ========================================================================
    # Statistiques
    # ========================================================================

    @staticmethod
    async def get_stats(db: AsyncSession) -> Dict[str, Any]:
        """Récupère les statistiques globales du système"""
        users_count = await AdminRepository.count(db, User)
        conversations_count = await AdminRepository.count(db, Conversation)
        documents_count = await AdminRepository.count(db, Document)

        return {
            "users": {"total": users_count},
            "conversations": {"total": conversations_count},
            "documents": {"total": documents_count}
        }

    # ========================================================================
    # CRUD Roles
    # ========================================================================

    @staticmethod
    async def create_role(db: AsyncSession, role_data: dict) -> Role:
        """Crée un nouveau rôle"""
        # Vérification anti-doublon
        existing = await db.execute(select(Role).where(Role.name == role_data['name']))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"Role with name '{role_data['name']}' already exists"
            )

        new_role = Role(**role_data)
        db.add(new_role)
        await db.commit()
        await db.refresh(new_role)

        return new_role

    @staticmethod
    async def update_role(db: AsyncSession, role_id: int, role_data: dict) -> Role:
        """Met à jour un rôle"""
        role = await AdminRepository.get_by_id(db, Role, role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # Vérification anti-doublon si le nom change
        if 'name' in role_data and role_data['name'] != role.name:
            existing = await db.execute(select(Role).where(Role.name == role_data['name']))
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=409,
                    detail=f"Role with name '{role_data['name']}' already exists"
                )

        for key, value in role_data.items():
            setattr(role, key, value)

        await db.commit()
        await db.refresh(role)

        return role

    @staticmethod
    async def delete_role(db: AsyncSession, role_id: int) -> bool:
        """Supprime un rôle"""
        role = await AdminRepository.get_by_id(db, Role, role_id)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # Vérifier si le rôle est utilisé
        users_count = await db.execute(select(func.count(User.id)).where(User.role_id == role_id))
        if users_count.scalar() > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete role '{role.name}': it is assigned to {users_count.scalar()} user(s)"
            )

        await db.delete(role)
        await db.commit()

        return True

    # ========================================================================
    # CRUD Conversation Modes
    # ========================================================================

    @staticmethod
    async def create_conversation_mode(db: AsyncSession, mode_data: dict) -> ConversationMode:
        """Crée un mode de conversation"""
        existing = await db.execute(
            select(ConversationMode).where(ConversationMode.name == mode_data['name'])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"Conversation mode with name '{mode_data['name']}' already exists"
            )

        new_mode = ConversationMode(**mode_data)
        db.add(new_mode)
        await db.commit()
        await db.refresh(new_mode)

        return new_mode

    @staticmethod
    async def update_conversation_mode(
        db: AsyncSession,
        mode_id: int,
        mode_data: dict
    ) -> ConversationMode:
        """Met à jour un mode de conversation"""
        mode = await AdminRepository.get_by_id(db, ConversationMode, mode_id)
        if not mode:
            raise HTTPException(status_code=404, detail="Conversation mode not found")

        if 'name' in mode_data and mode_data['name'] != mode.name:
            existing = await db.execute(
                select(ConversationMode).where(ConversationMode.name == mode_data['name'])
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=409,
                    detail=f"Conversation mode with name '{mode_data['name']}' already exists"
                )

        for key, value in mode_data.items():
            setattr(mode, key, value)

        await db.commit()
        await db.refresh(mode)

        return mode

    @staticmethod
    async def delete_conversation_mode(db: AsyncSession, mode_id: int) -> bool:
        """Supprime un mode de conversation"""
        mode = await AdminRepository.get_by_id(db, ConversationMode, mode_id)
        if not mode:
            raise HTTPException(status_code=404, detail="Conversation mode not found")

        # Vérifier si le mode est utilisé
        conversations_count = await db.execute(
            select(func.count(Conversation.id)).where(Conversation.mode_id == mode_id)
        )
        if conversations_count.scalar() > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete conversation mode '{mode.name}': it is used in {conversations_count.scalar()} conversation(s)"
            )

        await db.delete(mode)
        await db.commit()

        return True

    # ========================================================================
    # Documents - Suppression avec ChromaDB
    # ========================================================================

    @staticmethod
    async def delete_document(db: AsyncSession, document_id: uuid.UUID) -> bool:
        """Supprime un document (aussi dans ChromaDB si possible)"""
        document = await AdminRepository.get_by_id(db, Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Tentative de suppression dans ChromaDB
        try:
            chroma_client = get_chroma_client()
            if chroma_client:
                collection = chroma_client.get_collection(name=settings.collection_name)
                collection.delete(where={"file_hash": document.file_hash})
                logger.info(f"Document chunks deleted from ChromaDB: {document.file_hash}")
        except Exception as e:
            logger.warning(f"Could not delete document from ChromaDB: {e}")

        # Suppression de la base de données
        await db.delete(document)
        await db.commit()

        return True
