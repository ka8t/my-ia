"""
Router Conversations

Endpoints pour la gestion des conversations utilisateur.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models import User
from app.features.auth.service import current_active_user
from app.features.conversations.service import ConversationService
from app.features.conversations.schemas import (
    ConversationCreate,
    ConversationUpdate,
    ConversationRead,
    ConversationDetail,
    ConversationListResponse,
    MessageCreate,
    MessageRead,
    ChatRequest,
    ChatResponse
)

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"]
)


import logging
logger = logging.getLogger(__name__)


@router.get(
    "/test-auth",
    summary="Test auth endpoint"
)
async def test_auth(
    current_user: User = Depends(current_active_user)
):
    """Test endpoint pour debug auth"""
    return {"user_id": str(current_user.id), "email": current_user.email}


@router.get(
    "/",
    response_model=ConversationListResponse,
    summary="Lister mes conversations",
    description="Récupère la liste des conversations de l'utilisateur connecté."
)
async def list_conversations(
    limit: int = Query(50, ge=1, le=100, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Décalage pour pagination"),
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session)
) -> ConversationListResponse:
    logger.info(f"list_conversations called - user_id={current_user.id}")
    """
    Liste les conversations de l'utilisateur authentifié.

    - **limit**: Nombre maximum de conversations (1-100)
    - **offset**: Décalage pour la pagination
    """
    items, total = await ConversationService.list_conversations(
        db, current_user.id, limit, offset
    )

    return ConversationListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )


@router.post(
    "",
    response_model=ConversationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une conversation",
    description="Crée une nouvelle conversation pour l'utilisateur connecté."
)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session)
) -> ConversationRead:
    """
    Crée une nouvelle conversation.

    - **title**: Titre de la conversation
    - **mode_id**: ID du mode (1=chatbot, 2=assistant)
    """
    return await ConversationService.create_conversation(
        db, current_user.id, data
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetail,
    summary="Récupérer une conversation",
    description="Récupère une conversation avec tous ses messages."
)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session)
) -> ConversationDetail:
    """
    Récupère une conversation par son ID.

    Retourne la conversation avec la liste complète des messages.
    """
    conversation = await ConversationService.get_conversation(
        db, conversation_id, current_user.id
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation non trouvée"
        )

    return conversation


@router.patch(
    "/{conversation_id}",
    response_model=ConversationRead,
    summary="Modifier une conversation",
    description="Met à jour le titre d'une conversation."
)
async def update_conversation(
    conversation_id: uuid.UUID,
    data: ConversationUpdate,
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session)
) -> ConversationRead:
    """
    Met à jour une conversation.

    - **title**: Nouveau titre (optionnel)
    """
    conversation = await ConversationService.update_conversation(
        db, conversation_id, current_user.id, data
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation non trouvée"
        )

    return conversation


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une conversation",
    description="Supprime une conversation et tous ses messages."
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session)
) -> None:
    """
    Supprime une conversation.

    Cette action est irréversible. Tous les messages seront supprimés.
    """
    deleted = await ConversationService.delete_conversation(
        db, conversation_id, current_user.id
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation non trouvée"
        )


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter un message",
    description="Ajoute un message à une conversation existante."
)
async def add_message(
    conversation_id: uuid.UUID,
    data: MessageCreate,
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session)
) -> MessageRead:
    """
    Ajoute un message à une conversation.

    - **sender_type**: 'user' ou 'assistant'
    - **content**: Contenu du message
    - **sources**: Sources RAG (optionnel)
    """
    message = await ConversationService.add_message(
        db, conversation_id, current_user.id, data
    )

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation non trouvée"
        )

    return message


@router.post(
    "/{conversation_id}/chat",
    response_model=ChatResponse,
    summary="Chat dans une conversation",
    description="Envoie un message, génère une réponse RAG et sauvegarde les deux."
)
async def chat_in_conversation(
    conversation_id: uuid.UUID,
    data: ChatRequest,
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session)
) -> ChatResponse:
    """
    Chat avec sauvegarde automatique dans la conversation.

    - Sauvegarde le message utilisateur
    - Génère une réponse avec RAG selon le mode de la conversation
    - Sauvegarde la réponse assistant
    - Retourne les deux messages sauvegardés
    """
    result = await ConversationService.chat_and_save(
        db, conversation_id, current_user.id, data.query
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation non trouvée"
        )

    return result
