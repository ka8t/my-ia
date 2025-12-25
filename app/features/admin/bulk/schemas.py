"""
Schemas Admin Bulk

Schémas Pydantic pour les opérations en masse.
"""
import uuid
from typing import List, Dict, Optional

from pydantic import BaseModel, Field


# =============================================================================
# REQUÊTES BULK
# =============================================================================

class BulkUserIds(BaseModel):
    """Liste d'IDs utilisateurs pour opérations bulk"""
    user_ids: List[uuid.UUID] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Liste des IDs utilisateurs (max 100)"
    )


class BulkRoleChange(BaseModel):
    """Changement de rôle en masse"""
    user_ids: List[uuid.UUID] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Liste des IDs utilisateurs (max 100)"
    )
    new_role_id: int = Field(..., ge=1, description="Nouveau rôle ID")
    reason: Optional[str] = Field(None, max_length=500, description="Raison du changement")


class BulkIds(BaseModel):
    """Liste d'IDs génériques pour opérations bulk"""
    ids: List[uuid.UUID] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Liste des IDs (max 100)"
    )


class BulkDeleteRequest(BaseModel):
    """Requête de suppression en masse"""
    ids: List[uuid.UUID] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Liste des IDs à supprimer (max 100)"
    )
    confirm: bool = Field(
        default=False,
        description="Confirmation obligatoire (doit être true)"
    )


# =============================================================================
# RÉPONSES BULK
# =============================================================================

class BulkOperationResult(BaseModel):
    """Résultat d'une opération bulk"""
    success_count: int = Field(..., description="Nombre d'opérations réussies")
    failed_count: int = Field(..., description="Nombre d'opérations échouées")
    failed_ids: List[uuid.UUID] = Field(
        default_factory=list,
        description="IDs des opérations échouées"
    )
    errors: Dict[str, str] = Field(
        default_factory=dict,
        description="Détails des erreurs par ID"
    )
