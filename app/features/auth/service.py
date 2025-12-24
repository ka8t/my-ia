"""
Service d'authentification

Configure FastAPI Users avec le backend JWT.
"""
import uuid
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport

from app.models import User
from app.features.auth.config import get_jwt_strategy
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
