import os
import logging
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
import tempfile
import uuid

import httpx
import chromadb
from chromadb.config import Settings
from fastapi import FastAPI, HTTPException, Header, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import des fonctions d'ingestion (legacy)
from ingest import chunk, embed, embed_with_progress, extract_pdf_text, extract_html_text

# Import du nouveau système d'ingestion v2
from ingest_v2 import AdvancedIngestionPipeline

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

# FastAPI app
app = FastAPI(
    title="MY-IA API",
    description="API d'IA conversationnelle avec RAG et automatisation",
    version="1.0.0"
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
    x_api_key: Optional[str] = Header(None)
):
    """Endpoint pour uploader et indexer un fichier dans ChromaDB"""
    verify_api_key(x_api_key)

    # Vérifier le type de fichier
    allowed_extensions = {".pdf", ".txt", ".md", ".html", ".jsonl"}
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non supporté. Extensions autorisées: {', '.join(allowed_extensions)}"
        )

    try:
        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            # Écrire le contenu uploadé
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        logger.info(f"File uploaded: {file.filename} ({len(content)} bytes)")

        # Extraire le texte selon le type de fichier
        text = ""
        if file_ext == ".pdf":
            text = extract_pdf_text(tmp_file_path)
        elif file_ext == ".html":
            text = extract_html_text(tmp_file_path)
        elif file_ext == ".jsonl":
            # Pour JSONL, lire ligne par ligne
            import json
            with open(tmp_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        row = json.loads(line)
                        text += row.get("text") or row.get("content") or ""
                        text += "\n"
        else:  # .txt ou .md
            with open(tmp_file_path, "r", encoding="utf-8") as f:
                text = f.read()

        # Supprimer le fichier temporaire
        os.unlink(tmp_file_path)

        if not text.strip():
            raise HTTPException(status_code=400, detail="Le fichier ne contient pas de texte extractible")

        # Découper en chunks
        chunks = chunk(text)
        logger.info(f"Document split into {len(chunks)} chunks")

        # Ajouter à ChromaDB
        if chroma_client is None:
            raise HTTPException(status_code=500, detail="ChromaDB client not initialized")

        try:
            collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
            file_id = str(uuid.uuid4())

            # Traiter par batches pour éviter les timeouts
            BATCH_SIZE = 64
            total_indexed = 0

            for i in range(0, len(chunks), BATCH_SIZE):
                batch_chunks = chunks[i:i+BATCH_SIZE]
                batch_num = i//BATCH_SIZE + 1
                total_batches = (len(chunks)-1)//BATCH_SIZE + 1
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_chunks)} chunks)")

                # Générer les embeddings pour ce batch
                embeddings = await embed(batch_chunks)

                # Générer les IDs et métadonnées pour ce batch
                batch_ids = [f"{file_id}-{i+j}" for j in range(len(batch_chunks))]
                batch_metadatas = [{"source": file.filename} for _ in batch_chunks]

                # Ajouter ce batch à ChromaDB
                collection.add(
                    ids=batch_ids,
                    embeddings=embeddings,
                    documents=batch_chunks,
                    metadatas=batch_metadatas
                )
                total_indexed += len(batch_chunks)
                logger.info(f"Indexed {total_indexed}/{len(chunks)} chunks")

            logger.info(f"Successfully indexed {len(chunks)} chunks from {file.filename}")
        except Exception as e:
            logger.error(f"Error adding to ChromaDB: {e}")
            raise HTTPException(status_code=500, detail=f"Error indexing file: {str(e)}")

        REQUEST_COUNT.labels(endpoint="/upload", method="POST", status="200").inc()

        return UploadResponse(
            success=True,
            filename=file.filename,
            chunks_indexed=len(chunks),
            message=f"Fichier '{file.filename}' indexé avec succès ({len(chunks)} chunks)"
        )

    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels(endpoint="/upload", method="POST", status="500").inc()
        logger.error(f"Error in upload endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload/stream")
@limiter.limit("10/minute")
async def upload_file_stream(
    request: Request,
    file: UploadFile = File(...),
    x_api_key: Optional[str] = Header(None)
):
    """Endpoint pour uploader et indexer un fichier avec progression SSE"""
    verify_api_key(x_api_key)

    # Vérifier le type de fichier et lire le contenu AVANT le générateur
    allowed_extensions = {".pdf", ".txt", ".md", ".html", ".jsonl"}
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        error_msg = f"Type de fichier non supporté. Extensions autorisées: {', '.join(allowed_extensions)}"
        async def error_gen():
            yield f"data: {json.dumps({'error': error_msg})}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")

    # Lire le fichier AVANT d'entrer dans le générateur
    content = await file.read()
    filename = file.filename

    async def generate():
        try:
            # Créer un fichier temporaire
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                tmp_file.write(content)
                tmp_file_path = tmp_file.name

            logger.info(f"File uploaded: {filename} ({len(content)} bytes)")
            yield f"data: {json.dumps({'status': 'uploaded', 'filename': filename, 'size': len(content)})}\n\n"

            # Extraire le texte
            text = ""
            if file_ext == ".pdf":
                text = extract_pdf_text(tmp_file_path)
            elif file_ext == ".html":
                text = extract_html_text(tmp_file_path)
            elif file_ext == ".jsonl":
                import json as json_lib
                with open(tmp_file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            row = json_lib.loads(line)
                            text += row.get("text") or row.get("content") or ""
                            text += "\n"
            else:
                with open(tmp_file_path, "r", encoding="utf-8") as f:
                    text = f.read()

            os.unlink(tmp_file_path)

            if not text.strip():
                yield f"data: {json.dumps({'error': 'Le fichier ne contient pas de texte extractible'})}\n\n"
                return

            # Découper en chunks
            chunks = chunk(text)
            logger.info(f"Document split into {len(chunks)} chunks")
            yield f"data: {json.dumps({'status': 'chunked', 'total_chunks': len(chunks)})}\n\n"

            # Générer les embeddings (tous d'un coup pour plus de performance)
            yield f"data: {json.dumps({'status': 'embedding', 'total_chunks': len(chunks)})}\n\n"
            embeddings = await embed(chunks)

            # Générer les IDs et métadonnées
            file_id = str(uuid.uuid4())
            ids = [f"{file_id}-{i}" for i in range(len(chunks))]
            metadatas = [{"source": filename} for _ in chunks]

            # Ajouter à ChromaDB
            if chroma_client is None:
                yield f"data: {json.dumps({'error': 'ChromaDB client not initialized'})}\n\n"
                return

            collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas
            )
            logger.info(f"Successfully indexed {len(chunks)} chunks from {filename}")

            yield f"data: {json.dumps({'status': 'completed', 'chunks_indexed': len(chunks), 'filename': filename})}\n\n"

        except Exception as e:
            logger.error(f"Error in upload/stream endpoint: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/upload/v2", response_model=UploadResponse)
@limiter.limit("10/minute")
async def upload_file_v2(
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
            REQUEST_COUNT.labels(endpoint="/upload/v2", method="POST", status="200").inc()

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
        REQUEST_COUNT.labels(endpoint="/upload/v2", method="POST", status="500").inc()
        logger.error(f"Error in upload/v2 endpoint: {e}", exc_info=True)

        # Clean up temp file if it exists
        if 'tmp_file_path' in locals():
            try:
                os.unlink(tmp_file_path)
            except:
                pass

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
