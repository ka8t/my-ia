"""
Router Admin Documents - Endpoints d'administration des documents.

Endpoints:
    GET    /api/admin/documents              - Liste tous les documents
    GET    /api/admin/documents/stats        - Statistiques globales
    GET    /api/admin/documents/{id}         - Détail document
    PATCH  /api/admin/documents/{id}         - Modifier document
    DELETE /api/admin/documents/{id}         - Supprimer document
    POST   /api/admin/documents/bulk/visibility - Changer visibilité en masse
    POST   /api/admin/documents/bulk/delete  - Supprimer en masse
    POST   /api/admin/documents/bulk/indexing - Toggle indexation en masse
    GET    /api/admin/users/{id}/quota       - Quota utilisateur
    PUT    /api/admin/users/{id}/quota       - Définir quota
    DELETE /api/admin/users/{id}/quota       - Reset quota (défaut)
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_storage_service, get_chroma_client, get_current_admin_user
from app.models import User
from app.features.admin.documents.service import AdminDocumentService
from app.features.admin.documents.schemas import (
    AdminBulkDeleteRequest,
    AdminBulkOperationResponse,
    AdminBulkVisibilityRequest,
    AdminDocumentDetailResponse,
    AdminDocumentListResponse,
    AdminDocumentResponse,
    AdminDocumentUpdateRequest,
    AdminQuotaUpdateRequest,
    AdminStorageStatsResponse,
    AdminUserQuotaResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/documents", tags=["Admin Documents"])
quota_router = APIRouter(prefix="/api/admin/users", tags=["Admin User Quotas"])


def get_admin_document_service(
    session: AsyncSession = Depends(get_db),
    storage_service=Depends(get_storage_service),
    chroma_client=Depends(get_chroma_client),
) -> AdminDocumentService:
    """Factory pour le service admin documents."""
    return AdminDocumentService(
        session=session,
        storage_service=storage_service,
        chroma_client=chroma_client,
    )


# === Documents List & Detail ===


@router.get("", response_model=AdminDocumentListResponse)
async def list_all_documents(
    user_id: Optional[UUID] = Query(None, description="Filtrer par utilisateur"),
    visibility: Optional[str] = Query(None, pattern="^(public|private|shared)$"),
    file_type: Optional[str] = Query(None),
    is_indexed: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, min_length=2),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin_user),
    service: AdminDocumentService = Depends(get_admin_document_service),
):
    """
    Liste tous les documents du système (admin).

    Filtres disponibles:
    - **user_id**: Documents d'un utilisateur spécifique
    - **visibility**: public/private/shared
    - **file_type**: Type MIME
    - **is_indexed**: Documents indexés ou non
    - **search**: Recherche dans le nom de fichier
    """
    return await service.list_all_documents(
        user_id=user_id,
        visibility=visibility,
        file_type=file_type,
        is_indexed=is_indexed,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=AdminStorageStatsResponse)
async def get_storage_stats(
    admin: User = Depends(get_current_admin_user),
    service: AdminDocumentService = Depends(get_admin_document_service),
):
    """
    Récupère les statistiques globales de stockage.

    Inclut le top 10 des utilisateurs par usage.
    """
    return await service.get_storage_stats()


@router.get("/{document_id}", response_model=AdminDocumentDetailResponse)
async def get_document(
    document_id: UUID,
    admin: User = Depends(get_current_admin_user),
    service: AdminDocumentService = Depends(get_admin_document_service),
):
    """
    Récupère les détails d'un document avec historique des versions.
    """
    return await service.get_document(document_id)


# === Document CRUD ===


@router.patch("/{document_id}", response_model=AdminDocumentResponse)
async def update_document(
    document_id: UUID,
    update: AdminDocumentUpdateRequest,
    admin: User = Depends(get_current_admin_user),
    service: AdminDocumentService = Depends(get_admin_document_service),
):
    """
    Modifie un document (admin).

    Permet de modifier:
    - **visibility**: public/private/shared
    - **is_indexed**: Active/désactive l'indexation RAG
    - **filename**: Renommer le document
    """
    return await service.update_document(
        document_id=document_id,
        visibility=update.visibility,
        is_indexed=update.is_indexed,
        filename=update.filename,
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    admin: User = Depends(get_current_admin_user),
    service: AdminDocumentService = Depends(get_admin_document_service),
):
    """
    Supprime un document et tous ses fichiers.
    """
    await service.delete_document(document_id)
    return None


# === Bulk Operations ===


@router.post("/bulk/visibility", response_model=AdminBulkOperationResponse)
async def bulk_update_visibility(
    request: AdminBulkVisibilityRequest,
    admin: User = Depends(get_current_admin_user),
    service: AdminDocumentService = Depends(get_admin_document_service),
):
    """
    Change la visibilité de plusieurs documents en une seule opération.

    Maximum 100 documents par requête.
    """
    return await service.bulk_update_visibility(
        document_ids=request.document_ids,
        visibility=request.visibility,
    )


@router.post("/bulk/delete", response_model=AdminBulkOperationResponse)
async def bulk_delete_documents(
    request: AdminBulkDeleteRequest,
    admin: User = Depends(get_current_admin_user),
    service: AdminDocumentService = Depends(get_admin_document_service),
):
    """
    Supprime plusieurs documents en une seule opération.

    Maximum 100 documents par requête.
    """
    return await service.bulk_delete(request.document_ids)


@router.post("/bulk/indexing", response_model=AdminBulkOperationResponse)
async def bulk_toggle_indexing(
    document_ids: list[UUID] = Query(..., max_length=50),
    is_indexed: bool = Query(...),
    admin: User = Depends(get_current_admin_user),
    service: AdminDocumentService = Depends(get_admin_document_service),
):
    """
    Active ou désactive l'indexation RAG de plusieurs documents.

    Maximum 50 documents par requête.
    """
    return await service.bulk_toggle_indexing(
        document_ids=document_ids,
        is_indexed=is_indexed,
    )


# === User Quotas ===


@quota_router.get("/{user_id}/quota", response_model=AdminUserQuotaResponse)
async def get_user_quota(
    user_id: UUID,
    admin: User = Depends(get_current_admin_user),
    service: AdminDocumentService = Depends(get_admin_document_service),
):
    """
    Récupère le quota et l'usage de stockage d'un utilisateur.
    """
    return await service.get_user_quota(user_id)


@quota_router.put("/{user_id}/quota", response_model=AdminUserQuotaResponse)
async def set_user_quota(
    user_id: UUID,
    request: AdminQuotaUpdateRequest,
    admin: User = Depends(get_current_admin_user),
    service: AdminDocumentService = Depends(get_admin_document_service),
):
    """
    Définit un quota personnalisé pour un utilisateur.

    Le quota est en bytes. Exemples:
    - 100 MB = 104857600
    - 500 MB = 524288000
    - 1 GB = 1073741824
    """
    return await service.set_user_quota(
        user_id=user_id,
        quota_bytes=request.quota_bytes,
        admin_id=admin.id,
    )


@quota_router.delete("/{user_id}/quota", status_code=204)
async def delete_user_quota(
    user_id: UUID,
    admin: User = Depends(get_current_admin_user),
    service: AdminDocumentService = Depends(get_admin_document_service),
):
    """
    Supprime le quota personnalisé d'un utilisateur.

    L'utilisateur reviendra au quota par défaut du système.
    """
    await service.delete_user_quota(user_id)
    return None
