"""
Configuration de l'authentification JWT

Contient la configuration des secrets et de la stratégie JWT.
"""
import os
from fastapi_users.authentication import JWTStrategy


# Configuration JWT
# En production, cette clé doit être chargée depuis les variables d'environnement
SECRET = os.getenv("JWT_SECRET_KEY", "SECRET_KEY_TO_CHANGE_IN_ENV_FOR_DEV_ONLY")


def get_jwt_strategy() -> JWTStrategy:
    """
    Retourne la stratégie JWT configurée

    Returns:
        JWTStrategy: Stratégie JWT avec secret et durée de vie de 1 heure
    """
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)
