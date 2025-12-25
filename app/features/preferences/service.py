"""
Service Preferences

Logique métier pour la gestion des préférences utilisateur.
"""
import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.preferences.repository import PreferencesRepository
from app.features.preferences.schemas import PreferencesRead, PreferencesUpdate

logger = logging.getLogger(__name__)


class PreferencesService:
    """Service pour la gestion des préférences"""

    @staticmethod
    async def get_preferences(
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> PreferencesRead:
        """
        Récupère les préférences de l'utilisateur.
        Crée les préférences par défaut si elles n'existent pas.

        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur

        Returns:
            Préférences de l'utilisateur
        """
        preferences = await PreferencesRepository.get_by_user_id(db, user_id)

        # Créer les préférences par défaut si inexistantes
        if not preferences:
            logger.info(f"Creating default preferences for user {user_id}")
            preferences = await PreferencesRepository.create(db, user_id)

        return PreferencesRead(
            top_k=preferences.top_k,
            show_sources=preferences.show_sources,
            theme=preferences.theme,
            default_mode_id=preferences.default_mode_id,
            default_mode_name=preferences.default_mode.name if preferences.default_mode else None
        )

    @staticmethod
    async def update_preferences(
        db: AsyncSession,
        user_id: uuid.UUID,
        data: PreferencesUpdate
    ) -> PreferencesRead:
        """
        Met à jour les préférences de l'utilisateur.

        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            data: Données de mise à jour

        Returns:
            Préférences mises à jour
        """
        preferences = await PreferencesRepository.get_by_user_id(db, user_id)

        # Créer les préférences si inexistantes
        if not preferences:
            preferences = await PreferencesRepository.create(db, user_id)

        # Mettre à jour
        updated = await PreferencesRepository.update(
            db,
            preferences,
            top_k=data.top_k,
            show_sources=data.show_sources,
            theme=data.theme,
            default_mode_id=data.default_mode_id
        )

        logger.info(f"Preferences updated for user {user_id}")

        return PreferencesRead(
            top_k=updated.top_k,
            show_sources=updated.show_sources,
            theme=updated.theme,
            default_mode_id=updated.default_mode_id,
            default_mode_name=updated.default_mode.name if updated.default_mode else None
        )
