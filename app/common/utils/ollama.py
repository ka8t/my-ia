"""
Utilitaires Ollama

Fonctions helpers pour interagir avec Ollama (embeddings, génération).
"""
import logging
from typing import List, Dict, Any, Optional

import httpx
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_embeddings(text: str) -> List[float]:
    """
    Génère des embeddings via Ollama

    Args:
        text: Texte à transformer en embedding

    Returns:
        Liste de floats représentant l'embedding

    Raises:
        HTTPException: En cas d'erreur de communication avec Ollama
    """
    try:
        async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
            response = await client.post(
                f"{settings.ollama_url}/api/embeddings",
                json={"model": settings.embed_model, "prompt": text}
            )
            response.raise_for_status()
            return response.json()["embedding"]
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise HTTPException(status_code=500, detail="Error generating embeddings")


async def generate_response(
    query: str,
    system_prompt: str,
    context: Optional[List[Dict[str, Any]]] = None,
    stream: bool = False
):
    """
    Génère une réponse via Ollama

    Args:
        query: Question de l'utilisateur
        system_prompt: Prompt système
        context: Contexte RAG optionnel
        stream: Mode streaming ou non

    Returns:
        Réponse d'Ollama (str si stream=False, httpx.Response si stream=True)

    Raises:
        HTTPException: En cas d'erreur de génération
    """
    try:
        # Construire le prompt avec contexte
        full_prompt = system_prompt + "\n\n"

        if context:
            full_prompt += "**Contexte disponible :**\n\n"
            for i, ctx in enumerate(context, 1):
                source = ctx.get("metadata", {}).get("source", "Unknown")
                full_prompt += f"[Source {i}: {source}]\n{ctx['content']}\n\n"

        full_prompt += f"**Question de l'utilisateur :**\n{query}\n\n**Réponse :**"

        logger.info(f"Sending request to Ollama with model {settings.model_name}")

        # Appel à Ollama
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            response = await client.post(
                f"{settings.ollama_url}/api/generate",
                json={
                    "model": settings.model_name,
                    "prompt": full_prompt,
                    "stream": stream
                },
                timeout=settings.ollama_timeout
            )
            response.raise_for_status()

            if stream:
                return response
            else:
                result = response.json()
                logger.info("Ollama response received successfully")
                return result["response"]

    except Exception as e:
        import traceback
        logger.error(f"Error generating response: {type(e).__name__}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating response: {type(e).__name__}: {str(e)}"
        )
