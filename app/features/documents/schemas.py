"""
Schemas Documents

Schémas Pydantic pour les documents utilisateur.
"""
import uuid
from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class DocumentRead(BaseModel):
    """Schéma de lecture d'un document"""
    id: uuid.UUID
    filename: str
    file_type: str
    file_size: int
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Réponse pour la liste des documents"""
    items: List[DocumentRead]
    total: int
    limit: int
    offset: int
