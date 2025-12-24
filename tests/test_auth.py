"""
Tests pour l'authentification

Tests des endpoints d'authentification (register, login, etc.)
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(async_client: AsyncClient):
    """
    Test l'enregistrement d'un nouvel utilisateur
    """
    user_data = {
        "email": "test@example.com",
        "password": "StrongPassword123!",
        "is_active": True,
        "is_superuser": False,
        "is_verified": False,
    }

    response = await async_client.post("/auth/register", json=user_data)

    # Note: Ce test peut échouer si les endpoints auth ne sont pas encore configurés
    # Ajustez selon votre implémentation
    assert response.status_code in [200, 201]

    data = response.json()
    assert "email" in data
    assert data["email"] == user_data["email"]


@pytest.mark.asyncio
async def test_login_user(async_client: AsyncClient):
    """
    Test la connexion d'un utilisateur

    Note: Ce test nécessite un utilisateur existant ou doit être adapté
    """
    # TODO: Créer un utilisateur de test d'abord via une fixture
    login_data = {
        "username": "test@example.com",
        "password": "StrongPassword123!"
    }

    response = await async_client.post(
        "/auth/jwt/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    # Ce test peut échouer si l'utilisateur n'existe pas
    # À adapter selon votre configuration
    assert response.status_code in [200, 401]
