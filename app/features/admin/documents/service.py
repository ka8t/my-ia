"""
Service Admin Documents - Logique métier pour l'administration des documents.

Ce service permet aux administrateurs de gérer tous les documents du système.
"""

import logging
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.storage.service import StorageService
from app.models import Document, DocumentVersion, DocumentVisibility, User, UserQuota
from app.features.admin.documents.schemas import (
    AdminBulkOperationResponse,
    AdminDocumentDetailResponse,
    AdminDocumentListResponse,
    AdminDocumentResponse,
    AdminDocumentVersionResponse,
    AdminStorageStatsResponse,
    AdminUserQuotaResponse,
)

logger = logging.getLogger(__name__)


class AdminDocumentService:
    """Service d'administration des documents."""

    def __init__(
        self,
        session: AsyncSession,
        storage_service: StorageService,
        chroma_client=None,
    ):
        self.session = session
        self.storage = storage_service
        self.chroma = chroma_client

    # === List & Search ===

    async def list_all_documents(
        self,
        user_id: Optional[UUID] = None,
        visibility: Optional[str] = None,
        file_type: Optional[str] = None,
        is_indexed: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminDocumentListResponse:
        """Liste tous les documents avec filtres admin."""
        query = select(Document).options(selectinload(Document.user))

        # Filtres
        if user_id:
            query = query.where(Document.user_id == user_id)
        if visibility:
            query = query.where(Document.visibility == visibility)
        if file_type:
            query = query.where(Document.file_type == file_type)
        if is_indexed is not None:
            query = query.where(Document.is_indexed == is_indexed)
        if search:
            query = query.where(Document.filename.ilike(f"%{search}%"))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Pagination
        query = (
            query.order_by(desc(Document.updated_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.session.execute(query)
        documents = list(result.scalars().all())

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return AdminDocumentListResponse(
            documents=[
                AdminDocumentResponse(
                    id=doc.id,
                    user_id=doc.user_id,
                    username=doc.user.username if doc.user else None,
                    filename=doc.filename,
                    file_hash=doc.file_hash,
                    file_size=doc.file_size,
                    file_type=doc.file_type,
                    file_path=doc.file_path,
                    chunk_count=doc.chunk_count,
                    current_version=doc.current_version or 1,
                    visibility=doc.visibility.value,
                    is_indexed=doc.is_indexed,
                    created_at=doc.created_at,
                    updated_at=doc.updated_at,
                )
                for doc in documents
            ],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_document(self, document_id: UUID) -> AdminDocumentDetailResponse:
        """Récupère un document avec détails admin."""
        result = await self.session.execute(
            select(Document)
            .options(selectinload(Document.user), selectinload(Document.versions))
            .where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document non trouvé")

        # Récupérer les usernames des créateurs de versions
        versions = []
        for v in document.versions:
            creator_username = None
            if v.created_by:
                creator_result = await self.session.execute(
                    select(User.username).where(User.id == v.created_by)
                )
                creator_username = creator_result.scalar_one_or_none()

            versions.append(
                AdminDocumentVersionResponse(
                    id=v.id,
                    document_id=v.document_id,
                    version_number=v.version_number,
                    file_path=v.file_path,
                    file_size=v.file_size,
                    file_hash=v.file_hash,
                    chunk_count=v.chunk_count,
                    comment=v.comment,
                    created_at=v.created_at,
                    created_by=v.created_by,
                    created_by_username=creator_username,
                )
            )

        return AdminDocumentDetailResponse(
            id=document.id,
            user_id=document.user_id,
            username=document.user.username if document.user else None,
            filename=document.filename,
            file_hash=document.file_hash,
            file_size=document.file_size,
            file_type=document.file_type,
            file_path=document.file_path,
            chunk_count=document.chunk_count,
            current_version=document.current_version or 1,
            visibility=document.visibility.value,
            is_indexed=document.is_indexed,
            created_at=document.created_at,
            updated_at=document.updated_at,
            versions=versions,
        )

    # === Update ===

    async def update_document(
        self,
        document_id: UUID,
        visibility: Optional[str] = None,
        is_indexed: Optional[bool] = None,
        filename: Optional[str] = None,
    ) -> AdminDocumentResponse:
        """Met à jour un document (admin)."""
        result = await self.session.execute(
            select(Document)
            .options(selectinload(Document.user))
            .where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document non trouvé")

        if visibility:
            document.visibility = DocumentVisibility(visibility)
        if is_indexed is not None:
            document.is_indexed = is_indexed
        if filename:
            document.filename = filename

        await self.session.flush()
        await self.session.refresh(document)
        await self.session.commit()

        return AdminDocumentResponse(
            id=document.id,
            user_id=document.user_id,
            username=document.user.username if document.user else None,
            filename=document.filename,
            file_hash=document.file_hash,
            file_size=document.file_size,
            file_type=document.file_type,
            file_path=document.file_path,
            chunk_count=document.chunk_count,
            current_version=document.current_version or 1,
            visibility=document.visibility.value,
            is_indexed=document.is_indexed,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    async def delete_document(self, document_id: UUID) -> bool:
        """Supprime un document (admin)."""
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Document non trouvé")

        try:
            # Supprimer du storage
            await self.storage.delete_document(document.user_id, document.id)

            # TODO: Supprimer de ChromaDB

            # Supprimer de la DB
            await self.session.delete(document)
            await self.session.commit()

            logger.info(f"Admin: Document {document_id} supprimé")
            return True

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Erreur suppression document: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors de la suppression")

    # === Bulk Operations ===

    async def bulk_update_visibility(
        self, document_ids: List[UUID], visibility: str
    ) -> AdminBulkOperationResponse:
        """Change la visibilité de plusieurs documents."""
        success_count = 0
        errors = []

        for doc_id in document_ids:
            try:
                result = await self.session.execute(
                    select(Document).where(Document.id == doc_id)
                )
                document = result.scalar_one_or_none()

                if document:
                    document.visibility = DocumentVisibility(visibility)
                    success_count += 1
                else:
                    errors.append(f"Document {doc_id} non trouvé")

            except Exception as e:
                errors.append(f"Document {doc_id}: {str(e)}")

        await self.session.commit()

        return AdminBulkOperationResponse(
            success_count=success_count,
            error_count=len(errors),
            errors=errors,
        )

    async def bulk_delete(
        self, document_ids: List[UUID]
    ) -> AdminBulkOperationResponse:
        """Supprime plusieurs documents."""
        success_count = 0
        errors = []

        for doc_id in document_ids:
            try:
                result = await self.session.execute(
                    select(Document).where(Document.id == doc_id)
                )
                document = result.scalar_one_or_none()

                if document:
                    # Supprimer du storage
                    await self.storage.delete_document(document.user_id, document.id)
                    # Supprimer de la DB
                    await self.session.delete(document)
                    success_count += 1
                else:
                    errors.append(f"Document {doc_id} non trouvé")

            except Exception as e:
                errors.append(f"Document {doc_id}: {str(e)}")

        await self.session.commit()

        return AdminBulkOperationResponse(
            success_count=success_count,
            error_count=len(errors),
            errors=errors,
        )

    async def bulk_toggle_indexing(
        self, document_ids: List[UUID], is_indexed: bool
    ) -> AdminBulkOperationResponse:
        """Active/désactive l'indexation de plusieurs documents."""
        success_count = 0
        errors = []

        for doc_id in document_ids:
            try:
                result = await self.session.execute(
                    select(Document).where(Document.id == doc_id)
                )
                document = result.scalar_one_or_none()

                if document:
                    document.is_indexed = is_indexed
                    success_count += 1

                    # TODO: Si désindexé, supprimer de ChromaDB
                    # TODO: Si réindexé, ajouter à ChromaDB

                else:
                    errors.append(f"Document {doc_id} non trouvé")

            except Exception as e:
                errors.append(f"Document {doc_id}: {str(e)}")

        await self.session.commit()

        return AdminBulkOperationResponse(
            success_count=success_count,
            error_count=len(errors),
            errors=errors,
        )

    # === Quotas ===

    async def get_user_quota(self, user_id: UUID) -> AdminUserQuotaResponse:
        """Récupère le quota d'un utilisateur."""
        # Vérifier que l'utilisateur existe
        user_result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

        # Quota personnalisé?
        quota_result = await self.session.execute(
            select(UserQuota).where(UserQuota.user_id == user_id)
        )
        user_quota = quota_result.scalar_one_or_none()

        # Stats de stockage
        stats = await self.storage.get_user_stats(
            user_id, user_quota.quota_bytes if user_quota else None
        )

        return AdminUserQuotaResponse(
            user_id=user_id,
            username=user.username,
            used_bytes=stats.used_bytes,
            quota_bytes=stats.quota_bytes or self.storage.config.default_quota_bytes,
            quota_used_percent=stats.quota_used_percent,
            file_count=stats.file_count,
            is_custom_quota=user_quota is not None,
        )

    async def set_user_quota(
        self, user_id: UUID, quota_bytes: int, admin_id: UUID
    ) -> AdminUserQuotaResponse:
        """Définit le quota d'un utilisateur."""
        # Vérifier que l'utilisateur existe
        user_result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

        # Chercher quota existant
        quota_result = await self.session.execute(
            select(UserQuota).where(UserQuota.user_id == user_id)
        )
        user_quota = quota_result.scalar_one_or_none()

        if user_quota:
            user_quota.quota_bytes = quota_bytes
            user_quota.updated_by = admin_id
        else:
            user_quota = UserQuota(
                user_id=user_id,
                quota_bytes=quota_bytes,
                updated_by=admin_id,
            )
            self.session.add(user_quota)

        await self.session.commit()

        logger.info(f"Admin {admin_id}: Quota de {user_id} mis à {quota_bytes} bytes")

        return await self.get_user_quota(user_id)

    async def delete_user_quota(self, user_id: UUID) -> bool:
        """Supprime le quota personnalisé (retour au défaut)."""
        result = await self.session.execute(
            select(UserQuota).where(UserQuota.user_id == user_id)
        )
        user_quota = result.scalar_one_or_none()

        if not user_quota:
            raise HTTPException(
                status_code=404, detail="Aucun quota personnalisé pour cet utilisateur"
            )

        await self.session.delete(user_quota)
        await self.session.commit()

        return True

    # === Storage Stats ===

    async def get_storage_stats(self) -> AdminStorageStatsResponse:
        """Récupère les statistiques globales de stockage."""
        # Stats du backend
        backend_stats = await self.storage.get_global_stats()

        # Nombre d'utilisateurs avec fichiers
        users_count_result = await self.session.execute(
            select(func.count(func.distinct(Document.user_id)))
        )
        users_with_files = users_count_result.scalar() or 0

        # Nombre total de fichiers
        files_count_result = await self.session.execute(
            select(func.count(Document.id))
        )
        total_files = files_count_result.scalar() or 0

        # Taille moyenne
        avg_size = backend_stats.total_bytes / total_files if total_files > 0 else 0

        # Top utilisateurs par usage
        top_users_query = (
            select(
                Document.user_id,
                User.username,
                func.sum(Document.file_size).label("total_size"),
                func.count(Document.id).label("file_count"),
            )
            .join(User, Document.user_id == User.id)
            .group_by(Document.user_id, User.username)
            .order_by(desc("total_size"))
            .limit(10)
        )
        top_users_result = await self.session.execute(top_users_query)
        top_users_rows = top_users_result.all()

        top_users = []
        for row in top_users_rows:
            # Récupérer quota personnalisé
            quota_result = await self.session.execute(
                select(UserQuota.quota_bytes).where(UserQuota.user_id == row.user_id)
            )
            custom_quota = quota_result.scalar_one_or_none()
            quota = custom_quota or self.storage.config.default_quota_bytes

            top_users.append(
                AdminUserQuotaResponse(
                    user_id=row.user_id,
                    username=row.username,
                    used_bytes=row.total_size or 0,
                    quota_bytes=quota,
                    quota_used_percent=(
                        (row.total_size / quota * 100) if quota > 0 else 0
                    ),
                    file_count=row.file_count,
                    is_custom_quota=custom_quota is not None,
                )
            )

        return AdminStorageStatsResponse(
            total_bytes=backend_stats.total_bytes,
            used_bytes=backend_stats.used_bytes,
            free_bytes=backend_stats.free_bytes,
            total_files=total_files,
            total_users=users_with_files,
            avg_file_size=avg_size,
            top_users=top_users,
        )
