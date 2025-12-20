# Système d'Ingestion Avancé v2.0

## 📋 Vue d'ensemble

Le nouveau système d'ingestion v2 utilise les meilleures pratiques 2025 pour le parsing de documents et le chunking sémantique dans les pipelines RAG.

## 🚀 Fonctionnalités principales

### 1. Parsing multi-format avec Unstructured.io

**Formats supportés :**
- **Documents** : PDF, DOCX, DOC, TXT, MD, HTML
- **Feuilles de calcul** : XLSX, XLS, CSV
- **Présentations** : PPTX, PPT
- **Données structurées** : JSON, JSONL
- **Images** : PNG, JPG, JPEG (avec OCR automatique)

**Stratégies de parsing :**
- `auto` : Détection automatique (défaut)
- `fast` : Rapide, pour documents simples
- `hi_res` : Haute résolution, extraction optimale
- `ocr_only` : Forcer l'OCR pour images/PDFs scannés

### 2. Chunking sémantique intelligent

**3 stratégies disponibles :**

#### a) Recursive Character Splitting (défaut)
- Respecte la structure naturelle du texte
- Séparateurs : paragraphes > phrases > mots
- Préserve la cohésion sémantique
- Taille configurable (défaut : 1000 caractères, overlap : 200)

#### b) By Title
- Découpe par structure du document (titres, sections)
- Idéal pour documents structurés
- Préserve la hiérarchie

#### c) Markdown Header Splitting
- Spécialisé pour fichiers Markdown
- Découpe par headers (#, ##, ###)
- Métadonnées de headers préservées

### 3. Déduplication automatique

- Hash SHA256 de chaque document
- Vérification avant indexation
- Skip automatique des duplicatas
- Économie de ressources et d'espace

### 4. Métadonnées enrichies

Chaque chunk contient :
```json
{
  "filename": "document.pdf",
  "file_extension": ".pdf",
  "file_size": 524288,
  "created_at": "2025-01-15T10:30:00",
  "modified_at": "2025-01-15T11:00:00",
  "file_path": "/path/to/document.pdf",
  "document_hash": "abc123...",
  "chunk_index": 0,
  "total_chunks": 42,
  "chunk_type": "text",
  "indexed_at": "2025-01-15T11:05:00",
  "ingestion_version": "2.0"
}
```

### 5. Extraction de tables

- Détection automatique des tables dans les documents
- Structure préservée
- Indexation séparée pour recherche optimale

### 6. OCR pour images

- Tesseract OCR intégré
- Support français et anglais
- Extraction de texte depuis images/PDFs scannés

### 7. Pipeline asynchrone optimisé

- Traitement par batches
- Génération d'embeddings parallélisée
- Gestion de progression en temps réel
- Optimisé pour gros volumes

## 🔧 Configuration

Variables d'environnement :

```bash
# Chunking
CHUNK_SIZE=1000                    # Taille des chunks (caractères)
CHUNK_OVERLAP=200                  # Chevauchement entre chunks
CHUNKING_STRATEGY=semantic         # 'semantic', 'recursive', 'by_title'

# Chemins
DATASETS_DIR=/app/datasets         # Dossier source pour ingestion batch
CHROMA_PATH=/chroma/chroma        # Stockage ChromaDB
```

## 📡 API Endpoints

### POST /upload/v2

Nouvel endpoint d'upload avancé.

**Paramètres :**
- `file` (FormData) : Fichier à uploader
- `parsing_strategy` (query, optionnel) : 'auto', 'fast', 'hi_res', 'ocr_only'
- `skip_duplicates` (query, optionnel) : true/false (défaut: true)
- `X-API-Key` (header) : Clé API

**Exemple avec curl :**
```bash
curl -X POST http://localhost:8080/upload/v2 \
  -H "X-API-Key: change-me-in-production" \
  -F "file=@document.pdf"
```

**Exemple avec parsing haute résolution :**
```bash
curl -X POST "http://localhost:8080/upload/v2?parsing_strategy=hi_res" \
  -H "X-API-Key: change-me-in-production" \
  -F "file=@complex_document.pdf"
```

**Réponse :**
```json
{
  "success": true,
  "filename": "document.pdf",
  "chunks_indexed": 42,
  "message": "Fichier 'document.pdf' indexé avec succès (42 chunks, 3 tables détectées)"
}
```

### POST /upload (legacy)

Ancien endpoint maintenu pour compatibilité ascendante.
Utilise le système d'ingestion simple (ingest.py).

## 🔄 Migration depuis v1

Les deux systèmes coexistent :
- `/upload` utilise l'ancien système (ingest.py)
- `/upload/v2` utilise le nouveau système (ingest_v2.py)

Le frontend utilise maintenant `/upload/v2` par défaut.

## 🛠️ Utilisation en ligne de commande

### Ingestion d'un dossier complet

```bash
docker compose run --rm app python ingest_v2.py
```

Cela ingère tous les documents du dossier `/app/datasets` (défini par `DATASETS_DIR`).

### Ingestion programmée

Créer un workflow N8N ou un cron job pour ingestion régulière :

```bash
# Tous les jours à 2h du matin
0 2 * * * docker compose run --rm app python ingest_v2.py
```

## 📊 Comparaison v1 vs v2

| Fonctionnalité | v1 (ingest.py) | v2 (ingest_v2.py) |
|----------------|----------------|-------------------|
| **Formats** | PDF, TXT, MD, HTML, JSONL | + DOCX, XLSX, PPTX, Images |
| **Chunking** | Fixe (900 chars) | Sémantique intelligent |
| **Parsing** | PyMuPDF, BeautifulSoup | Unstructured.io |
| **OCR** | ❌ | ✅ Tesseract |
| **Tables** | ❌ | ✅ Extraction dédiée |
| **Déduplication** | ❌ | ✅ Hash SHA256 |
| **Métadonnées** | Basiques | Enrichies |
| **Versioning** | ❌ | ✅ Hash + timestamps |
| **Performance** | Bonne | Excellente (async) |

## 🎯 Best Practices

### 1. Choix de la stratégie de chunking

- **Documents structurés** (rapports, documentation) → `by_title`
- **Documents Markdown** → `markdown`
- **Documents variés** → `semantic` (défaut)

### 2. Choix de la stratégie de parsing

- **Documents standards** → `auto` (défaut)
- **Performances prioritaires** → `fast`
- **Qualité maximale** → `hi_res`
- **PDFs scannés/images** → `ocr_only`

### 3. Optimisation des performances

```python
# Variables d'environnement
CHUNK_SIZE=800           # Chunks plus petits = recherche plus précise
CHUNK_OVERLAP=150        # Overlap minimal pour performance
```

### 4. Déduplication

Toujours activé par défaut. Désactiver uniquement si :
- Réindexation forcée nécessaire
- Tests et développement

## 🔍 Debugging

Logs détaillés disponibles :

```bash
# Voir les logs du service app
docker compose logs -f app

# Filtrer pour ingestion seulement
docker compose logs -f app | grep -E "(Parsing|Ingestion|chunks)"
```

Niveau de log configurable :
```bash
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

## 🚧 Limitations connues

1. **Taille maximale** : Fichiers > 100MB peuvent être lents
2. **OCR** : Qualité dépend de la qualité de l'image source
3. **Tables complexes** : Tableaux très imbriqués peuvent perdre structure
4. **Langues OCR** : Français et anglais uniquement (configurable)

## 📚 Références

- [Unstructured.io Documentation](https://unstructured-io.github.io/unstructured/)
- [LangChain Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_transformers/)
- [Best Chunking Strategies for RAG 2025](https://www.firecrawl.dev/blog/best-chunking-strategies-rag-2025)
- [ChromaDB Documentation](https://docs.trychroma.com/)

## 🤝 Contribution

Pour améliorer le système d'ingestion :

1. Tester de nouveaux formats
2. Ajuster les paramètres de chunking
3. Reporter les bugs via GitHub Issues
4. Proposer de nouvelles fonctionnalités

---

**Version** : 2.0.0
**Date** : Décembre 2025
**Auteur** : MY-IA Team
