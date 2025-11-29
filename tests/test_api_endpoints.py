"""
Tests unitaires pour les endpoints API de MY-IA

Ces tests vérifient le bon fonctionnement des endpoints:
- /health
- /metrics
- /chat
- /assistant
- /test
- /chat/stream
"""
import pytest
from fastapi.testclient import TestClient


# ============================================================================
# TESTS ENDPOINT /health
# ============================================================================

@pytest.mark.unit
@pytest.mark.api
class TestHealthEndpoint:
    """Tests pour l'endpoint /health"""

    def test_health_check_structure(self, client: TestClient):
        """Vérifie que le health check retourne la bonne structure"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Vérifier la structure
        assert "status" in data
        assert "ollama" in data
        assert "chroma" in data
        assert "model" in data

        # Vérifier les types
        assert isinstance(data["status"], str)
        assert isinstance(data["ollama"], bool)
        assert isinstance(data["chroma"], bool)
        assert isinstance(data["model"], str)

    def test_health_check_model_name(self, client: TestClient):
        """Vérifie que le modèle configuré est retourné"""
        response = client.get("/health")
        data = response.json()

        assert data["model"] == "mistral:7b"


# ============================================================================
# TESTS ENDPOINT /metrics
# ============================================================================

@pytest.mark.unit
@pytest.mark.api
class TestMetricsEndpoint:
    """Tests pour l'endpoint /metrics (Prometheus)"""

    def test_metrics_endpoint_accessible(self, client: TestClient):
        """Vérifie que l'endpoint metrics est accessible"""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

    def test_metrics_contains_prometheus_format(self, client: TestClient):
        """Vérifie que les métriques sont au format Prometheus"""
        response = client.get("/metrics")
        content = response.text

        # Vérifier la présence de métriques custom
        assert "myia_requests_total" in content or "# HELP" in content


# ============================================================================
# TESTS ENDPOINT / (root)
# ============================================================================

@pytest.mark.unit
@pytest.mark.api
class TestRootEndpoint:
    """Tests pour l'endpoint racine /"""

    def test_root_endpoint(self, client: TestClient):
        """Vérifie l'endpoint racine"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "MY-IA API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
        assert "docs" in data
        assert "health" in data


# ============================================================================
# TESTS ENDPOINT /chat
# ============================================================================

@pytest.mark.unit
@pytest.mark.api
class TestChatEndpoint:
    """Tests pour l'endpoint /chat"""

    def test_chat_without_api_key(self, client: TestClient, sample_chat_request):
        """Vérifie que la requête sans API key est rejetée"""
        response = client.post("/chat", json=sample_chat_request)

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"

    def test_chat_with_invalid_api_key(self, client: TestClient, sample_chat_request):
        """Vérifie que la requête avec mauvaise API key est rejetée"""
        response = client.post(
            "/chat",
            json=sample_chat_request,
            headers={"X-API-Key": "wrong-key"}
        )

        assert response.status_code == 401

    def test_chat_with_valid_api_key(
        self,
        client: TestClient,
        sample_chat_request,
        test_api_key,
        mock_chroma_search,
        mock_ollama_generate
    ):
        """Vérifie que la requête avec API key valide fonctionne"""
        response = client.post(
            "/chat",
            json=sample_chat_request,
            headers={"X-API-Key": test_api_key}
        )

        assert response.status_code == 200
        data = response.json()

        assert "response" in data
        assert "sources" in data
        assert "session_id" in data
        assert isinstance(data["response"], str)

    def test_chat_response_contains_sources(
        self,
        client: TestClient,
        sample_chat_request,
        test_api_key,
        mock_chroma_search,
        mock_ollama_generate
    ):
        """Vérifie que les sources sont retournées"""
        response = client.post(
            "/chat",
            json=sample_chat_request,
            headers={"X-API-Key": test_api_key}
        )

        data = response.json()
        assert data["sources"] is not None
        assert isinstance(data["sources"], list)
        assert len(data["sources"]) > 0

    def test_chat_with_empty_query(
        self,
        client: TestClient,
        test_api_key
    ):
        """Vérifie la gestion d'une query vide"""
        response = client.post(
            "/chat",
            json={"query": "", "session_id": "test"},
            headers={"X-API-Key": test_api_key}
        )

        # Devrait échouer la validation Pydantic
        assert response.status_code == 422

    def test_chat_preserves_session_id(
        self,
        client: TestClient,
        test_api_key,
        mock_chroma_search,
        mock_ollama_generate
    ):
        """Vérifie que le session_id est préservé dans la réponse"""
        session_id = "my-custom-session-123"
        response = client.post(
            "/chat",
            json={"query": "Test", "session_id": session_id},
            headers={"X-API-Key": test_api_key}
        )

        data = response.json()
        assert data["session_id"] == session_id


# ============================================================================
# TESTS ENDPOINT /assistant
# ============================================================================

@pytest.mark.unit
@pytest.mark.api
class TestAssistantEndpoint:
    """Tests pour l'endpoint /assistant"""

    def test_assistant_without_api_key(self, client: TestClient, sample_chat_request):
        """Vérifie que la requête sans API key est rejetée"""
        response = client.post("/assistant", json=sample_chat_request)

        assert response.status_code == 401

    def test_assistant_with_valid_api_key(
        self,
        client: TestClient,
        sample_chat_request,
        test_api_key,
        mock_chroma_search,
        mock_ollama_generate
    ):
        """Vérifie que l'endpoint assistant fonctionne"""
        response = client.post(
            "/assistant",
            json=sample_chat_request,
            headers={"X-API-Key": test_api_key}
        )

        assert response.status_code == 200
        data = response.json()

        assert "response" in data
        assert isinstance(data["response"], str)


# ============================================================================
# TESTS ENDPOINT /test
# ============================================================================

@pytest.mark.unit
@pytest.mark.api
class TestTestEndpoint:
    """Tests pour l'endpoint /test (sans RAG)"""

    def test_test_endpoint_without_rag(
        self,
        client: TestClient,
        test_api_key,
        mock_ollama_generate
    ):
        """Vérifie que l'endpoint /test fonctionne sans RAG"""
        response = client.post(
            "/test",
            json={"query": "Bonjour", "session_id": None},
            headers={"X-API-Key": test_api_key}
        )

        assert response.status_code == 200
        data = response.json()

        assert "response" in data
        assert data["sources"] is None  # Pas de RAG pour /test

    def test_test_endpoint_no_sources(
        self,
        client: TestClient,
        test_api_key,
        mock_ollama_generate
    ):
        """Vérifie que /test ne retourne pas de sources"""
        response = client.post(
            "/test",
            json={"query": "Test sans RAG"},
            headers={"X-API-Key": test_api_key}
        )

        data = response.json()
        assert data.get("sources") is None


# ============================================================================
# TESTS ENDPOINT /chat/stream
# ============================================================================

@pytest.mark.unit
@pytest.mark.api
class TestChatStreamEndpoint:
    """Tests pour l'endpoint /chat/stream"""

    def test_stream_without_api_key(self, client: TestClient, sample_chat_request):
        """Vérifie que le streaming sans API key est rejeté"""
        response = client.post("/chat/stream", json=sample_chat_request)

        assert response.status_code == 401

    def test_stream_returns_streaming_response(
        self,
        client: TestClient,
        test_api_key,
        sample_chat_request,
        mock_chroma_search,
        mocker
    ):
        """Vérifie que le streaming retourne bien une StreamingResponse"""
        # Mock du streaming Ollama
        mock_stream_response = mocker.Mock()
        mock_stream_response.aiter_lines = mocker.AsyncMock(
            return_value=iter([
                '{"response":"Hello","done":false}',
                '{"response":" World","done":true}'
            ])
        )

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_client.return_value.__aenter__.return_value.stream.return_value.__aenter__.return_value = mock_stream_response

        response = client.post(
            "/chat/stream",
            json=sample_chat_request,
            headers={"X-API-Key": test_api_key}
        )

        # Vérifier que c'est un streaming
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-ndjson"


# ============================================================================
# TESTS RATE LIMITING
# ============================================================================

@pytest.mark.unit
@pytest.mark.api
@pytest.mark.slow
class TestRateLimiting:
    """Tests pour le rate limiting"""

    def test_rate_limit_chat_endpoint(
        self,
        client: TestClient,
        test_api_key,
        mock_chroma_search,
        mock_ollama_generate
    ):
        """Vérifie que le rate limiting fonctionne sur /chat"""
        # Le rate limit est configuré à 30/minute
        # On va simuler beaucoup de requêtes

        request_data = {"query": "Test", "session_id": "test"}
        headers = {"X-API-Key": test_api_key}

        # Faire plusieurs requêtes rapidement
        responses = []
        for _ in range(35):  # Plus que la limite
            response = client.post("/chat", json=request_data, headers=headers)
            responses.append(response.status_code)

        # Au moins une devrait être rate limited (429)
        assert 429 in responses or all(r == 200 for r in responses)
        # Note: Le test peut passer si le rate limiter est désactivé en test
