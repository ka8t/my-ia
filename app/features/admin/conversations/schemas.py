"""
Schemas Admin Conversations

Schémas Pydantic pour la gestion des conversations admin.
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


# =============================================================================
# LECTURE
# =============================================================================

class ConversationDetailRead(BaseModel):
    """Lecture détaillée d'une conversation avec messages"""
    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    title: str
    mode_id: int
    mode_name: str
    messages_count: int
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None
    messages: List["MessageRead"] = Field(default_factory=list)

    class Config:
        from_attributes = True


class MessageRead(BaseModel):
    """Lecture d'un message"""
    id: uuid.UUID
    sender_type: str
    content: str
    sources: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationListItem(BaseModel):
    """Élément de liste de conversations"""
    id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    title: str
    mode_id: int
    mode_name: str
    messages_count: int
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================================
# FILTRES
# =============================================================================

class ConversationFilter(BaseModel):
    """Filtres pour la liste des conversations"""
    user_id: Optional[uuid.UUID] = Field(None, description="Filtrer par utilisateur")
    mode_id: Optional[int] = Field(None, description="Filtrer par mode de conversation")
    search: Optional[str] = Field(None, max_length=100, description="Recherche dans le titre")
    created_after: Optional[datetime] = Field(None, description="Créé après cette date")
    created_before: Optional[datetime] = Field(None, description="Créé avant cette date")


# =============================================================================
# EXPORT
# =============================================================================

class ConversationExport(BaseModel):
    """Export d'une conversation complète"""
    conversation: ConversationDetailRead
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    export_format: str = "json"
