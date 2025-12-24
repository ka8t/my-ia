"""
Router pour les endpoints d'authentification

Expose tous les endpoints d'authentification (login, register, reset-password, verify).
"""
from fastapi import APIRouter
from app.features.auth.service import auth_backend, fastapi_users
from app.features.user.schemas import UserRead, UserCreate


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
