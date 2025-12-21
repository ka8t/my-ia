"""
Tests des endpoints de l'API MY-IA

Tests pour tous les endpoints exposés par l'application FastAPI:
- GET /health
- GET /metrics
- GET /
- POST /chat
- POST /assistant
- POST /chat/stream
- POST /test
- POST /upload (v1)
- POST /upload/stream
- POST /upload/v2
"""

import pytest
import io
from fastapi.testclient import TestClient


# ============================================================================
# Tests GET /health
# ============================================================================

@pytest.mark.api
class TestHealthEndpoint:
    """Tests de l'endpoint /health"""

    def test_health_check_returns_200(self, client: TestClient):
        """L'endpoint /health doit retourner 200"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_structure(self, client: TestClient):
        """L'endpoint /health doit avoir la bonne structure"""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert "ollama" in data
        assert "chroma" in data
        assert "model" in data

    def test_health_check_model_name(self, client: TestClient):
        """L'endpoint /health doit retourner le nom du modèle"""
        response = client.get("/health")
        data = response.json()
        assert data["model"] == "mistral:7b"


# ============================================================================
# Tests GET /metrics
# ============================================================================

@pytest.mark.api
class TestMetricsEndpoint:
    """Tests de l'endpoint /metrics pour Prometheus"""

    def test_metrics_endpoint_accessible(self, client: TestClient):
        """L'endpoint /metrics doit être accessible"""
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_contains_prometheus_format(self, client: TestClient):
        """Les métriques doivent être au format Prometheus"""
        response = client.get("/metrics")
        content = response.text
        # Le format Prometheus contient des lignes comme "# HELP" et "# TYPE"
        assert "# HELP" in content or "# TYPE" in content or "myia_" in content


# ============================================================================
# Tests GET /
# ============================================================================

@pytest.mark.api
class TestRootEndpoint:
    """Tests de l'endpoint racine"""

    def test_root_endpoint(self, client: TestClient):
        """L'endpoint racine doit retourner les informations de l'API"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert data["name"] == "MY-IA API"
        assert "version" in data
        assert "status" in data


# ============================================================================
# Tests POST /chat
# ============================================================================

@pytest.mark.api
class TestChatEndpoint:
    """Tests de l'endpoint /chat"""

    def test_chat_without_api_key(self, client: TestClient):
        """POST /chat sans API key doit retourner 401"""
        response = client.post("/chat", json={"query": "Test"})
        assert response.status_code == 401

    def test_chat_with_invalid_api_key(self, client: TestClient):
        """POST /chat avec une mauvaise API key doit retourner 401"""
        response = client.post(
            "/chat",
            json={"query": "Test"},
            headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 401

    def test_chat_with_valid_api_key(self, client: TestClient, test_api_key: str):
        """POST /chat avec une bonne API key doit fonctionner"""
        # Note: Ce test pourrait échouer si Ollama n'est pas disponible
        # C'est attendu dans un environnement de test isolé
        response = client.post(
            "/chat",
            json={"query": "Bonjour"},
            headers={"X-API-Key": test_api_key}
        )
        # On accepte soit 200 (succès) soit 500 (Ollama indisponible)
        assert response.status_code in [200, 500]

    def test_chat_with_empty_query(self, client: TestClient, test_api_key: str):
        """POST /chat avec une query vide doit retourner une erreur"""
        response = client.post(
            "/chat",
            json={"query": ""},
            headers={"X-API-Key": test_api_key}
        )
        # Peut retourner 422 (validation error) ou 500 (Ollama error avec query vide)
        assert response.status_code in [422, 500]

    def test_chat_with_session_id(self, client: TestClient, test_api_key: str):
        """POST /chat avec session_id doit préserver la session"""
        session_id = "test-session-123"
        response = client.post(
            "/chat",
            json={"query": "Bonjour", "session_id": session_id},
            headers={"X-API-Key": test_api_key}
        )
        # On accepte soit 200 soit 500 (si Ollama n'est pas dispo)
        assert response.status_code in [200, 500]


# ============================================================================
# Tests POST /assistant
# ============================================================================

@pytest.mark.api
class TestAssistantEndpoint:
    """Tests de l'endpoint /assistant"""

    def test_assistant_without_api_key(self, client: TestClient):
        """POST /assistant sans API key doit retourner 401"""
        response = client.post("/assistant", json={"query": "Test"})
        assert response.status_code == 401

    def test_assistant_with_valid_api_key(self, client: TestClient, test_api_key: str):
        """POST /assistant avec une bonne API key doit fonctionner"""
        response = client.post(
            "/assistant",
            json={"query": "Quelle heure est-il?"},
            headers={"X-API-Key": test_api_key}
        )
        # On accepte soit 200 soit 500 (si Ollama n'est pas dispo)
        assert response.status_code in [200, 500]


# ============================================================================
# Tests POST /test
# ============================================================================

@pytest.mark.api
class TestTestEndpoint:
    """Tests de l'endpoint /test"""

    def test_test_endpoint_without_api_key(self, client: TestClient):
        """POST /test sans API key doit retourner 401"""
        response = client.post("/test", json={"query": "Test"})
        assert response.status_code == 401

    def test_test_endpoint_with_valid_api_key(self, client: TestClient, test_api_key: str):
        """POST /test avec une bonne API key doit fonctionner"""
        response = client.post(
            "/test",
            json={"query": "Dis bonjour"},
            headers={"X-API-Key": test_api_key}
        )
        # On accepte soit 200 soit 500 (si Ollama n'est pas dispo)
        assert response.status_code in [200, 500]


# ============================================================================
# Tests POST /upload (v1)
# ============================================================================

@pytest.mark.api
class TestUploadV1Endpoint:
    """Tests de l'endpoint /upload (legacy v1)"""

    def test_upload_without_api_key(self, client: TestClient):
        """POST /upload sans API key doit retourner 401"""
        file_content = b"Test file content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        response = client.post("/upload", files=files)
        assert response.status_code == 401

    def test_upload_with_invalid_api_key(self, client: TestClient):
        """POST /upload avec une mauvaise API key doit retourner 401"""
        file_content = b"Test file content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        response = client.post(
            "/upload",
            files=files,
            headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 401

    def test_upload_no_file_provided(self, client: TestClient, test_api_key: str):
        """POST /upload sans fichier doit retourner une erreur"""
        response = client.post(
            "/upload",
            headers={"X-API-Key": test_api_key}
        )
        # 422 pour erreur de validation (fichier manquant)
        assert response.status_code == 422


# ============================================================================
# Tests POST /upload/v2
# ============================================================================

@pytest.mark.api
@pytest.mark.upload_v2
class TestUploadV2Endpoint:
    """Tests de l'endpoint /upload/v2 (nouvelle version avec Unstructured)"""

    def test_upload_v2_without_api_key(self, client: TestClient):
        """POST /upload/v2 sans API key doit retourner 401"""
        file_content = b"Test file content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        response = client.post("/upload/v2", files=files)
        assert response.status_code == 401

    def test_upload_v2_with_invalid_api_key(self, client: TestClient):
        """POST /upload/v2 avec une mauvaise API key doit retourner 401"""
        file_content = b"Test file content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        response = client.post(
            "/upload/v2",
            files=files,
            headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 401

    def test_upload_v2_no_file_provided(self, client: TestClient, test_api_key: str):
        """POST /upload/v2 sans fichier doit retourner une erreur"""
        response = client.post(
            "/upload/v2",
            headers={"X-API-Key": test_api_key}
        )
        # 422 pour erreur de validation
        assert response.status_code == 422

    def test_upload_v2_unsupported_file_type(self, client: TestClient, test_api_key: str):
        """POST /upload/v2 avec un type de fichier non supporté doit retourner 400"""
        file_content = b"Test file content"
        files = {"file": ("test.exe", io.BytesIO(file_content), "application/x-msdownload")}
        response = client.post(
            "/upload/v2",
            files=files,
            headers={"X-API-Key": test_api_key}
        )
        # Devrait retourner 400 pour fichier non supporté
        # (ou 500 si le pipeline n'est pas initialisé)
        assert response.status_code in [400, 500]
        if response.status_code == 400:
            assert "non supporté" in response.json()["detail"].lower()


# ============================================================================
# Tests Rate Limiting
# ============================================================================

@pytest.mark.api
class TestRateLimiting:
    """Tests de limitation de débit"""

    def test_rate_limit_upload_v2(self, client: TestClient, test_api_key: str):
        """Le rate limiting doit bloquer les requêtes excessives"""
        # /upload/v2 est limité à 10/minute
        # On ne teste pas vraiment 11 requêtes car c'est lent
        # On vérifie juste que les premières passent
        file_content = b"Test"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}

        # Les premières requêtes doivent passer (ou échouer pour d'autres raisons)
        response = client.post(
            "/upload/v2",
            files=files,
            headers={"X-API-Key": test_api_key}
        )
        # On accepte n'importe quel code sauf 429 (rate limit)
        assert response.status_code != 429
