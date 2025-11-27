import os
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

import httpx
import chromadb
from chromadb.config import Settings
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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
            response = await client.get(f"{CHROMA_HOST}/api/v1/heartbeat")
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
                    async for chunk in response.aiter_bytes():
                        yield chunk

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
