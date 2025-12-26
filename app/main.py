"""
MY-IA API - Point d'entrée principal

Application FastAPI avec architecture modulaire basée sur les features.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.deps import get_chroma_client, get_ingestion_pipeline

# Import des routers
from app.features.health.router import router as health_router
from app.features.chat.router import router as chat_router, assistant_router, test_router
from app.features.ingestion.router import router as ingestion_router
from app.features.admin.router import router as admin_router

# Import de l'authentification et des utilisateurs
from app.features.auth.router import router as auth_router
from app.features.user.router import router as user_router

# Import des modules utilisateur
from app.features.conversations.router import router as conversations_router
from app.features.documents.router import router as documents_router
from app.features.preferences.router import router as preferences_router

# Import du module geo (public)
from app.features.geo.router import router as geo_router

# Import des modules admin documents
from app.features.admin.documents.router import router as admin_documents_router
from app.features.admin.documents.router import quota_router as admin_quota_router

# Configuration du logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestion du cycle de vie de l'application

    Initialise ChromaDB et le pipeline d'ingestion au démarrage.
    """
    # Startup
    logger.info("Starting MY-IA API...")

    # Initialiser ChromaDB
    chroma_client = get_chroma_client()
    if chroma_client:
        logger.info("ChromaDB initialized successfully")

    # Initialiser le pipeline d'ingestion
    pipeline = get_ingestion_pipeline()
    if pipeline:
        logger.info("Ingestion pipeline initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down MY-IA API...")


# Création de l'application FastAPI
app = FastAPI(
    title=settings.app_name,
    description="API d'IA conversationnelle avec RAG et automatisation",
    version=settings.app_version,
    lifespan=lifespan
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# ROUTERS
# ============================================================================

# Health & Metrics
app.include_router(health_router)

# Authentication & Users
app.include_router(auth_router)
app.include_router(user_router)

# User Features (conversations, documents, preferences)
app.include_router(conversations_router)
app.include_router(documents_router)
app.include_router(preferences_router)

# Chat
app.include_router(chat_router)
app.include_router(assistant_router)
app.include_router(test_router)

# Ingestion
app.include_router(ingestion_router)

# Geo (public)
app.include_router(geo_router, prefix="/geo", tags=["Geo"])

# Admin
app.include_router(admin_router)
app.include_router(admin_documents_router)
app.include_router(admin_quota_router)

logger.info(f"{settings.app_name} initialized successfully")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.app_host, port=settings.app_port)
