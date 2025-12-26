"""
Schemas Documents

Schémas Pydantic pour les documents utilisateur.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentRead(BaseModel):
    """Schéma de lecture d'un document"""
    id: uuid.UUID
    filename: str
    file_type: Optional[str] = None
    file_size: int
    chunk_count: int
    visibility: str = "public"
    is_indexed: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Réponse pour la liste des documents"""
    items: List[DocumentRead]
    total: int
    limit: int
    offset: int


class VisibilityUpdate(BaseModel):
    """Schéma pour la mise à jour de la visibilité"""
    visibility: str = Field(..., pattern="^(public|private)$")
