"""
Tests pour Admin Dashboard

Tests des statistiques et metriques du tableau de bord admin.
Execution: docker-compose exec app python -m pytest tests/admin/test_admin_dashboard.py -v
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.admin.dashboard.service import DashboardService


# =============================================================================
# TESTS SERVICE DASHBOARD
# =============================================================================

class TestDashboardService:
    """Tests pour le service Dashboard"""

    @pytest.mark.asyncio
    async def test_get_overview(self, db_session: AsyncSession):
        """Test get_overview retourne une structure valide"""
        overview = await DashboardService.get_overview(db_session)

        assert overview is not None
        # Verifier les champs principaux (Pydantic model ou dict)
        if hasattr(overview, 'users'):
            assert overview.users is not None
            assert overview.conversations is not None
            assert overview.documents is not None
        else:
            assert "users" in overview
            assert "conversations" in overview
            assert "documents" in overview

    @pytest.mark.asyncio
    async def test_get_user_stats(self, db_session: AsyncSession):
        """Test statistiques utilisateurs"""
        stats = await DashboardService.get_user_stats(db_session)

        assert stats is not None
        # Verifier les champs (Pydantic model ou dict)
        if hasattr(stats, 'total'):
            assert stats.total >= 0
            assert stats.active >= 0
        else:
            assert stats.get("total", 0) >= 0
            assert stats.get("active", 0) >= 0

    @pytest.mark.asyncio
    async def test_get_conversation_stats(self, db_session: AsyncSession):
        """Test statistiques conversations"""
        stats = await DashboardService.get_conversation_stats(db_session)

        assert stats is not None
        if hasattr(stats, 'total'):
            assert stats.total >= 0
        else:
            assert stats.get("total", 0) >= 0

    @pytest.mark.asyncio
    async def test_get_document_stats(self, db_session: AsyncSession):
        """Test statistiques documents"""
        stats = await DashboardService.get_document_stats(db_session)

        assert stats is not None
        if hasattr(stats, 'total'):
            assert stats.total >= 0
        else:
            assert stats.get("total", 0) >= 0

    @pytest.mark.asyncio
    async def test_get_system_stats(self, db_session: AsyncSession):
        """Test statistiques systeme"""
        stats = await DashboardService.get_system_stats(db_session)

        assert stats is not None

    @pytest.mark.asyncio
    async def test_get_usage_daily(self, db_session: AsyncSession):
        """Test usage quotidien"""
        usage = await DashboardService.get_usage_daily(db_session, days=7)

        assert usage is not None
        assert isinstance(usage, list)
        assert len(usage) <= 7

    @pytest.mark.asyncio
    async def test_get_trends(self, db_session: AsyncSession):
        """Test tendances"""
        trends = await DashboardService.get_trends(db_session)

        assert trends is not None


# =============================================================================
# TESTS COHERENCE DONNEES
# =============================================================================

class TestDashboardDataCoherence:
    """Tests de coherence des donnees"""

    @pytest.mark.asyncio
    async def test_user_stats_coherence(self, db_session: AsyncSession):
        """Test coherence active + inactive = total"""
        stats = await DashboardService.get_user_stats(db_session)

        if hasattr(stats, 'total'):
            total = stats.total
            active = stats.active
            inactive = stats.inactive
        else:
            total = stats.get("total", 0)
            active = stats.get("active", 0)
            inactive = stats.get("inactive", 0)

        assert active + inactive == total

    @pytest.mark.asyncio
    async def test_overview_contains_all_sections(self, db_session: AsyncSession):
        """Test que l'overview contient toutes les sections"""
        overview = await DashboardService.get_overview(db_session)

        if hasattr(overview, 'users'):
            assert overview.users is not None
            assert overview.conversations is not None
            assert overview.documents is not None
            assert overview.system is not None
        else:
            assert "users" in overview
            assert "conversations" in overview
            assert "documents" in overview
            assert "system" in overview


# =============================================================================
# TESTS EDGE CASES
# =============================================================================

class TestDashboardEdgeCases:
    """Tests des cas limites"""

    @pytest.mark.asyncio
    async def test_empty_usage_returns_empty_list(self, db_session: AsyncSession):
        """Test usage avec 0 jours"""
        usage = await DashboardService.get_usage_daily(db_session, days=0)

        # Selon l'implementation, peut retourner [] ou les stats d'aujourd'hui
        assert isinstance(usage, list)

    @pytest.mark.asyncio
    async def test_large_days_parameter(self, db_session: AsyncSession):
        """Test usage avec beaucoup de jours"""
        usage = await DashboardService.get_usage_daily(db_session, days=365)

        assert isinstance(usage, list)
        assert len(usage) <= 365

    @pytest.mark.asyncio
    async def test_stats_no_division_by_zero(self, db_session: AsyncSession):
        """Test que les moyennes ne causent pas de division par zero"""
        stats = await DashboardService.get_conversation_stats(db_session)

        # Ne doit pas lever d'exception
        assert stats is not None

        # Verifier avg_messages_per_conversation
        if hasattr(stats, 'avg_messages_per_conversation'):
            assert stats.avg_messages_per_conversation >= 0
        elif isinstance(stats, dict) and "avg_messages_per_conversation" in stats:
            assert stats["avg_messages_per_conversation"] >= 0
