"""
Repository Preferences

Opérations de base de données pour les préférences utilisateur.
"""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import UserPreference


class PreferencesRepository:
    """Repository pour les opérations sur les préférences"""

    @staticmethod
    async def get_by_user_id(
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> Optional[UserPreference]:
        """
        Récupère les préférences d'un utilisateur.

        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur

        Returns:
            Préférences ou None si non trouvées
        """
        result = await db.execute(
            select(UserPreference)
            .options(selectinload(UserPreference.default_mode))
            .where(UserPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: uuid.UUID,
        top_k: int = 4,
        show_sources: bool = True,
        theme: str = "light",
        default_mode_id: int = 1
    ) -> UserPreference:
        """
        Crée les préférences pour un utilisateur.

        Args:
            db: Session de base de données
            user_id: ID de l'utilisateur
            top_k: Nombre de sources RAG
            show_sources: Afficher les sources
            theme: Thème
            default_mode_id: Mode par défaut

        Returns:
            Préférences créées
        """
        preferences = UserPreference(
            user_id=user_id,
            top_k=top_k,
            show_sources=show_sources,
            theme=theme,
            default_mode_id=default_mode_id
        )
        db.add(preferences)
        await db.commit()
        await db.refresh(preferences)
        await db.refresh(preferences, ["default_mode"])
        return preferences

    @staticmethod
    async def update(
        db: AsyncSession,
        preferences: UserPreference,
        top_k: Optional[int] = None,
        show_sources: Optional[bool] = None,
        theme: Optional[str] = None,
        default_mode_id: Optional[int] = None
    ) -> UserPreference:
        """
        Met à jour les préférences.

        Args:
            db: Session de base de données
            preferences: Préférences à modifier
            top_k: Nombre de sources RAG (optionnel)
            show_sources: Afficher les sources (optionnel)
            theme: Thème (optionnel)
            default_mode_id: Mode par défaut (optionnel)

        Returns:
            Préférences mises à jour
        """
        if top_k is not None:
            preferences.top_k = top_k
        if show_sources is not None:
            preferences.show_sources = show_sources
        if theme is not None:
            preferences.theme = theme
        if default_mode_id is not None:
            preferences.default_mode_id = default_mode_id

        await db.commit()
        await db.refresh(preferences)
        await db.refresh(preferences, ["default_mode"])
        return preferences
