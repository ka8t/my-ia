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
from app.users import current_active_user
from app.ingest_v2 import AdvancedIngestionPipeline

logger = logging.getLogger(__name__)


# ============================================================================
# ChromaDB Client (Singleton Pattern)
# ============================================================================

_chroma_client: Optional[chromadb.PersistentClient] = None
_ingestion_pipeline: Optional[AdvancedIngestionPipeline] = None


def get_chroma_client() -> Optional[chromadb.PersistentClient]:
    """
    Retourne le client ChromaDB (singleton)

    Returns:
        Client ChromaDB ou None si l'initialisation a échoué
    """
    global _chroma_client

    if _chroma_client is None:
        try:
            _chroma_client = chromadb.PersistentClient(
                path=settings.chroma_path,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            logger.info(f"ChromaDB client initialized at {settings.chroma_path}")
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
