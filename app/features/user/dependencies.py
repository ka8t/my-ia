"""
Dépendances pour la gestion des utilisateurs

Contient les dépendances FastAPI pour l'accès à la base de données utilisateurs.
"""
from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models import User
from app.features.user.service import UserManager


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    """
    Dépendance pour obtenir la base de données utilisateurs

    Args:
        session: Session SQLAlchemy asynchrone

    Yields:
        SQLAlchemyUserDatabase: Instance de la base de données utilisateurs
    """
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    """
    Dépendance pour obtenir le gestionnaire d'utilisateurs

    Args:
        user_db: Base de données utilisateurs

    Yields:
        UserManager: Instance du gestionnaire d'utilisateurs
    """
    yield UserManager(user_db)
