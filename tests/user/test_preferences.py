"""
Tests pour le module Preferences utilisateur

Execution: docker-compose exec app python -m pytest tests/user/test_preferences.py -v
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


class TestPreferencesEndpoints:
    """Tests des endpoints /preferences"""

    async def test_get_preferences_requires_auth(self, async_client: AsyncClient):
        """Récupération des préférences sans auth retourne 401"""
        response = await async_client.get("/preferences/")
        assert response.status_code == 401

    async def test_get_preferences(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Récupération des préférences avec auth"""
        response = await async_client.get("/preferences/", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        assert "top_k" in data
        assert "show_sources" in data
        assert "theme" in data
        assert "default_mode_id" in data

    async def test_get_preferences_default_values(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Préférences par défaut sont correctes"""
        response = await async_client.get("/preferences/", headers=user_headers)
        assert response.status_code == 200
        data = response.json()

        # Valeurs par défaut attendues
        assert data["top_k"] >= 1
        assert data["top_k"] <= 10
        assert isinstance(data["show_sources"], bool)
        assert data["theme"] in ["light", "dark"]
        assert data["default_mode_id"] >= 1

    async def test_update_preferences_requires_auth(self, async_client: AsyncClient):
        """Mise à jour des préférences sans auth retourne 401"""
        response = await async_client.patch("/preferences/", json={"top_k": 5})
        assert response.status_code == 401

    async def test_update_preferences_top_k(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Mise à jour de top_k"""
        response = await async_client.patch(
            "/preferences/",
            json={"top_k": 6},
            headers=user_headers
        )
        assert response.status_code == 200
        assert response.json()["top_k"] == 6

    async def test_update_preferences_show_sources(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Mise à jour de show_sources"""
        response = await async_client.patch(
            "/preferences/",
            json={"show_sources": False},
            headers=user_headers
        )
        assert response.status_code == 200
        assert response.json()["show_sources"] is False

    async def test_update_preferences_theme(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Mise à jour du thème"""
        response = await async_client.patch(
            "/preferences/",
            json={"theme": "dark"},
            headers=user_headers
        )
        assert response.status_code == 200
        assert response.json()["theme"] == "dark"

    async def test_update_preferences_invalid_theme(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Thème invalide retourne erreur validation"""
        response = await async_client.patch(
            "/preferences/",
            json={"theme": "invalid"},
            headers=user_headers
        )
        assert response.status_code == 422  # Validation error

    async def test_update_preferences_invalid_top_k(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """top_k hors limites retourne erreur validation"""
        response = await async_client.patch(
            "/preferences/",
            json={"top_k": 100},  # Trop grand
            headers=user_headers
        )
        assert response.status_code == 422

    async def test_update_multiple_preferences(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Mise à jour de plusieurs préférences"""
        response = await async_client.patch(
            "/preferences/",
            json={
                "top_k": 3,
                "show_sources": True,
                "theme": "light"
            },
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["top_k"] == 3
        assert data["show_sources"] is True
        assert data["theme"] == "light"


class TestPreferencesService:
    """Tests du service Preferences"""

    async def test_get_preferences_creates_default(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """get_preferences crée les préférences par défaut si inexistantes"""
        from app.features.preferences.service import PreferencesService

        # Peut récupérer ou créer
        result = await PreferencesService.get_preferences(db_session, user_id)

        assert result is not None
        assert result.top_k >= 1
        assert result.theme in ["light", "dark"]

    async def test_update_preferences_service(
        self, db_session: AsyncSession, user_id: uuid.UUID
    ):
        """Test mise à jour via service"""
        from app.features.preferences.service import PreferencesService
        from app.features.preferences.schemas import PreferencesUpdate

        data = PreferencesUpdate(top_k=7, theme="dark")
        result = await PreferencesService.update_preferences(db_session, user_id, data)

        assert result is not None
        assert result.top_k == 7
        assert result.theme == "dark"
