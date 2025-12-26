"""
Utilitaires ChromaDB

Fonctions helpers pour interagir avec ChromaDB (recherche de contexte).
"""
import logging
from typing import List, Dict, Any, Optional, Set

from app.core.config import settings
from app.core.deps import get_chroma_client
from app.common.utils.ollama import get_embeddings

logger = logging.getLogger(__name__)


async def get_indexed_document_hashes(db_session) -> Set[str]:
    """
    Recupere les hashes des documents indexes (is_indexed=True) depuis PostgreSQL

    Args:
        db_session: Session SQLAlchemy async

    Returns:
        Set des file_hash des documents indexes
    """
    from sqlalchemy import select
    from app.models import Document

    try:
        result = await db_session.execute(
            select(Document.file_hash).where(Document.is_indexed == True)
        )
        return {row[0] for row in result.fetchall()}
    except Exception as e:
        logger.error(f"Error fetching indexed document hashes: {e}")
        return set()


async def search_context(
    query: str,
    top_k: Optional[int] = None,
    user_id: Optional[str] = None,
    db_session = None
) -> List[Dict[str, Any]]:
    """
    Recherche de contexte dans ChromaDB avec filtrage par visibilite

    Logique de visibilite:
    - Documents "public" : accessibles a tous
    - Documents "private" : accessibles uniquement au proprietaire (user_id)
    - Documents non indexes (is_indexed=False) : exclus de la recherche

    Args:
        query: Question de l'utilisateur
        top_k: Nombre de résultats à retourner (défaut: settings.top_k)
        user_id: UUID de l'utilisateur connecte (pour filtrer les docs prives)
        db_session: Session DB pour verifier is_indexed

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

        # Construire le filtre de visibilite pour ChromaDB
        # On recupere plus de resultats pour filtrer ensuite par is_indexed
        fetch_multiplier = 3  # On fetch 3x plus pour compenser le filtrage

        # Filtre ChromaDB: public OU (private ET meme user)
        where_filter = None
        if user_id:
            # User connecte: voir public + ses propres documents prives
            where_filter = {
                "$or": [
                    {"visibility": "public"},
                    {"$and": [
                        {"visibility": "private"},
                        {"user_id": user_id}
                    ]}
                ]
            }
        else:
            # Pas de user: uniquement public
            where_filter = {"visibility": "public"}

        # Recherche dans ChromaDB avec filtre
        try:
            results_data = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k * fetch_multiplier,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            # Fallback sans filtre si erreur (documents legacy sans visibility)
            logger.warning(f"Query with filter failed, fallback without filter: {e}")
            results_data = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k * fetch_multiplier,
                include=["documents", "metadatas", "distances"]
            )

        # Recuperer les documents indexes si db_session fournie
        indexed_hashes = None
        if db_session:
            indexed_hashes = await get_indexed_document_hashes(db_session)

        results = []
        if results_data.get("documents") and results_data["documents"][0]:
            for i, doc in enumerate(results_data["documents"][0]):
                metadata = results_data.get("metadatas", [[]])[0][i] if results_data.get("metadatas") else {}

                # Filtrer par is_indexed si on a la session DB
                if indexed_hashes is not None:
                    doc_hash = metadata.get("document_hash")
                    if doc_hash and doc_hash not in indexed_hashes:
                        continue  # Document desindexe, on l'ignore

                # Verifier la visibilite (double check)
                visibility = metadata.get("visibility", "public")
                doc_user_id = metadata.get("user_id")

                if visibility == "private" and doc_user_id != user_id:
                    continue  # Document prive d'un autre user

                results.append({
                    "content": doc,
                    "metadata": metadata,
                    "distance": results_data.get("distances", [[]])[0][i] if results_data.get("distances") else None
                })

                # Limiter aux top_k resultats
                if len(results) >= top_k:
                    break

        logger.info(f"Found {len(results)} context results for query (user_id={user_id})")
        return results

    except Exception as e:
        logger.error(f"Error searching context: {e}")
        return []
