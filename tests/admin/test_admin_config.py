"""
Tests pour Admin Config

Tests de la gestion de la configuration systeme runtime.
Execution: docker-compose exec app python -m pytest tests/admin/test_admin_config.py -v
"""
import pytest

from app.features.admin.config.service import ConfigService
from app.features.admin.config.schemas import (
    SystemConfigRead, RAGConfigRead, RAGConfigUpdate,
    TimeoutsConfigRead, TimeoutsConfigUpdate
)


# =============================================================================
# TESTS GET CONFIG
# =============================================================================

class TestConfigRead:
    """Tests lecture de configuration"""

    def test_get_system_config(self):
        """Test recuperation configuration complete"""
        config = ConfigService.get_system_config()

        assert config is not None
        assert isinstance(config, SystemConfigRead)
        assert hasattr(config, 'app_name')
        assert hasattr(config, 'environment')
        assert hasattr(config, 'rag')
        assert hasattr(config, 'timeouts')

    def test_get_rag_config(self):
        """Test recuperation config RAG"""
        rag_config = ConfigService.get_rag_config()

        assert rag_config is not None
        assert isinstance(rag_config, RAGConfigRead)
        assert isinstance(rag_config.top_k, int)
        assert rag_config.top_k > 0

    def test_get_timeouts_config(self):
        """Test recuperation config timeouts"""
        timeouts = ConfigService.get_timeouts_config()

        assert timeouts is not None
        assert isinstance(timeouts, TimeoutsConfigRead)
        assert timeouts.ollama_timeout > 0


# =============================================================================
# TESTS UPDATE CONFIG
# =============================================================================

class TestConfigUpdate:
    """Tests mise a jour de configuration"""

    def test_update_rag_config(self):
        """Test mise a jour config RAG"""
        # Sauvegarder original
        original = ConfigService.get_rag_config()
        original_top_k = original.top_k

        try:
            # Mettre a jour
            update = RAGConfigUpdate(top_k=8)
            new_config = ConfigService.update_rag_config(update)

            assert isinstance(new_config, RAGConfigRead)
            assert new_config.top_k == 8

        finally:
            # Restaurer
            restore = RAGConfigUpdate(top_k=original_top_k)
            ConfigService.update_rag_config(restore)

    def test_update_timeouts_config(self):
        """Test mise a jour config timeouts"""
        original = ConfigService.get_timeouts_config()
        original_timeout = original.ollama_timeout

        try:
            update = TimeoutsConfigUpdate(ollama_timeout=120.0)
            new_config = ConfigService.update_timeouts_config(update)

            assert isinstance(new_config, TimeoutsConfigRead)
            assert new_config.ollama_timeout == 120.0

        finally:
            restore = TimeoutsConfigUpdate(ollama_timeout=original_timeout)
            ConfigService.update_timeouts_config(restore)


# =============================================================================
# TESTS PROTECTION CONFIG SENSIBLE
# =============================================================================

class TestConfigProtection:
    """Tests protection des configs sensibles"""

    def test_database_url_not_exposed(self):
        """Test que database_url n'est pas expose dans SystemConfigRead"""
        config = ConfigService.get_system_config()

        # SystemConfigRead ne doit pas avoir de champ database_url
        assert not hasattr(config, 'database_url')
        assert not hasattr(config, 'DATABASE_URL')

    def test_secret_key_not_exposed(self):
        """Test que secret_key n'est pas expose"""
        config = ConfigService.get_system_config()

        assert not hasattr(config, 'secret_key')
        assert not hasattr(config, 'SECRET_KEY')
        assert not hasattr(config, 'jwt_secret')


# =============================================================================
# TESTS RELOAD CONFIG
# =============================================================================

class TestConfigReload:
    """Tests rechargement de configuration"""

    def test_reload_config(self):
        """Test rechargement config"""
        # Faire un changement
        update = RAGConfigUpdate(top_k=15)
        ConfigService.update_rag_config(update)

        # Verifier que l'override existe
        overrides = ConfigService.get_runtime_overrides()
        assert 'top_k' in overrides

        # Reload
        result = ConfigService.reload_config()

        # Doit retourner SystemConfigRead
        assert isinstance(result, SystemConfigRead)

        # Les overrides doivent etre vides
        overrides = ConfigService.get_runtime_overrides()
        assert overrides == {}

    def test_get_runtime_overrides(self):
        """Test recuperation des overrides"""
        # Reset d'abord
        ConfigService.reload_config()

        overrides = ConfigService.get_runtime_overrides()
        assert isinstance(overrides, dict)
        assert overrides == {}

        # Ajouter un override
        update = RAGConfigUpdate(top_k=10)
        ConfigService.update_rag_config(update)

        overrides = ConfigService.get_runtime_overrides()
        assert 'top_k' in overrides
        assert overrides['top_k'] == 10

        # Cleanup
        ConfigService.reload_config()


# =============================================================================
# TESTS EDGE CASES
# =============================================================================

class TestConfigEdgeCases:
    """Tests cas limites configuration"""

    def test_config_returns_valid_values(self):
        """Test que les valeurs sont valides"""
        rag = ConfigService.get_rag_config()

        assert rag.top_k > 0
        assert rag.top_k <= 100
        assert rag.chunk_size > 0
        assert rag.chunk_overlap >= 0

    def test_partial_update_preserves_other_values(self):
        """Test mise a jour partielle"""
        # Reset
        ConfigService.reload_config()

        original = ConfigService.get_rag_config()
        original_chunk_size = original.chunk_size

        # Mettre a jour seulement top_k
        update = RAGConfigUpdate(top_k=12)
        ConfigService.update_rag_config(update)

        current = ConfigService.get_rag_config()

        # top_k change, chunk_size inchange
        assert current.top_k == 12
        assert current.chunk_size == original_chunk_size

        # Cleanup
        ConfigService.reload_config()

    def test_config_thread_safety(self):
        """Test basique de thread safety"""
        import threading
        import time

        errors = []
        results = []

        def read_config():
            try:
                for _ in range(10):
                    config = ConfigService.get_rag_config()
                    results.append(config)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read_config) for _ in range(3)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 30
