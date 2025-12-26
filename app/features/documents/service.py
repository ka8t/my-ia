"""
Service Documents - Logique métier pour la gestion des documents.

Ce service orchestre les opérations entre le repository, le storage et ChromaDB.
"""

import hashlib
import logging
import mimetypes
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.storage.exceptions import (
    FileTooLargeError,
    InvalidFileTypeError,
    QuotaExceededError,
    StorageFileNotFoundError,
)
from app.common.storage.service import StorageService
from app.models import Document, DocumentVersion, DocumentVisibility, UserQuota
from app.features.documents.repository import DocumentRepository
from app.features.documents.schemas import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentSearchResponse,
    DocumentSearchResult,
    DocumentStatsResponse,
    DocumentUploadResponse,
    DocumentVersionResponse,
)

logger = logging.getLogger(__name__)


class DocumentService:
    """Service de gestion des documents utilisateur."""

    def __init__(
        self,
        session: AsyncSession,
        storage_service: StorageService,
        chroma_client=None,
    ):
        self.session = session
        self.storage = storage_service
        self.chroma = chroma_client
        self.repo = DocumentRepository(session)

    # === List & Get ===

    async def list_documents(
        self,
        user_id: UUID,
        visibility: Optional[str] = None,
        file_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> DocumentListResponse:
        """Liste les documents d'un utilisateur avec pagination."""
        documents, total = await self.repo.list_user_documents(
            user_id=user_id,
            visibility=visibility,
            file_type=file_type,
            page=page,
            page_size=page_size,
        )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return DocumentListResponse(
            documents=[DocumentResponse.model_validate(doc) for doc in documents],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_document(
        self, user_id: UUID, document_id: UUID
    ) -> DocumentDetailResponse:
        """Récupère un document avec ses versions."""
        document = await self.repo.get_user_document_with_versions(user_id, document_id)

        if not document:
            raise HTTPException(status_code=404, detail="Document non trouvé")

        return DocumentDetailResponse(
            **DocumentResponse.model_validate(document).model_dump(),
            versions=[
                DocumentVersionResponse.model_validate(v) for v in document.versions
            ],
        )

    async def get_document_for_access(
        self, user_id: UUID, document_id: UUID
    ) -> Document:
        """
        Récupère un document en vérifiant les droits d'accès.
        
        Un utilisateur peut accéder à:
        - Ses propres documents
        - Les documents publics
        """
        document = await self.repo.get_by_id(document_id)

        if not document:
            raise HTTPException(status_code=404, detail="Document non trouvé")

        # Vérifier accès
        if document.user_id != user_id:
            if document.visibility != DocumentVisibility.PUBLIC:
                raise HTTPException(status_code=403, detail="Accès refusé")

        return document

    # === Search ===

    async def search_documents(
        self,
        user_id: UUID,
        query: str,
        visibility: Optional[str] = None,
        limit: int = 50,
    ) -> DocumentSearchResponse:
        """Recherche dans les documents de l'utilisateur."""
        if not query or len(query) < 2:
            raise HTTPException(
                status_code=400, detail="La requête doit contenir au moins 2 caractères"
            )

        documents = await self.repo.search_user_documents(
            user_id=user_id,
            query=query,
            visibility=visibility,
            limit=limit,
        )

        results = [
            DocumentSearchResult(
                id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                visibility=doc.visibility.value,
                created_at=doc.created_at,
            )
            for doc in documents
        ]

        return DocumentSearchResponse(results=results, total=len(results), query=query)

    # === Upload & Replace ===

    async def upload_document(
        self,
        user_id: UUID,
        file: UploadFile,
        visibility: str = "public",
    ) -> DocumentUploadResponse:
        """Upload un nouveau document."""
        # Lire le contenu
        content = await file.read()

        # Calculer le hash
        file_hash = hashlib.sha256(content).hexdigest()

        # Vérifier si le document existe déjà (même hash)
        existing = await self.repo.get_by_hash(file_hash)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Ce document existe déjà (ID: {existing.id})",
            )

        # Déterminer le type MIME
        mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

        # Récupérer le quota personnalisé si existant
        user_quota = await self._get_user_quota(user_id)

        # Créer le document en DB d'abord pour avoir l'ID
        document = Document(
            user_id=user_id,
            filename=file.filename,
            file_hash=file_hash,
            file_size=len(content),
            file_type=mime_type,
            chunk_count=0,
            current_version=1,
            visibility=DocumentVisibility(visibility),
            is_indexed=True,
        )

        try:
            document = await self.repo.create(document)

            # Sauvegarder dans le storage
            file_path = await self.storage.upload(
                user_id=user_id,
                document_id=document.id,
                filename=file.filename,
                content=content,
                mime_type=mime_type,
                version=1,
                user_quota=user_quota,
            )

            # Mettre à jour le path
            document.file_path = file_path

            # Créer la version
            version = DocumentVersion(
                document_id=document.id,
                version_number=1,
                file_path=file_path,
                file_size=len(content),
                file_hash=file_hash,
                chunk_count=0,
                created_by=user_id,
            )
            await self.repo.create_version(version)

            await self.session.commit()

            logger.info(f"Document uploadé: {document.id} par user {user_id}")

            return DocumentUploadResponse(
                id=document.id,
                filename=document.filename,
                file_size=document.file_size,
                file_type=document.file_type,
                version=1,
                message="Document uploadé avec succès",
            )

        except (FileTooLargeError, InvalidFileTypeError, QuotaExceededError) as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur upload document: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors de l'upload")

    async def replace_document(
        self,
        user_id: UUID,
        document_id: UUID,
        file: UploadFile,
        comment: Optional[str] = None,
    ) -> DocumentUploadResponse:
        """Remplace un document par une nouvelle version."""
        # Récupérer le document existant
        document = await self.repo.get_user_document(user_id, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document non trouvé")

        # Lire le contenu
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()

        # Vérifier que ce n'est pas le même contenu
        if file_hash == document.file_hash:
            raise HTTPException(
                status_code=400, detail="Le fichier est identique à la version actuelle"
            )

        # Déterminer le type MIME
        mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or document.file_type

        # Nouvelle version
        new_version = document.current_version + 1

        # Récupérer quota
        user_quota = await self._get_user_quota(user_id)

        try:
            # Sauvegarder dans le storage
            file_path = await self.storage.upload(
                user_id=user_id,
                document_id=document.id,
                filename=file.filename,
                content=content,
                mime_type=mime_type,
                version=new_version,
                user_quota=user_quota,
            )

            # Créer la version
            version = DocumentVersion(
                document_id=document.id,
                version_number=new_version,
                file_path=file_path,
                file_size=len(content),
                file_hash=file_hash,
                chunk_count=0,
                comment=comment,
                created_by=user_id,
            )
            await self.repo.create_version(version)

            # Mettre à jour le document principal
            document.file_hash = file_hash
            document.file_size = len(content)
            document.file_type = mime_type
            document.file_path = file_path
            document.current_version = new_version
            document.filename = file.filename
            await self.repo.update(document)

            # TODO: Re-indexer dans ChromaDB (supprimer anciens chunks, créer nouveaux)

            await self.session.commit()

            logger.info(
                f"Document remplacé: {document.id} v{new_version} par user {user_id}"
            )

            return DocumentUploadResponse(
                id=document.id,
                filename=document.filename,
                file_size=document.file_size,
                file_type=document.file_type,
                version=new_version,
                message=f"Document mis à jour (version {new_version})",
            )

        except (FileTooLargeError, InvalidFileTypeError, QuotaExceededError) as e:
            await self.session.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur remplacement document: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors du remplacement")

    # === Update ===

    async def update_document(
        self,
        user_id: UUID,
        document_id: UUID,
        visibility: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> DocumentResponse:
        """Met à jour les métadonnées d'un document."""
        document = await self.repo.get_user_document(user_id, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document non trouvé")

        if visibility:
            document.visibility = DocumentVisibility(visibility)

        if filename:
            document.filename = filename

        document = await self.repo.update(document)
        await self.session.commit()

        return DocumentResponse.model_validate(document)

    # === Delete ===

    async def delete_document(self, user_id: UUID, document_id: UUID) -> bool:
        """Supprime un document et ses fichiers."""
        document = await self.repo.get_user_document(user_id, document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document non trouvé")

        try:
            # Supprimer du storage
            await self.storage.delete_document(user_id, document_id)

            # TODO: Supprimer de ChromaDB

            # Supprimer de la DB (cascade sur versions)
            await self.repo.delete(document)
            await self.session.commit()

            logger.info(f"Document supprimé: {document_id} par user {user_id}")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur suppression document: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors de la suppression")

    # === Download ===

    async def get_download_content(
        self, user_id: UUID, document_id: UUID, version: Optional[int] = None
    ) -> Tuple[bytes, str, str]:
        """
        Récupère le contenu d'un document pour téléchargement.

        Returns:
            Tuple[content, filename, mime_type]
        """
        document = await self.get_document_for_access(user_id, document_id)

        # Déterminer le chemin
        if version:
            doc_version = await self.repo.get_version(document_id, version)
            if not doc_version:
                raise HTTPException(
                    status_code=404, detail=f"Version {version} non trouvée"
                )
            file_path = doc_version.file_path
        else:
            file_path = document.file_path

        if not file_path:
            raise HTTPException(status_code=404, detail="Fichier non disponible")

        try:
            content = await self.storage.download(file_path)
            return content, document.filename, document.file_type
        except StorageFileNotFoundError:
            raise HTTPException(status_code=404, detail="Fichier introuvable")

    # === Stats ===

    async def get_user_stats(self, user_id: UUID) -> DocumentStatsResponse:
        """Récupère les statistiques de stockage d'un utilisateur."""
        user_quota = await self._get_user_quota(user_id)
        stats = await self.storage.get_user_stats(user_id, user_quota)

        remaining = None
        if stats.quota_bytes:
            remaining = max(0, stats.quota_bytes - stats.used_bytes)

        return DocumentStatsResponse(
            used_bytes=stats.used_bytes,
            file_count=stats.file_count,
            quota_bytes=stats.quota_bytes,
            quota_used_percent=stats.quota_used_percent,
            remaining_bytes=remaining,
        )

    # === Helpers ===

    async def _get_user_quota(self, user_id: UUID) -> Optional[int]:
        """Récupère le quota personnalisé d'un utilisateur."""
        from sqlalchemy import select

        result = await self.session.execute(
            select(UserQuota.quota_bytes).where(UserQuota.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        return row if row else None
