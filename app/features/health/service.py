"""
Service Health Check

Logique métier pour vérifier l'état des services.
"""
import logging
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class HealthService:
    """Service pour vérifier la santé des composants système"""

    @staticmethod
    async def check_ollama() -> bool:
        """
        Vérifie si Ollama est accessible

        Returns:
            True si Ollama répond correctement
        """
        try:
            async with httpx.AsyncClient(timeout=settings.health_check_timeout) as client:
                response = await client.get(f"{settings.ollama_host}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    @staticmethod
    async def check_chroma() -> bool:
        """
        Vérifie si ChromaDB est accessible

        Returns:
            True si ChromaDB répond correctement
        """
        try:
            async with httpx.AsyncClient(timeout=settings.health_check_timeout) as client:
                response = await client.get(f"{settings.chroma_host}/api/v2/heartbeat")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"ChromaDB health check failed: {e}")
            return False

    @staticmethod
    async def get_health_status() -> dict:
        """
        Vérifie l'état de tous les services

        Returns:
            Dictionnaire avec l'état de chaque service
        """
        ollama_healthy = await HealthService.check_ollama()
        chroma_healthy = await HealthService.check_chroma()

        status = "healthy" if (ollama_healthy and chroma_healthy) else "degraded"

        return {
            "status": status,
            "ollama": ollama_healthy,
            "chroma": chroma_healthy,
            "model": settings.model_name
        }
