"""
Service Ingestion

Logique métier pour l'ingestion de documents avec le pipeline v2.
"""
import os
import logging
import tempfile
import uuid
from typing import Dict, Any, Optional

from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_ingestion_pipeline
from app.models import Document, DocumentVisibility

logger = logging.getLogger(__name__)

# Extensions supportées
ALLOWED_EXTENSIONS = {
    ".pdf", ".txt", ".md", ".html", ".htm",
    ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
    ".jsonl", ".json", ".csv",
    ".png", ".jpg", ".jpeg"
}


class IngestionService:
    """Service pour l'ingestion de documents"""

    @staticmethod
    async def ingest_document(
        file: UploadFile,
        parsing_strategy: str = "auto",
        skip_duplicates: bool = True,
        user_id: Optional[str] = None,
        visibility: str = "public",
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Ingère un document avec le pipeline avancé v2

        Args:
            file: Fichier uploadé
            parsing_strategy: Stratégie de parsing ('auto', 'fast', 'hi_res', 'ocr_only')
            skip_duplicates: Ignorer les doublons
            user_id: UUID de l'utilisateur proprietaire
            visibility: Visibilite du document ('public' ou 'private')
            db: Session database pour sauvegarder le Document

        Returns:
            Dictionnaire avec le résultat de l'ingestion

        Raises:
            HTTPException: Si le pipeline n'est pas initialisé ou erreur d'ingestion
        """
        ingestion_pipeline = get_ingestion_pipeline()
        if not ingestion_pipeline:
            raise HTTPException(
                status_code=500,
                detail="Ingestion pipeline not initialized"
            )

        # Vérifier l'extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Type de fichier non supporté. Extensions autorisées: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        tmp_file_path = None
        try:
            # Créer un fichier temporaire
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_file_path = tmp_file.name

            logger.info(f"File uploaded: {file.filename} ({len(content)} bytes)")

            # Ingestion avec le pipeline avancé (avec user_id et visibility)
            result = await ingestion_pipeline.ingest_file(
                file_path=tmp_file_path,
                parsing_strategy=parsing_strategy,
                skip_duplicates=skip_duplicates,
                user_id=user_id,
                visibility=visibility
            )

            # Nettoyer le fichier temporaire
            os.unlink(tmp_file_path)

            # Gérer les différents statuts de résultat
            if result["status"] == "skipped":
                return {
                    "success": True,
                    "filename": file.filename,
                    "chunks_indexed": 0,
                    "message": f"Document déjà indexé (hash: {result['document_hash'][:8]}...)"
                }
            elif result["status"] == "failed":
                raise HTTPException(
                    status_code=400,
                    detail=f"Échec de l'ingestion: {result.get('reason', 'unknown error')}"
                )
            else:  # success
                # Sauvegarder le Document en PostgreSQL si db fournie
                if db and user_id:
                    try:
                        doc_visibility = DocumentVisibility(visibility)
                        new_doc = Document(
                            filename=file.filename,
                            file_hash=result.get("document_hash", ""),
                            file_size=len(content),
                            mime_type=file.content_type or "application/octet-stream",
                            chunk_count=result["chunks_indexed"],
                            user_id=uuid.UUID(user_id),
                            visibility=doc_visibility,
                            is_indexed=True
                        )
                        db.add(new_doc)
                        await db.commit()
                        await db.refresh(new_doc)
                        logger.info(f"Document saved to DB: {new_doc.id} (user={user_id}, visibility={visibility})")
                    except Exception as e:
                        logger.error(f"Error saving document to DB: {e}")
                        # On ne fait pas échouer l'ingestion si la sauvegarde DB échoue
                        # Le document est déjà dans ChromaDB

                message = f"Fichier '{file.filename}' indexé avec succès ({result['chunks_indexed']} chunks"
                if result.get('tables_found', 0) > 0:
                    message += f", {result['tables_found']} tables détectées"
                message += ")"

                return {
                    "success": True,
                    "filename": file.filename,
                    "chunks_indexed": result["chunks_indexed"],
                    "message": message
                }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error in ingestion: {e}", exc_info=True)

            # Nettoyer le fichier temporaire si il existe
            if tmp_file_path and os.path.exists(tmp_file_path):
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass

            raise HTTPException(status_code=500, detail=str(e))
