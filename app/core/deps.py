"""
Dépendances injectables FastAPI

Ce module centralise toutes les dépendances injectables
pour éviter les imports circulaires et améliorer la testabilité.
"""
import logging
from typing import Optional, AsyncGenerator

import chromadb
from chromadb.config import Settings as ChromaSettings
from fastapi import Header, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import get_async_session
from app.models import User
from app.features.auth.service import current_active_user
from app.ingest_v2 import AdvancedIngestionPipeline

logger = logging.getLogger(__name__)


# ============================================================================
# ChromaDB Client (Singleton Pattern)
# ============================================================================

_chroma_client: Optional[chromadb.HttpClient] = None
_ingestion_pipeline: Optional[AdvancedIngestionPipeline] = None


def get_chroma_client() -> Optional[chromadb.HttpClient]:
    """
    Retourne le client ChromaDB (singleton)

    Returns:
        Client ChromaDB ou None si l'initialisation a échoué
    """
    global _chroma_client

    if _chroma_client is None:
        try:
            _chroma_client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            logger.info(f"ChromaDB client initialized at {settings.chroma_url}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            _chroma_client = None

    return _chroma_client


def get_ingestion_pipeline() -> Optional[AdvancedIngestionPipeline]:
    """
    Retourne le pipeline d'ingestion (singleton)

    Returns:
        Pipeline d'ingestion ou None si l'initialisation a échoué
    """
    global _ingestion_pipeline

    if _ingestion_pipeline is None:
        chroma_client = get_chroma_client()
        if chroma_client:
            try:
                _ingestion_pipeline = AdvancedIngestionPipeline(chroma_client=chroma_client)
                logger.info("Advanced Ingestion Pipeline v2 initialized")
            except Exception as e:
                logger.error(f"Failed to initialize ingestion pipeline: {e}")
                _ingestion_pipeline = None

    return _ingestion_pipeline


# ============================================================================
# Security Dependencies
# ============================================================================

async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """
    Vérifie la clé API

    Args:
        x_api_key: Clé API dans le header X-API-Key

    Returns:
        True si la clé est valide

    Raises:
        HTTPException: Si la clé est invalide
    """
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


async def verify_jwt_or_api_key(
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
) -> bool:
    """
    Vérifie l'authentification JWT (par défaut) ou API key (fallback)

    Permet l'accès via:
    - Header Authorization: Bearer <token> (pour le frontend - défaut)
    - Header X-API-Key (pour les clients API externes)

    Returns:
        True si l'un des deux est valide

    Raises:
        HTTPException: Si aucune authentification valide
    """
    # Essayer d'abord le JWT (méthode par défaut)
    if authorization and authorization.startswith("Bearer "):
        try:
            from app.features.auth.service import verify_jwt_token
            token = authorization.split(" ")[1]
            payload = await verify_jwt_token(token)
            if payload:
                return True
        except Exception as e:
            logger.debug(f"JWT verification failed: {e}")

    # Fallback sur la clé API (pour clients externes)
    if x_api_key and x_api_key == settings.api_key:
        return True

    raise HTTPException(status_code=401, detail="Invalid authentication")


async def get_current_admin_user(user: User = Depends(current_active_user)) -> User:
    """
    Vérifie que l'utilisateur actuel est un administrateur

    Args:
        user: Utilisateur authentifié

    Returns:
        L'utilisateur si c'est un admin

    Raises:
        HTTPException: Si l'utilisateur n'est pas admin
    """
    if user.role_id != 1:  # 1 = role admin
        raise HTTPException(
            status_code=403,
            detail="Access forbidden: Admin role required"
        )
    return user


# ============================================================================
# Database Dependencies
# ============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Générateur de session de base de données

    Yields:
        AsyncSession: Session de base de données

    Note:
        Utilise get_async_session de db.py pour la compatibilité
    """
    async for session in get_async_session():
        yield session


# ============================================================================
# Storage Dependencies
# ============================================================================

_storage_backend = None
_storage_service = None


def get_quota_config():
    """
    Retourne la configuration des quotas depuis settings.

    Returns:
        QuotaConfig: Configuration des quotas
    """
    from app.common.storage.schemas import QuotaConfig

    return QuotaConfig(
        default_quota_bytes=settings.storage_default_quota_mb * 1024 * 1024,
        max_file_size_bytes=settings.storage_max_file_size_mb * 1024 * 1024,
        allowed_mime_types=[
            t.strip()
            for t in settings.storage_allowed_mime_types.split(",")
            if t.strip()
        ],
        blocked_extensions=[
            e.strip()
            for e in settings.storage_blocked_extensions.split(",")
            if e.strip()
        ],
    )


def get_storage_backend():
    """
    Factory pour le backend de stockage (singleton).

    Returns:
        StorageBackend: Backend de stockage

    Raises:
        NotImplementedError: Si le backend n'est pas implémenté
        ValueError: Si le backend est inconnu
    """
    global _storage_backend

    if _storage_backend is None:
        if settings.storage_backend == "local":
            from app.common.storage.backends.local import LocalStorageBackend

            _storage_backend = LocalStorageBackend(settings.storage_local_path)
            logger.info(
                f"LocalStorageBackend initialized at {settings.storage_local_path}"
            )
        elif settings.storage_backend == "minio":
            # Futur: from app.common.storage.backends.minio import MinIOStorageBackend
            raise NotImplementedError("MinIO backend not implemented yet")
        elif settings.storage_backend == "s3":
            # Futur: from app.common.storage.backends.s3 import S3StorageBackend
            raise NotImplementedError("S3 backend not implemented yet")
        else:
            raise ValueError(f"Unknown storage backend: {settings.storage_backend}")

    return _storage_backend


def get_storage_service():
    """
    Retourne le service de stockage avec quotas (singleton).

    Returns:
        StorageService: Service de stockage
    """
    global _storage_service

    if _storage_service is None:
        from app.common.storage.service import StorageService

        _storage_service = StorageService(
            backend=get_storage_backend(),
            quota_config=get_quota_config(),
        )
        logger.info("StorageService initialized")

    return _storage_service
