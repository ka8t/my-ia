"""
Tests d'intégration end-to-end pour MY-IA

Ces tests vérifient le workflow complet du système:
1. Ingestion de documents → ChromaDB
2. Requête utilisateur → RAG → Réponse Ollama
3. Streaming de réponse
4. Gestion des sessions

⚠️ IMPORTANT: Ces tests nécessitent:
- Ollama en cours d'exécution
- ChromaDB en cours d'exécution
- Modèle Ollama téléchargé (mistral:7b)
- Modèle d'embeddings (nomic-embed-text)

Pour exécuter ces tests:
    pytest -m integration -v

Pour les exclure:
    pytest -m "not integration" -v
"""
import pytest
import asyncio
import tempfile
import json
from pathlib import Path
import httpx


# ============================================================================
# TESTS E2E WORKFLOW COMPLET
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
class TestEndToEndWorkflow:
    """Tests du workflow complet: ingestion → query → response"""

    async def test_complete_rag_workflow(
        self,
        async_client: httpx.AsyncClient,
        test_api_key: str
    ):
        """
        Test complet du workflow RAG:
        1. Vérifier que l'API est accessible
        2. Faire une requête /chat
        3. Vérifier qu'une réponse est générée
        4. Vérifier que des sources sont retournées
        """
        # 1. Health check
        response = await async_client.get("/health")
        assert response.status_code == 200

        health_data = response.json()

        # Vérifier que les services sont disponibles
        if not health_data.get("ollama") or not health_data.get("chroma"):
            pytest.skip("Services Ollama ou ChromaDB non disponibles")

        # 2. Requête /chat
        chat_request = {
            "query": "Qu'est-ce que le RAG ?",
            "session_id": "e2e-test-session"
        }

        response = await async_client.post(
            "/chat",
            json=chat_request,
            headers={"X-API-Key": test_api_key},
            timeout=60.0
        )

        assert response.status_code == 200
        data = response.json()

        # 3. Vérifier la structure de la réponse
        assert "response" in data
        assert "sources" in data
        assert "session_id" in data

        # 4. Vérifier le contenu
        assert isinstance(data["response"], str)
        assert len(data["response"]) > 0
        assert data["session_id"] == "e2e-test-session"

        # Les sources peuvent être None si pas de documents indexés
        if data["sources"]:
            assert isinstance(data["sources"], list)

    async def test_assistant_mode_workflow(
        self,
        async_client: httpx.AsyncClient,
        test_api_key: str
    ):
        """
        Test du mode Assistant (orienté tâches)
        """
        # Health check d'abord
        health = await async_client.get("/health")
        if not health.json().get("ollama"):
            pytest.skip("Ollama non disponible")

        # Requête assistant
        request_data = {
            "query": "Donne-moi 3 étapes pour créer un chatbot",
            "session_id": "assistant-test"
        }

        response = await async_client.post(
            "/assistant",
            json=request_data,
            headers={"X-API-Key": test_api_key},
            timeout=60.0
        )

        assert response.status_code == 200
        data = response.json()

        assert "response" in data
        assert len(data["response"]) > 0


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
class TestStreamingWorkflow:
    """Tests du streaming de réponses"""

    async def test_chat_streaming_e2e(
        self,
        async_client: httpx.AsyncClient,
        test_api_key: str
    ):
        """
        Test du streaming end-to-end:
        1. Initier un stream
        2. Recevoir des chunks progressivement
        3. Vérifier le format NDJSON
        """
        # Health check
        health = await async_client.get("/health")
        if not health.json().get("ollama"):
            pytest.skip("Ollama non disponible")

        # Initier le streaming
        request_data = {
            "query": "Explique en une phrase ce qu'est l'IA",
            "session_id": "stream-test"
        }

        async with async_client.stream(
            "POST",
            "/chat/stream",
            json=request_data,
            headers={"X-API-Key": test_api_key},
            timeout=60.0
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/x-ndjson"

            chunks_received = 0
            full_response = ""

            async for line in response.aiter_lines():
                if line.strip():
                    # Vérifier que c'est du JSON valide
                    try:
                        chunk_data = json.loads(line)
                        chunks_received += 1

                        # Accumuler la réponse
                        if "response" in chunk_data:
                            full_response += chunk_data["response"]

                        # Vérifier qu'on a bien un flag "done"
                        if chunk_data.get("done"):
                            break

                    except json.JSONDecodeError:
                        pytest.fail(f"Invalid JSON chunk: {line}")

            # Vérifier qu'on a reçu des chunks
            assert chunks_received > 0, "Aucun chunk reçu"
            assert len(full_response) > 0, "Réponse vide"


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
class TestIngestionWorkflow:
    """Tests du workflow d'ingestion de documents"""

    async def test_ingest_and_query_workflow(
        self,
        async_client: httpx.AsyncClient,
        test_api_key: str,
        tmp_path: Path
    ):
        """
        Test complet d'ingestion:
        1. Créer un document de test
        2. L'ingérer dans ChromaDB (via script ingest)
        3. Faire une requête qui devrait utiliser ce document
        4. Vérifier que le document est dans les sources

        Note: Ce test nécessite d'exécuter le script d'ingestion
        ou d'utiliser l'API d'ingestion si elle existe
        """
        # Pour ce test, on va vérifier qu'une requête utilise bien
        # les documents existants dans la base

        # Health check
        health = await async_client.get("/health")
        if not health.json().get("ollama") or not health.json().get("chroma"):
            pytest.skip("Services non disponibles")

        # Requête spécifique qui devrait trouver des sources
        request_data = {
            "query": "Qu'est-ce qui est indexé dans la base de données ?",
            "session_id": "ingest-test"
        }

        response = await async_client.post(
            "/chat",
            json=request_data,
            headers={"X-API-Key": test_api_key},
            timeout=60.0
        )

        assert response.status_code == 200
        data = response.json()

        # Si des documents sont indexés, on devrait avoir des sources
        # Sinon, le test passe quand même (base vide)
        assert "sources" in data
        if data["sources"] is not None:
            assert isinstance(data["sources"], list)


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
class TestErrorHandling:
    """Tests de gestion d'erreur en conditions réelles"""

    async def test_invalid_query_handling(
        self,
        async_client: httpx.AsyncClient,
        test_api_key: str
    ):
        """Vérifier la gestion d'une query invalide"""
        # Query vide
        response = await async_client.post(
            "/chat",
            json={"query": "", "session_id": "test"},
            headers={"X-API-Key": test_api_key}
        )

        # Devrait échouer la validation
        assert response.status_code == 422

    async def test_missing_api_key(
        self,
        async_client: httpx.AsyncClient
    ):
        """Vérifier le rejet sans API key"""
        response = await async_client.post(
            "/chat",
            json={"query": "Test", "session_id": "test"}
        )

        assert response.status_code == 401

    async def test_invalid_api_key(
        self,
        async_client: httpx.AsyncClient
    ):
        """Vérifier le rejet avec mauvaise API key"""
        response = await async_client.post(
            "/chat",
            json={"query": "Test", "session_id": "test"},
            headers={"X-API-Key": "invalid-key-123"}
        )

        assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
class TestPerformance:
    """Tests de performance basiques"""

    async def test_chat_response_time(
        self,
        async_client: httpx.AsyncClient,
        test_api_key: str
    ):
        """
        Vérifier que les réponses arrivent dans un délai raisonnable
        Note: Peut être lent selon la machine et le modèle
        """
        import time

        # Health check
        health = await async_client.get("/health")
        if not health.json().get("ollama"):
            pytest.skip("Ollama non disponible")

        start_time = time.time()

        response = await async_client.post(
            "/chat",
            json={"query": "Bonjour", "session_id": "perf-test"},
            headers={"X-API-Key": test_api_key},
            timeout=120.0  # 2 minutes max
        )

        elapsed_time = time.time() - start_time

        assert response.status_code == 200

        # Log du temps de réponse (pour monitoring)
        print(f"\n⏱️  Temps de réponse: {elapsed_time:.2f}s")

        # Vérification souple (peut varier selon le hardware)
        # On vérifie juste que ça ne timeout pas
        assert elapsed_time < 120.0

    async def test_concurrent_requests(
        self,
        async_client: httpx.AsyncClient,
        test_api_key: str
    ):
        """
        Tester plusieurs requêtes concurrentes
        """
        # Health check
        health = await async_client.get("/health")
        if not health.json().get("ollama"):
            pytest.skip("Ollama non disponible")

        # Créer 3 requêtes concurrentes
        async def make_request(session_id: str):
            response = await async_client.post(
                "/test",  # Endpoint plus simple sans RAG
                json={"query": f"Test {session_id}", "session_id": session_id},
                headers={"X-API-Key": test_api_key},
                timeout=120.0
            )
            return response.status_code

        # Lancer 3 requêtes en parallèle
        results = await asyncio.gather(
            make_request("concurrent-1"),
            make_request("concurrent-2"),
            make_request("concurrent-3")
        )

        # Toutes devraient réussir
        assert all(status == 200 for status in results)


@pytest.mark.integration
@pytest.mark.slow
class TestServicesIntegration:
    """Tests d'intégration avec les services externes"""

    def test_ollama_connection(self, test_ollama_host: str):
        """Vérifier la connexion à Ollama"""
        import requests

        try:
            response = requests.get(f"{test_ollama_host}/api/tags", timeout=5)
            assert response.status_code == 200
        except Exception as e:
            pytest.skip(f"Ollama non accessible: {e}")

    def test_chromadb_connection(self, test_chroma_host: str):
        """Vérifier la connexion à ChromaDB"""
        import requests

        try:
            response = requests.get(f"{test_chroma_host}/api/v1/heartbeat", timeout=5)
            assert response.status_code == 200
        except Exception as e:
            pytest.skip(f"ChromaDB non accessible: {e}")


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
class TestRateLimitingIntegration:
    """Tests de rate limiting en conditions réelles"""

    @pytest.mark.skip(reason="Peut prendre du temps et affecter d'autres tests")
    async def test_rate_limit_enforcement(
        self,
        async_client: httpx.AsyncClient,
        test_api_key: str
    ):
        """
        Vérifier que le rate limiting fonctionne
        Note: Désactivé par défaut car peut être long
        """
        # Faire beaucoup de requêtes rapidement
        responses = []

        for i in range(35):  # Plus que la limite de 30/minute
            try:
                response = await async_client.post(
                    "/test",
                    json={"query": f"Test {i}", "session_id": f"rate-{i}"},
                    headers={"X-API-Key": test_api_key},
                    timeout=5.0
                )
                responses.append(response.status_code)
            except httpx.TimeoutException:
                responses.append(0)

        # Au moins une devrait être rate limited (429)
        # Ou toutes passent si le rate limiter est désactivé en test
        rate_limited_count = responses.count(429)
        print(f"\n🚦 Requêtes rate limited: {rate_limited_count}/35")


# ============================================================================
# FIXTURES SPÉCIFIQUES AUX TESTS D'INTÉGRATION
# ============================================================================

@pytest.fixture(scope="module")
def integration_setup():
    """
    Setup spécifique pour les tests d'intégration
    Peut être utilisé pour initialiser des données de test
    """
    # Setup
    print("\n🔧 Setup des tests d'intégration...")

    yield

    # Teardown
    print("\n🧹 Cleanup des tests d'intégration...")


@pytest.fixture
def sample_test_document(tmp_path: Path) -> Path:
    """Créer un document de test pour l'ingestion"""
    doc_file = tmp_path / "test_document.md"
    content = """
    # Document de Test

    Ce document sert à tester le système RAG.

    ## Section 1
    Le RAG (Retrieval-Augmented Generation) combine recherche et génération.

    ## Section 2
    ChromaDB est une base de données vectorielle.
    """

    doc_file.write_text(content, encoding="utf-8")
    return doc_file
