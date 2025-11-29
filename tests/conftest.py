"""
Configuration pytest et fixtures globales pour tous les tests
"""
import os
import sys
from typing import AsyncGenerator, Generator
from pathlib import Path

import pytest
import httpx
from fastapi.testclient import TestClient

# Ajouter le répertoire parent au PYTHONPATH pour importer app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app


# ============================================================================
# FIXTURES GLOBALES
# ============================================================================

@pytest.fixture(scope="session")
def test_api_key() -> str:
    """Clé API de test"""
    return "test-api-key-12345"


@pytest.fixture(scope="session")
def test_ollama_host() -> str:
    """URL du serveur Ollama de test"""
    return os.getenv("OLLAMA_HOST", "http://localhost:11434")


@pytest.fixture(scope="session")
def test_chroma_host() -> str:
    """URL du serveur ChromaDB de test"""
    return os.getenv("CHROMA_HOST", "http://localhost:8000")


# ============================================================================
# FIXTURES CLIENT API
# ============================================================================

@pytest.fixture(scope="function")
def client(test_api_key: str) -> Generator[TestClient, None, None]:
    """
    Client de test FastAPI synchrone.
    Utilise TestClient qui gère automatiquement le lifecycle de l'app.
    """
    # Override de la clé API pour les tests
    os.environ["API_KEY"] = test_api_key

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
async def async_client(test_api_key: str) -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Client HTTP asynchrone pour tester les endpoints avec streaming.
    """
    os.environ["API_KEY"] = test_api_key

    async with httpx.AsyncClient(
        app=app,
        base_url="http://testserver",
        timeout=30.0
    ) as ac:
        yield ac


# ============================================================================
# FIXTURES DONNÉES DE TEST
# ============================================================================

@pytest.fixture
def sample_chat_request() -> dict:
    """Requête de chat valide pour les tests"""
    return {
        "query": "Qu'est-ce que le RAG ?",
        "session_id": "test-session-123"
    }


@pytest.fixture
def sample_document_text() -> str:
    """Texte de document exemple pour tests d'ingestion"""
    return """
    # Guide sur le RAG (Retrieval-Augmented Generation)

    Le RAG est une technique qui combine la recherche d'information et la génération de texte.

    ## Fonctionnement
    1. Indexation de documents dans une base vectorielle
    2. Recherche de documents pertinents via embeddings
    3. Génération de réponse avec contexte augmenté

    ## Avantages
    - Réduit les hallucinations
    - Permet d'utiliser des données privées
    - Reste à jour sans retraining
    """


@pytest.fixture
def sample_embeddings() -> list[float]:
    """Vecteur d'embeddings exemple (simulé, dimension réduite)"""
    return [0.1] * 768  # Dimension typique pour nomic-embed-text


@pytest.fixture
def mock_chroma_results() -> dict:
    """Résultats mockés de ChromaDB"""
    return {
        "documents": [[
            "Le RAG combine recherche et génération.",
            "ChromaDB est une base vectorielle."
        ]],
        "metadatas": [[
            {"source": "docs/rag.md", "chunk_id": 0},
            {"source": "docs/chroma.md", "chunk_id": 1}
        ]],
        "distances": [[0.15, 0.23]]
    }


@pytest.fixture
def mock_ollama_response() -> dict:
    """Réponse mockée d'Ollama (non-streaming)"""
    return {
        "model": "mistral:7b",
        "created_at": "2024-11-27T10:00:00Z",
        "response": "Le RAG (Retrieval-Augmented Generation) est une technique...",
        "done": True,
        "context": [],
        "total_duration": 5000000000,
        "load_duration": 1000000000,
        "prompt_eval_count": 100,
        "eval_count": 50
    }


@pytest.fixture
def mock_ollama_stream_chunks() -> list[str]:
    """Chunks de streaming mockés d'Ollama"""
    return [
        '{"model":"mistral:7b","created_at":"2024-11-27T10:00:00Z","response":"Le ","done":false}\n',
        '{"model":"mistral:7b","created_at":"2024-11-27T10:00:01Z","response":"RAG ","done":false}\n',
        '{"model":"mistral:7b","created_at":"2024-11-27T10:00:02Z","response":"est","done":false}\n',
        '{"model":"mistral:7b","created_at":"2024-11-27T10:00:03Z","response":"...","done":true}\n'
    ]


# ============================================================================
# FIXTURES ENVIRONNEMENT
# ============================================================================

@pytest.fixture(autouse=True)
def reset_env_vars():
    """
    Reset des variables d'environnement avant chaque test.
    autouse=True => s'exécute automatiquement pour chaque test.
    """
    original_env = os.environ.copy()

    # Configuration de test par défaut
    os.environ["LOG_LEVEL"] = "ERROR"  # Réduire le bruit dans les tests
    os.environ["MODEL_NAME"] = "mistral:7b"
    os.environ["EMBED_MODEL"] = "nomic-embed-text"
    os.environ["TOP_K"] = "4"

    yield

    # Restaurer l'environnement original
    os.environ.clear()
    os.environ.update(original_env)


# ============================================================================
# FIXTURES MOCK SERVICES
# ============================================================================

@pytest.fixture
def mock_ollama_embeddings(mocker, sample_embeddings):
    """Mock de la fonction get_embeddings"""
    mock = mocker.patch("app.main.get_embeddings")
    mock.return_value = sample_embeddings
    return mock


@pytest.fixture
def mock_chroma_search(mocker, mock_chroma_results):
    """Mock de la fonction search_context"""
    mock = mocker.patch("app.main.search_context")
    mock.return_value = [
        {
            "content": doc,
            "metadata": meta,
            "distance": dist
        }
        for doc, meta, dist in zip(
            mock_chroma_results["documents"][0],
            mock_chroma_results["metadatas"][0],
            mock_chroma_results["distances"][0]
        )
    ]
    return mock


@pytest.fixture
def mock_ollama_generate(mocker, mock_ollama_response):
    """Mock de la fonction generate_response"""
    mock = mocker.patch("app.main.generate_response")
    mock.return_value = mock_ollama_response["response"]
    return mock


# ============================================================================
# HOOKS PYTEST
# ============================================================================

def pytest_configure(config):
    """Configuration globale de pytest"""
    # Ajouter des markers personnalisés
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modifier la collection de tests.
    Par exemple, marquer automatiquement certains tests.
    """
    for item in items:
        # Marquer les tests d'intégration comme slow
        if "integration" in item.keywords:
            item.add_marker(pytest.mark.slow)
