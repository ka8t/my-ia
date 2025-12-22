"""
Schémas Pydantic pour l'Ingestion

DTOs pour l'upload et l'ingestion de documents.
"""
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Réponse après upload d'un document"""
    success: bool
    filename: str
    chunks_indexed: int
    message: str
