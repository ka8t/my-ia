"""
Service Admin Config

Logique métier pour la gestion de la configuration système.
Note: Les modifications runtime sont stockées en mémoire et non persistées.
"""
import logging
from typing import Dict, Any, Optional

from app.core.config import settings
from app.features.admin.config.schemas import (
    SystemConfigRead, RAGConfigRead, RAGConfigUpdate,
    TimeoutsConfigRead, TimeoutsConfigUpdate, RateLimitsConfigRead
)

logger = logging.getLogger(__name__)

# Stockage des overrides runtime (en mémoire)
_runtime_overrides: Dict[str, Any] = {}


class ConfigService:
    """Service pour la gestion de la configuration"""

    # ========================================================================
    # LECTURE CONFIGURATION
    # ========================================================================

    @staticmethod
    def get_system_config() -> SystemConfigRead:
        """
        Récupère la configuration système complète.

        Returns:
            SystemConfigRead avec toutes les configurations
        """
        return SystemConfigRead(
            app_name=settings.app_name,
            app_version=settings.app_version,
            environment=settings.environment,
            debug=settings.debug,
            rag=ConfigService.get_rag_config(),
            timeouts=ConfigService.get_timeouts_config(),
            rate_limits=ConfigService.get_rate_limits_config(),
            ollama_host=f"{settings.ollama_host}:{settings.ollama_port}",
            ollama_model=settings.llm_model,
            chroma_host=f"{settings.chroma_host}:{settings.chroma_port}",
            collection_name=settings.collection_name
        )

    @staticmethod
    def get_rag_config() -> RAGConfigRead:
        """Récupère la configuration RAG."""
        return RAGConfigRead(
            top_k=_runtime_overrides.get('top_k', settings.top_k),
            chunk_size=_runtime_overrides.get('chunk_size', settings.chunk_size),
            chunk_overlap=_runtime_overrides.get('chunk_overlap', settings.chunk_overlap),
            chunking_strategy=_runtime_overrides.get(
                'chunking_strategy', settings.chunking_strategy
            )
        )

    @staticmethod
    def get_timeouts_config() -> TimeoutsConfigRead:
        """Récupère la configuration des timeouts."""
        return TimeoutsConfigRead(
            ollama_timeout=_runtime_overrides.get(
                'ollama_timeout', settings.ollama_timeout
            ),
            http_timeout=_runtime_overrides.get('http_timeout', settings.http_timeout),
            health_check_timeout=_runtime_overrides.get(
                'health_check_timeout', settings.health_check_timeout
            )
        )

    @staticmethod
    def get_rate_limits_config() -> RateLimitsConfigRead:
        """Récupère la configuration des rate limits."""
        return RateLimitsConfigRead(
            chat=settings.rate_limit_chat,
            upload=settings.rate_limit_upload,
            admin=settings.rate_limit_admin
        )

    # ========================================================================
    # MISE À JOUR CONFIGURATION
    # ========================================================================

    @staticmethod
    def update_rag_config(config: RAGConfigUpdate) -> RAGConfigRead:
        """
        Met à jour la configuration RAG (runtime).

        Args:
            config: Nouvelles valeurs de configuration

        Returns:
            Configuration RAG mise à jour
        """
        update_dict = config.model_dump(exclude_unset=True)

        for key, value in update_dict.items():
            _runtime_overrides[key] = value
            logger.info(f"RAG config updated: {key} = {value}")

        return ConfigService.get_rag_config()

    @staticmethod
    def update_timeouts_config(config: TimeoutsConfigUpdate) -> TimeoutsConfigRead:
        """
        Met à jour la configuration des timeouts (runtime).

        Args:
            config: Nouvelles valeurs de configuration

        Returns:
            Configuration timeouts mise à jour
        """
        update_dict = config.model_dump(exclude_unset=True)

        for key, value in update_dict.items():
            _runtime_overrides[key] = value
            logger.info(f"Timeout config updated: {key} = {value}")

        return ConfigService.get_timeouts_config()

    # ========================================================================
    # RESET CONFIGURATION
    # ========================================================================

    @staticmethod
    def reload_config() -> SystemConfigRead:
        """
        Recharge la configuration depuis les valeurs par défaut.
        Efface tous les overrides runtime.

        Returns:
            Configuration système rechargée
        """
        global _runtime_overrides
        _runtime_overrides = {}

        logger.info("Configuration reloaded - all runtime overrides cleared")

        return ConfigService.get_system_config()

    @staticmethod
    def get_runtime_overrides() -> Dict[str, Any]:
        """
        Récupère les overrides runtime actuels.

        Returns:
            Dictionnaire des overrides
        """
        return _runtime_overrides.copy()
