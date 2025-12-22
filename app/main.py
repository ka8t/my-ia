import os
import logging
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
import tempfile
import uuid
from contextlib import asynccontextmanager

import httpx
import chromadb
from chromadb.config import Settings
from fastapi import FastAPI, HTTPException, Header, Request, UploadFile, File, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import du nouveau système d'ingestion v2
from ingest_v2 import AdvancedIngestionPipeline

# Imports Authentification & DB
from db import engine, Base, get_async_session
from users import auth_backend, fastapi_users, current_active_user
from schemas import (
    UserRead, UserCreate, UserUpdate,
    RoleRead, RoleCreate, RoleUpdate,
    ConversationModeRead, ConversationModeCreate, ConversationModeUpdate,
    ResourceTypeRead, ResourceTypeCreate, ResourceTypeUpdate,
    AuditActionRead, AuditActionCreate, AuditActionUpdate,
    UserPreferenceRead, UserPreferenceUpdate,
    ConversationRead, MessageRead, DocumentRead, SessionRead
)
from models import (
    User, Role, ConversationMode, ResourceType, AuditAction,
    UserPreference, Conversation, Message, Document, Session
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

# Configuration du logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration depuis les variables d'environnement
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
CHROMA_HOST = os.getenv("CHROMA_HOST", "http://localhost:8000")
CHROMA_PATH = "/chroma/chroma"  # Chemin vers les données persistantes
COLLECTION_NAME = "knowledge_base"
MODEL_NAME = os.getenv("MODEL_NAME", "mistral:7b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
TOP_K = int(os.getenv("TOP_K", "4"))
API_KEY = os.getenv("API_KEY", "change-me-in-production")

# Initialiser le client ChromaDB en mode persistant
try:
    chroma_client = chromadb.PersistentClient(
        path=CHROMA_PATH,
        settings=Settings(anonymized_telemetry=False)
    )
    logger.info(f"ChromaDB client initialized at {CHROMA_PATH}")
except Exception as e:
    logger.error(f"Failed to initialize ChromaDB client: {e}")
    chroma_client = None

# Initialiser le pipeline d'ingestion avancé v2
ingestion_pipeline = None
if chroma_client:
    try:
        ingestion_pipeline = AdvancedIngestionPipeline(chroma_client=chroma_client)
        logger.info("Advanced Ingestion Pipeline v2 initialized")
    except Exception as e:
        logger.error(f"Failed to initialize ingestion pipeline: {e}")

# Chargement des system prompts
PROMPTS_DIR = Path(__file__).parent / "prompts"

try:
    with open(PROMPTS_DIR / "chatbot_system.md", "r", encoding="utf-8") as f:
        CHATBOT_SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    logger.warning("chatbot_system.md not found, using default prompt")
    CHATBOT_SYSTEM_PROMPT = "Tu es un assistant IA serviable."

try:
    with open(PROMPTS_DIR / "assistant_system.md", "r", encoding="utf-8") as f:
        ASSISTANT_SYSTEM_PROMPT = f.read()
except FileNotFoundError:
    logger.warning("assistant_system.md not found, using default prompt")
    ASSISTANT_SYSTEM_PROMPT = "Tu es un assistant orienté tâches."

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Lifespan context manager for DB init
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables (for dev simplicity, use Alembic in prod)
    # Note: This is commented out as Alembic should be the source of truth.
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    # logger.info("Database tables checked/created")
    yield
    # Shutdown
    pass

# FastAPI app
app = FastAPI(
    title="MY-IA API",
    description="API d'IA conversationnelle avec RAG et automatisation",
    version="1.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS pour N8N et autres intégrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Authentication Routes ---
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    return {"message": f"Hello {user.email}!"}

# Métriques Prometheus
REQUEST_COUNT = Counter(
    "myia_requests_total",
    "Total number of requests",
    ["endpoint", "method", "status"]
)
REQUEST_LATENCY = Histogram(
    "myia_request_duration_seconds",
    "Request latency in seconds",
    ["endpoint"]
)

# Modèles Pydantic
class ChatRequest(BaseModel):
    query: str = Field(..., description="Question de l'utilisateur")
    session_id: Optional[str] = Field(None, description="ID de session pour le contexte")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Réponse de l'IA")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="Sources utilisées")
    session_id: Optional[str] = Field(None, description="ID de session")

class HealthResponse(BaseModel):
    status: str
    ollama: bool
    chroma: bool
    model: str

class UploadResponse(BaseModel):
    success: bool
    filename: str
    chunks_indexed: int
    message: str

# Fonctions utilitaires
def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """Vérifie la clé API"""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

async def get_embeddings(text: str) -> List[float]:
    """Génère des embeddings via Ollama"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/embeddings",
                json={"model": EMBED_MODEL, "prompt": text}
            )
            response.raise_for_status()
            return response.json()["embedding"]
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise HTTPException(status_code=500, detail="Error generating embeddings")

async def search_context(query: str, top_k: int = TOP_K) -> List[Dict[str, Any]]:
    """Recherche de contexte dans ChromaDB"""
    try:
        if chroma_client is None:
            logger.error("ChromaDB client not initialized")
            return []

        # Générer l'embedding de la query
        query_embedding = await get_embeddings(query)

        # Récupérer la collection
        try:
            collection = chroma_client.get_collection(name=COLLECTION_NAME)
        except Exception as e:
            logger.error(f"Collection '{COLLECTION_NAME}' not found: {e}")
            return []

        # Recherche dans ChromaDB
        results_data = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        results = []
        if results_data.get("documents") and results_data["documents"][0]:
            for i, doc in enumerate(results_data["documents"][0]):
                results.append({
                    "content": doc,
                    "metadata": results_data.get("metadatas", [[]])[0][i] if results_data.get("metadatas") else {},
                    "distance": results_data.get("distances", [[]])[0][i] if results_data.get("distances") else None
                })

        logger.info(f"Found {len(results)} context results for query")
        return results

    except Exception as e:
        logger.error(f"Error searching context: {e}")
        return []

async def generate_response(
    query: str,
    system_prompt: str,
    context: Optional[List[Dict[str, Any]]] = None,
    stream: bool = False
):
    """Génère une réponse via Ollama"""
    try:
        # Construire le prompt avec contexte
        full_prompt = system_prompt + "\n\n"

        if context:
            full_prompt += "**Contexte disponible :**\n\n"
            for i, ctx in enumerate(context, 1):
                source = ctx.get("metadata", {}).get("source", "Unknown")
                full_prompt += f"[Source {i}: {source}]\n{ctx['content']}\n\n"

        full_prompt += f"**Question de l'utilisateur :**\n{query}\n\n**Réponse :**"

        logger.info(f"Sending request to Ollama with model {MODEL_NAME}")

        # Appel à Ollama avec timeout très long pour modèles lents
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": MODEL_NAME,
                    "prompt": full_prompt,
                    "stream": stream
                },
                timeout=600.0
            )
            response.raise_for_status()

            if stream:
                return response
            else:
                result = response.json()
                logger.info(f"Ollama response received successfully")
                return result["response"]

    except Exception as e:
        import traceback
        logger.error(f"Error generating response: {type(e).__name__}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {type(e).__name__}: {str(e)}")

# Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check de tous les services"""
    ollama_healthy = False
    chroma_healthy = False

    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            ollama_healthy = response.status_code == 200
    except:
        pass

    # Check ChromaDB
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{CHROMA_HOST}/api/v2/heartbeat")
            chroma_healthy = response.status_code == 200
    except:
        pass

    status = "healthy" if (ollama_healthy and chroma_healthy) else "degraded"

    return HealthResponse(
        status=status,
        ollama=ollama_healthy,
        chroma=chroma_healthy,
        model=MODEL_NAME
    )

@app.get("/metrics")
async def metrics():
    """Métriques Prometheus"""
    return Response(content=generate_latest(), media_type="text/plain")

@app.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat(
    request: Request,
    chat_request: ChatRequest,
    x_api_key: Optional[str] = Header(None)
):
    """Endpoint ChatBot conversationnel avec RAG"""
    verify_api_key(x_api_key)

    with REQUEST_LATENCY.labels(endpoint="/chat").time():
        try:
            # Recherche de contexte
            context = await search_context(chat_request.query)

            # Génération de réponse
            response_text = await generate_response(
                chat_request.query,
                CHATBOT_SYSTEM_PROMPT,
                context,
                stream=False
            )

            REQUEST_COUNT.labels(endpoint="/chat", method="POST", status="200").inc()

            return ChatResponse(
                response=response_text,
                sources=[{"source": ctx.get("metadata", {}).get("source", "Unknown")} for ctx in context] if context else None,
                session_id=chat_request.session_id
            )

        except Exception as e:
            REQUEST_COUNT.labels(endpoint="/chat", method="POST", status="500").inc()
            logger.error(f"Error in chat endpoint: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/assistant", response_model=ChatResponse)
@limiter.limit("30/minute")
async def assistant(
    request: Request,
    chat_request: ChatRequest,
    x_api_key: Optional[str] = Header(None)
):
    """Endpoint Assistant orienté tâches avec RAG"""
    verify_api_key(x_api_key)

    with REQUEST_LATENCY.labels(endpoint="/assistant").time():
        try:
            # Recherche de contexte
            context = await search_context(chat_request.query)

            # Génération de réponse
            response_text = await generate_response(
                chat_request.query,
                ASSISTANT_SYSTEM_PROMPT,
                context,
                stream=False
            )

            REQUEST_COUNT.labels(endpoint="/assistant", method="POST", status="200").inc()

            return ChatResponse(
                response=response_text,
                sources=[{"source": ctx.get("metadata", {}).get("source", "Unknown")} for ctx in context] if context else None,
                session_id=chat_request.session_id
            )

        except Exception as e:
            REQUEST_COUNT.labels(endpoint="/assistant", method="POST", status="500").inc()
            logger.error(f"Error in assistant endpoint: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/stream")
@limiter.limit("20/minute")
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    x_api_key: Optional[str] = Header(None)
):
    """Endpoint ChatBot avec streaming"""
    verify_api_key(x_api_key)

    try:
        # Recherche de contexte
        context = await search_context(chat_request.query)

        # Construire le prompt avec contexte
        full_prompt = CHATBOT_SYSTEM_PROMPT + "\n\n"

        if context:
            full_prompt += "**Contexte disponible :**\n\n"
            for i, ctx in enumerate(context, 1):
                source = ctx.get("metadata", {}).get("source", "Unknown")
                full_prompt += f"[Source {i}: {source}]\n{ctx['content']}\n\n"

        full_prompt += f"**Question de l'utilisateur :**\n{chat_request.query}\n\n**Réponse :**"

        # Streaming depuis Ollama
        async def generate_stream():
            async with httpx.AsyncClient(timeout=600.0) as client:
                async with client.stream(
                    "POST",
                    f"{OLLAMA_HOST}/api/generate",
                    json={
                        "model": MODEL_NAME,
                        "prompt": full_prompt,
                        "stream": True
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line.strip():
                            # Ollama renvoie déjà du JSON par ligne, on le transmet tel quel
                            yield line + "\n"

        REQUEST_COUNT.labels(endpoint="/chat/stream", method="POST", status="200").inc()

        return StreamingResponse(generate_stream(), media_type="application/x-ndjson")

    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/chat/stream", method="POST", status="500").inc()
        logger.error(f"Error in chat/stream endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test")
@limiter.limit("30/minute")
async def test_ollama(
    request: Request,
    chat_request: ChatRequest,
    x_api_key: Optional[str] = Header(None)
):
    """Endpoint de test sans RAG - juste Ollama"""
    verify_api_key(x_api_key)

    with REQUEST_LATENCY.labels(endpoint="/test").time():
        try:
            logger.info(f"Test request: {chat_request.query}")

            # Simple prompt sans RAG
            simple_prompt = f"Tu es un assistant IA. Réponds brièvement à cette question: {chat_request.query}"

            # Génération directe sans contexte
            response_text = await generate_response(
                chat_request.query,
                "Tu es un assistant IA serviable et concis.",
                context=None,  # Pas de RAG
                stream=False
            )

            REQUEST_COUNT.labels(endpoint="/test", method="POST", status="200").inc()

            return ChatResponse(
                response=response_text,
                sources=None,
                session_id=chat_request.session_id
            )

        except Exception as e:
            REQUEST_COUNT.labels(endpoint="/test", method="POST", status="500").inc()
            logger.error(f"Error in test endpoint: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload", response_model=UploadResponse)
@limiter.limit("10/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    parsing_strategy: str = "auto",
    skip_duplicates: bool = True,
    x_api_key: Optional[str] = Header(None)
):
    """
    Advanced upload endpoint with Unstructured.io parsing and semantic chunking

    Features:
    - Multi-format support (PDF, DOCX, XLSX, PPTX, images with OCR, etc.)
    - Semantic chunking with LangChain
    - Automatic deduplication
    - Rich metadata extraction
    - Table extraction

    Args:
        file: File to upload
        parsing_strategy: 'auto', 'fast', 'hi_res', or 'ocr_only'
        skip_duplicates: Skip if document hash already exists
        x_api_key: API key for authentication
    """
    verify_api_key(x_api_key)

    if not ingestion_pipeline:
        raise HTTPException(status_code=500, detail="Ingestion pipeline not initialized")

    # Supported extensions
    allowed_extensions = {
        ".pdf", ".txt", ".md", ".html", ".htm",
        ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
        ".jsonl", ".json", ".csv",
        ".png", ".jpg", ".jpeg"
    }
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non supporté. Extensions autorisées: {', '.join(sorted(allowed_extensions))}"
        )

    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        logger.info(f"File uploaded: {file.filename} ({len(content)} bytes)")

        # Ingest with advanced pipeline
        result = await ingestion_pipeline.ingest_file(
            file_path=tmp_file_path,
            parsing_strategy=parsing_strategy,
            skip_duplicates=skip_duplicates
        )

        # Clean up temp file
        os.unlink(tmp_file_path)

        # Handle different result statuses
        if result["status"] == "skipped":
            return UploadResponse(
                success=True,
                filename=file.filename,
                chunks_indexed=0,
                message=f"Document déjà indexé (hash: {result['document_hash'][:8]}...)"
            )
        elif result["status"] == "failed":
            raise HTTPException(
                status_code=400,
                detail=f"Échec de l'ingestion: {result.get('reason', 'unknown error')}"
            )
        else:  # success
            REQUEST_COUNT.labels(endpoint="/upload", method="POST", status="200").inc()

            message = f"Fichier '{file.filename}' indexé avec succès ({result['chunks_indexed']} chunks"
            if result.get('tables_found', 0) > 0:
                message += f", {result['tables_found']} tables détectées"
            message += ")"

            return UploadResponse(
                success=True,
                filename=file.filename,
                chunks_indexed=result["chunks_indexed"],
                message=message
            )

    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/upload", method="POST", status="500").inc()
        logger.error(f"Error in upload endpoint: {e}", exc_info=True)

        # Clean up temp file if it exists
        if 'tmp_file_path' in locals():
            try:
                os.unlink(tmp_file_path)
            except:
                pass

        raise HTTPException(status_code=500, detail=str(e))

# --- Helper Functions for Admin ---
async def get_current_admin_user(user: User = Depends(current_active_user)):
    """Vérifie que l'utilisateur actuel est un administrateur"""
    if user.role_id != 1:  # 1 = role admin
        raise HTTPException(
            status_code=403,
            detail="Access forbidden: Admin role required"
        )
    return user

# --- Admin Endpoints ---

@app.get("/admin/audit")
async def get_audit_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Récupère les logs d'audit avec filtres

    Query Parameters:
    - user_id: Filtrer par utilisateur (UUID)
    - action: Filtrer par nom d'action (ex: 'login_success')
    - limit: Nombre de résultats (défaut: 50, max: 200)
    - offset: Pagination

    Requires: Admin role
    """
    from sqlalchemy import select, desc
    from models import AuditLog, AuditAction, ResourceType, User as UserModel

    try:
        # Limiter le nombre maximum de résultats
        limit = min(limit, 200)

        # Construire la requête de base avec jointures
        query = select(AuditLog).order_by(desc(AuditLog.created_at))

        # Filtrer par user_id si fourni
        if user_id:
            try:
                user_uuid = uuid.UUID(user_id)
                query = query.where(AuditLog.user_id == user_uuid)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid user_id format")

        # Filtrer par action si fourni
        if action:
            # Récupérer l'action_id depuis le nom
            action_result = await db.execute(
                select(AuditAction).where(AuditAction.name == action)
            )
            action_obj = action_result.scalar_one_or_none()
            if action_obj:
                query = query.where(AuditLog.action_id == action_obj.id)

        # Appliquer la pagination
        query = query.limit(limit).offset(offset)

        # Exécuter la requête
        result = await db.execute(query)
        audit_logs = result.scalars().all()

        # Préparer la réponse avec les détails enrichis
        logs_data = []
        for log in audit_logs:
            # Récupérer l'utilisateur
            user_data = None
            if log.user_id:
                user_result = await db.execute(
                    select(UserModel).where(UserModel.id == log.user_id)
                )
                user_obj = user_result.scalar_one_or_none()
                if user_obj:
                    user_data = {
                        "id": str(user_obj.id),
                        "email": user_obj.email,
                        "username": user_obj.username
                    }

            # Récupérer l'action
            action_result = await db.execute(
                select(AuditAction).where(AuditAction.id == log.action_id)
            )
            action_obj = action_result.scalar_one()

            # Récupérer le type de ressource
            resource_type_data = None
            if log.resource_type_id:
                resource_type_result = await db.execute(
                    select(ResourceType).where(ResourceType.id == log.resource_type_id)
                )
                resource_type_obj = resource_type_result.scalar_one_or_none()
                if resource_type_obj:
                    resource_type_data = {
                        "id": resource_type_obj.id,
                        "name": resource_type_obj.name,
                        "display_name": resource_type_obj.display_name
                    }

            logs_data.append({
                "id": str(log.id),
                "user": user_data,
                "action": {
                    "id": action_obj.id,
                    "name": action_obj.name,
                    "display_name": action_obj.display_name,
                    "severity": action_obj.severity
                },
                "resource_type": resource_type_data,
                "resource_id": str(log.resource_id) if log.resource_id else None,
                "details": log.details,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "created_at": log.created_at.isoformat()
            })

        REQUEST_COUNT.labels(endpoint="/admin/audit", method="GET", status="200").inc()

        return {
            "total": len(logs_data),
            "limit": limit,
            "offset": offset,
            "logs": logs_data
        }

    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/audit", method="GET", status="500").inc()
        logger.error(f"Error fetching audit logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/stats")
async def get_admin_stats(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Récupère les statistiques globales du système

    Requires: Admin role
    """
    from sqlalchemy import select, func
    from models import User as UserModel, Conversation, Document

    try:
        # Compter les utilisateurs
        users_count_result = await db.execute(select(func.count(UserModel.id)))
        users_count = users_count_result.scalar()

        # Compter les conversations
        conversations_count_result = await db.execute(select(func.count(Conversation.id)))
        conversations_count = conversations_count_result.scalar()

        # Compter les documents
        documents_count_result = await db.execute(select(func.count(Document.id)))
        documents_count = documents_count_result.scalar()

        REQUEST_COUNT.labels(endpoint="/admin/stats", method="GET", status="200").inc()

        return {
            "users": {
                "total": users_count
            },
            "conversations": {
                "total": conversations_count
            },
            "documents": {
                "total": documents_count
            }
        }

    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/stats", method="GET", status="500").inc()
        logger.error(f"Error fetching admin stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# ADMIN ROUTES - TABLES DE RÉFÉRENCE
# =============================================================================

# --- Gestion des Rôles ---

@app.get("/admin/roles", response_model=list[RoleRead])
async def get_roles(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Récupère tous les rôles

    Requires: Admin role
    """
    try:
        result = await db.execute(select(Role).order_by(Role.id))
        roles = result.scalars().all()

        REQUEST_COUNT.labels(endpoint="/admin/roles", method="GET", status="200").inc()
        return roles
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/roles", method="GET", status="500").inc()
        logger.error(f"Error fetching roles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/roles", response_model=RoleRead, status_code=201)
async def create_role(
    role_data: RoleCreate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Crée un nouveau rôle

    Requires: Admin role
    """
    try:
        # Vérification anti-doublon
        existing = await db.execute(select(Role).where(Role.name == role_data.name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Role with name '{role_data.name}' already exists")

        # Création du rôle
        new_role = Role(**role_data.model_dump())
        db.add(new_role)
        await db.commit()
        await db.refresh(new_role)

        # Audit log
        await audit_service.log_action(
            db=db,
            action_name='role_created',
            user_id=admin_user.id,
            resource_type_name='role',
            resource_id=None,
            details={'role_name': new_role.name, 'role_id': new_role.id},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/roles", method="POST", status="201").inc()
        return new_role
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/roles", method="POST", status="500").inc()
        logger.error(f"Error creating role: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/admin/roles/{role_id}", response_model=RoleRead)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Met à jour un rôle

    Requires: Admin role
    """
    try:
        # Récupérer le rôle
        result = await db.execute(select(Role).where(Role.id == role_id))
        role = result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # Vérification anti-doublon si le nom change
        if role_data.name and role_data.name != role.name:
            existing = await db.execute(select(Role).where(Role.name == role_data.name))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=409, detail=f"Role with name '{role_data.name}' already exists")

        # Mise à jour
        old_values = {'name': role.name, 'display_name': role.display_name}
        for key, value in role_data.model_dump(exclude_unset=True).items():
            setattr(role, key, value)

        await db.commit()
        await db.refresh(role)

        # Audit log
        await audit_service.log_action(
            db=db,
            action_name='role_updated',
            user_id=admin_user.id,
            resource_type_name='role',
            resource_id=None,
            details={'role_id': role.id, 'old_values': old_values, 'new_values': role_data.model_dump(exclude_unset=True)},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/roles", method="PATCH", status="200").inc()
        return role
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/roles", method="PATCH", status="500").inc()
        logger.error(f"Error updating role: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/roles/{role_id}", status_code=204)
async def delete_role(
    role_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Supprime un rôle

    Requires: Admin role
    """
    try:
        # Récupérer le rôle
        result = await db.execute(select(Role).where(Role.id == role_id))
        role = result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # Vérifier si le rôle est utilisé
        users_count = await db.execute(select(func.count(User.id)).where(User.role_id == role_id))
        if users_count.scalar() > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete role '{role.name}': it is assigned to {users_count.scalar()} user(s)"
            )

        # Suppression
        role_name = role.name
        await db.delete(role)
        await db.commit()

        # Audit log
        await audit_service.log_action(
            db=db,
            action_name='role_deleted',
            user_id=admin_user.id,
            resource_type_name='role',
            resource_id=None,
            details={'role_id': role_id, 'role_name': role_name},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/roles", method="DELETE", status="204").inc()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/roles", method="DELETE", status="500").inc()
        logger.error(f"Error deleting role: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Gestion des Modes de Conversation ---

@app.get("/admin/conversation-modes", response_model=list[ConversationModeRead])
async def get_conversation_modes(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Récupère tous les modes de conversation

    Requires: Admin role
    """
    try:
        result = await db.execute(select(ConversationMode).order_by(ConversationMode.id))
        modes = result.scalars().all()

        REQUEST_COUNT.labels(endpoint="/admin/conversation-modes", method="GET", status="200").inc()
        return modes
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/conversation-modes", method="GET", status="500").inc()
        logger.error(f"Error fetching conversation modes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/conversation-modes", response_model=ConversationModeRead, status_code=201)
async def create_conversation_mode(
    mode_data: ConversationModeCreate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Crée un nouveau mode de conversation

    Requires: Admin role
    """
    try:
        # Vérification anti-doublon
        existing = await db.execute(select(ConversationMode).where(ConversationMode.name == mode_data.name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Conversation mode with name '{mode_data.name}' already exists")

        # Création du mode
        new_mode = ConversationMode(**mode_data.model_dump())
        db.add(new_mode)
        await db.commit()
        await db.refresh(new_mode)

        # Audit log
        await audit_service.log_action(
            db=db,
            action_name='conversation_mode_created',
            user_id=admin_user.id,
            resource_type_name='conversation_mode',
            resource_id=None,
            details={'mode_name': new_mode.name, 'mode_id': new_mode.id},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/conversation-modes", method="POST", status="201").inc()
        return new_mode
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/conversation-modes", method="POST", status="500").inc()
        logger.error(f"Error creating conversation mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/admin/conversation-modes/{mode_id}", response_model=ConversationModeRead)
async def update_conversation_mode(
    mode_id: int,
    mode_data: ConversationModeUpdate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Met à jour un mode de conversation

    Requires: Admin role
    """
    try:
        # Récupérer le mode
        result = await db.execute(select(ConversationMode).where(ConversationMode.id == mode_id))
        mode = result.scalar_one_or_none()
        if not mode:
            raise HTTPException(status_code=404, detail="Conversation mode not found")

        # Vérification anti-doublon si le nom change
        if mode_data.name and mode_data.name != mode.name:
            existing = await db.execute(select(ConversationMode).where(ConversationMode.name == mode_data.name))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=409, detail=f"Conversation mode with name '{mode_data.name}' already exists")

        # Mise à jour
        old_values = {'name': mode.name, 'display_name': mode.display_name}
        for key, value in mode_data.model_dump(exclude_unset=True).items():
            setattr(mode, key, value)

        await db.commit()
        await db.refresh(mode)

        # Audit log
        await audit_service.log_action(
            db=db,
            action_name='conversation_mode_updated',
            user_id=admin_user.id,
            resource_type_name='conversation_mode',
            resource_id=None,
            details={'mode_id': mode.id, 'old_values': old_values, 'new_values': mode_data.model_dump(exclude_unset=True)},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/conversation-modes", method="PATCH", status="200").inc()
        return mode
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/conversation-modes", method="PATCH", status="500").inc()
        logger.error(f"Error updating conversation mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/conversation-modes/{mode_id}", status_code=204)
async def delete_conversation_mode(
    mode_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Supprime un mode de conversation

    Requires: Admin role
    """
    try:
        # Récupérer le mode
        result = await db.execute(select(ConversationMode).where(ConversationMode.id == mode_id))
        mode = result.scalar_one_or_none()
        if not mode:
            raise HTTPException(status_code=404, detail="Conversation mode not found")

        # Vérifier si le mode est utilisé
        conversations_count = await db.execute(select(func.count(Conversation.id)).where(Conversation.mode_id == mode_id))
        if conversations_count.scalar() > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete conversation mode '{mode.name}': it is used in {conversations_count.scalar()} conversation(s)"
            )

        # Suppression
        mode_name = mode.name
        await db.delete(mode)
        await db.commit()

        # Audit log
        await audit_service.log_action(
            db=db,
            action_name='conversation_mode_deleted',
            user_id=admin_user.id,
            resource_type_name='conversation_mode',
            resource_id=None,
            details={'mode_id': mode_id, 'mode_name': mode_name},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/conversation-modes", method="DELETE", status="204").inc()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/conversation-modes", method="DELETE", status="500").inc()
        logger.error(f"Error deleting conversation mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Gestion des Types de Ressources ---

@app.get("/admin/resource-types", response_model=list[ResourceTypeRead])
async def get_resource_types(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Récupère tous les types de ressources

    Requires: Admin role
    """
    try:
        result = await db.execute(select(ResourceType).order_by(ResourceType.id))
        types = result.scalars().all()

        REQUEST_COUNT.labels(endpoint="/admin/resource-types", method="GET", status="200").inc()
        return types
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/resource-types", method="GET", status="500").inc()
        logger.error(f"Error fetching resource types: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/resource-types", response_model=ResourceTypeRead, status_code=201)
async def create_resource_type(
    type_data: ResourceTypeCreate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Crée un nouveau type de ressource

    Requires: Admin role
    """
    try:
        # Vérification anti-doublon
        existing = await db.execute(select(ResourceType).where(ResourceType.name == type_data.name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Resource type with name '{type_data.name}' already exists")

        # Création du type
        new_type = ResourceType(**type_data.model_dump())
        db.add(new_type)
        await db.commit()
        await db.refresh(new_type)

        # Audit log
        await audit_service.log_action(
            db=db,
            action_name='resource_type_created',
            user_id=admin_user.id,
            resource_type_name='resource_type',
            resource_id=None,
            details={'type_name': new_type.name, 'type_id': new_type.id},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/resource-types", method="POST", status="201").inc()
        return new_type
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/resource-types", method="POST", status="500").inc()
        logger.error(f"Error creating resource type: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/admin/resource-types/{type_id}", response_model=ResourceTypeRead)
async def update_resource_type(
    type_id: int,
    type_data: ResourceTypeUpdate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Met à jour un type de ressource

    Requires: Admin role
    """
    try:
        # Récupérer le type
        result = await db.execute(select(ResourceType).where(ResourceType.id == type_id))
        resource_type = result.scalar_one_or_none()
        if not resource_type:
            raise HTTPException(status_code=404, detail="Resource type not found")

        # Vérification anti-doublon si le nom change
        if type_data.name and type_data.name != resource_type.name:
            existing = await db.execute(select(ResourceType).where(ResourceType.name == type_data.name))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=409, detail=f"Resource type with name '{type_data.name}' already exists")

        # Mise à jour
        old_values = {'name': resource_type.name, 'display_name': resource_type.display_name}
        for key, value in type_data.model_dump(exclude_unset=True).items():
            setattr(resource_type, key, value)

        await db.commit()
        await db.refresh(resource_type)

        # Audit log
        await audit_service.log_action(
            db=db,
            action_name='resource_type_updated',
            user_id=admin_user.id,
            resource_type_name='resource_type',
            resource_id=None,
            details={'type_id': resource_type.id, 'old_values': old_values, 'new_values': type_data.model_dump(exclude_unset=True)},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/resource-types", method="PATCH", status="200").inc()
        return resource_type
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/resource-types", method="PATCH", status="500").inc()
        logger.error(f"Error updating resource type: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/resource-types/{type_id}", status_code=204)
async def delete_resource_type(
    type_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Supprime un type de ressource

    Requires: Admin role
    """
    try:
        # Récupérer le type
        result = await db.execute(select(ResourceType).where(ResourceType.id == type_id))
        resource_type = result.scalar_one_or_none()
        if not resource_type:
            raise HTTPException(status_code=404, detail="Resource type not found")

        # Vérifier si le type est utilisé dans audit_logs
        from models import AuditLog
        logs_count = await db.execute(select(func.count(AuditLog.id)).where(AuditLog.resource_type_id == type_id))
        if logs_count.scalar() > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete resource type '{resource_type.name}': it is referenced in {logs_count.scalar()} audit log(s)"
            )

        # Suppression
        type_name = resource_type.name
        await db.delete(resource_type)
        await db.commit()

        # Audit log
        await audit_service.log_action(
            db=db,
            action_name='resource_type_deleted',
            user_id=admin_user.id,
            resource_type_name='resource_type',
            resource_id=None,
            details={'type_id': type_id, 'type_name': type_name},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/resource-types", method="DELETE", status="204").inc()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/resource-types", method="DELETE", status="500").inc()
        logger.error(f"Error deleting resource type: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Gestion des Actions d'Audit ---

@app.get("/admin/audit-actions", response_model=list[AuditActionRead])
async def get_audit_actions(
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Récupère toutes les actions d'audit

    Requires: Admin role
    """
    try:
        result = await db.execute(select(AuditAction).order_by(AuditAction.id))
        actions = result.scalars().all()

        REQUEST_COUNT.labels(endpoint="/admin/audit-actions", method="GET", status="200").inc()
        return actions
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/audit-actions", method="GET", status="500").inc()
        logger.error(f"Error fetching audit actions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/audit-actions", response_model=AuditActionRead, status_code=201)
async def create_audit_action(
    action_data: AuditActionCreate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Crée une nouvelle action d'audit

    Requires: Admin role
    """
    try:
        # Vérification anti-doublon
        existing = await db.execute(select(AuditAction).where(AuditAction.name == action_data.name))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Audit action with name '{action_data.name}' already exists")

        # Création de l'action
        new_action = AuditAction(**action_data.model_dump())
        db.add(new_action)
        await db.commit()
        await db.refresh(new_action)

        # Audit log
        await audit_service.log_action(
            db=db,
            action_name='audit_action_created',
            user_id=admin_user.id,
            resource_type_name='audit_action',
            resource_id=None,
            details={'action_name': new_action.name, 'action_id': new_action.id},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/audit-actions", method="POST", status="201").inc()
        return new_action
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/audit-actions", method="POST", status="500").inc()
        logger.error(f"Error creating audit action: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/admin/audit-actions/{action_id}", response_model=AuditActionRead)
async def update_audit_action(
    action_id: int,
    action_data: AuditActionUpdate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Met à jour une action d'audit

    Requires: Admin role
    """
    try:
        # Récupérer l'action
        result = await db.execute(select(AuditAction).where(AuditAction.id == action_id))
        action = result.scalar_one_or_none()
        if not action:
            raise HTTPException(status_code=404, detail="Audit action not found")

        # Vérification anti-doublon si le nom change
        if action_data.name and action_data.name != action.name:
            existing = await db.execute(select(AuditAction).where(AuditAction.name == action_data.name))
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=409, detail=f"Audit action with name '{action_data.name}' already exists")

        # Mise à jour
        old_values = {'name': action.name, 'display_name': action.display_name, 'severity': action.severity}
        for key, value in action_data.model_dump(exclude_unset=True).items():
            setattr(action, key, value)

        await db.commit()
        await db.refresh(action)

        # Audit log
        await audit_service.log_action(
            db=db,
            action_name='audit_action_updated',
            user_id=admin_user.id,
            resource_type_name='audit_action',
            resource_id=None,
            details={'action_id': action.id, 'old_values': old_values, 'new_values': action_data.model_dump(exclude_unset=True)},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/audit-actions", method="PATCH", status="200").inc()
        return action
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/audit-actions", method="PATCH", status="500").inc()
        logger.error(f"Error updating audit action: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/audit-actions/{action_id}", status_code=204)
async def delete_audit_action(
    action_id: int,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Supprime une action d'audit

    Requires: Admin role
    """
    try:
        # Récupérer l'action
        result = await db.execute(select(AuditAction).where(AuditAction.id == action_id))
        action = result.scalar_one_or_none()
        if not action:
            raise HTTPException(status_code=404, detail="Audit action not found")

        # Vérifier si l'action est utilisée dans audit_logs
        from models import AuditLog
        logs_count = await db.execute(select(func.count(AuditLog.id)).where(AuditLog.action_id == action_id))
        if logs_count.scalar() > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete audit action '{action.name}': it is referenced in {logs_count.scalar()} audit log(s)"
            )

        # Suppression
        action_name = action.name
        await db.delete(action)
        await db.commit()

        # Audit log (on ne peut pas logger la suppression d'une action avec elle-même)
        logger.info(f"Audit action deleted: {action_name} (id={action_id}) by admin {admin_user.email}")

        REQUEST_COUNT.labels(endpoint="/admin/audit-actions", method="DELETE", status="204").inc()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/audit-actions", method="DELETE", status="500").inc()
        logger.error(f"Error deleting audit action: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# ADMIN ROUTES - DONNÉES UTILISATEURS ÉTENDUES
# =============================================================================

# --- Gestion des Préférences Utilisateurs ---

@app.get("/admin/user-preferences/{user_id}", response_model=UserPreferenceRead)
async def get_user_preferences(
    user_id: uuid.UUID,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Récupère les préférences d'un utilisateur

    Requires: Admin role
    """
    try:
        # Vérifier que l'utilisateur existe
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Récupérer les préférences
        result = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
        preferences = result.scalar_one_or_none()
        if not preferences:
            raise HTTPException(status_code=404, detail="User preferences not found")

        REQUEST_COUNT.labels(endpoint="/admin/user-preferences", method="GET", status="200").inc()
        return preferences
    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/user-preferences", method="GET", status="500").inc()
        logger.error(f"Error fetching user preferences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/admin/user-preferences/{user_id}", response_model=UserPreferenceRead)
async def update_user_preferences(
    user_id: uuid.UUID,
    preferences_data: UserPreferenceUpdate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Met à jour les préférences d'un utilisateur

    Requires: Admin role
    """
    try:
        # Vérifier que l'utilisateur existe
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Récupérer les préférences
        result = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
        preferences = result.scalar_one_or_none()
        if not preferences:
            raise HTTPException(status_code=404, detail="User preferences not found")

        # Sauvegarder les anciennes valeurs
        old_preferences = {
            'top_k': preferences.top_k,
            'show_sources': preferences.show_sources,
            'theme': preferences.theme,
            'default_mode_id': preferences.default_mode_id
        }

        # Mise à jour
        for key, value in preferences_data.model_dump(exclude_unset=True).items():
            setattr(preferences, key, value)

        await db.commit()
        await db.refresh(preferences)

        # Calcul des changements
        new_preferences = preferences_data.model_dump(exclude_unset=True)

        # Audit log
        await audit_service.log_preferences_updated_by_admin(
            db=db,
            admin_user_id=admin_user.id,
            target_user_id=user_id,
            target_user_email=user.email,
            old_preferences=old_preferences,
            new_preferences=new_preferences,
            reason=None,
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/user-preferences", method="PATCH", status="200").inc()
        return preferences
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/user-preferences", method="PATCH", status="500").inc()
        logger.error(f"Error updating user preferences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Gestion des Conversations ---

@app.get("/admin/conversations", response_model=list[ConversationRead])
async def get_conversations(
    user_id: Optional[uuid.UUID] = None,
    mode_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Récupère toutes les conversations avec filtres

    Query Parameters:
    - user_id: Filtrer par utilisateur
    - mode_id: Filtrer par mode de conversation
    - limit: Nombre de résultats (max 200)
    - offset: Pagination

    Requires: Admin role
    """
    try:
        # Limiter le nombre maximum de résultats
        limit = min(limit, 200)

        # Construire la requête
        query = select(Conversation).order_by(Conversation.updated_at.desc())

        if user_id:
            query = query.where(Conversation.user_id == user_id)
        if mode_id:
            query = query.where(Conversation.mode_id == mode_id)

        query = query.limit(limit).offset(offset)

        # Exécuter
        result = await db.execute(query)
        conversations = result.scalars().all()

        REQUEST_COUNT.labels(endpoint="/admin/conversations", method="GET", status="200").inc()
        return conversations
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/conversations", method="GET", status="500").inc()
        logger.error(f"Error fetching conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/conversations/{conversation_id}", response_model=ConversationRead)
async def get_conversation(
    conversation_id: uuid.UUID,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Récupère une conversation spécifique

    Requires: Admin role
    """
    try:
        result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        REQUEST_COUNT.labels(endpoint="/admin/conversations", method="GET", status="200").inc()
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/conversations", method="GET", status="500").inc()
        logger.error(f"Error fetching conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Supprime une conversation (et ses messages en cascade)

    Requires: Admin role
    """
    try:
        result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Compter les messages pour l'audit
        messages_count = await db.execute(select(func.count(Message.id)).where(Message.conversation_id == conversation_id))

        # Suppression (cascade automatique sur les messages)
        await db.delete(conversation)
        await db.commit()

        # Audit log
        await audit_service.log_action(
            db=db,
            action_name='conversation_deleted',
            user_id=admin_user.id,
            resource_type_name='conversation',
            resource_id=conversation_id,
            details={
                'conversation_title': conversation.title,
                'user_id': str(conversation.user_id),
                'messages_deleted': messages_count.scalar()
            },
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/conversations", method="DELETE", status="204").inc()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/conversations", method="DELETE", status="500").inc()
        logger.error(f"Error deleting conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Gestion des Messages ---

@app.get("/admin/messages", response_model=list[MessageRead])
async def get_messages(
    conversation_id: Optional[uuid.UUID] = None,
    sender_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Récupère tous les messages avec filtres

    Query Parameters:
    - conversation_id: Filtrer par conversation
    - sender_type: Filtrer par type d'expéditeur ('user' ou 'assistant')
    - limit: Nombre de résultats (max 200)
    - offset: Pagination

    Requires: Admin role
    """
    try:
        # Limiter le nombre maximum de résultats
        limit = min(limit, 200)

        # Construire la requête
        query = select(Message).order_by(Message.created_at.desc())

        if conversation_id:
            query = query.where(Message.conversation_id == conversation_id)
        if sender_type:
            query = query.where(Message.sender_type == sender_type)

        query = query.limit(limit).offset(offset)

        # Exécuter
        result = await db.execute(query)
        messages = result.scalars().all()

        REQUEST_COUNT.labels(endpoint="/admin/messages", method="GET", status="200").inc()
        return messages
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/messages", method="GET", status="500").inc()
        logger.error(f"Error fetching messages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/messages/{message_id}", status_code=204)
async def delete_message(
    message_id: uuid.UUID,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Supprime un message

    Requires: Admin role
    """
    try:
        result = await db.execute(select(Message).where(Message.id == message_id))
        message = result.scalar_one_or_none()
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        # Suppression
        await db.delete(message)
        await db.commit()

        # Audit log
        await audit_service.log_action(
            db=db,
            action_name='message_deleted',
            user_id=admin_user.id,
            resource_type_name='message',
            resource_id=message_id,
            details={
                'conversation_id': str(message.conversation_id),
                'sender_type': message.sender_type
            },
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/messages", method="DELETE", status="204").inc()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/messages", method="DELETE", status="500").inc()
        logger.error(f"Error deleting message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Gestion des Documents ---

@app.get("/admin/documents", response_model=list[DocumentRead])
async def get_documents(
    user_id: Optional[uuid.UUID] = None,
    file_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Récupère tous les documents avec filtres

    Query Parameters:
    - user_id: Filtrer par utilisateur
    - file_type: Filtrer par type de fichier
    - limit: Nombre de résultats (max 200)
    - offset: Pagination

    Requires: Admin role
    """
    try:
        # Limiter le nombre maximum de résultats
        limit = min(limit, 200)

        # Construire la requête
        query = select(Document).order_by(Document.created_at.desc())

        if user_id:
            query = query.where(Document.user_id == user_id)
        if file_type:
            query = query.where(Document.file_type == file_type)

        query = query.limit(limit).offset(offset)

        # Exécuter
        result = await db.execute(query)
        documents = result.scalars().all()

        REQUEST_COUNT.labels(endpoint="/admin/documents", method="GET", status="200").inc()
        return documents
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/documents", method="GET", status="500").inc()
        logger.error(f"Error fetching documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/documents/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: uuid.UUID,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Récupère un document spécifique

    Requires: Admin role
    """
    try:
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        REQUEST_COUNT.labels(endpoint="/admin/documents", method="GET", status="200").inc()
        return document
    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/documents", method="GET", status="500").inc()
        logger.error(f"Error fetching document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Supprime un document (aussi dans ChromaDB si possible)

    Requires: Admin role
    """
    try:
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Tentative de suppression dans ChromaDB (best effort)
        try:
            if chroma_client:
                collection = chroma_client.get_collection(name=COLLECTION_NAME)
                # Supprimer par métadonnée file_hash
                collection.delete(where={"file_hash": document.file_hash})
                logger.info(f"Document chunks deleted from ChromaDB: {document.file_hash}")
        except Exception as e:
            logger.warning(f"Could not delete document from ChromaDB: {e}")

        # Suppression de la base de données
        document_info = {
            'filename': document.filename,
            'file_hash': document.file_hash,
            'user_id': str(document.user_id)
        }
        await db.delete(document)
        await db.commit()

        # Audit log
        await audit_service.log_action(
            db=db,
            action_name='document_deleted',
            user_id=admin_user.id,
            resource_type_name='document',
            resource_id=document_id,
            details=document_info,
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/documents", method="DELETE", status="204").inc()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/documents", method="DELETE", status="500").inc()
        logger.error(f"Error deleting document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Gestion des Sessions ---

@app.get("/admin/sessions", response_model=list[SessionRead])
async def get_sessions(
    user_id: Optional[uuid.UUID] = None,
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Récupère toutes les sessions avec filtres

    Query Parameters:
    - user_id: Filtrer par utilisateur
    - active_only: Afficher seulement les sessions actives (non expirées)
    - limit: Nombre de résultats (max 200)
    - offset: Pagination

    Requires: Admin role
    """
    try:
        from datetime import datetime
        # Limiter le nombre maximum de résultats
        limit = min(limit, 200)

        # Construire la requête
        query = select(Session).order_by(Session.created_at.desc())

        if user_id:
            query = query.where(Session.user_id == user_id)
        if active_only:
            query = query.where(Session.expires_at > datetime.utcnow())

        query = query.limit(limit).offset(offset)

        # Exécuter
        result = await db.execute(query)
        sessions = result.scalars().all()

        REQUEST_COUNT.labels(endpoint="/admin/sessions", method="GET", status="200").inc()
        return sessions
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/admin/sessions", method="GET", status="500").inc()
        logger.error(f"Error fetching sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/sessions/{session_id}", status_code=204)
async def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Révoque (supprime) une session

    Requires: Admin role
    """
    try:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Suppression
        session_info = {'user_id': str(session.user_id)}
        await db.delete(session)
        await db.commit()

        # Audit log
        await audit_service.log_action(
            db=db,
            action_name='session_revoked',
            user_id=admin_user.id,
            resource_type_name='session',
            resource_id=session_id,
            details=session_info,
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/sessions", method="DELETE", status="204").inc()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/sessions", method="DELETE", status="500").inc()
        logger.error(f"Error revoking session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/sessions/user/{user_id}", status_code=204)
async def revoke_all_user_sessions(
    user_id: uuid.UUID,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Révoque toutes les sessions d'un utilisateur

    Requires: Admin role
    """
    try:
        # Vérifier que l'utilisateur existe
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Compter les sessions
        sessions_count = await db.execute(select(func.count(Session.id)).where(Session.user_id == user_id))
        count = sessions_count.scalar()

        # Suppression de toutes les sessions de l'utilisateur
        await db.execute(delete(Session).where(Session.user_id == user_id))
        await db.commit()

        # Audit log
        await audit_service.log_action(
            db=db,
            action_name='all_sessions_revoked',
            user_id=admin_user.id,
            resource_type_name='session',
            resource_id=user_id,
            details={'target_user_id': str(user_id), 'sessions_revoked': count},
            request=request
        )

        REQUEST_COUNT.labels(endpoint="/admin/sessions", method="DELETE", status="204").inc()
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        REQUEST_COUNT.labels(endpoint="/admin/sessions", method="DELETE", status="500").inc()
        logger.error(f"Error revoking all user sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Endpoint racine"""
    return {
        "name": "MY-IA API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
