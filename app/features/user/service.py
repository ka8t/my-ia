"""
Service de gestion des utilisateurs

Contient le UserManager avec les hooks pour l'audit des actions utilisateurs.
"""
import uuid
from typing import Optional
from fastapi import Request, Response
from fastapi_users import BaseUserManager, UUIDIDMixin

from app.models import User
from app.features.auth.config import SECRET
from app.features.audit import service as audit_service


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """
    Gestionnaire d'utilisateurs avec hooks d'audit

    Gère l'inscription, la connexion, la réinitialisation de mot de passe
    et enregistre toutes les actions dans l'audit trail.
    """
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
        self, user: User, request: Optional[Request] = None, response: Optional[Response] = None
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
