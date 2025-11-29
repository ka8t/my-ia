"""
Tests unitaires pour les fonctions utilitaires de MY-IA

Ces tests vérifient:
- verify_api_key()
- get_embeddings()
- search_context()
- generate_response()
"""
import pytest
from unittest.mock import AsyncMock, Mock
import httpx
from fastapi import HTTPException


# ============================================================================
# TESTS verify_api_key()
# ============================================================================

@pytest.mark.unit
class TestVerifyApiKey:
    """Tests pour la fonction verify_api_key"""

    def test_verify_api_key_valid(self, test_api_key):
        """Vérifie qu'une clé API valide passe"""
        from app.main import verify_api_key

        result = verify_api_key(x_api_key=test_api_key)
        assert result is True

    def test_verify_api_key_invalid(self):
        """Vérifie qu'une clé API invalide lève une exception"""
        from app.main import verify_api_key

        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(x_api_key="wrong-key")

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in str(exc_info.value.detail)

    def test_verify_api_key_none(self):
        """Vérifie qu'une clé API None lève une exception"""
        from app.main import verify_api_key

        with pytest.raises(HTTPException) as exc_info:
            verify_api_key(x_api_key=None)

        assert exc_info.value.status_code == 401


# ============================================================================
# TESTS get_embeddings()
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestGetEmbeddings:
    """Tests pour la fonction get_embeddings"""

    async def test_get_embeddings_success(self, mocker, sample_embeddings):
        """Vérifie que get_embeddings fonctionne avec Ollama"""
        from app.main import get_embeddings

        # Mock de httpx.AsyncClient
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={"embedding": sample_embeddings})

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await get_embeddings("Test text")

        assert result == sample_embeddings
        assert isinstance(result, list)
        assert len(result) == 768

    async def test_get_embeddings_http_error(self, mocker):
        """Vérifie la gestion d'erreur HTTP"""
        from app.main import get_embeddings

        # Mock qui lève une erreur HTTP
        mock_response = Mock()
        mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError(
            "Error", request=Mock(), response=Mock()
        ))

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_embeddings("Test")

        assert exc_info.value.status_code == 500
        assert "Error generating embeddings" in str(exc_info.value.detail)

    async def test_get_embeddings_request_format(self, mocker, sample_embeddings):
        """Vérifie le format de la requête envoyée à Ollama"""
        from app.main import get_embeddings, OLLAMA_HOST, EMBED_MODEL

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={"embedding": sample_embeddings})

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        text = "Test embedding"
        await get_embeddings(text)

        # Vérifier que post a été appelé avec les bons arguments
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Vérifier l'URL
        assert call_args[0][0] == f"{OLLAMA_HOST}/api/embeddings"

        # Vérifier le payload JSON
        payload = call_args[1]["json"]
        assert payload["model"] == EMBED_MODEL
        assert payload["prompt"] == text


# ============================================================================
# TESTS search_context()
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestSearchContext:
    """Tests pour la fonction search_context"""

    async def test_search_context_success(
        self,
        mocker,
        sample_embeddings,
        mock_chroma_results
    ):
        """Vérifie que search_context retourne des résultats"""
        from app.main import search_context

        # Mock get_embeddings
        mocker.patch("app.main.get_embeddings", return_value=sample_embeddings)

        # Mock ChromaDB
        mock_collection = Mock()
        mock_collection.query = Mock(return_value=mock_chroma_results)

        mock_chroma = mocker.patch("app.main.chroma_client")
        mock_chroma.get_collection = Mock(return_value=mock_collection)

        results = await search_context("Test query", top_k=2)

        assert isinstance(results, list)
        assert len(results) == 2
        assert "content" in results[0]
        assert "metadata" in results[0]
        assert "distance" in results[0]

    async def test_search_context_no_client(self, mocker):
        """Vérifie le comportement quand ChromaDB n'est pas disponible"""
        from app.main import search_context

        # Simuler chroma_client = None
        mocker.patch("app.main.chroma_client", None)

        results = await search_context("Test")

        assert results == []

    async def test_search_context_collection_not_found(self, mocker, sample_embeddings):
        """Vérifie le comportement quand la collection n'existe pas"""
        from app.main import search_context

        mocker.patch("app.main.get_embeddings", return_value=sample_embeddings)

        # Mock ChromaDB qui lève une exception
        mock_chroma = mocker.patch("app.main.chroma_client")
        mock_chroma.get_collection = Mock(side_effect=Exception("Collection not found"))

        results = await search_context("Test")

        assert results == []

    async def test_search_context_respects_top_k(
        self,
        mocker,
        sample_embeddings,
        mock_chroma_results
    ):
        """Vérifie que top_k est respecté"""
        from app.main import search_context

        mocker.patch("app.main.get_embeddings", return_value=sample_embeddings)

        mock_collection = Mock()
        mock_collection.query = Mock(return_value=mock_chroma_results)

        mock_chroma = mocker.patch("app.main.chroma_client")
        mock_chroma.get_collection = Mock(return_value=mock_collection)

        top_k = 5
        await search_context("Test", top_k=top_k)

        # Vérifier que query a été appelé avec n_results=top_k
        call_args = mock_collection.query.call_args
        assert call_args[1]["n_results"] == top_k


# ============================================================================
# TESTS generate_response()
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestGenerateResponse:
    """Tests pour la fonction generate_response"""

    async def test_generate_response_without_context(
        self,
        mocker,
        mock_ollama_response
    ):
        """Vérifie la génération de réponse sans contexte RAG"""
        from app.main import generate_response

        # Mock httpx
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value=mock_ollama_response)

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        query = "Test question"
        system_prompt = "Tu es un assistant"
        result = await generate_response(query, system_prompt, context=None, stream=False)

        assert isinstance(result, str)
        assert len(result) > 0
        assert result == mock_ollama_response["response"]

    async def test_generate_response_with_context(
        self,
        mocker,
        mock_ollama_response
    ):
        """Vérifie la génération avec contexte RAG"""
        from app.main import generate_response

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value=mock_ollama_response)

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        context = [
            {"content": "Context 1", "metadata": {"source": "doc1.md"}},
            {"content": "Context 2", "metadata": {"source": "doc2.md"}}
        ]

        result = await generate_response(
            "Test",
            "System prompt",
            context=context,
            stream=False
        )

        # Vérifier que le contexte a été inclus dans le prompt
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        prompt = payload["prompt"]

        assert "Context 1" in prompt
        assert "Context 2" in prompt
        assert "doc1.md" in prompt
        assert "doc2.md" in prompt

    async def test_generate_response_streaming_mode(self, mocker):
        """Vérifie que le mode streaming retourne une réponse httpx"""
        from app.main import generate_response

        mock_response = Mock(spec=httpx.Response)

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        result = await generate_response(
            "Test",
            "System",
            context=None,
            stream=True
        )

        # En mode stream, on retourne la response brute
        assert result == mock_response

    async def test_generate_response_http_error(self, mocker):
        """Vérifie la gestion d'erreur HTTP"""
        from app.main import generate_response

        mock_response = Mock()
        mock_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError("Error", request=Mock(), response=Mock())
        )

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(HTTPException) as exc_info:
            await generate_response("Test", "System", stream=False)

        assert exc_info.value.status_code == 500

    async def test_generate_response_uses_correct_model(
        self,
        mocker,
        mock_ollama_response
    ):
        """Vérifie que le bon modèle est utilisé"""
        from app.main import generate_response, MODEL_NAME

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value=mock_ollama_response)

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        await generate_response("Test", "System", stream=False)

        call_args = mock_post.call_args
        payload = call_args[1]["json"]

        assert payload["model"] == MODEL_NAME
        assert payload["stream"] is False
