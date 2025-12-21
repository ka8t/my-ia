"""
Configuration pytest et fixtures globales pour tous les tests
"""
import os
import sys
from typing import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ajouter les répertoires au PYTHONPATH pour importer app
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "app"))

# IMPORTANT: Configurer l'API key AVANT d'importer l'app
# Sinon l'app lit la valeur par défaut au moment de l'import
os.environ["API_KEY"] = "test-api-key-12345"
os.environ["LOG_LEVEL"] = "ERROR"

# Mock des modules manquants (chromadb, unstructured, etc.)
from unittest.mock import MagicMock

# Mock chromadb (non compatible Python 3.13 à cause de onnxruntime)
try:
    import chromadb
except ImportError:
    sys.modules['chromadb'] = MagicMock()
    sys.modules['chromadb.config'] = MagicMock()
    sys.modules['chromadb.utils'] = MagicMock()
    sys.modules['chromadb.api'] = MagicMock()

# Mock unstructured (lourd à installer, ne fonctionne pas partout)
try:
    import unstructured
except ImportError:
    sys.modules['unstructured'] = MagicMock()
    sys.modules['unstructured.partition'] = MagicMock()
    sys.modules['unstructured.partition.auto'] = MagicMock()
    sys.modules['unstructured.cleaners'] = MagicMock()
    sys.modules['unstructured.cleaners.core'] = MagicMock()
    sys.modules['unstructured.chunking'] = MagicMock()
    sys.modules['unstructured.chunking.title'] = MagicMock()
    sys.modules['unstructured.staging'] = MagicMock()
    sys.modules['unstructured.staging.base'] = MagicMock()

# Mock ingest (legacy v1 - peut ne pas être présent localement)
try:
    import ingest
except ImportError:
    # Créer un mock complet avec les fonctions attendues
    ingest_mock = MagicMock()
    ingest_mock.chunk = MagicMock(return_value=[])
    ingest_mock.embed = MagicMock()
    ingest_mock.embed_with_progress = MagicMock()
    ingest_mock.extract_pdf_text = MagicMock(return_value="")
    ingest_mock.extract_html_text = MagicMock(return_value="")
    sys.modules['ingest'] = ingest_mock

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
    Configure automatiquement l'API key pour les tests.
    """
    # Override de la clé API pour les tests
    os.environ["API_KEY"] = test_api_key

    with TestClient(app) as test_client:
        yield test_client


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
    config.addinivalue_line(
        "markers", "ingest_v2: mark test as testing ingestion v2.0"
    )
    config.addinivalue_line(
        "markers", "api: mark test as testing API endpoints"
    )
    config.addinivalue_line(
        "markers", "upload_v2: mark test as testing upload v2 endpoint"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modifier la collection de tests.
    Marquer automatiquement certains tests.
    """
    for item in items:
        # Marquer les tests d'intégration comme slow
        if "integration" in item.keywords:
            item.add_marker(pytest.mark.slow)
