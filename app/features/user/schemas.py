"""
Schemas Pydantic pour les utilisateurs

Définit les modèles de données pour la création, lecture et mise à jour des utilisateurs.
"""
import uuid
from typing import Optional
from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Schéma pour la lecture d'un utilisateur"""
    username: str
    full_name: Optional[str] = None
    role_id: int

    class Config:
        from_attributes = True


class UserCreate(schemas.BaseUserCreate):
    """Schéma pour la création d'un utilisateur"""
    username: str
    full_name: Optional[str] = None


class UserUpdate(schemas.BaseUserUpdate):
    """Schéma pour la mise à jour d'un utilisateur"""
    username: Optional[str] = None
    full_name: Optional[str] = None
