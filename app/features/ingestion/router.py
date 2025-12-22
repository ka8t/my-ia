"""
Router Ingestion

Endpoints pour l'ingestion de documents.
"""
import logging

from fastapi import APIRouter, Request, UploadFile, File, Depends

from app.core.deps import verify_api_key
from app.features.ingestion.schemas import UploadResponse
from app.features.ingestion.service import IngestionService
from app.common.metrics import REQUEST_COUNT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["ingestion"])


@router.post("", response_model=UploadResponse)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    parsing_strategy: str = "auto",
    skip_duplicates: bool = True,
    _: bool = Depends(verify_api_key)
):
    """
    Upload et ingestion de documents avec parsing avancé

    Features:
    - Multi-format support (PDF, DOCX, XLSX, PPTX, images avec OCR, etc.)
    - Semantic chunking avec LangChain
    - Déduplication automatique
    - Extraction de métadonnées riches
    - Extraction de tables

    Args:
        file: Fichier à uploader
        parsing_strategy: 'auto', 'fast', 'hi_res', ou 'ocr_only'
        skip_duplicates: Ignorer si le hash du document existe déjà
        _: Vérification API key

    Returns:
        Résultat de l'ingestion
    """
    try:
        result = await IngestionService.ingest_document(
            file=file,
            parsing_strategy=parsing_strategy,
            skip_duplicates=skip_duplicates
        )

        REQUEST_COUNT.labels(endpoint="/upload", method="POST", status="200").inc()

        return UploadResponse(**result)

    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/upload", method="POST", status="500").inc()
        logger.error(f"Error in upload endpoint: {e}")
        raise
