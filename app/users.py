import uuid
import os
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models import User
from app.features.audit import service as audit_service

# --- Configuration JWT ---
# En production, cette clé doit être chargée depuis les variables d'environnement
SECRET = os.getenv("JWT_SECRET_KEY", "SECRET_KEY_TO_CHANGE_IN_ENV_FOR_DEV_ONLY")

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)

# --- Transports ---
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

# --- Auth Backend ---
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

# --- User Manager ---
class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """Hook appelé après inscription réussie"""
        print(f"User {user.id} has registered.")

        # Log l'inscription dans l'audit trail
        try:
            await audit_service.log_user_created(
                db=self.user_db.session,
                admin_user_id=None,  # Auto-registration (pas d'admin)
                new_user_id=user.id,
                new_user_email=user.email,
                role_id=user.role_id,
                request=request
            )
        except Exception as e:
            print(f"Error logging user registration: {e}")

    async def on_after_login(
        self, user: User, request: Optional[Request] = None
    ):
        """Hook appelé après connexion réussie"""
        print(f"User {user.id} has logged in.")

        # Log la connexion dans l'audit trail
        try:
            await audit_service.log_login_success(
                db=self.user_db.session,
                user_id=user.id,
                request=request
            )
        except Exception as e:
            print(f"Error logging login: {e}")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Hook appelé après demande de réinitialisation de mot de passe"""
        print(f"User {user.id} has forgot their password. Reset token: {token}")

        # Log la demande de reset dans l'audit trail
        try:
            await audit_service.log_action(
                db=self.user_db.session,
                action_name='password_reset_requested',
                user_id=user.id,
                resource_type_name='user',
                resource_id=user.id,
                details={'email': user.email},
                request=request
            )
        except Exception as e:
            print(f"Error logging password reset request: {e}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Hook appelé après demande de vérification email"""
        print(f"Verification requested for user {user.id}. Verification token: {token}")

async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)

async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)

# --- FastAPI Users Instance ---
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

current_active_user = fastapi_users.current_user(active=True)
