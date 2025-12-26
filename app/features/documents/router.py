"""
Router Documents - Endpoints API pour la gestion des documents utilisateur.

Endpoints:
    GET    /api/user/documents          - Liste des documents
    GET    /api/user/documents/search   - Recherche
    GET    /api/user/documents/stats    - Statistiques stockage
    GET    /api/user/documents/{id}     - Détail document
    POST   /api/user/documents          - Upload nouveau document
    PUT    /api/user/documents/{id}     - Remplacer (nouvelle version)
    PATCH  /api/user/documents/{id}     - Modifier métadonnées
    DELETE /api/user/documents/{id}     - Supprimer
    GET    /api/user/documents/{id}/download - Télécharger
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_storage_service, get_chroma_client
from app.features.auth.service import current_active_user
from app.models import User
from app.features.documents.service import DocumentService
from app.features.documents.schemas import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentSearchResponse,
    DocumentStatsResponse,
    DocumentUploadResponse,
    DocumentUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user/documents", tags=["User Documents"])


def get_document_service(
    session: AsyncSession = Depends(get_db),
    storage_service=Depends(get_storage_service),
    chroma_client=Depends(get_chroma_client),
) -> DocumentService:
    """Factory pour le service documents."""
    return DocumentService(
        session=session,
        storage_service=storage_service,
        chroma_client=chroma_client,
    )


# === List & Search ===


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    visibility: Optional[str] = Query(None, pattern="^(public|private)$"),
    file_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(current_active_user),
    service: DocumentService = Depends(get_document_service),
):
    """
    Liste les documents de l'utilisateur connecté.

    - **visibility**: Filtrer par visibilité (public/private)
    - **file_type**: Filtrer par type MIME
    - **page**: Numéro de page (défaut: 1)
    - **page_size**: Taille de page (défaut: 20, max: 100)
    """
    return await service.list_documents(
        user_id=user.id,
        visibility=visibility,
        file_type=file_type,
        page=page,
        page_size=page_size,
    )


@router.get("/search", response_model=DocumentSearchResponse)
async def search_documents(
    q: str = Query(..., min_length=2, description="Terme de recherche"),
    visibility: Optional[str] = Query(None, pattern="^(public|private)$"),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(current_active_user),
    service: DocumentService = Depends(get_document_service),
):
    """
    Recherche dans les documents de l'utilisateur.

    Recherche sur le nom de fichier (insensible à la casse).
    """
    return await service.search_documents(
        user_id=user.id,
        query=q,
        visibility=visibility,
        limit=limit,
    )


@router.get("/stats", response_model=DocumentStatsResponse)
async def get_storage_stats(
    user: User = Depends(current_active_user),
    service: DocumentService = Depends(get_document_service),
):
    """
    Récupère les statistiques de stockage de l'utilisateur.

    Retourne l'espace utilisé, le quota et le pourcentage.
    """
    return await service.get_user_stats(user.id)


# === CRUD ===


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: UUID,
    user: User = Depends(current_active_user),
    service: DocumentService = Depends(get_document_service),
):
    """
    Récupère les détails d'un document avec l'historique des versions.
    """
    return await service.get_document(user.id, document_id)


@router.post("", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    visibility: str = Form(default="public", pattern="^(public|private)$"),
    user: User = Depends(current_active_user),
    service: DocumentService = Depends(get_document_service),
):
    """
    Upload un nouveau document.

    - **file**: Fichier à uploader
    - **visibility**: Visibilité du document (public/private, défaut: public)
    """
    return await service.upload_document(
        user_id=user.id,
        file=file,
        visibility=visibility,
    )


@router.put("/{document_id}", response_model=DocumentUploadResponse)
async def replace_document(
    document_id: UUID,
    file: UploadFile = File(...),
    comment: Optional[str] = Form(None, max_length=500),
    user: User = Depends(current_active_user),
    service: DocumentService = Depends(get_document_service),
):
    """
    Remplace un document par une nouvelle version.

    L'ancienne version est conservée dans l'historique.

    - **file**: Nouveau fichier
    - **comment**: Note optionnelle pour cette version
    """
    return await service.replace_document(
        user_id=user.id,
        document_id=document_id,
        file=file,
        comment=comment,
    )


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: UUID,
    update: DocumentUpdateRequest,
    user: User = Depends(current_active_user),
    service: DocumentService = Depends(get_document_service),
):
    """
    Modifie les métadonnées d'un document.

    - **visibility**: Nouvelle visibilité (public/private)
    - **filename**: Nouveau nom de fichier
    """
    return await service.update_document(
        user_id=user.id,
        document_id=document_id,
        visibility=update.visibility,
        filename=update.filename,
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    user: User = Depends(current_active_user),
    service: DocumentService = Depends(get_document_service),
):
    """
    Supprime un document et toutes ses versions.

    Cette action est irréversible.
    """
    await service.delete_document(user.id, document_id)
    return None


# === Download ===


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    version: Optional[int] = Query(None, description="Version spécifique à télécharger"),
    user: User = Depends(current_active_user),
    service: DocumentService = Depends(get_document_service),
):
    """
    Télécharge un document.

    Par défaut, télécharge la version actuelle.
    Spécifiez **version** pour une version spécifique.
    """
    content, filename, mime_type = await service.get_download_content(
        user_id=user.id,
        document_id=document_id,
        version=version,
    )

    return Response(
        content=content,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )
