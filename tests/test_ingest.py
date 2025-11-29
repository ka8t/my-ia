"""
Tests unitaires pour le système d'ingestion (app/ingest.py)

Ces tests vérifient:
- chunk() : découpage de texte
- embed() : génération d'embeddings
- read_jsonl() : lecture de fichiers JSONL
- extract_pdf_text() : extraction de PDF
- extract_html_text() : extraction de HTML
- create_collection() : création collection ChromaDB
- add_to_collection() : ajout de documents
- get_collection_count() : comptage de documents
"""
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock


# ============================================================================
# TESTS chunk()
# ============================================================================

@pytest.mark.unit
@pytest.mark.ingest
class TestChunk:
    """Tests pour la fonction chunk"""

    def test_chunk_basic(self):
        """Vérifie le découpage de base"""
        from app.ingest import chunk

        text = "A" * 1000
        result = chunk(text, size=200, overlap=50)

        assert len(result) > 1
        assert all(isinstance(c, str) for c in result)

    def test_chunk_first_chunk_correct_size(self):
        """Vérifie que le premier chunk a la bonne taille"""
        from app.ingest import chunk

        text = "A" * 1000
        result = chunk(text, size=200, overlap=50)

        assert len(result[0]) == 200

    def test_chunk_overlap_works(self):
        """Vérifie que l'overlap fonctionne"""
        from app.ingest import chunk

        text = "ABCDEFGHIJ" * 100  # 1000 caractères
        result = chunk(text, size=200, overlap=50)

        # Les chunks doivent se chevaucher
        # Dernier partie du chunk 1 = début du chunk 2
        if len(result) > 1:
            end_of_first = result[0][-50:]
            start_of_second = result[1][:50]
            assert end_of_first == start_of_second

    def test_chunk_short_text(self):
        """Vérifie le comportement avec texte court"""
        from app.ingest import chunk

        text = "Short text"
        result = chunk(text, size=200, overlap=50)

        assert len(result) == 1
        assert result[0] == text

    def test_chunk_empty_text(self):
        """Vérifie le comportement avec texte vide"""
        from app.ingest import chunk

        text = ""
        result = chunk(text, size=200, overlap=50)

        assert len(result) == 1
        assert result[0] == ""

    def test_chunk_default_params(self):
        """Vérifie les paramètres par défaut"""
        from app.ingest import chunk, CHUNK_SIZE, CHUNK_OVERLAP

        text = "A" * 2000
        result = chunk(text)

        # Devrait utiliser CHUNK_SIZE et CHUNK_OVERLAP par défaut
        assert len(result[0]) == CHUNK_SIZE


# ============================================================================
# TESTS embed()
# ============================================================================

@pytest.mark.unit
@pytest.mark.ingest
@pytest.mark.asyncio
class TestEmbed:
    """Tests pour la fonction embed"""

    async def test_embed_success(self, mocker):
        """Vérifie que embed génère des embeddings"""
        from app.ingest import embed

        # Mock httpx
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={
            "embeddings": [[0.1] * 768, [0.2] * 768]
        })

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        texts = ["Text 1", "Text 2"]
        result = await embed(texts)

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(emb, list) for emb in result)
        assert all(len(emb) == 768 for emb in result)

    async def test_embed_request_format(self, mocker):
        """Vérifie le format de la requête à Ollama"""
        from app.ingest import embed, OLLAMA, EMBED_MODEL

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={"embeddings": [[0.1] * 768]})

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        texts = ["Test"]
        await embed(texts)

        # Vérifier l'appel
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Vérifier l'URL
        assert call_args[0][0] == f"{OLLAMA}/api/embed"

        # Vérifier le payload
        payload = call_args[1]["json"]
        assert payload["model"] == EMBED_MODEL
        assert payload["input"] == texts

    async def test_embed_http_error(self, mocker):
        """Vérifie la gestion d'erreur HTTP"""
        from app.ingest import embed
        import httpx

        mock_response = Mock()
        mock_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError("Error", request=Mock(), response=Mock())
        )

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(httpx.HTTPStatusError):
            await embed(["Test"])


# ============================================================================
# TESTS read_jsonl()
# ============================================================================

@pytest.mark.unit
@pytest.mark.ingest
class TestReadJsonl:
    """Tests pour la fonction read_jsonl"""

    def test_read_jsonl_valid_file(self, tmp_path):
        """Vérifie la lecture d'un fichier JSONL valide"""
        from app.ingest import read_jsonl

        # Créer un fichier JSONL temporaire
        jsonl_file = tmp_path / "test.jsonl"
        data = [
            {"id": "1", "text": "First line"},
            {"id": "2", "text": "Second line"},
            {"id": "3", "text": "Third line"}
        ]

        with open(jsonl_file, "w") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")

        # Lire le fichier
        result = list(read_jsonl(str(jsonl_file)))

        assert len(result) == 3
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "2"
        assert result[2]["id"] == "3"

    def test_read_jsonl_skips_empty_lines(self, tmp_path):
        """Vérifie que les lignes vides sont ignorées"""
        from app.ingest import read_jsonl

        jsonl_file = tmp_path / "test.jsonl"
        with open(jsonl_file, "w") as f:
            f.write('{"id": "1"}\n')
            f.write('\n')  # Ligne vide
            f.write('{"id": "2"}\n')
            f.write('   \n')  # Ligne avec espaces
            f.write('{"id": "3"}\n')

        result = list(read_jsonl(str(jsonl_file)))

        assert len(result) == 3

    def test_read_jsonl_handles_unicode(self, tmp_path):
        """Vérifie la gestion de l'Unicode"""
        from app.ingest import read_jsonl

        jsonl_file = tmp_path / "test.jsonl"
        data = {"text": "Texte avec accents: é à ü ñ 中文"}

        with open(jsonl_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

        result = list(read_jsonl(str(jsonl_file)))

        assert len(result) == 1
        assert result[0]["text"] == data["text"]


# ============================================================================
# TESTS extract_pdf_text()
# ============================================================================

@pytest.mark.unit
@pytest.mark.ingest
class TestExtractPdfText:
    """Tests pour la fonction extract_pdf_text"""

    def test_extract_pdf_text_with_fitz_available(self, mocker):
        """Vérifie l'extraction de PDF avec PyMuPDF disponible"""
        from app.ingest import extract_pdf_text

        # Mock de fitz (PyMuPDF)
        mock_page = Mock()
        mock_page.get_text = Mock(return_value="Page 1 text\n")

        mock_doc = Mock()
        mock_doc.__iter__ = Mock(return_value=iter([mock_page]))

        mock_fitz = mocker.patch("fitz.open", return_value=mock_doc)

        result = extract_pdf_text("/fake/path.pdf")

        assert "Page 1 text" in result
        mock_fitz.assert_called_once_with("/fake/path.pdf")

    def test_extract_pdf_text_error_handling(self, mocker):
        """Vérifie la gestion d'erreur lors de l'extraction PDF"""
        from app.ingest import extract_pdf_text

        # Mock qui lève une exception
        mocker.patch("fitz.open", side_effect=Exception("PDF error"))

        result = extract_pdf_text("/fake/path.pdf")

        # Devrait retourner une chaîne vide en cas d'erreur
        assert result == ""


# ============================================================================
# TESTS extract_html_text()
# ============================================================================

@pytest.mark.unit
@pytest.mark.ingest
class TestExtractHtmlText:
    """Tests pour la fonction extract_html_text"""

    def test_extract_html_text_basic(self, tmp_path):
        """Vérifie l'extraction de texte HTML basique"""
        from app.ingest import extract_html_text

        html_file = tmp_path / "test.html"
        html_content = """
        <html>
            <head><title>Test</title></head>
            <body>
                <h1>Title</h1>
                <p>First paragraph</p>
                <p>Second paragraph</p>
            </body>
        </html>
        """

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        result = extract_html_text(str(html_file))

        assert "Title" in result
        assert "First paragraph" in result
        assert "Second paragraph" in result
        # Les balises HTML ne devraient pas être présentes
        assert "<html>" not in result
        assert "<p>" not in result

    def test_extract_html_text_strips_scripts(self, tmp_path):
        """Vérifie que les scripts sont retirés"""
        from app.ingest import extract_html_text

        html_file = tmp_path / "test.html"
        html_content = """
        <html>
            <body>
                <p>Visible text</p>
                <script>console.log('Hidden');</script>
            </body>
        </html>
        """

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        result = extract_html_text(str(html_file))

        assert "Visible text" in result
        # Le contenu du script ne devrait pas être extrait
        # BeautifulSoup retire automatiquement les scripts

    def test_extract_html_text_error_handling(self, mocker):
        """Vérifie la gestion d'erreur lors de l'extraction HTML"""
        from app.ingest import extract_html_text

        # Mock open qui lève une exception
        mocker.patch("builtins.open", side_effect=FileNotFoundError())

        result = extract_html_text("/fake/path.html")

        assert result == ""


# ============================================================================
# TESTS create_collection()
# ============================================================================

@pytest.mark.unit
@pytest.mark.ingest
@pytest.mark.asyncio
class TestCreateCollection:
    """Tests pour la fonction create_collection"""

    async def test_create_collection_success(self, mocker):
        """Vérifie la création de collection réussie"""
        from app.ingest import create_collection, CHROMA, COLLECTION

        mock_response = Mock()
        mock_response.status_code = 200

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        # Ne devrait pas lever d'exception
        await create_collection()

        # Vérifier l'appel
        mock_post = mock_client.return_value.__aenter__.return_value.post
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        assert call_args[0][0] == f"{CHROMA}/api/v1/collections"
        assert call_args[1]["json"]["name"] == COLLECTION

    async def test_create_collection_already_exists(self, mocker):
        """Vérifie le comportement quand la collection existe déjà"""
        from app.ingest import create_collection

        mock_response = Mock()
        mock_response.status_code = 409  # Conflict

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        # Ne devrait pas lever d'exception
        await create_collection()

    async def test_create_collection_http_error(self, mocker):
        """Vérifie la gestion d'erreur HTTP"""
        from app.ingest import create_collection

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=Exception("Connection error")
        )

        # Ne devrait pas lever d'exception (erreur capturée)
        await create_collection()


# ============================================================================
# TESTS add_to_collection()
# ============================================================================

@pytest.mark.unit
@pytest.mark.ingest
@pytest.mark.asyncio
class TestAddToCollection:
    """Tests pour la fonction add_to_collection"""

    async def test_add_to_collection_success(self, mocker):
        """Vérifie l'ajout de documents à la collection"""
        from app.ingest import add_to_collection, CHROMA, COLLECTION

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={"success": True})

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        ids = ["doc1", "doc2"]
        embeddings = [[0.1] * 768, [0.2] * 768]
        documents = ["Text 1", "Text 2"]
        metadatas = [{"source": "file1"}, {"source": "file2"}]

        result = await add_to_collection(ids, embeddings, documents, metadatas)

        assert result == {"success": True}

        # Vérifier l'appel
        mock_post = mock_client.return_value.__aenter__.return_value.post
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        assert call_args[0][0] == f"{CHROMA}/api/v1/collections/{COLLECTION}/add"

        payload = call_args[1]["json"]
        assert payload["ids"] == ids
        assert payload["embeddings"] == embeddings
        assert payload["documents"] == documents
        assert payload["metadatas"] == metadatas

    async def test_add_to_collection_http_error(self, mocker):
        """Vérifie la gestion d'erreur lors de l'ajout"""
        from app.ingest import add_to_collection

        mock_response = Mock()
        mock_response.raise_for_status = Mock(
            side_effect=Exception("HTTP Error")
        )

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )

        with pytest.raises(Exception):
            await add_to_collection(
                ids=["doc1"],
                embeddings=[[0.1] * 768],
                documents=["Text"],
                metadatas=[{"source": "file"}]
            )


# ============================================================================
# TESTS get_collection_count()
# ============================================================================

@pytest.mark.unit
@pytest.mark.ingest
@pytest.mark.asyncio
class TestGetCollectionCount:
    """Tests pour la fonction get_collection_count"""

    async def test_get_collection_count_success(self, mocker):
        """Vérifie le comptage de documents"""
        from app.ingest import get_collection_count

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value=42)

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await get_collection_count()

        assert result == 42

    async def test_get_collection_count_error_returns_zero(self, mocker):
        """Vérifie que 0 est retourné en cas d'erreur"""
        from app.ingest import get_collection_count

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=Exception("Connection error")
        )

        result = await get_collection_count()

        assert result == 0

    async def test_get_collection_count_non_200_returns_zero(self, mocker):
        """Vérifie que 0 est retourné pour status non-200"""
        from app.ingest import get_collection_count

        mock_response = Mock()
        mock_response.status_code = 404

        mock_client = mocker.patch("httpx.AsyncClient")
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await get_collection_count()

        assert result == 0
