"""
Tests pour le service Geo.

Execution: docker-compose exec app python -m pytest tests/geo/ -v
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.geo.service import GeoService
from app.features.geo.repository import CountryRepository, CityRepository


class TestGeoServiceCountries:
    """Tests du service pays."""

    @pytest.mark.asyncio
    async def test_get_countries(self, db_session: AsyncSession):
        """Test recuperation des pays actifs."""
        countries = await GeoService.get_countries(db_session)

        # Peut etre vide si pas encore importe
        assert isinstance(countries, list)

    @pytest.mark.asyncio
    async def test_get_country_not_found(self, db_session: AsyncSession):
        """Test 404 si pays inexistant."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await GeoService.get_country(db_session, "ZZ")

        assert exc_info.value.status_code == 404


class TestGeoServiceCities:
    """Tests du service villes."""

    @pytest.mark.asyncio
    async def test_search_cities_empty_result(self, db_session: AsyncSession):
        """Test recherche sans resultat."""
        cities = await GeoService.search_cities(
            db_session, "ZZZZZZZZZ", "FR", 20
        )

        assert isinstance(cities, list)
        assert len(cities) == 0

    @pytest.mark.asyncio
    async def test_search_cities_short_query(self, db_session: AsyncSession):
        """Test recherche avec query trop courte."""
        cities = await GeoService.search_cities(
            db_session, "P", "FR", 20
        )

        # Retourne liste vide car < 2 caracteres
        assert cities == []

    @pytest.mark.asyncio
    async def test_get_city_not_found(self, db_session: AsyncSession):
        """Test 404 si ville inexistante."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await GeoService.get_city(db_session, 999999999)

        assert exc_info.value.status_code == 404


class TestGeoRepository:
    """Tests des repositories geo."""

    @pytest.mark.asyncio
    async def test_country_count(self, db_session: AsyncSession):
        """Test comptage des pays."""
        count = await CountryRepository.count(db_session)

        assert isinstance(count, int)
        assert count >= 0

    @pytest.mark.asyncio
    async def test_city_count(self, db_session: AsyncSession):
        """Test comptage des villes."""
        count = await CityRepository.count(db_session)

        assert isinstance(count, int)
        assert count >= 0

    @pytest.mark.asyncio
    async def test_city_count_by_country(self, db_session: AsyncSession):
        """Test comptage des villes par pays."""
        count = await CityRepository.count(db_session, "FR")

        assert isinstance(count, int)
        assert count >= 0
