"""
Repository Documents

Opérations de base de données pour les documents utilisateur.
"""
import uuid
from typing import Optional, List, Tuple

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document


class DocumentRepository:
    """Repository pour les opérations CRUD sur les documents"""

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Document]:
        """
        Récupère un document par son ID pour un utilisateur donné.

        Args:
            db: Session de base de données
            document_id: ID du document
            user_id: ID de l'utilisateur propriétaire

        Returns:
            Document ou None si non trouvé
        """
        result = await db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_user(
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Document], int]:
        """
        Liste les documents d'un utilisateur avec pagination.

        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            limit: Nombre max de résultats
            offset: Décalage pour la pagination

        Returns:
            Tuple (liste des documents, total)
        """
        # Compte total
        count_query = select(func.count()).select_from(Document).where(
            Document.user_id == user_id
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Liste paginée
        query = (
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(query)
        documents = list(result.scalars().all())

        return documents, total

    @staticmethod
    async def delete(
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[Document]:
        """
        Supprime un document.

        Args:
            db: Session de base de données
            document_id: ID du document
            user_id: ID de l'utilisateur propriétaire

        Returns:
            Document supprimé ou None si non trouvé
        """
        document = await DocumentRepository.get_by_id(db, document_id, user_id)
        if not document:
            return None

        await db.delete(document)
        await db.commit()
        return document
