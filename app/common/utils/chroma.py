"""
Utilitaires ChromaDB

Fonctions helpers pour interagir avec ChromaDB (recherche de contexte).
"""
import logging
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.core.deps import get_chroma_client
from app.common.utils.ollama import get_embeddings

logger = logging.getLogger(__name__)


async def search_context(query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Recherche de contexte dans ChromaDB

    Args:
        query: Question de l'utilisateur
        top_k: Nombre de résultats à retourner (défaut: settings.top_k)

    Returns:
        Liste de dictionnaires contenant le contexte trouvé
    """
    try:
        if top_k is None:
            top_k = settings.top_k

        chroma_client = get_chroma_client()
        if chroma_client is None:
            logger.error("ChromaDB client not initialized")
            return []

        # Générer l'embedding de la query
        query_embedding = await get_embeddings(query)

        # Récupérer la collection
        try:
            collection = chroma_client.get_collection(name=settings.collection_name)
        except Exception as e:
            logger.error(f"Collection '{settings.collection_name}' not found: {e}")
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
