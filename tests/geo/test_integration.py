"""
Tests d'integration HTTP pour Geo.

Execution: docker-compose exec app python -m pytest tests/geo/ -v
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestGeoPublicEndpoints:
    """Tests des endpoints publics."""

    async def test_list_countries_public(self, async_client: AsyncClient):
        """Test liste des pays est public (pas besoin d'auth)."""
        response = await async_client.get("/geo/countries")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_search_cities_public(self, async_client: AsyncClient):
        """Test recherche villes est public."""
        response = await async_client.get(
            "/geo/cities",
            params={"q": "Paris", "country": "FR"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_search_cities_query_too_short(self, async_client: AsyncClient):
        """Test erreur 422 si query trop courte."""
        response = await async_client.get(
            "/geo/cities",
            params={"q": "P", "country": "FR"}
        )

        # FastAPI validation: min_length=2
        assert response.status_code == 422

    async def test_get_country_not_found(self, async_client: AsyncClient):
        """Test 404 si pays inexistant."""
        response = await async_client.get("/geo/countries/ZZ")

        assert response.status_code == 404

    async def test_get_city_not_found(self, async_client: AsyncClient):
        """Test 404 si ville inexistante."""
        response = await async_client.get("/geo/cities/999999999")

        assert response.status_code == 404


class TestGeoAdminEndpoints:
    """Tests des endpoints admin."""

    async def test_geo_stats_requires_auth(self, async_client: AsyncClient):
        """Test stats geo necessite auth."""
        response = await async_client.get("/admin/geo/stats")

        assert response.status_code == 401

    async def test_geo_stats_with_auth(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Test stats geo avec auth admin."""
        response = await async_client.get(
            "/admin/geo/stats",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "countries_total" in data
        assert "cities_total" in data

    async def test_import_countries_requires_auth(self, async_client: AsyncClient):
        """Test import pays necessite auth."""
        response = await async_client.post("/admin/geo/import/countries")

        assert response.status_code == 401

    async def test_import_countries_with_auth(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Test import pays avec auth admin."""
        response = await async_client.post(
            "/admin/geo/import/countries",
            headers=admin_headers,
            json={"reset": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "imported_count" in data
        assert data["entity_type"] == "countries"

    async def test_list_admin_countries_requires_auth(self, async_client: AsyncClient):
        """Test liste pays admin necessite auth."""
        response = await async_client.get("/admin/geo/countries")

        assert response.status_code == 401

    async def test_list_admin_countries_with_auth(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Test liste pays admin avec auth."""
        response = await async_client.get(
            "/admin/geo/countries",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestGeoImport:
    """Tests d'import des donnees geo."""

    async def test_import_countries_creates_data(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Test que l'import cree bien des pays."""
        # Import
        response = await async_client.post(
            "/admin/geo/import/countries",
            headers=admin_headers,
            json={"reset": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verifier que des pays existent maintenant
        list_response = await async_client.get("/geo/countries")
        countries = list_response.json()

        # Au moins quelques pays devraient exister
        # (skipped_count si deja importes)
        total = data["imported_count"] + data.get("skipped_count", 0)
        assert total > 0 or len(countries) > 0

    async def test_import_cities_unsupported_country(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Test import villes pour pays non supporte."""
        response = await async_client.post(
            "/admin/geo/import/cities",
            headers=admin_headers,
            json={"country_code": "US", "reset": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "non supporte" in data["message"].lower()


class TestCountryCRUD:
    """Tests CRUD pays admin."""

    async def test_create_country(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Test creation d'un pays."""
        import uuid

        code = f"T{uuid.uuid4().hex[:1].upper()}"  # Code 2 lettres unique

        response = await async_client.post(
            "/admin/geo/countries",
            headers=admin_headers,
            json={
                "code": code,
                "name": "Test Country",
                "flag": "\U0001F3F3",  # White flag
                "phone_prefix": "+99",
                "is_active": True,
                "display_order": 999
            }
        )

        if response.status_code == 409:
            # Code deja existe, pas grave
            return

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == code
        assert data["name"] == "Test Country"

        # Cleanup
        await async_client.delete(
            f"/admin/geo/countries/{code}",
            headers=admin_headers
        )

    async def test_update_country(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Test mise a jour d'un pays."""
        # D'abord s'assurer que FR existe
        await async_client.post(
            "/admin/geo/import/countries",
            headers=admin_headers,
            json={"reset": False}
        )

        # Modifier l'ordre d'affichage de FR
        response = await async_client.patch(
            "/admin/geo/countries/FR",
            headers=admin_headers,
            json={"display_order": 1}
        )

        if response.status_code == 404:
            pytest.skip("Pays FR non trouve")

        assert response.status_code == 200
        data = response.json()
        assert data["display_order"] == 1

    async def test_toggle_country_active(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Test activation/desactivation d'un pays."""
        # S'assurer que les pays sont importes
        await async_client.post(
            "/admin/geo/import/countries",
            headers=admin_headers,
            json={"reset": False}
        )

        # Recuperer l'etat actuel
        get_response = await async_client.get(
            "/admin/geo/countries/DE",
            headers=admin_headers
        )

        if get_response.status_code == 404:
            pytest.skip("Pays DE non trouve")

        original_state = get_response.json()["is_active"]

        # Toggle
        toggle_response = await async_client.post(
            "/admin/geo/countries/DE/toggle-active",
            headers=admin_headers
        )

        assert toggle_response.status_code == 200
        new_state = toggle_response.json()["is_active"]
        assert new_state != original_state

        # Re-toggle pour restaurer l'etat
        await async_client.post(
            "/admin/geo/countries/DE/toggle-active",
            headers=admin_headers
        )
