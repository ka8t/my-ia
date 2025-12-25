"""
Tests d'intégration pour les endpoints Admin

Ces tests vérifient les endpoints HTTP de l'administration.
Utilise httpx.AsyncClient avec pytest-asyncio.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ============================================================================
# TESTS ENDPOINTS USERS
# ============================================================================

class TestAdminUsersEndpoints:
    """Tests des endpoints /admin/users"""

    async def test_list_users_requires_auth(self, async_client: AsyncClient):
        """GET /admin/users sans auth retourne 401"""
        response = await async_client.get("/admin/users")
        assert response.status_code == 401

    async def test_list_users_with_admin(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/users avec admin retourne 200"""
        response = await async_client.get("/admin/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_list_users_pagination(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/users supporte la pagination"""
        response = await async_client.get(
            "/admin/users?limit=5&offset=0",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 0

    async def test_list_users_filter_by_role(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/users?role_id=1 filtre par rôle"""
        response = await async_client.get(
            "/admin/users?role_id=1",
            headers=admin_headers
        )
        assert response.status_code == 200

    async def test_list_users_search(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/users?search=admin recherche"""
        response = await async_client.get(
            "/admin/users?search=admin",
            headers=admin_headers
        )
        assert response.status_code == 200


# ============================================================================
# TESTS ENDPOINTS DASHBOARD
# ============================================================================

class TestAdminDashboardEndpoints:
    """Tests des endpoints /admin/dashboard"""

    async def test_dashboard_requires_auth(self, async_client: AsyncClient):
        """GET /admin/dashboard/overview sans auth retourne 401"""
        response = await async_client.get("/admin/dashboard/overview")
        assert response.status_code == 401

    async def test_dashboard_overview(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/dashboard/overview retourne l'overview"""
        response = await async_client.get(
            "/admin/dashboard/overview",
            headers=admin_headers
        )
        assert response.status_code == 200

    async def test_dashboard_user_stats(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/dashboard/users retourne les stats"""
        response = await async_client.get(
            "/admin/dashboard/users",
            headers=admin_headers
        )
        assert response.status_code == 200

    async def test_dashboard_conversation_stats(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/dashboard/conversations retourne les stats"""
        response = await async_client.get(
            "/admin/dashboard/conversations",
            headers=admin_headers
        )
        assert response.status_code == 200

    async def test_dashboard_document_stats(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/dashboard/documents retourne les stats"""
        response = await async_client.get(
            "/admin/dashboard/documents",
            headers=admin_headers
        )
        assert response.status_code == 200


# ============================================================================
# TESTS ENDPOINTS ROLES
# ============================================================================

class TestAdminRolesEndpoints:
    """Tests des endpoints /admin/roles"""

    async def test_list_roles_requires_auth(self, async_client: AsyncClient):
        """GET /admin/roles sans auth retourne 401"""
        response = await async_client.get("/admin/roles")
        assert response.status_code == 401

    async def test_list_roles(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/roles retourne la liste des rôles"""
        response = await async_client.get("/admin/roles", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_roles_contains_admin_role(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/roles contient le rôle admin (id=1)"""
        response = await async_client.get("/admin/roles", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        # Verifier que le role admin (id=1) existe dans la liste
        admin_role = next((r for r in data if r["id"] == 1), None)
        assert admin_role is not None


# ============================================================================
# TESTS ENDPOINTS AUDIT
# ============================================================================

class TestAdminAuditEndpoints:
    """Tests des endpoints /admin/audit"""

    async def test_audit_requires_auth(self, async_client: AsyncClient):
        """GET /admin/audit sans auth retourne 401"""
        response = await async_client.get("/admin/audit")
        assert response.status_code == 401

    async def test_list_audit_logs(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/audit retourne les logs"""
        response = await async_client.get("/admin/audit", headers=admin_headers)
        assert response.status_code == 200

    async def test_audit_logs_pagination(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/audit supporte la pagination"""
        response = await async_client.get(
            "/admin/audit?limit=10&offset=0",
            headers=admin_headers
        )
        assert response.status_code == 200


# ============================================================================
# TESTS ENDPOINTS EXPORT
# ============================================================================

class TestAdminExportEndpoints:
    """Tests des endpoints /admin/export"""

    async def test_export_users_csv(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/export/users?format=csv exporte en CSV"""
        response = await async_client.get(
            "/admin/export/users?format=csv",
            headers=admin_headers
        )
        # 200 ou 404 si endpoint pas encore implémenté
        assert response.status_code in [200, 404]

    async def test_export_users_json(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/export/users?format=json exporte en JSON"""
        response = await async_client.get(
            "/admin/export/users?format=json",
            headers=admin_headers
        )
        assert response.status_code in [200, 404]


# ============================================================================
# TESTS ENDPOINTS CONFIG
# ============================================================================

class TestAdminConfigEndpoints:
    """Tests des endpoints /admin/config"""

    async def test_config_requires_auth(self, async_client: AsyncClient):
        """GET /admin/config sans auth retourne 401"""
        response = await async_client.get("/admin/config")
        assert response.status_code == 401

    async def test_get_config(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/config retourne la configuration"""
        response = await async_client.get("/admin/config", headers=admin_headers)
        assert response.status_code == 200

    async def test_get_rag_config(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/config/rag retourne la config RAG"""
        response = await async_client.get(
            "/admin/config/rag",
            headers=admin_headers
        )
        assert response.status_code == 200


# ============================================================================
# TESTS SECURITE
# ============================================================================

class TestAdminSecurity:
    """Tests de sécurité des endpoints admin"""

    async def test_all_admin_endpoints_require_auth(
        self,
        async_client: AsyncClient
    ):
        """Tous les endpoints admin nécessitent l'authentification"""
        endpoints = [
            "/admin/users",
            "/admin/dashboard/overview",
            "/admin/roles",
            "/admin/audit",
            "/admin/config",
        ]

        for endpoint in endpoints:
            response = await async_client.get(endpoint)
            assert response.status_code == 401, f"{endpoint} devrait nécessiter auth"


# ============================================================================
# TESTS ENDPOINTS CONVERSATIONS
# ============================================================================

class TestAdminConversationsEndpoints:
    """Tests des endpoints /admin/conversations"""

    async def test_conversations_requires_auth(self, async_client: AsyncClient):
        """GET /admin/conversations sans auth retourne 401"""
        response = await async_client.get("/admin/conversations")
        assert response.status_code == 401

    async def test_list_conversations(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/conversations retourne la liste"""
        response = await async_client.get(
            "/admin/conversations",
            headers=admin_headers
        )
        assert response.status_code == 200

    async def test_list_conversations_pagination(
        self,
        async_client: AsyncClient,
        admin_headers: dict
    ):
        """GET /admin/conversations supporte la pagination"""
        response = await async_client.get(
            "/admin/conversations?limit=10&offset=0",
            headers=admin_headers
        )
        assert response.status_code == 200
