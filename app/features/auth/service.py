"""
Service d'authentification

Configure FastAPI Users avec le backend JWT.
"""
import uuid
import jwt
from typing import Optional
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport

from app.models import User
from app.features.auth.config import get_jwt_strategy, SECRET
from app.features.user.dependencies import get_user_manager


# Transports
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

# Auth Backend
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# FastAPI Users Instance
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

# Dependency pour récupérer l'utilisateur actif
current_active_user = fastapi_users.current_user(active=True)


async def verify_jwt_token(token: str) -> Optional[dict]:
    """
    Vérifie un token JWT et retourne le payload si valide

    Args:
        token: Token JWT à vérifier

    Returns:
        Payload du token si valide, None sinon
    """
    try:
        payload = jwt.decode(
            token,
            SECRET,
            algorithms=["HS256"],
            audience=["fastapi-users:auth"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
