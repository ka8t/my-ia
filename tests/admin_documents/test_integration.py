"""
Tests d'integration HTTP pour les endpoints Admin Documents.

Execution: docker-compose exec app python -m pytest tests/admin_documents/test_integration.py -v
"""

import pytest
from uuid import uuid4

from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


class TestAdminDocumentsListEndpoint:
    """Tests pour GET /api/admin/documents"""

    async def test_list_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401."""
        response = await async_client.get("/api/admin/documents")
        assert response.status_code == 401

    async def test_list_requires_admin(
        self, async_client: AsyncClient, user_headers: dict
    ):
        """Endpoint avec user non-admin retourne 403."""
        response = await async_client.get(
            "/api/admin/documents", headers=user_headers
        )
        # Peut etre 403 ou 401 selon l'implementation
        assert response.status_code in [401, 403]

    async def test_list_documents_as_admin(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Admin peut lister tous les documents."""
        response = await async_client.get(
            "/api/admin/documents", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "total" in data
        assert "page" in data

    async def test_list_with_filters(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Liste avec filtres."""
        response = await async_client.get(
            "/api/admin/documents?visibility=public&page=1&page_size=5",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    async def test_list_with_search(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Recherche par nom de fichier."""
        response = await async_client.get(
            "/api/admin/documents?search=test",
            headers=admin_headers,
        )

        assert response.status_code == 200


class TestAdminDocumentsStatsEndpoint:
    """Tests pour GET /api/admin/documents/stats"""

    async def test_stats_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401."""
        response = await async_client.get("/api/admin/documents/stats")
        assert response.status_code == 401

    async def test_stats_as_admin(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Admin peut voir les stats globales."""
        response = await async_client.get(
            "/api/admin/documents/stats", headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_bytes" in data
        assert "total_files" in data
        assert "total_users" in data
        assert "top_users" in data


class TestAdminDocumentsDetailEndpoint:
    """Tests pour GET /api/admin/documents/{id}"""

    async def test_detail_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401."""
        response = await async_client.get(f"/api/admin/documents/{uuid4()}")
        assert response.status_code == 401

    async def test_detail_not_found(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Document non trouve retourne 404."""
        response = await async_client.get(
            f"/api/admin/documents/{uuid4()}", headers=admin_headers
        )
        assert response.status_code == 404


class TestAdminDocumentsUpdateEndpoint:
    """Tests pour PATCH /api/admin/documents/{id}"""

    async def test_update_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401."""
        response = await async_client.patch(
            f"/api/admin/documents/{uuid4()}",
            json={"is_indexed": False},
        )
        assert response.status_code == 401

    async def test_update_not_found(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Document non trouve retourne 404."""
        response = await async_client.patch(
            f"/api/admin/documents/{uuid4()}",
            json={"is_indexed": False},
            headers=admin_headers,
        )
        assert response.status_code == 404


class TestAdminDocumentsDeleteEndpoint:
    """Tests pour DELETE /api/admin/documents/{id}"""

    async def test_delete_requires_auth(self, async_client: AsyncClient):
        """Endpoint sans auth retourne 401."""
        response = await async_client.delete(f"/api/admin/documents/{uuid4()}")
        assert response.status_code == 401

    async def test_delete_not_found(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Document non trouve retourne 404."""
        response = await async_client.delete(
            f"/api/admin/documents/{uuid4()}", headers=admin_headers
        )
        assert response.status_code == 404


class TestAdminBulkOperations:
    """Tests pour les operations en masse."""

    async def test_bulk_visibility_requires_auth(self, async_client: AsyncClient):
        """Bulk visibility sans auth retourne 401."""
        response = await async_client.post(
            "/api/admin/documents/bulk/visibility",
            json={"document_ids": [str(uuid4())], "visibility": "private"},
        )
        assert response.status_code == 401

    async def test_bulk_visibility_as_admin(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Admin peut changer la visibilite en masse."""
        response = await async_client.post(
            "/api/admin/documents/bulk/visibility",
            json={"document_ids": [str(uuid4())], "visibility": "private"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "success_count" in data
        assert "error_count" in data

    async def test_bulk_delete_requires_auth(self, async_client: AsyncClient):
        """Bulk delete sans auth retourne 401."""
        response = await async_client.post(
            "/api/admin/documents/bulk/delete",
            json={"document_ids": [str(uuid4())]},
        )
        assert response.status_code == 401

    async def test_bulk_delete_as_admin(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Admin peut supprimer en masse."""
        response = await async_client.post(
            "/api/admin/documents/bulk/delete",
            json={"document_ids": [str(uuid4())]},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "success_count" in data


class TestAdminUserQuotaEndpoints:
    """Tests pour les endpoints de quota utilisateur."""

    async def test_get_quota_requires_auth(self, async_client: AsyncClient):
        """Get quota sans auth retourne 401."""
        response = await async_client.get(f"/api/admin/users/{uuid4()}/quota")
        assert response.status_code == 401

    async def test_get_quota_not_found(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Utilisateur non trouve retourne 404."""
        response = await async_client.get(
            f"/api/admin/users/{uuid4()}/quota", headers=admin_headers
        )
        assert response.status_code == 404

    async def test_set_quota_requires_auth(self, async_client: AsyncClient):
        """Set quota sans auth retourne 401."""
        response = await async_client.put(
            f"/api/admin/users/{uuid4()}/quota",
            json={"quota_bytes": 1073741824},
        )
        assert response.status_code == 401

    async def test_set_quota_validation(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        """Quota doit etre positif."""
        response = await async_client.put(
            f"/api/admin/users/{uuid4()}/quota",
            json={"quota_bytes": -100},
            headers=admin_headers,
        )
        assert response.status_code == 422

    async def test_delete_quota_requires_auth(self, async_client: AsyncClient):
        """Delete quota sans auth retourne 401."""
        response = await async_client.delete(f"/api/admin/users/{uuid4()}/quota")
        assert response.status_code == 401
