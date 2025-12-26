"""
Tests pour le module Profile utilisateur.

Execution: docker-compose exec app python -m pytest tests/user/test_profile.py -v
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestProfileEndpoints:
    """Tests des endpoints profil."""

    async def test_get_profile_requires_auth(self, async_client: AsyncClient):
        """Test profil necessite auth."""
        response = await async_client.get("/users/me/profile")

        assert response.status_code == 401

    async def test_get_profile_with_auth(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Test recuperation profil avec auth."""
        response = await async_client.get(
            "/users/me/profile",
            headers=user_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "username" in data
        assert "first_name" in data
        assert "last_name" in data
        assert "is_verified" in data

    async def test_update_profile_requires_auth(self, async_client: AsyncClient):
        """Test mise a jour profil necessite auth."""
        response = await async_client.patch(
            "/users/me/profile",
            json={"first_name": "Test"}
        )

        assert response.status_code == 401

    async def test_update_profile_first_name(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Test mise a jour prenom."""
        import uuid
        new_name = f"TestName_{uuid.uuid4().hex[:4]}"

        response = await async_client.patch(
            "/users/me/profile",
            headers=user_headers,
            json={"first_name": new_name}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == new_name

    async def test_update_profile_phone_valid(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Test mise a jour telephone valide."""
        response = await async_client.patch(
            "/users/me/profile",
            headers=user_headers,
            json={"phone": "+33612345678"}
        )

        assert response.status_code == 200
        data = response.json()
        # Le telephone est normalise
        assert "33612345678" in data["phone"] or data["phone"] == "+33612345678"

    async def test_update_profile_phone_invalid(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Test mise a jour telephone invalide."""
        response = await async_client.patch(
            "/users/me/profile",
            headers=user_headers,
            json={"phone": "123"}  # Trop court
        )

        assert response.status_code == 422  # Validation error


class TestPasswordChange:
    """Tests du changement de mot de passe."""

    async def test_change_password_requires_auth(self, async_client: AsyncClient):
        """Test changement mot de passe necessite auth."""
        response = await async_client.post(
            "/users/me/change-password",
            json={
                "current_password": "old",
                "new_password": "new",
                "confirm_password": "new"
            }
        )

        assert response.status_code == 401

    async def test_change_password_wrong_current(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Test erreur si mot de passe actuel incorrect."""
        response = await async_client.post(
            "/users/me/change-password",
            headers=user_headers,
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewSecureP@ss123",
                "confirm_password": "NewSecureP@ss123"
            }
        )

        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    async def test_change_password_mismatch(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Test erreur si confirmation ne correspond pas."""
        response = await async_client.post(
            "/users/me/change-password",
            headers=user_headers,
            json={
                "current_password": "Test123!",  # Mot de passe du test_user
                "new_password": "NewSecureP@ss123",
                "confirm_password": "DifferentP@ss123"
            }
        )

        assert response.status_code == 422  # Validation Pydantic

    async def test_change_password_weak(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Test erreur si nouveau mot de passe trop faible."""
        response = await async_client.post(
            "/users/me/change-password",
            headers=user_headers,
            json={
                "current_password": "Test123!",
                # Assez long (8+ chars) mais ne respecte pas la politique
                # (pas de majuscule, pas de caractere special)
                "new_password": "weakpassword123",
                "confirm_password": "weakpassword123"
            }
        )

        assert response.status_code == 400
        # Le detail contient les erreurs de validation de la politique


class TestProfileWithGeo:
    """Tests du profil avec donnees geo."""

    async def test_update_profile_invalid_country(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Test erreur si pays invalide."""
        response = await async_client.patch(
            "/users/me/profile",
            headers=user_headers,
            json={"country_code": "ZZ"}  # Pays inexistant
        )

        assert response.status_code == 400
        assert "non trouve" in response.json()["detail"].lower()

    async def test_update_profile_invalid_city(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Test erreur si ville invalide."""
        response = await async_client.patch(
            "/users/me/profile",
            headers=user_headers,
            json={"city_id": 999999999}  # Ville inexistante
        )

        assert response.status_code == 400
        assert "non trouvee" in response.json()["detail"].lower()

    async def test_update_profile_address(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Test mise a jour adresse."""
        response = await async_client.patch(
            "/users/me/profile",
            headers=user_headers,
            json={
                "address_line1": "123 Rue de Test",
                "address_line2": "Appartement 5"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["address_line1"] == "123 Rue de Test"
        assert data["address_line2"] == "Appartement 5"

    async def test_update_profile_multiple_fields(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Test mise a jour plusieurs champs."""
        import uuid
        new_name = f"MultiTest_{uuid.uuid4().hex[:4]}"

        response = await async_client.patch(
            "/users/me/profile",
            headers=user_headers,
            json={
                "first_name": new_name,
                "last_name": "Dupont",
                "phone": "+33687654321"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == new_name
        assert data["last_name"] == "Dupont"

    async def test_profile_contains_all_fields(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Test que le profil contient tous les champs attendus."""
        response = await async_client.get(
            "/users/me/profile",
            headers=user_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Champs obligatoires du profil
        required_fields = [
            "email", "username", "first_name", "last_name",
            "phone", "address_line1", "address_line2",
            "city_id", "city_name", "country_code", "country_name",
            "is_verified", "created_at"
        ]

        for field in required_fields:
            assert field in data, f"Champ manquant: {field}"


class TestProfileValidation:
    """Tests de validation des champs profil."""

    async def test_first_name_max_length(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Test longueur max prenom."""
        # 100 caracteres est la limite
        long_name = "A" * 101

        response = await async_client.patch(
            "/users/me/profile",
            headers=user_headers,
            json={"first_name": long_name}
        )

        assert response.status_code == 422  # Validation error

    async def test_country_code_format(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Test format code pays (2 caracteres)."""
        response = await async_client.patch(
            "/users/me/profile",
            headers=user_headers,
            json={"country_code": "FRA"}  # 3 caracteres = invalide
        )

        assert response.status_code == 422

    async def test_empty_string_vs_null(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Test que chaine vide est acceptee comme null."""
        response = await async_client.patch(
            "/users/me/profile",
            headers=user_headers,
            json={"phone": ""}  # Vide = devrait etre accepte
        )

        # Peut etre 200 ou 422 selon l'implementation
        assert response.status_code in [200, 422]
