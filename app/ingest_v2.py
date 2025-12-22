"""
Advanced Document Ingestion Pipeline v2.0
------------------------------------------
Modern RAG ingestion system with:
- Multi-format parsing (Unstructured.io)
- Semantic chunking (LangChain)
- Deduplication & versioning
- Rich metadata extraction
- Optimized async pipeline
- OCR support for images
- Table extraction
"""

import os
import json
import hashlib
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid

import httpx
import chromadb
from chromadb.config import Settings

# Unstructured for multi-format parsing
from unstructured.partition.auto import partition
from unstructured.chunking.title import chunk_by_title
from unstructured.staging.base import elements_to_json

# LangChain for semantic chunking
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
)
from langchain_core.documents import Document as LangchainDocument

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
CHROMA_HOST = os.getenv("CHROMA_HOST", "http://localhost:8000")
CHROMA_PATH = "/chroma/chroma"
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
COLLECTION_NAME = "knowledge_base"

# Chunking configuration
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
CHUNKING_STRATEGY = os.getenv("CHUNKING_STRATEGY", "semantic")  # 'semantic', 'recursive', 'by_title'

# Logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DocumentParser:
    """Advanced multi-format document parser using Unstructured.io"""

    @staticmethod
    def parse_document(file_path: str, strategy: str = "auto") -> List[Dict[str, Any]]:
        """
        Parse document using Unstructured.io

        Args:
            file_path: Path to document
            strategy: Parsing strategy ('auto', 'fast', 'hi_res', 'ocr_only')

        Returns:
            List of document elements with metadata
        """
        try:
            logger.info(f"Parsing {file_path} with strategy '{strategy}'")

            # Parse with Unstructured
            elements = partition(
                filename=file_path,
                strategy=strategy,
                include_metadata=True,
                extract_images_in_pdf=True,  # Extract images from PDFs
                infer_table_structure=True,  # Preserve table structure
            )

            # Convert to JSON-serializable format
            parsed_elements = []
            for element in elements:
                parsed_elements.append({
                    "type": element.category,
                    "text": str(element),
                    "metadata": element.metadata.to_dict() if hasattr(element.metadata, 'to_dict') else {}
                })

            logger.info(f"Parsed {len(parsed_elements)} elements from {file_path}")
            return parsed_elements

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            raise

    @staticmethod
    def extract_tables(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract and structure tables separately"""
        tables = []
        for elem in elements:
            if elem["type"] == "Table":
                tables.append({
                    "content": elem["text"],
                    "metadata": elem["metadata"]
                })
        return tables


class SemanticChunker:
    """Semantic chunking using LangChain"""

    def __init__(self, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Initialize text splitters
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],  # Semantic separators
        )

        # Markdown header splitter for structured documents
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ]
        )

    def chunk_recursive(self, text: str, metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Chunk using recursive character splitting (respects paragraphs/sentences)"""
        docs = self.recursive_splitter.create_documents([text], metadatas=[metadata] if metadata else None)

        return [
            {
                "text": doc.page_content,
                "metadata": doc.metadata or {}
            }
            for doc in docs
        ]

    def chunk_by_title(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Chunk by document structure (titles, sections)"""
        from unstructured.documents.elements import Title, NarrativeText, ListItem, Table

        # This would use Unstructured's chunk_by_title
        # For now, we'll group by title elements
        chunks = []
        current_chunk = []
        current_metadata = {}

        for elem in elements:
            if elem["type"] == "Title":
                # Save previous chunk
                if current_chunk:
                    chunks.append({
                        "text": "\n".join(current_chunk),
                        "metadata": current_metadata.copy()
                    })
                # Start new chunk
                current_chunk = [elem["text"]]
                current_metadata = elem["metadata"].copy()
            else:
                current_chunk.append(elem["text"])

        # Add last chunk
        if current_chunk:
            chunks.append({
                "text": "\n".join(current_chunk),
                "metadata": current_metadata
            })

        return chunks

    def chunk_markdown(self, text: str) -> List[Dict[str, Any]]:
        """Chunk markdown preserving header structure"""
        docs = self.markdown_splitter.split_text(text)

        chunks = []
        for doc in docs:
            # Further split if still too large
            if len(doc.page_content) > self.chunk_size:
                sub_docs = self.recursive_splitter.split_documents([doc])
                chunks.extend([
                    {"text": d.page_content, "metadata": d.metadata}
                    for d in sub_docs
                ])
            else:
                chunks.append({
                    "text": doc.page_content,
                    "metadata": doc.metadata
                })

        return chunks


class DocumentDeduplicator:
    """Handle document deduplication and versioning"""

    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA256 hash of content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    @staticmethod
    def compute_file_hash(file_path: str) -> str:
        """Compute SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def check_duplicate(collection, document_hash: str) -> bool:
        """Check if document already exists in collection"""
        try:
            results = collection.get(
                where={"document_hash": document_hash}
            )
            return len(results["ids"]) > 0
        except:
            return False


class MetadataExtractor:
    """Extract rich metadata from documents"""

    @staticmethod
    def extract_file_metadata(file_path: str) -> Dict[str, Any]:
        """Extract file system metadata"""
        path = Path(file_path)
        stat = path.stat()

        return {
            "filename": path.name,
            "file_extension": path.suffix,
            "file_size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "file_path": str(path.absolute()),
        }

    @staticmethod
    def enrich_metadata(
        base_metadata: Dict[str, Any],
        file_metadata: Dict[str, Any],
        document_hash: str,
        chunk_index: int,
        total_chunks: int,
        chunk_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Combine and enrich metadata"""
        return {
            **file_metadata,
            **base_metadata,
            "document_hash": document_hash,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "chunk_type": chunk_type or "text",
            "indexed_at": datetime.now().isoformat(),
            "ingestion_version": "2.0",
        }


class EmbeddingGenerator:
    """Generate embeddings using Ollama"""

    def __init__(self, ollama_host: str = OLLAMA_HOST, model: str = EMBED_MODEL):
        self.ollama_host = ollama_host
        self.model = model

    async def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 100,
        progress_callback: Optional[callable] = None
    ) -> List[List[float]]:
        """Generate embeddings with batching and progress tracking"""
        all_embeddings = []
        total = len(texts)

        async with httpx.AsyncClient(timeout=600.0) as client:
            for i in range(0, total, batch_size):
                batch = texts[i:i + batch_size]

                try:
                    response = await client.post(
                        f"{self.ollama_host}/api/embed",
                        json={"model": self.model, "input": batch}
                    )
                    response.raise_for_status()
                    batch_embeddings = response.json()["embeddings"]
                    all_embeddings.extend(batch_embeddings)

                    if progress_callback:
                        await progress_callback(min(i + batch_size, total), total)

                    logger.info(f"Generated embeddings for batch {i//batch_size + 1}/{(total-1)//batch_size + 1}")

                except Exception as e:
                    logger.error(f"Error generating embeddings for batch {i//batch_size + 1}: {e}")
                    raise

        return all_embeddings


class AdvancedIngestionPipeline:
    """Main ingestion pipeline orchestrator"""

    def __init__(
        self,
        chroma_client: chromadb.Client,
        collection_name: str = COLLECTION_NAME,
        chunking_strategy: str = CHUNKING_STRATEGY
    ):
        self.chroma_client = chroma_client
        self.collection_name = collection_name
        self.chunking_strategy = chunking_strategy

        # Initialize components
        self.parser = DocumentParser()
        self.chunker = SemanticChunker()
        self.deduplicator = DocumentDeduplicator()
        self.metadata_extractor = MetadataExtractor()
        self.embedder = EmbeddingGenerator()

        # Get or create collection
        self.collection = chroma_client.get_or_create_collection(name=collection_name)

    async def ingest_file(
        self,
        file_path: str,
        parsing_strategy: str = "auto",
        skip_duplicates: bool = True
    ) -> Dict[str, Any]:
        """
        Ingest a single file with full pipeline

        Args:
            file_path: Path to file
            parsing_strategy: Unstructured parsing strategy
            skip_duplicates: Skip if document already indexed

        Returns:
            Ingestion result with statistics
        """
        logger.info(f"Starting ingestion of {file_path}")

        # Extract file metadata
        file_metadata = self.metadata_extractor.extract_file_metadata(file_path)
        document_hash = self.deduplicator.compute_file_hash(file_path)

        # Check for duplicates
        if skip_duplicates and self.deduplicator.check_duplicate(self.collection, document_hash):
            logger.info(f"Document {file_path} already indexed (hash: {document_hash[:8]}...), skipping")
            return {
                "status": "skipped",
                "reason": "duplicate",
                "document_hash": document_hash,
                "chunks_indexed": 0
            }

        # Parse document
        elements = self.parser.parse_document(file_path, strategy=parsing_strategy)

        # Extract tables separately
        tables = self.parser.extract_tables(elements)

        # Chunk based on strategy
        chunks = await self._chunk_elements(elements, file_path)

        if not chunks:
            logger.warning(f"No chunks generated from {file_path}")
            return {
                "status": "failed",
                "reason": "no_content",
                "chunks_indexed": 0
            }

        # Generate embeddings
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings = await self.embedder.generate_embeddings(chunk_texts)

        # Prepare for ChromaDB
        ids = []
        metadatas = []
        documents = []

        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{document_hash}-{idx}"
            ids.append(chunk_id)

            # Enrich metadata
            metadata = self.metadata_extractor.enrich_metadata(
                base_metadata=chunk.get("metadata", {}),
                file_metadata=file_metadata,
                document_hash=document_hash,
                chunk_index=idx,
                total_chunks=len(chunks),
                chunk_type=chunk.get("type", "text")
            )
            metadatas.append(metadata)
            documents.append(chunk["text"])

        # Add to ChromaDB in batches
        BATCH_SIZE = 100
        for i in range(0, len(ids), BATCH_SIZE):
            batch_slice = slice(i, i + BATCH_SIZE)
            self.collection.add(
                ids=ids[batch_slice],
                embeddings=embeddings[batch_slice],
                documents=documents[batch_slice],
                metadatas=metadatas[batch_slice]
            )
            logger.info(f"Indexed batch {i//BATCH_SIZE + 1}/{(len(ids)-1)//BATCH_SIZE + 1}")

        logger.info(f"Successfully indexed {len(chunks)} chunks from {file_path}")

        return {
            "status": "success",
            "filename": file_metadata["filename"],
            "document_hash": document_hash,
            "chunks_indexed": len(chunks),
            "tables_found": len(tables),
            "file_size": file_metadata["file_size"],
        }

    async def _chunk_elements(self, elements: List[Dict[str, Any]], file_path: str) -> List[Dict[str, Any]]:
        """Chunk elements based on strategy"""

        # Combine all text from elements
        full_text = "\n\n".join([elem["text"] for elem in elements if elem["text"].strip()])

        if not full_text.strip():
            return []

        # Choose chunking strategy
        if self.chunking_strategy == "by_title":
            chunks = self.chunker.chunk_by_title(elements)

        elif self.chunking_strategy == "markdown" and file_path.endswith(('.md', '.markdown')):
            chunks = self.chunker.chunk_markdown(full_text)

        else:  # Default to recursive (semantic)
            # Aggregate metadata from elements
            metadata = {}
            if elements and elements[0].get("metadata"):
                metadata = elements[0]["metadata"]

            chunks = self.chunker.chunk_recursive(full_text, metadata)

        return chunks

    async def ingest_directory(
        self,
        directory: str,
        recursive: bool = True,
        file_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Ingest all files in a directory

        Args:
            directory: Path to directory
            recursive: Scan subdirectories
            file_patterns: List of glob patterns (e.g., ['*.pdf', '*.docx'])

        Returns:
            Ingestion statistics
        """
        logger.info(f"Starting directory ingestion: {directory}")

        path = Path(directory)

        # Default patterns
        if file_patterns is None:
            file_patterns = [
                "*.pdf", "*.txt", "*.md", "*.html", "*.htm",
                "*.docx", "*.doc", "*.xlsx", "*.xls", "*.pptx", "*.ppt",
                "*.jsonl", "*.json", "*.csv",
                "*.png", "*.jpg", "*.jpeg"  # OCR images
            ]

        # Find all files
        files = []
        for pattern in file_patterns:
            if recursive:
                files.extend(path.rglob(pattern))
            else:
                files.extend(path.glob(pattern))

        logger.info(f"Found {len(files)} files to process")

        # Ingest each file
        results = {
            "total_files": len(files),
            "successful": 0,
            "skipped": 0,
            "failed": 0,
            "total_chunks": 0,
            "files": []
        }

        for file in files:
            try:
                result = await self.ingest_file(str(file))
                results["files"].append(result)

                if result["status"] == "success":
                    results["successful"] += 1
                    results["total_chunks"] += result["chunks_indexed"]
                elif result["status"] == "skipped":
                    results["skipped"] += 1
                else:
                    results["failed"] += 1

            except Exception as e:
                logger.error(f"Error ingesting {file}: {e}")
                results["failed"] += 1
                results["files"].append({
                    "status": "failed",
                    "filename": file.name,
                    "error": str(e)
                })

        logger.info(f"Directory ingestion complete: {results['successful']} successful, "
                   f"{results['skipped']} skipped, {results['failed']} failed")

        return results


async def main():
    """Main ingestion script"""
    logger.info("🚀 Starting Advanced Ingestion Pipeline v2.0")

    # Initialize ChromaDB
    chroma_client = chromadb.PersistentClient(
        path=CHROMA_PATH,
        settings=Settings(anonymized_telemetry=False)
    )

    # Create pipeline
    pipeline = AdvancedIngestionPipeline(
        chroma_client=chroma_client,
        chunking_strategy=CHUNKING_STRATEGY
    )

    # Ingest from datasets directory
    datasets_dir = os.getenv("DATASETS_DIR", "/app/datasets")

    results = await pipeline.ingest_directory(
        directory=datasets_dir,
        recursive=True
    )

    # Display results
    logger.info("=" * 60)
    logger.info("📊 INGESTION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total files found: {results['total_files']}")
    logger.info(f"✅ Successful: {results['successful']}")
    logger.info(f"⏭️  Skipped (duplicates): {results['skipped']}")
    logger.info(f"❌ Failed: {results['failed']}")
    logger.info(f"📦 Total chunks indexed: {results['total_chunks']}")
    logger.info("=" * 60)

    # Get collection count
    collection = chroma_client.get_collection(name=COLLECTION_NAME)
    total_count = collection.count()
    logger.info(f"📚 Total documents in database: {total_count}")


if __name__ == "__main__":
    asyncio.run(main())
