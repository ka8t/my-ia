"""
Configuration de l'authentification JWT

Contient la configuration des secrets et de la stratégie JWT.
"""
import os
from fastapi_users.authentication import JWTStrategy


# Configuration JWT
SECRET = os.getenv("JWT_SECRET_KEY", "SECRET_KEY_TO_CHANGE_IN_ENV_FOR_DEV_ONLY")
TOKEN_LIFETIME_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
TOKEN_LIFETIME_SECONDS = TOKEN_LIFETIME_MINUTES * 60


def get_jwt_strategy() -> JWTStrategy:
    """
    Retourne la stratégie JWT configurée

    Returns:
        JWTStrategy: Stratégie JWT avec secret et durée de vie configurable
    """
    return JWTStrategy(secret=SECRET, lifetime_seconds=TOKEN_LIFETIME_SECONDS)
