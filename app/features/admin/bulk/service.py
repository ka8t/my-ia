"""
Service Admin Bulk

Logique métier pour les opérations en masse.
"""
import uuid
import logging
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import HTTPException

from app.models import User, Conversation, Document, Session
from app.features.admin.bulk.schemas import BulkOperationResult
from app.core.deps import get_chroma_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class BulkService:
    """Service pour les opérations bulk"""

    # ========================================================================
    # UTILISATEURS
    # ========================================================================

    @staticmethod
    async def activate_users(
        db: AsyncSession,
        user_ids: List[uuid.UUID],
        admin_user_id: uuid.UUID
    ) -> BulkOperationResult:
        """
        Active plusieurs utilisateurs.

        Args:
            db: Session de base de données
            user_ids: Liste des IDs utilisateurs
            admin_user_id: ID de l'admin effectuant l'action

        Returns:
            BulkOperationResult
        """
        success_count = 0
        failed_ids = []
        errors = {}

        for user_id in user_ids:
            try:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()

                if not user:
                    failed_ids.append(user_id)
                    errors[str(user_id)] = "User not found"
                    continue

                user.is_active = True
                success_count += 1

            except Exception as e:
                failed_ids.append(user_id)
                errors[str(user_id)] = str(e)

        await db.commit()

        return BulkOperationResult(
            success_count=success_count,
            failed_count=len(failed_ids),
            failed_ids=failed_ids,
            errors=errors
        )

    @staticmethod
    async def deactivate_users(
        db: AsyncSession,
        user_ids: List[uuid.UUID],
        admin_user_id: uuid.UUID
    ) -> BulkOperationResult:
        """
        Désactive plusieurs utilisateurs.

        Args:
            db: Session de base de données
            user_ids: Liste des IDs utilisateurs
            admin_user_id: ID de l'admin effectuant l'action

        Returns:
            BulkOperationResult
        """
        success_count = 0
        failed_ids = []
        errors = {}

        for user_id in user_ids:
            try:
                # Empêcher la désactivation de soi-même
                if user_id == admin_user_id:
                    failed_ids.append(user_id)
                    errors[str(user_id)] = "Cannot deactivate your own account"
                    continue

                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()

                if not user:
                    failed_ids.append(user_id)
                    errors[str(user_id)] = "User not found"
                    continue

                user.is_active = False
                success_count += 1

            except Exception as e:
                failed_ids.append(user_id)
                errors[str(user_id)] = str(e)

        await db.commit()

        return BulkOperationResult(
            success_count=success_count,
            failed_count=len(failed_ids),
            failed_ids=failed_ids,
            errors=errors
        )

    @staticmethod
    async def change_users_role(
        db: AsyncSession,
        user_ids: List[uuid.UUID],
        new_role_id: int,
        admin_user_id: uuid.UUID
    ) -> BulkOperationResult:
        """
        Change le rôle de plusieurs utilisateurs.

        Args:
            db: Session de base de données
            user_ids: Liste des IDs utilisateurs
            new_role_id: Nouveau rôle ID
            admin_user_id: ID de l'admin effectuant l'action

        Returns:
            BulkOperationResult
        """
        success_count = 0
        failed_ids = []
        errors = {}

        for user_id in user_ids:
            try:
                # Empêcher la modification de son propre rôle
                if user_id == admin_user_id and new_role_id != 1:
                    failed_ids.append(user_id)
                    errors[str(user_id)] = "Cannot demote yourself"
                    continue

                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()

                if not user:
                    failed_ids.append(user_id)
                    errors[str(user_id)] = "User not found"
                    continue

                user.role_id = new_role_id
                user.is_superuser = (new_role_id == 1)
                success_count += 1

            except Exception as e:
                failed_ids.append(user_id)
                errors[str(user_id)] = str(e)

        await db.commit()

        return BulkOperationResult(
            success_count=success_count,
            failed_count=len(failed_ids),
            failed_ids=failed_ids,
            errors=errors
        )

    @staticmethod
    async def delete_users(
        db: AsyncSession,
        user_ids: List[uuid.UUID],
        admin_user_id: uuid.UUID,
        confirm: bool
    ) -> BulkOperationResult:
        """
        Supprime plusieurs utilisateurs.

        Args:
            db: Session de base de données
            user_ids: Liste des IDs utilisateurs
            admin_user_id: ID de l'admin effectuant l'action
            confirm: Confirmation obligatoire

        Returns:
            BulkOperationResult

        Raises:
            HTTPException 400 si confirm n'est pas True
        """
        if not confirm:
            raise HTTPException(
                status_code=400,
                detail="Bulk delete requires confirm=true"
            )

        success_count = 0
        failed_ids = []
        errors = {}

        for user_id in user_ids:
            try:
                # Empêcher la suppression de soi-même
                if user_id == admin_user_id:
                    failed_ids.append(user_id)
                    errors[str(user_id)] = "Cannot delete your own account"
                    continue

                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()

                if not user:
                    failed_ids.append(user_id)
                    errors[str(user_id)] = "User not found"
                    continue

                await db.delete(user)
                success_count += 1

            except Exception as e:
                failed_ids.append(user_id)
                errors[str(user_id)] = str(e)

        await db.commit()

        return BulkOperationResult(
            success_count=success_count,
            failed_count=len(failed_ids),
            failed_ids=failed_ids,
            errors=errors
        )

    # ========================================================================
    # CONVERSATIONS
    # ========================================================================

    @staticmethod
    async def delete_conversations(
        db: AsyncSession,
        conversation_ids: List[uuid.UUID],
        confirm: bool
    ) -> BulkOperationResult:
        """
        Supprime plusieurs conversations.

        Args:
            db: Session de base de données
            conversation_ids: Liste des IDs conversations
            confirm: Confirmation obligatoire

        Returns:
            BulkOperationResult
        """
        if not confirm:
            raise HTTPException(
                status_code=400,
                detail="Bulk delete requires confirm=true"
            )

        success_count = 0
        failed_ids = []
        errors = {}

        for conv_id in conversation_ids:
            try:
                result = await db.execute(
                    select(Conversation).where(Conversation.id == conv_id)
                )
                conversation = result.scalar_one_or_none()

                if not conversation:
                    failed_ids.append(conv_id)
                    errors[str(conv_id)] = "Conversation not found"
                    continue

                await db.delete(conversation)
                success_count += 1

            except Exception as e:
                failed_ids.append(conv_id)
                errors[str(conv_id)] = str(e)

        await db.commit()

        return BulkOperationResult(
            success_count=success_count,
            failed_count=len(failed_ids),
            failed_ids=failed_ids,
            errors=errors
        )

    # ========================================================================
    # DOCUMENTS
    # ========================================================================

    @staticmethod
    async def delete_documents(
        db: AsyncSession,
        document_ids: List[uuid.UUID],
        confirm: bool
    ) -> BulkOperationResult:
        """
        Supprime plusieurs documents (DB + ChromaDB).

        Args:
            db: Session de base de données
            document_ids: Liste des IDs documents
            confirm: Confirmation obligatoire

        Returns:
            BulkOperationResult
        """
        if not confirm:
            raise HTTPException(
                status_code=400,
                detail="Bulk delete requires confirm=true"
            )

        success_count = 0
        failed_ids = []
        errors = {}

        # Récupérer le client ChromaDB une fois
        chroma_client = None
        try:
            chroma_client = get_chroma_client()
        except Exception as e:
            logger.warning(f"ChromaDB unavailable: {e}")

        for doc_id in document_ids:
            try:
                result = await db.execute(select(Document).where(Document.id == doc_id))
                document = result.scalar_one_or_none()

                if not document:
                    failed_ids.append(doc_id)
                    errors[str(doc_id)] = "Document not found"
                    continue

                # Supprimer de ChromaDB
                if chroma_client:
                    try:
                        collection = chroma_client.get_collection(name=settings.collection_name)
                        collection.delete(where={"file_hash": document.file_hash})
                    except Exception as e:
                        logger.warning(f"Could not delete from ChromaDB: {e}")

                # Supprimer de la DB
                await db.delete(document)
                success_count += 1

            except Exception as e:
                failed_ids.append(doc_id)
                errors[str(doc_id)] = str(e)

        await db.commit()

        return BulkOperationResult(
            success_count=success_count,
            failed_count=len(failed_ids),
            failed_ids=failed_ids,
            errors=errors
        )

    # ========================================================================
    # SESSIONS
    # ========================================================================

    @staticmethod
    async def revoke_sessions(
        db: AsyncSession,
        session_ids: List[uuid.UUID],
        confirm: bool
    ) -> BulkOperationResult:
        """
        Révoque plusieurs sessions.

        Args:
            db: Session de base de données
            session_ids: Liste des IDs sessions
            confirm: Confirmation obligatoire

        Returns:
            BulkOperationResult
        """
        if not confirm:
            raise HTTPException(
                status_code=400,
                detail="Bulk delete requires confirm=true"
            )

        success_count = 0
        failed_ids = []
        errors = {}

        for session_id in session_ids:
            try:
                result = await db.execute(
                    select(Session).where(Session.id == session_id)
                )
                session = result.scalar_one_or_none()

                if not session:
                    failed_ids.append(session_id)
                    errors[str(session_id)] = "Session not found"
                    continue

                await db.delete(session)
                success_count += 1

            except Exception as e:
                failed_ids.append(session_id)
                errors[str(session_id)] = str(e)

        await db.commit()

        return BulkOperationResult(
            success_count=success_count,
            failed_count=len(failed_ids),
            failed_ids=failed_ids,
            errors=errors
        )
