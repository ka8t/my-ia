"""
Service Chat

Logique métier pour le chat conversationnel avec RAG.
"""
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.common.utils.chroma import search_context
from app.common.utils.ollama import generate_response

logger = logging.getLogger(__name__)

# Chargement des system prompts
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

try:
    with open(PROMPTS_DIR / "chatbot_system.md", "r", encoding="utf-8") as f:
        CHATBOT_SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    logger.warning("chatbot_system.md not found, using default prompt")
    CHATBOT_SYSTEM_PROMPT = "Tu es un assistant IA serviable."

try:
    with open(PROMPTS_DIR / "assistant_system.md", "r", encoding="utf-8") as f:
        ASSISTANT_SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    logger.warning("assistant_system.md not found, using default prompt")
    ASSISTANT_SYSTEM_PROMPT = "Tu es un assistant orienté tâches."


class ChatService:
    """Service de chat conversationnel avec RAG"""

    @staticmethod
    async def chat_with_rag(
        query: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Chat conversationnel avec RAG

        Args:
            query: Question de l'utilisateur
            session_id: ID de session (optionnel)
            user_id: UUID utilisateur pour filtrage visibilite
            db: Session DB pour verifier is_indexed

        Returns:
            Dictionnaire contenant la réponse et les sources
        """
        # Recherche de contexte avec filtrage visibilite
        context = await search_context(query, user_id=user_id, db_session=db)

        # Génération de réponse
        response_text = await generate_response(
            query,
            CHATBOT_SYSTEM_PROMPT,
            context,
            stream=False
        )

        return {
            "response": response_text,
            "sources": [{"source": ctx.get("metadata", {}).get("source", "Unknown")} for ctx in context] if context else None,
            "session_id": session_id
        }

    @staticmethod
    async def assistant_with_rag(
        query: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Assistant orienté tâches avec RAG

        Args:
            query: Question de l'utilisateur
            session_id: ID de session (optionnel)
            user_id: UUID utilisateur pour filtrage visibilite
            db: Session DB pour verifier is_indexed

        Returns:
            Dictionnaire contenant la réponse et les sources
        """
        # Recherche de contexte avec filtrage visibilite
        context = await search_context(query, user_id=user_id, db_session=db)

        # Génération de réponse
        response_text = await generate_response(
            query,
            ASSISTANT_SYSTEM_PROMPT,
            context,
            stream=False
        )

        return {
            "response": response_text,
            "sources": [{"source": ctx.get("metadata", {}).get("source", "Unknown")} for ctx in context] if context else None,
            "session_id": session_id
        }

    @staticmethod
    async def test_ollama(query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Test simple sans RAG - juste Ollama

        Args:
            query: Question de l'utilisateur
            session_id: ID de session (optionnel)

        Returns:
            Dictionnaire contenant la réponse
        """
        logger.info(f"Test request: {query}")

        # Génération directe sans contexte
        response_text = await generate_response(
            query,
            "Tu es un assistant IA serviable et concis.",
            context=None,  # Pas de RAG
            stream=False
        )

        return {
            "response": response_text,
            "sources": None,
            "session_id": session_id
        }

    @staticmethod
    async def chat_stream(
        query: str,
        user_id: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ):
        """
        Chat avec streaming - retourne un générateur asynchrone

        Args:
            query: Question de l'utilisateur
            user_id: UUID utilisateur pour filtrage visibilite
            db: Session DB pour verifier is_indexed

        Yields:
            Lignes JSON de la réponse Ollama
        """
        # Recherche de contexte avec filtrage visibilite
        context = await search_context(query, user_id=user_id, db_session=db)

        # Construire le prompt avec contexte
        full_prompt = CHATBOT_SYSTEM_PROMPT + "\n\n"

        if context:
            full_prompt += "**Contexte disponible :**\n\n"
            for i, ctx in enumerate(context, 1):
                source = ctx.get("metadata", {}).get("source", "Unknown")
                full_prompt += f"[Source {i}: {source}]\n{ctx['content']}\n\n"

        full_prompt += f"**Question de l'utilisateur :**\n{query}\n\n**Réponse :**"

        # Streaming avec client qui reste ouvert
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            async with client.stream(
                "POST",
                f"{settings.ollama_url}/api/generate",
                json={
                    "model": settings.llm_model,
                    "prompt": full_prompt,
                    "stream": True
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line.strip():
                        yield line + "\n"
