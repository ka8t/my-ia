"""
Schémas Pydantic pour le Chat

DTOs pour les endpoints de chat.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Requête de chat"""
    query: str = Field(..., description="Question de l'utilisateur")
    session_id: Optional[str] = Field(None, description="ID de session pour le contexte")


class ChatResponse(BaseModel):
    """Réponse de chat"""
    response: str = Field(..., description="Réponse de l'IA")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="Sources utilisées")
    session_id: Optional[str] = Field(None, description="ID de session")
