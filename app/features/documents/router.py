"""
Router Documents

Endpoints pour la gestion des documents utilisateur.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models import User
from app.features.auth.service import current_active_user
from app.features.documents.service import DocumentService
from app.features.documents.schemas import DocumentRead, DocumentListResponse, VisibilityUpdate

router = APIRouter(
    prefix="/documents",
    tags=["documents"]
)


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="Lister mes documents",
    description="Récupère la liste des documents de l'utilisateur connecté."
)
async def list_documents(
    limit: int = Query(50, ge=1, le=100, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Décalage pour pagination"),
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session)
) -> DocumentListResponse:
    """
    Liste les documents de l'utilisateur authentifié.

    - **limit**: Nombre maximum de documents (1-100)
    - **offset**: Décalage pour la pagination
    """
    items, total = await DocumentService.list_documents(
        db, current_user.id, limit, offset
    )

    return DocumentListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get(
    "/{document_id}",
    response_model=DocumentRead,
    summary="Récupérer un document",
    description="Récupère les détails d'un document."
)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session)
) -> DocumentRead:
    """
    Récupère un document par son ID.
    """
    document = await DocumentService.get_document(db, document_id, current_user.id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document non trouvé"
        )

    return document


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un document",
    description="Supprime un document et ses chunks de l'index."
)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session)
) -> None:
    """
    Supprime un document.

    Cette action supprime également les chunks de l'index vectoriel.
    """
    deleted = await DocumentService.delete_document(db, document_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document non trouvé"
        )


@router.patch(
    "/{document_id}/visibility",
    response_model=DocumentRead,
    summary="Modifier la visibilité d'un document",
    description="Change la visibilité d'un document (public ou private)."
)
async def update_document_visibility(
    document_id: uuid.UUID,
    visibility_data: VisibilityUpdate,
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session)
) -> DocumentRead:
    """
    Met à jour la visibilité d'un document.

    - **visibility**: 'public' (visible par tous) ou 'private' (visible uniquement par le propriétaire)

    Seul le propriétaire du document peut modifier sa visibilité.
    """
    return await DocumentService.update_visibility(
        db,
        document_id,
        current_user.id,
        visibility_data.visibility
    )
