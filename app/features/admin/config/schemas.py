"""
Schemas Admin Config

Schémas Pydantic pour la configuration système.
"""
from typing import Optional, Dict

from pydantic import BaseModel, Field


# =============================================================================
# CONFIG RAG
# =============================================================================

class RAGConfigRead(BaseModel):
    """Lecture de la configuration RAG"""
    top_k: int = Field(..., description="Nombre de résultats de recherche")
    chunk_size: int = Field(..., description="Taille des chunks en caractères")
    chunk_overlap: int = Field(..., description="Overlap entre chunks")
    chunking_strategy: str = Field(..., description="Stratégie de chunking")


class RAGConfigUpdate(BaseModel):
    """Mise à jour de la configuration RAG"""
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Nombre de résultats (1-20)")
    chunk_size: Optional[int] = Field(None, ge=100, le=4000, description="Taille chunks (100-4000)")
    chunk_overlap: Optional[int] = Field(None, ge=0, le=500, description="Overlap (0-500)")
    chunking_strategy: Optional[str] = Field(None, description="Stratégie de chunking")


# =============================================================================
# CONFIG TIMEOUTS
# =============================================================================

class TimeoutsConfigRead(BaseModel):
    """Lecture de la configuration des timeouts"""
    ollama_timeout: float = Field(..., description="Timeout Ollama en secondes")
    http_timeout: float = Field(..., description="Timeout HTTP en secondes")
    health_check_timeout: float = Field(..., description="Timeout health check en secondes")


class TimeoutsConfigUpdate(BaseModel):
    """Mise à jour de la configuration des timeouts"""
    ollama_timeout: Optional[float] = Field(
        None, ge=5.0, le=600.0,
        description="Timeout Ollama (5-600s)"
    )
    http_timeout: Optional[float] = Field(
        None, ge=1.0, le=120.0,
        description="Timeout HTTP (1-120s)"
    )
    health_check_timeout: Optional[float] = Field(
        None, ge=1.0, le=30.0,
        description="Timeout health check (1-30s)"
    )


# =============================================================================
# CONFIG RATE LIMITS
# =============================================================================

class RateLimitsConfigRead(BaseModel):
    """Lecture de la configuration des rate limits"""
    chat: str = Field(..., description="Rate limit pour /chat")
    upload: str = Field(..., description="Rate limit pour /upload")
    admin: str = Field(..., description="Rate limit pour /admin")


# =============================================================================
# CONFIG SYSTÈME COMPLÈTE
# =============================================================================

class SystemConfigRead(BaseModel):
    """Lecture de la configuration système complète"""
    app_name: str = Field(..., description="Nom de l'application")
    app_version: str = Field(..., description="Version de l'application")
    environment: str = Field(..., description="Environnement (dev, prod)")
    debug: bool = Field(..., description="Mode debug")
    rag: RAGConfigRead
    timeouts: TimeoutsConfigRead
    rate_limits: RateLimitsConfigRead
    ollama_host: str = Field(..., description="Host Ollama")
    ollama_model: str = Field(..., description="Modèle LLM")
    chroma_host: str = Field(..., description="Host ChromaDB")
    collection_name: str = Field(..., description="Nom de la collection")
