"""
Router Chat

Endpoints pour le chat conversationnel avec RAG.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Request, Header, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import verify_api_key, verify_jwt_or_api_key, get_db
from app.features.chat.schemas import ChatRequest, ChatResponse
from app.features.chat.service import ChatService
from app.features.auth.router import current_active_user, optional_current_user
from app.common.metrics import REQUEST_COUNT, REQUEST_LATENCY
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: Request,
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(optional_current_user)
):
    """
    Endpoint ChatBot conversationnel avec RAG

    Args:
        chat_request: Requête de chat avec query et session_id optionnel
        db: Session database
        user: Utilisateur connecte (optionnel)

    Returns:
        Réponse du chatbot avec sources filtrees par visibilite
    """
    with REQUEST_LATENCY.labels(endpoint="/chat").time():
        try:
            user_id = str(user.id) if user else None

            result = await ChatService.chat_with_rag(
                chat_request.query,
                chat_request.session_id,
                user_id=user_id,
                db=db
            )

            REQUEST_COUNT.labels(endpoint="/chat", method="POST", status="200").inc()

            return ChatResponse(**result)

        except Exception as e:
            REQUEST_COUNT.labels(endpoint="/chat", method="POST", status="500").inc()
            logger.error(f"Error in chat endpoint: {e}")
            raise


@router.post("/stream")
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(optional_current_user)
):
    """
    Endpoint ChatBot avec streaming

    Args:
        chat_request: Requête de chat
        db: Session database
        user: Utilisateur connecte (optionnel)

    Returns:
        Streaming response avec sources filtrees
    """
    try:
        REQUEST_COUNT.labels(endpoint="/chat/stream", method="POST", status="200").inc()
        user_id = str(user.id) if user else None

        return StreamingResponse(
            ChatService.chat_stream(chat_request.query, user_id=user_id, db=db),
            media_type="application/x-ndjson"
        )

    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/chat/stream", method="POST", status="500").inc()
        logger.error(f"Error in chat/stream endpoint: {e}")
        raise


# Router pour les autres modes de chat
assistant_router = APIRouter(prefix="/assistant", tags=["assistant"])
test_router = APIRouter(prefix="/test", tags=["test"])


@assistant_router.post("", response_model=ChatResponse)
async def assistant(
    request: Request,
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(optional_current_user)
):
    """
    Endpoint Assistant orienté tâches avec RAG

    Args:
        chat_request: Requête de chat
        db: Session database
        user: Utilisateur connecte (optionnel)

    Returns:
        Réponse de l'assistant avec sources filtrees
    """
    with REQUEST_LATENCY.labels(endpoint="/assistant").time():
        try:
            user_id = str(user.id) if user else None

            result = await ChatService.assistant_with_rag(
                chat_request.query,
                chat_request.session_id,
                user_id=user_id,
                db=db
            )

            REQUEST_COUNT.labels(endpoint="/assistant", method="POST", status="200").inc()

            return ChatResponse(**result)

        except Exception as e:
            REQUEST_COUNT.labels(endpoint="/assistant", method="POST", status="500").inc()
            logger.error(f"Error in assistant endpoint: {e}")
            raise


@test_router.post("", response_model=ChatResponse)
async def test_ollama(
    request: Request,
    chat_request: ChatRequest,
    _: bool = Depends(verify_jwt_or_api_key)
):
    """
    Endpoint de test sans RAG - juste Ollama

    Args:
        chat_request: Requête de chat
        _: Vérification de la clé API

    Returns:
        Réponse sans sources
    """
    with REQUEST_LATENCY.labels(endpoint="/test").time():
        try:
            result = await ChatService.test_ollama(
                chat_request.query,
                chat_request.session_id
            )

            REQUEST_COUNT.labels(endpoint="/test", method="POST", status="200").inc()

            return ChatResponse(**result)

        except Exception as e:
            REQUEST_COUNT.labels(endpoint="/test", method="POST", status="500").inc()
            logger.error(f"Error in test endpoint: {e}")
            raise
