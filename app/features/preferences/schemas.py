"""
Schemas Preferences

Schémas Pydantic pour les préférences utilisateur.
"""
from typing import Optional

from pydantic import BaseModel, Field


class PreferencesRead(BaseModel):
    """Schéma de lecture des préférences"""
    top_k: int = Field(description="Nombre de sources RAG à utiliser")
    show_sources: bool = Field(description="Afficher les sources dans les réponses")
    theme: str = Field(description="Thème de l'interface (light/dark)")
    default_mode_id: int = Field(description="Mode de conversation par défaut")
    default_mode_name: Optional[str] = Field(None, description="Nom du mode par défaut")

    class Config:
        from_attributes = True


class PreferencesUpdate(BaseModel):
    """Schéma de mise à jour des préférences"""
    top_k: Optional[int] = Field(None, ge=1, le=10, description="Nombre de sources RAG (1-10)")
    show_sources: Optional[bool] = Field(None, description="Afficher les sources")
    theme: Optional[str] = Field(None, pattern="^(light|dark)$", description="Thème (light/dark)")
    default_mode_id: Optional[int] = Field(None, ge=1, description="Mode par défaut")
