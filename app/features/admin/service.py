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
    # CRUD Resource Types
    # ========================================================================

    @staticmethod
    async def create_resource_type(db: AsyncSession, type_data: dict) -> ResourceType:
        """Crée un type de ressource"""
        existing = await db.execute(
            select(ResourceType).where(ResourceType.name == type_data['name'])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"Resource type with name '{type_data['name']}' already exists"
            )

        new_type = ResourceType(**type_data)
        db.add(new_type)
        await db.commit()
        await db.refresh(new_type)

        return new_type

    @staticmethod
    async def update_resource_type(
        db: AsyncSession,
        type_id: int,
        type_data: dict
    ) -> ResourceType:
        """Met à jour un type de ressource"""
        resource_type = await AdminRepository.get_by_id(db, ResourceType, type_id)
        if not resource_type:
            raise HTTPException(status_code=404, detail="Resource type not found")

        if 'name' in type_data and type_data['name'] != resource_type.name:
            existing = await db.execute(
                select(ResourceType).where(ResourceType.name == type_data['name'])
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=409,
                    detail=f"Resource type with name '{type_data['name']}' already exists"
                )

        for key, value in type_data.items():
            setattr(resource_type, key, value)

        await db.commit()
        await db.refresh(resource_type)

        return resource_type

    @staticmethod
    async def delete_resource_type(db: AsyncSession, type_id: int) -> bool:
        """Supprime un type de ressource"""
        resource_type = await AdminRepository.get_by_id(db, ResourceType, type_id)
        if not resource_type:
            raise HTTPException(status_code=404, detail="Resource type not found")

        # Vérifier si le type est utilisé dans les audit logs
        usage_count = await db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.resource_type_id == type_id)
        )
        if usage_count.scalar() > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete resource type: it is used in {usage_count.scalar()} audit log(s)"
            )

        await db.delete(resource_type)
        await db.commit()

        return True

    # ========================================================================
    # CRUD Audit Actions
    # ========================================================================

    @staticmethod
    async def create_audit_action(db: AsyncSession, action_data: dict) -> AuditAction:
        """Crée une action d'audit"""
        existing = await db.execute(
            select(AuditAction).where(AuditAction.name == action_data['name'])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"Audit action with name '{action_data['name']}' already exists"
            )

        new_action = AuditAction(**action_data)
        db.add(new_action)
        await db.commit()
        await db.refresh(new_action)

        return new_action

    @staticmethod
    async def update_audit_action(
        db: AsyncSession,
        action_id: int,
        action_data: dict
    ) -> AuditAction:
        """Met à jour une action d'audit"""
        audit_action = await AdminRepository.get_by_id(db, AuditAction, action_id)
        if not audit_action:
            raise HTTPException(status_code=404, detail="Audit action not found")

        if 'name' in action_data and action_data['name'] != audit_action.name:
            existing = await db.execute(
                select(AuditAction).where(AuditAction.name == action_data['name'])
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=409,
                    detail=f"Audit action with name '{action_data['name']}' already exists"
                )

        for key, value in action_data.items():
            setattr(audit_action, key, value)

        await db.commit()
        await db.refresh(audit_action)

        return audit_action

    @staticmethod
    async def delete_audit_action(db: AsyncSession, action_id: int) -> bool:
        """Supprime une action d'audit"""
        audit_action = await AdminRepository.get_by_id(db, AuditAction, action_id)
        if not audit_action:
            raise HTTPException(status_code=404, detail="Audit action not found")

        # Vérifier si l'action est utilisée dans les audit logs
        usage_count = await db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.action_id == action_id)
        )
        if usage_count.scalar() > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete audit action: it is used in {usage_count.scalar()} audit log(s)"
            )

        await db.delete(audit_action)
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

    @staticmethod
    async def deindex_document(db: AsyncSession, document_id: uuid.UUID) -> Document:
        """
        Désindexe un document du RAG (is_indexed=False)

        Le document reste dans ChromaDB mais ne sera plus retourné dans les recherches.
        """
        document = await AdminRepository.get_by_id(db, Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        if not document.is_indexed:
            raise HTTPException(status_code=400, detail="Document is already deindexed")

        document.is_indexed = False
        await db.commit()
        await db.refresh(document)

        logger.info(f"Document deindexed: {document_id} ({document.filename})")
        return document

    @staticmethod
    async def reindex_document(db: AsyncSession, document_id: uuid.UUID) -> Document:
        """
        Réindexe un document dans le RAG (is_indexed=True)
        """
        document = await AdminRepository.get_by_id(db, Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        if document.is_indexed:
            raise HTTPException(status_code=400, detail="Document is already indexed")

        document.is_indexed = True
        await db.commit()
        await db.refresh(document)

        logger.info(f"Document reindexed: {document_id} ({document.filename})")
        return document

    @staticmethod
    async def update_document_visibility(
        db: AsyncSession,
        document_id: uuid.UUID,
        visibility: str,
        user_id: uuid.UUID,
        is_admin: bool = False
    ) -> Document:
        """
        Met à jour la visibilité d'un document

        Args:
            db: Session DB
            document_id: ID du document
            visibility: 'public' ou 'private'
            user_id: ID de l'utilisateur qui fait la demande
            is_admin: True si l'utilisateur est admin (peut modifier tous les docs)
        """
        from app.models import DocumentVisibility

        document = await AdminRepository.get_by_id(db, Document, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Vérifier les permissions (sauf admin)
        if not is_admin and document.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="You can only modify your own documents"
            )

        # Valider la visibilité
        try:
            new_visibility = DocumentVisibility(visibility)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid visibility. Must be 'public' or 'private'"
            )

        if document.visibility == new_visibility:
            raise HTTPException(
                status_code=400,
                detail=f"Document visibility is already '{visibility}'"
            )

        document.visibility = new_visibility
        await db.commit()
        await db.refresh(document)

        # Mettre à jour aussi dans ChromaDB
        try:
            chroma_client = get_chroma_client()
            if chroma_client:
                collection = chroma_client.get_collection(name=settings.collection_name)
                # On ne peut pas mettre à jour les metadata directement dans ChromaDB
                # Il faudrait supprimer et réinsérer les chunks
                logger.warning(
                    f"Document visibility updated in DB but not in ChromaDB. "
                    f"Re-upload document to sync: {document.filename}"
                )
        except Exception as e:
            logger.warning(f"Could not check ChromaDB: {e}")

        logger.info(f"Document visibility updated: {document_id} -> {visibility}")
        return document
