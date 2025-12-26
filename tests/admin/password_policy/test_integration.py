"""
Tests d'integration HTTP pour Password Policy.

Execution: docker-compose exec app python -m pytest tests/admin/password_policy/ -v
"""
import uuid
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# =============================================================================
# TESTS ENDPOINTS LIST & GET
# =============================================================================

class TestPasswordPolicyEndpoints:
    """Tests des endpoints REST."""

    async def test_list_policies_requires_auth(self, async_client: AsyncClient):
        """Test liste des politiques sans auth."""
        response = await async_client.get("/admin/password-policies")
        assert response.status_code == 401

    async def test_list_policies_with_auth(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Test liste des politiques avec auth admin."""
        response = await async_client.get(
            "/admin/password-policies",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1  # Au moins default

    async def test_get_requirements_public(self, async_client: AsyncClient):
        """Test endpoint requirements est public."""
        response = await async_client.get(
            "/admin/password-policies/requirements"
        )

        assert response.status_code == 200
        data = response.json()
        assert "min_length" in data
        assert "require_uppercase" in data

    async def test_get_policy_by_id(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Test recuperation d'une politique par ID."""
        # D'abord lister pour obtenir un ID
        list_response = await async_client.get(
            "/admin/password-policies",
            headers=admin_headers
        )
        policies = list_response.json()
        if not policies:
            pytest.skip("Aucune politique dans la DB")

        policy_id = policies[0]["id"]

        # Recuperer par ID
        response = await async_client.get(
            f"/admin/password-policies/{policy_id}",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == policy_id


# =============================================================================
# TESTS CRUD
# =============================================================================

class TestPasswordPolicyCRUD:
    """Tests CRUD via HTTP."""

    async def test_create_policy(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Test creation d'une politique."""
        unique_name = f"http_test_{uuid.uuid4().hex[:8]}"

        response = await async_client.post(
            "/admin/password-policies",
            headers=admin_headers,
            json={
                "name": unique_name,
                "min_length": 10,
                "max_length": 64,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_digit": False,
                "require_special": False,
                "history_count": 5
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == unique_name
        assert data["min_length"] == 10
        assert data["require_digit"] is False
        assert data["history_count"] == 5

        # Cleanup
        policy_id = data["id"]
        await async_client.delete(
            f"/admin/password-policies/{policy_id}",
            headers=admin_headers
        )

    async def test_create_policy_duplicate_name(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Test 409 si nom duplique."""
        response = await async_client.post(
            "/admin/password-policies",
            headers=admin_headers,
            json={
                "name": "default",  # Existe deja
                "min_length": 8
            }
        )

        assert response.status_code == 409

    async def test_update_policy(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Test mise a jour d'une politique."""
        # Creer une politique de test
        unique_name = f"update_http_{uuid.uuid4().hex[:8]}"
        create_response = await async_client.post(
            "/admin/password-policies",
            headers=admin_headers,
            json={"name": unique_name, "min_length": 8}
        )
        policy_id = create_response.json()["id"]

        try:
            # Mettre a jour
            update_response = await async_client.patch(
                f"/admin/password-policies/{policy_id}",
                headers=admin_headers,
                json={
                    "min_length": 12,
                    "require_special": False
                }
            )

            assert update_response.status_code == 200
            data = update_response.json()
            assert data["min_length"] == 12
            assert data["require_special"] is False
        finally:
            # Cleanup
            await async_client.delete(
                f"/admin/password-policies/{policy_id}",
                headers=admin_headers
            )

    async def test_delete_policy(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Test suppression d'une politique."""
        # Creer une politique de test
        unique_name = f"delete_http_{uuid.uuid4().hex[:8]}"
        create_response = await async_client.post(
            "/admin/password-policies",
            headers=admin_headers,
            json={"name": unique_name, "min_length": 8}
        )
        policy_id = create_response.json()["id"]

        # Supprimer
        delete_response = await async_client.delete(
            f"/admin/password-policies/{policy_id}",
            headers=admin_headers
        )

        assert delete_response.status_code == 204

        # Verifier suppression
        get_response = await async_client.get(
            f"/admin/password-policies/{policy_id}",
            headers=admin_headers
        )
        assert get_response.status_code == 404

    async def test_delete_default_forbidden(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Test impossible de supprimer default."""
        # Recuperer l'ID de default
        list_response = await async_client.get(
            "/admin/password-policies",
            headers=admin_headers
        )
        policies = list_response.json()
        default_policy = next((p for p in policies if p["name"] == "default"), None)

        if not default_policy:
            pytest.skip("Politique default non trouvee")

        # Essayer de supprimer
        delete_response = await async_client.delete(
            f"/admin/password-policies/{default_policy['id']}",
            headers=admin_headers
        )

        assert delete_response.status_code == 403


# =============================================================================
# TESTS VALIDATION ENDPOINT
# =============================================================================

class TestPasswordValidationEndpoint:
    """Tests de l'endpoint de validation."""

    async def test_validate_password_public(self, async_client: AsyncClient):
        """Test endpoint validation est public."""
        response = await async_client.post(
            "/admin/password-policies/validate",
            json={
                "password": "SecureP@ss123",
                "policy_name": "default"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "is_valid" in data
        assert "errors" in data
        assert "strength_score" in data
        assert "suggestions" in data

    async def test_validate_password_valid(self, async_client: AsyncClient):
        """Test validation mot de passe valide."""
        response = await async_client.post(
            "/admin/password-policies/validate",
            json={
                "password": "SecureP@ssword123!",
                "policy_name": "default"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["errors"] == []
        assert data["strength_score"] > 50

    async def test_validate_password_invalid(self, async_client: AsyncClient):
        """Test validation mot de passe invalide."""
        response = await async_client.post(
            "/admin/password-policies/validate",
            json={
                "password": "weak",
                "policy_name": "default"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert len(data["errors"]) > 0

    async def test_validate_password_strength_score(self, async_client: AsyncClient):
        """Test score de robustesse."""
        # Mot de passe faible
        weak_response = await async_client.post(
            "/admin/password-policies/validate",
            json={"password": "abc123", "policy_name": "default"}
        )
        weak_score = weak_response.json()["strength_score"]

        # Mot de passe fort
        strong_response = await async_client.post(
            "/admin/password-policies/validate",
            json={"password": "SecureP@ss123!XYZ", "policy_name": "default"}
        )
        strong_score = strong_response.json()["strength_score"]

        assert strong_score > weak_score
