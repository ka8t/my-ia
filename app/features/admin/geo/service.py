"""Service admin pour les donnees geographiques."""
import logging
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import Country, City
from app.features.geo.repository import CountryRepository, CityRepository
from app.features.admin.geo.schemas import (
    ImportResult,
    CountryCreate,
    CountryUpdate,
    GeoStats
)
from app.features.admin.geo.importer import GeoImporter

logger = logging.getLogger(__name__)


class GeoAdminService:
    """Service admin pour les donnees geographiques."""

    # =========================================================================
    # STATISTICS
    # =========================================================================

    @staticmethod
    async def get_stats(db: AsyncSession) -> GeoStats:
        """Recupere les statistiques geo."""
        # Compter les pays
        countries_total = await CountryRepository.count(db)

        # Compter les pays actifs
        result = await db.execute(
            select(func.count()).select_from(Country).where(Country.is_active == True)
        )
        countries_active = result.scalar() or 0

        # Compter les villes par pays
        result = await db.execute(
            select(City.country_code, func.count(City.id))
            .group_by(City.country_code)
        )
        cities_by_country = dict(result.all())
        cities_total = sum(cities_by_country.values())

        return GeoStats(
            countries_total=countries_total,
            countries_active=countries_active,
            cities_total=cities_total,
            cities_by_country=cities_by_country
        )

    # =========================================================================
    # IMPORT
    # =========================================================================

    @staticmethod
    async def import_countries(
        db: AsyncSession,
        reset: bool = False
    ) -> ImportResult:
        """Importe les pays."""
        return await GeoImporter.import_countries(db, reset)

    @staticmethod
    async def import_cities(
        db: AsyncSession,
        country_code: str,
        reset: bool = False
    ) -> ImportResult:
        """Importe les villes d'un pays."""
        country_code = country_code.upper()

        # Seul FR supporte pour l'instant
        if country_code != "FR":
            return ImportResult(
                success=False,
                entity_type="cities",
                country_code=country_code,
                errors=[f"Import non supporte pour le pays {country_code}. Seul FR est disponible."],
                message=f"Pays {country_code} non supporte"
            )

        return await GeoImporter.import_french_cities(db, reset)

    # =========================================================================
    # CRUD COUNTRIES (admin)
    # =========================================================================

    @staticmethod
    async def get_all_countries(db: AsyncSession):
        """Recupere tous les pays (y compris inactifs)."""
        return await CountryRepository.get_all(db)

    @staticmethod
    async def get_country(db: AsyncSession, code: str) -> Country:
        """Recupere un pays par son code."""
        country = await CountryRepository.get_by_code(db, code)
        if not country:
            raise HTTPException(status_code=404, detail=f"Pays '{code}' non trouve")
        return country

    @staticmethod
    async def create_country(
        db: AsyncSession,
        data: CountryCreate
    ) -> Country:
        """Cree un nouveau pays."""
        existing = await CountryRepository.get_by_code(db, data.code)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Le pays '{data.code}' existe deja"
            )

        country = Country(
            code=data.code.upper(),
            name=data.name,
            flag=data.flag,
            phone_prefix=data.phone_prefix,
            is_active=data.is_active,
            display_order=data.display_order
        )
        return await CountryRepository.create(db, country)

    @staticmethod
    async def update_country(
        db: AsyncSession,
        code: str,
        data: CountryUpdate
    ) -> Country:
        """Met a jour un pays."""
        country = await CountryRepository.get_by_code(db, code)
        if not country:
            raise HTTPException(status_code=404, detail=f"Pays '{code}' non trouve")

        # Mise a jour des champs
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(country, field, value)

        return await CountryRepository.update(db, country)

    @staticmethod
    async def toggle_country_active(
        db: AsyncSession,
        code: str
    ) -> Country:
        """Active/desactive un pays."""
        country = await CountryRepository.get_by_code(db, code)
        if not country:
            raise HTTPException(status_code=404, detail=f"Pays '{code}' non trouve")

        country.is_active = not country.is_active
        return await CountryRepository.update(db, country)

    @staticmethod
    async def delete_country(db: AsyncSession, code: str) -> None:
        """Supprime un pays (et ses villes en cascade)."""
        country = await CountryRepository.get_by_code(db, code)
        if not country:
            raise HTTPException(status_code=404, detail=f"Pays '{code}' non trouve")

        # Avertir si des villes existent
        cities_count = await CityRepository.count(db, code)
        if cities_count > 0:
            logger.warning(
                f"Suppression du pays {code} avec {cities_count} villes associees"
            )

        await CountryRepository.delete(db, country)
