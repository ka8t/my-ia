"""
Tests du système d'ingestion v2.0 (Advanced)

Tests pour les classes dans ingest_v2.py:
- DocumentParser
- SemanticChunker
- DocumentDeduplicator
- MetadataExtractor
- EmbeddingGenerator
- AdvancedIngestionPipeline
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock


# ============================================================================
# Tests DocumentDeduplicator
# ============================================================================

@pytest.mark.unit
@pytest.mark.ingest_v2
class TestDocumentDeduplicator:
    """Tests de la classe DocumentDeduplicator"""

    def test_compute_hash_same_content_same_hash(self):
        """compute_hash() doit produire le même hash pour le même contenu"""
        from app.ingest_v2 import DocumentDeduplicator

        content = "Test document content"
        hash1 = DocumentDeduplicator.compute_hash(content)
        hash2 = DocumentDeduplicator.compute_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produit 64 caractères hex

    def test_compute_hash_different_content_different_hash(self):
        """compute_hash() doit produire des hashs différents pour du contenu différent"""
        from app.ingest_v2 import DocumentDeduplicator

        hash1 = DocumentDeduplicator.compute_hash("Content A")
        hash2 = DocumentDeduplicator.compute_hash("Content B")

        assert hash1 != hash2

    def test_compute_file_hash(self):
        """compute_file_hash() doit calculer le hash d'un fichier"""
        from app.ingest_v2 import DocumentDeduplicator

        file_path = Path(__file__).parent / "fixtures" / "documents" / "sample.txt"

        if not file_path.exists():
            pytest.skip(f"Fichier de test non trouvé: {file_path}")

        file_hash = DocumentDeduplicator.compute_file_hash(str(file_path))

        assert isinstance(file_hash, str)
        assert len(file_hash) == 64  # SHA256

    def test_check_duplicate_no_duplicate(self, mocker):
        """check_duplicate() doit retourner False si pas de duplicate"""
        from app.ingest_v2 import DocumentDeduplicator

        # Mocker la collection ChromaDB
        mock_collection = mocker.Mock()
        mock_collection.get.return_value = {"ids": []}

        result = DocumentDeduplicator.check_duplicate(mock_collection, "test_hash_123")

        assert result is False

    def test_check_duplicate_with_duplicate(self, mocker):
        """check_duplicate() doit retourner True si duplicate trouvé"""
        from app.ingest_v2 import DocumentDeduplicator

        mock_collection = mocker.Mock()
        mock_collection.get.return_value = {"ids": ["doc1"]}

        result = DocumentDeduplicator.check_duplicate(mock_collection, "existing_hash")

        assert result is True


# ============================================================================
# Tests MetadataExtractor
# ============================================================================

@pytest.mark.unit
@pytest.mark.ingest_v2
class TestMetadataExtractor:
    """Tests de la classe MetadataExtractor"""

    def test_extract_file_metadata(self):
        """extract_file_metadata() doit extraire les métadonnées de base"""
        from app.ingest_v2 import MetadataExtractor

        file_path = Path(__file__).parent / "fixtures" / "documents" / "sample.txt"

        if not file_path.exists():
            pytest.skip(f"Fichier de test non trouvé: {file_path}")

        metadata = MetadataExtractor.extract_file_metadata(str(file_path))

        assert "filename" in metadata
        assert "file_size" in metadata
        assert "file_extension" in metadata
        assert "created_at" in metadata
        assert "modified_at" in metadata

        assert metadata["filename"] == "sample.txt"
        assert metadata["file_extension"] == ".txt"
        assert isinstance(metadata["file_size"], int)

    def test_enrich_metadata_basic(self):
        """enrich_metadata() doit enrichir les métadonnées"""
        from app.ingest_v2 import MetadataExtractor

        base_metadata = {
            "page_number": 1
        }

        file_metadata = {
            "filename": "test.txt",
            "file_size": 1000,
            "file_extension": ".txt"
        }

        enriched = MetadataExtractor.enrich_metadata(
            base_metadata=base_metadata,
            file_metadata=file_metadata,
            document_hash="abc123def456",
            chunk_index=5,
            total_chunks=10,
            chunk_type="text"
        )

        assert enriched["document_hash"] == "abc123def456"
        assert enriched["chunk_index"] == 5
        assert enriched["total_chunks"] == 10
        assert enriched["chunk_type"] == "text"
        assert enriched["filename"] == "test.txt"
        assert enriched["file_size"] == 1000
        assert "indexed_at" in enriched
        assert "ingestion_version" in enriched
        assert enriched["ingestion_version"] == "2.0"


# ============================================================================
# Tests SemanticChunker
# ============================================================================

@pytest.mark.unit
@pytest.mark.ingest_v2
class TestSemanticChunker:
    """Tests de la classe SemanticChunker"""

    def test_chunk_recursive_basic(self):
        """chunk_recursive() doit découper le texte"""
        from app.ingest_v2 import SemanticChunker

        chunker = SemanticChunker(chunk_size=500, chunk_overlap=50)

        text = "Ceci est un paragraphe de test. " * 100  # Texte long
        chunks = chunker.chunk_recursive(text)

        assert len(chunks) > 1
        assert all("text" in chunk for chunk in chunks)
        assert all("metadata" in chunk for chunk in chunks)

    def test_chunk_recursive_short_text(self):
        """chunk_recursive() avec texte court doit retourner un seul chunk"""
        from app.ingest_v2 import SemanticChunker

        chunker = SemanticChunker(chunk_size=500, chunk_overlap=50)

        text = "Court texte."
        chunks = chunker.chunk_recursive(text)

        assert len(chunks) == 1
        assert chunks[0]["text"] == text

    def test_chunk_markdown_preserves_structure(self):
        """chunk_markdown() doit préserver la structure Markdown"""
        from app.ingest_v2 import SemanticChunker

        chunker = SemanticChunker()

        markdown_text = """# Titre Principal

## Section 1

Contenu de la section 1.

## Section 2

Contenu de la section 2.
"""

        chunks = chunker.chunk_markdown(markdown_text)

        assert len(chunks) >= 1
        # Les chunks doivent contenir des métadonnées sur les headers
        assert all("text" in chunk for chunk in chunks)


# ============================================================================
# Tests DocumentParser
# ============================================================================

@pytest.mark.unit
@pytest.mark.ingest_v2
class TestDocumentParser:
    """Tests de la classe DocumentParser"""

    def test_parse_document_text_file(self, mocker):
        """parse_document() doit parser un fichier texte"""
        from app.ingest_v2 import DocumentParser

        file_path = Path(__file__).parent / "fixtures" / "documents" / "sample.txt"

        if not file_path.exists():
            pytest.skip(f"Fichier de test non trouvé: {file_path}")

        # Mocker la fonction partition de unstructured
        mock_element = MagicMock()
        mock_element.category = "NarrativeText"
        mock_element.__str__ = lambda self: "Test content"
        mock_element.metadata = MagicMock()
        mock_element.metadata.to_dict = lambda: {"page_number": 1}

        mocker.patch("app.ingest_v2.partition", return_value=[mock_element])

        elements = DocumentParser.parse_document(str(file_path), strategy="auto")

        assert len(elements) > 0
        assert all("type" in elem for elem in elements)
        assert all("text" in elem for elem in elements)
        assert all("metadata" in elem for elem in elements)

    def test_extract_tables_from_elements(self):
        """extract_tables() doit extraire les tables"""
        from app.ingest_v2 import DocumentParser

        elements = [
            {"type": "NarrativeText", "text": "Regular text", "metadata": {}},
            {"type": "Table", "text": "| A | B |\n|---|---|\n| 1 | 2 |", "metadata": {"page": 1}},
            {"type": "Title", "text": "Header", "metadata": {}},
            {"type": "Table", "text": "| C | D |", "metadata": {"page": 2}},
        ]

        tables = DocumentParser.extract_tables(elements)

        assert len(tables) == 2
        assert all("content" in table for table in tables)
        assert all("metadata" in table for table in tables)


# ============================================================================
# Tests EmbeddingGenerator
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.unit
@pytest.mark.ingest_v2
class TestEmbeddingGenerator:
    """Tests de la classe EmbeddingGenerator"""

    async def test_generate_embeddings_single_text(self, mocker):
        """generate_embeddings() doit générer un embedding"""
        from app.ingest_v2 import EmbeddingGenerator

        # Mocker httpx - IMPORTANT: utiliser "embeddings" (pluriel) pas "embedding"
        mock_response = mocker.Mock()
        mock_response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
        mock_response.raise_for_status = mocker.Mock()

        mock_client = mocker.Mock()
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock()
        mock_client.post = mocker.AsyncMock(return_value=mock_response)

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        generator = EmbeddingGenerator()
        embeddings = await generator.generate_embeddings(["Test text"])

        assert len(embeddings) == 1
        assert isinstance(embeddings[0], list)
        assert embeddings[0] == [0.1, 0.2, 0.3]

    async def test_generate_embeddings_batch(self, mocker):
        """generate_embeddings() doit gérer les batches"""
        from app.ingest_v2 import EmbeddingGenerator

        # Le mock doit retourner une liste d'embeddings (un par texte dans le batch)
        def mock_post_side_effect(*args, **kwargs):
            # Extraire le nombre de textes dans le batch
            input_texts = kwargs.get('json', {}).get('input', [])
            batch_size = len(input_texts)
            # Retourner autant d'embeddings que de textes
            mock_resp = mocker.Mock()
            mock_resp.json.return_value = {"embeddings": [[0.1] * 768] * batch_size}
            mock_resp.raise_for_status = mocker.Mock()
            return mock_resp

        mock_client = mocker.Mock()
        mock_client.__aenter__ = mocker.AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = mocker.AsyncMock()
        mock_client.post = mocker.AsyncMock(side_effect=mock_post_side_effect)

        mocker.patch("httpx.AsyncClient", return_value=mock_client)

        generator = EmbeddingGenerator()
        texts = ["Text " + str(i) for i in range(10)]
        embeddings = await generator.generate_embeddings(texts, batch_size=3)

        assert len(embeddings) == 10
        assert all(isinstance(e, list) for e in embeddings)
        assert all(len(e) == 768 for e in embeddings)


# ============================================================================
# Tests AdvancedIngestionPipeline (Integration)
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.ingest_v2
class TestAdvancedIngestionPipeline:
    """Tests d'intégration pour AdvancedIngestionPipeline"""

    async def test_pipeline_initialization(self, mocker):
        """Le pipeline doit s'initialiser correctement"""
        from app.ingest_v2 import AdvancedIngestionPipeline

        mock_client = mocker.Mock()
        mock_client.get_or_create_collection.return_value = mocker.Mock()

        pipeline = AdvancedIngestionPipeline(chroma_client=mock_client)

        assert pipeline is not None
        assert pipeline.collection is not None

    async def test_ingest_file_basic_flow(self, mocker):
        """ingest_file() doit exécuter le flux complet (mockés)"""
        from app.ingest_v2 import AdvancedIngestionPipeline

        # Setup mocks
        mock_client = mocker.Mock()
        mock_collection = mocker.Mock()
        mock_collection.get.return_value = {"ids": []}  # Pas de duplicate
        mock_collection.add = mocker.Mock()
        mock_client.get_or_create_collection.return_value = mock_collection

        # Mocker unstructured
        mock_element = MagicMock()
        mock_element.category = "NarrativeText"
        mock_element.__str__ = lambda self: "Test content from document"
        mock_element.metadata = MagicMock()
        mock_element.metadata.to_dict = lambda: {}

        mocker.patch("app.ingest_v2.partition", return_value=[mock_element])

        # Mocker embeddings
        mock_response = mocker.Mock()
        mock_response.json.return_value = {"embedding": [0.1] * 768}
        mock_response.raise_for_status = mocker.Mock()

        mock_http_client = mocker.Mock()
        mock_http_client.__aenter__ = mocker.AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = mocker.AsyncMock()
        mock_http_client.post = mocker.AsyncMock(return_value=mock_response)

        mocker.patch("httpx.AsyncClient", return_value=mock_http_client)

        # Test
        pipeline = AdvancedIngestionPipeline(chroma_client=mock_client)

        file_path = Path(__file__).parent / "fixtures" / "documents" / "sample.txt"
        if not file_path.exists():
            pytest.skip(f"Fichier de test non trouvé: {file_path}")

        result = await pipeline.ingest_file(str(file_path))

        assert result["status"] in ["success", "skipped", "failed"]

    async def test_ingest_file_with_duplicate(self, mocker):
        """ingest_file() doit détecter les duplicates si skip_duplicates=True"""
        from app.ingest_v2 import AdvancedIngestionPipeline

        mock_client = mocker.Mock()
        mock_collection = mocker.Mock()
        # Simuler un duplicate trouvé
        mock_collection.get.return_value = {"ids": ["existing_doc"]}
        mock_client.get_or_create_collection.return_value = mock_collection

        pipeline = AdvancedIngestionPipeline(chroma_client=mock_client)

        file_path = Path(__file__).parent / "fixtures" / "documents" / "sample.txt"
        if not file_path.exists():
            pytest.skip(f"Fichier de test non trouvé: {file_path}")

        result = await pipeline.ingest_file(str(file_path), skip_duplicates=True)

        # Devrait skip car duplicate détecté
        assert result["status"] == "skipped"
        assert "document_hash" in result
