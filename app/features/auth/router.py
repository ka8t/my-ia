"""
Router pour les endpoints d'authentification

Expose tous les endpoints d'authentification (login, register, reset-password, verify).
"""
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from app.features.auth.service import auth_backend, fastapi_users, current_active_user
from app.features.auth.config import SECRET, TOKEN_LIFETIME_SECONDS
from app.features.user.schemas import UserRead, UserCreate
from app.models import User


# Router principal pour l'authentification
router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

# Sous-routers générés par fastapi_users
auth_router = fastapi_users.get_auth_router(auth_backend)
register_router = fastapi_users.get_register_router(UserRead, UserCreate)
reset_password_router = fastapi_users.get_reset_password_router()
verify_router = fastapi_users.get_verify_router(UserRead)

# Inclure tous les sous-routers dans le router principal (pattern FastAPI standard)
router.include_router(auth_router, prefix="/jwt")
router.include_router(register_router, prefix="/register")
router.include_router(reset_password_router, prefix="/reset-password")
router.include_router(verify_router, prefix="/verify")


@router.post("/refresh")
async def refresh_token(current_user: User = Depends(current_active_user)):
    """
    Renouvelle le token JWT pour l'utilisateur connecte.

    Le token actuel doit etre valide pour obtenir un nouveau token.
    """
    # Generer un nouveau token
    payload = {
        "sub": str(current_user.id),
        "aud": ["fastapi-users:auth"],
        "exp": datetime.now(timezone.utc) + timedelta(seconds=TOKEN_LIFETIME_SECONDS)
    }

    new_token = jwt.encode(payload, SECRET, algorithm="HS256")

    return {
        "access_token": new_token,
        "token_type": "bearer"
    }
