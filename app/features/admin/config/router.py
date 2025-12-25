"""
Router Admin Config

Endpoints pour la gestion de la configuration système.
Tous les endpoints nécessitent le rôle admin.
"""
import logging

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin_user, get_db
from app.models import User
from app.features.admin.config.service import ConfigService
from app.features.admin.config.schemas import (
    SystemConfigRead, RAGConfigRead, RAGConfigUpdate,
    TimeoutsConfigRead, TimeoutsConfigUpdate, RateLimitsConfigRead
)
from app.features.audit.service import AuditService
from app.common.metrics import REQUEST_COUNT

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# LECTURE CONFIGURATION
# =============================================================================

@router.get("", response_model=SystemConfigRead)
async def get_system_config(
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Récupère la configuration système complète.

    Includes:
    - Informations application (nom, version, environnement)
    - Configuration RAG (top_k, chunk_size, etc.)
    - Configuration timeouts
    - Configuration rate limits
    - Endpoints externes (Ollama, ChromaDB)

    Requires: Admin role
    """
    try:
        config = ConfigService.get_system_config()

        REQUEST_COUNT.labels(
            endpoint="/admin/config", method="GET", status="200"
        ).inc()

        return config

    except Exception as e:
        REQUEST_COUNT.labels(
            endpoint="/admin/config", method="GET", status="500"
        ).inc()
        logger.error(f"Error getting system config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rag", response_model=RAGConfigRead)
async def get_rag_config(
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Récupère la configuration RAG.

    Requires: Admin role
    """
    try:
        config = ConfigService.get_rag_config()

        REQUEST_COUNT.labels(
            endpoint="/admin/config/rag", method="GET", status="200"
        ).inc()

        return config

    except Exception as e:
        REQUEST_COUNT.labels(
            endpoint="/admin/config/rag", method="GET", status="500"
        ).inc()
        logger.error(f"Error getting RAG config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeouts", response_model=TimeoutsConfigRead)
async def get_timeouts_config(
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Récupère la configuration des timeouts.

    Requires: Admin role
    """
    try:
        config = ConfigService.get_timeouts_config()

        REQUEST_COUNT.labels(
            endpoint="/admin/config/timeouts", method="GET", status="200"
        ).inc()

        return config

    except Exception as e:
        REQUEST_COUNT.labels(
            endpoint="/admin/config/timeouts", method="GET", status="500"
        ).inc()
        logger.error(f"Error getting timeouts config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rate-limits", response_model=RateLimitsConfigRead)
async def get_rate_limits_config(
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Récupère la configuration des rate limits.

    Note: Les rate limits ne sont pas modifiables en runtime.

    Requires: Admin role
    """
    try:
        config = ConfigService.get_rate_limits_config()

        REQUEST_COUNT.labels(
            endpoint="/admin/config/rate-limits", method="GET", status="200"
        ).inc()

        return config

    except Exception as e:
        REQUEST_COUNT.labels(
            endpoint="/admin/config/rate-limits", method="GET", status="500"
        ).inc()
        logger.error(f"Error getting rate limits config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# MISE À JOUR CONFIGURATION
# =============================================================================

@router.patch("/rag", response_model=RAGConfigRead)
async def update_rag_config(
    config_data: RAGConfigUpdate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Met à jour la configuration RAG (runtime).

    Body:
    - top_k: Nombre de résultats (1-20)
    - chunk_size: Taille des chunks (100-4000)
    - chunk_overlap: Overlap (0-500)
    - chunking_strategy: Stratégie de chunking

    Note: Ces modifications sont temporaires et seront perdues au redémarrage.

    Requires: Admin role
    """
    try:
        # Récupérer l'ancienne config pour l'audit
        old_config = ConfigService.get_rag_config()

        new_config = ConfigService.update_rag_config(config_data)

        # Audit log
        await AuditService.log_action(
            db=db,
            action_name='config_updated',
            user_id=admin_user.id,
            resource_type_name='config',
            resource_id=None,
            details={
                'config_type': 'rag',
                'old_values': old_config.model_dump(),
                'new_values': config_data.model_dump(exclude_unset=True)
            },
            request=request
        )

        REQUEST_COUNT.labels(
            endpoint="/admin/config/rag", method="PATCH", status="200"
        ).inc()

        return new_config

    except Exception as e:
        REQUEST_COUNT.labels(
            endpoint="/admin/config/rag", method="PATCH", status="500"
        ).inc()
        logger.error(f"Error updating RAG config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/timeouts", response_model=TimeoutsConfigRead)
async def update_timeouts_config(
    config_data: TimeoutsConfigUpdate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Met à jour la configuration des timeouts (runtime).

    Body:
    - ollama_timeout: Timeout Ollama (5-600s)
    - http_timeout: Timeout HTTP (1-120s)
    - health_check_timeout: Timeout health check (1-30s)

    Note: Ces modifications sont temporaires et seront perdues au redémarrage.

    Requires: Admin role
    """
    try:
        # Récupérer l'ancienne config pour l'audit
        old_config = ConfigService.get_timeouts_config()

        new_config = ConfigService.update_timeouts_config(config_data)

        # Audit log
        await AuditService.log_action(
            db=db,
            action_name='config_updated',
            user_id=admin_user.id,
            resource_type_name='config',
            resource_id=None,
            details={
                'config_type': 'timeouts',
                'old_values': old_config.model_dump(),
                'new_values': config_data.model_dump(exclude_unset=True)
            },
            request=request
        )

        REQUEST_COUNT.labels(
            endpoint="/admin/config/timeouts", method="PATCH", status="200"
        ).inc()

        return new_config

    except Exception as e:
        REQUEST_COUNT.labels(
            endpoint="/admin/config/timeouts", method="PATCH", status="500"
        ).inc()
        logger.error(f"Error updating timeouts config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RELOAD CONFIGURATION
# =============================================================================

@router.post("/reload", response_model=SystemConfigRead)
async def reload_config(
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Recharge la configuration depuis les valeurs par défaut.

    Efface tous les overrides runtime et revient aux valeurs du fichier .env.

    Requires: Admin role
    """
    try:
        # Récupérer les overrides actuels pour l'audit
        overrides = ConfigService.get_runtime_overrides()

        config = ConfigService.reload_config()

        # Audit log
        await AuditService.log_action(
            db=db,
            action_name='config_reloaded',
            user_id=admin_user.id,
            resource_type_name='config',
            resource_id=None,
            details={
                'cleared_overrides': overrides
            },
            request=request
        )

        REQUEST_COUNT.labels(
            endpoint="/admin/config/reload", method="POST", status="200"
        ).inc()

        return config

    except Exception as e:
        REQUEST_COUNT.labels(
            endpoint="/admin/config/reload", method="POST", status="500"
        ).inc()
        logger.error(f"Error reloading config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
