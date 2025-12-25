"""
Service Documents

Logique métier pour la gestion des documents utilisateur.
"""
import uuid
import logging
from typing import List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_chroma_client
from app.models import Document
from app.features.documents.repository import DocumentRepository
from app.features.documents.schemas import DocumentRead

logger = logging.getLogger(__name__)


class DocumentService:
    """Service pour la gestion des documents"""

    @staticmethod
    async def list_documents(
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[DocumentRead], int]:
        """
        Liste les documents de l'utilisateur.

        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            limit: Nombre max de résultats
            offset: Décalage pour pagination

        Returns:
            Tuple (liste des documents, total)
        """
        documents, total = await DocumentRepository.list_by_user(
            db, user_id, limit, offset
        )

        items = [
            DocumentRead(
                id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                chunk_count=doc.chunk_count,
                created_at=doc.created_at
            )
            for doc in documents
        ]

        return items, total

    @staticmethod
    async def get_document(
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> DocumentRead | None:
        """
        Récupère un document.

        Args:
            db: Session de base de données
            document_id: ID du document
            user_id: ID de l'utilisateur

        Returns:
            Document ou None
        """
        document = await DocumentRepository.get_by_id(db, document_id, user_id)

        if not document:
            return None

        return DocumentRead(
            id=document.id,
            filename=document.filename,
            file_type=document.file_type,
            file_size=document.file_size,
            chunk_count=document.chunk_count,
            created_at=document.created_at
        )

    @staticmethod
    async def delete_document(
        db: AsyncSession,
        document_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """
        Supprime un document (DB + ChromaDB).

        Args:
            db: Session de base de données
            document_id: ID du document
            user_id: ID de l'utilisateur

        Returns:
            True si supprimé, False si non trouvé
        """
        document = await DocumentRepository.delete(db, document_id, user_id)

        if not document:
            return False

        # Suppression dans ChromaDB
        try:
            chroma_client = get_chroma_client()
            if chroma_client:
                collection = chroma_client.get_collection(name=settings.collection_name)
                collection.delete(where={"file_hash": document.file_hash})
                logger.info(f"Document chunks deleted from ChromaDB: {document.file_hash}")
        except Exception as e:
            logger.warning(f"Could not delete document from ChromaDB: {e}")

        logger.info(f"Document deleted: {document_id}")
        return True
