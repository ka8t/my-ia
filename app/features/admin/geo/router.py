"""Endpoints admin pour les donnees geographiques."""
from typing import List

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_admin_user
from app.models import User
from app.features.admin.geo.service import GeoAdminService
from app.features.admin.geo.schemas import (
    ImportResult,
    ImportCountriesRequest,
    ImportCitiesRequest,
    CountryCreate,
    CountryUpdate,
    CountryAdminRead,
    GeoStats
)

router = APIRouter()


# =============================================================================
# STATISTICS
# =============================================================================

@router.get(
    "/stats",
    response_model=GeoStats,
    summary="Statistiques geo"
)
async def get_geo_stats(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
) -> GeoStats:
    """Retourne les statistiques des donnees geographiques."""
    return await GeoAdminService.get_stats(db)


# =============================================================================
# IMPORT ENDPOINTS
# =============================================================================

@router.post(
    "/import/countries",
    response_model=ImportResult,
    summary="Importer les pays"
)
async def import_countries(
    request: ImportCountriesRequest = None,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
) -> ImportResult:
    """
    Importe les pays depuis la liste statique.

    - **reset**: Si true, supprime tous les pays existants avant import
    """
    reset = request.reset if request else False
    return await GeoAdminService.import_countries(db, reset)


@router.post(
    "/import/cities",
    response_model=ImportResult,
    summary="Importer les villes"
)
async def import_cities(
    request: ImportCitiesRequest = None,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
) -> ImportResult:
    """
    Importe les villes depuis une API externe.

    - **country_code**: Code ISO du pays (defaut: FR, seul supporte)
    - **reset**: Si true, supprime les villes existantes du pays avant import

    Pour la France, utilise api.gouv.fr (~35000 villes).
    """
    country_code = request.country_code if request else "FR"
    reset = request.reset if request else False
    return await GeoAdminService.import_cities(db, country_code, reset)


# =============================================================================
# COUNTRIES CRUD
# =============================================================================

@router.get(
    "/countries",
    response_model=List[CountryAdminRead],
    summary="Liste tous les pays (admin)"
)
async def list_all_countries(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
) -> List[CountryAdminRead]:
    """Liste tous les pays, y compris les inactifs."""
    countries = await GeoAdminService.get_all_countries(db)
    return [CountryAdminRead.model_validate(c) for c in countries]


@router.get(
    "/countries/{code}",
    response_model=CountryAdminRead,
    summary="Detail d'un pays (admin)"
)
async def get_country(
    code: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
) -> CountryAdminRead:
    """Recupere les details d'un pays."""
    country = await GeoAdminService.get_country(db, code)
    return CountryAdminRead.model_validate(country)


@router.post(
    "/countries",
    response_model=CountryAdminRead,
    status_code=201,
    summary="Creer un pays"
)
async def create_country(
    data: CountryCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
) -> CountryAdminRead:
    """Cree un nouveau pays."""
    country = await GeoAdminService.create_country(db, data)
    return CountryAdminRead.model_validate(country)


@router.patch(
    "/countries/{code}",
    response_model=CountryAdminRead,
    summary="Modifier un pays"
)
async def update_country(
    code: str,
    data: CountryUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
) -> CountryAdminRead:
    """Met a jour un pays existant."""
    country = await GeoAdminService.update_country(db, code, data)
    return CountryAdminRead.model_validate(country)


@router.post(
    "/countries/{code}/toggle-active",
    response_model=CountryAdminRead,
    summary="Activer/desactiver un pays"
)
async def toggle_country_active(
    code: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
) -> CountryAdminRead:
    """Active ou desactive un pays."""
    country = await GeoAdminService.toggle_country_active(db, code)
    return CountryAdminRead.model_validate(country)


@router.delete(
    "/countries/{code}",
    status_code=204,
    summary="Supprimer un pays"
)
async def delete_country(
    code: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
) -> None:
    """
    Supprime un pays.

    **Attention**: Supprime egalement toutes les villes associees (cascade).
    """
    await GeoAdminService.delete_country(db, code)
