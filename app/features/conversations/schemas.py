"""
Schemas Conversations

Schémas Pydantic pour les conversations utilisateur.
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


# =============================================================================
# CRÉATION
# =============================================================================

class ConversationCreate(BaseModel):
    """Schéma pour créer une conversation"""
    title: str = Field(..., min_length=1, max_length=500, description="Titre de la conversation")
    mode_id: int = Field(default=1, ge=1, description="ID du mode de conversation (1=chatbot, 2=assistant)")


class MessageCreate(BaseModel):
    """Schéma pour créer un message"""
    sender_type: str = Field(..., pattern="^(user|assistant)$", description="Type d'expéditeur")
    content: str = Field(..., min_length=1, description="Contenu du message")
    sources: Optional[Dict[str, Any]] = Field(None, description="Sources RAG utilisées")


# =============================================================================
# LECTURE
# =============================================================================

class MessageRead(BaseModel):
    """Schéma de lecture d'un message"""
    id: uuid.UUID
    sender_type: str
    content: str
    sources: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationRead(BaseModel):
    """Schéma de lecture d'une conversation (liste)"""
    id: uuid.UUID
    title: str
    mode_id: int
    mode_name: Optional[str] = None
    messages_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    """Schéma de lecture détaillée d'une conversation avec messages"""
    id: uuid.UUID
    title: str
    mode_id: int
    mode_name: Optional[str] = None
    messages: List[MessageRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =============================================================================
# MISE À JOUR
# =============================================================================

class ConversationUpdate(BaseModel):
    """Schéma de mise à jour d'une conversation"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)


# =============================================================================
# RÉPONSES
# =============================================================================

class ConversationListResponse(BaseModel):
    """Réponse pour la liste des conversations"""
    items: List[ConversationRead]
    total: int
    limit: int
    offset: int


# =============================================================================
# CHAT
# =============================================================================

class ChatRequest(BaseModel):
    """Requête de chat dans une conversation"""
    query: str = Field(..., min_length=1, description="Question de l'utilisateur")


class ChatResponse(BaseModel):
    """Réponse de chat avec le message sauvegardé"""
    response: str = Field(..., description="Réponse de l'IA")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="Sources RAG")
    user_message: MessageRead = Field(..., description="Message utilisateur sauvegardé")
    assistant_message: MessageRead = Field(..., description="Message assistant sauvegardé")
