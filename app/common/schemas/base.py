"""
Schémas Pydantic de base

Schémas de base réutilisables pour l'ensemble de l'application.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Réponse du health check"""
    status: str
    ollama: bool
    chroma: bool
    model: str


class ErrorResponse(BaseModel):
    """Réponse d'erreur standard"""
    detail: str
    status_code: int = Field(..., description="Code HTTP de l'erreur")


class SuccessResponse(BaseModel):
    """Réponse de succès générique"""
    success: bool = True
    message: str
