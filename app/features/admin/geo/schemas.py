"""Schemas Pydantic pour l'import geo admin."""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class ImportStatus(BaseModel):
    """Statut d'une importation."""
    entity_type: str = Field(..., description="Type d'entite (countries, cities)")
    country_code: Optional[str] = Field(None, description="Code pays (pour villes)")
    status: str = Field(..., description="Status: pending, running, completed, failed")
    total_count: int = Field(0, description="Nombre total d'elements")
    imported_count: int = Field(0, description="Nombre d'elements importes")
    error_count: int = Field(0, description="Nombre d'erreurs")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ImportCountriesRequest(BaseModel):
    """Requete d'import des pays."""
    reset: bool = Field(False, description="Supprimer les pays existants avant import")


class ImportCitiesRequest(BaseModel):
    """Requete d'import des villes."""
    country_code: str = Field("FR", min_length=2, max_length=2, description="Code pays")
    reset: bool = Field(False, description="Supprimer les villes existantes avant import")


class ImportResult(BaseModel):
    """Resultat d'une importation."""
    success: bool
    entity_type: str
    country_code: Optional[str] = None
    imported_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: List[str] = []
    duration_seconds: float = 0.0
    message: str = ""


class CountryCreate(BaseModel):
    """Schema creation Country (admin)."""
    code: str = Field(..., min_length=2, max_length=2, description="Code ISO")
    name: str = Field(..., min_length=1, max_length=100)
    flag: str = Field(..., min_length=1, max_length=10)
    phone_prefix: Optional[str] = Field(None, max_length=5)
    is_active: bool = True
    display_order: int = 999


class CountryUpdate(BaseModel):
    """Schema mise a jour Country (admin)."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    flag: Optional[str] = Field(None, min_length=1, max_length=10)
    phone_prefix: Optional[str] = Field(None, max_length=5)
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class CountryAdminRead(BaseModel):
    """Schema lecture Country (admin, avec tous les champs)."""
    code: str
    name: str
    flag: str
    phone_prefix: Optional[str] = None
    is_active: bool
    display_order: int
    created_at: datetime

    class Config:
        from_attributes = True


class GeoStats(BaseModel):
    """Statistiques geo."""
    countries_total: int = 0
    countries_active: int = 0
    cities_total: int = 0
    cities_by_country: dict = {}
