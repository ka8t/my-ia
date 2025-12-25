"""
Router Preferences

Endpoints pour la gestion des préférences utilisateur.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models import User
from app.features.auth.service import current_active_user
from app.features.preferences.service import PreferencesService
from app.features.preferences.schemas import PreferencesRead, PreferencesUpdate

router = APIRouter(
    prefix="/preferences",
    tags=["preferences"]
)


@router.get(
    "/",
    response_model=PreferencesRead,
    summary="Récupérer mes préférences",
    description="Récupère les préférences de l'utilisateur connecté."
)
async def get_preferences(
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session)
) -> PreferencesRead:
    """
    Récupère les préférences de l'utilisateur.

    Si les préférences n'existent pas, elles sont créées avec les valeurs par défaut.
    """
    return await PreferencesService.get_preferences(db, current_user.id)


@router.patch(
    "/",
    response_model=PreferencesRead,
    summary="Modifier mes préférences",
    description="Met à jour les préférences de l'utilisateur connecté."
)
async def update_preferences(
    data: PreferencesUpdate,
    current_user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session)
) -> PreferencesRead:
    """
    Met à jour les préférences de l'utilisateur.

    - **top_k**: Nombre de sources RAG (1-10)
    - **show_sources**: Afficher les sources dans les réponses
    - **theme**: Thème de l'interface (light/dark)
    - **default_mode_id**: Mode de conversation par défaut
    """
    return await PreferencesService.update_preferences(db, current_user.id, data)
