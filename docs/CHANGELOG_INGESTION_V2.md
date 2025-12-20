# Changelog - Système d'Ingestion v2.0

## 📅 Date : Décembre 2025

## 🎯 Objectif
Modernisation complète du système d'ingestion de documents avec les meilleures pratiques RAG 2025.

---

## ✨ Nouvelles fonctionnalités

### 1. Parsing multi-format avancé (Unstructured.io)

**Avant (v1) :**
- ✅ PDF (PyMuPDF)
- ✅ TXT, MD
- ✅ HTML (BeautifulSoup)
- ✅ JSONL

**Après (v2) :**
- ✅ PDF (Unstructured avec extraction améliorée)
- ✅ TXT, MD (parsing optimisé)
- ✅ HTML (conservation de structure)
- ✅ JSONL, JSON
- 🆕 **DOCX, DOC** (Microsoft Word)
- 🆕 **XLSX, XLS** (Excel)
- 🆕 **PPTX, PPT** (PowerPoint)
- 🆕 **CSV** (données tabulaires)
- 🆕 **PNG, JPG, JPEG** (OCR automatique)

### 2. Chunking sémantique intelligent

**Avant (v1) :**
```python
chunk_size = 900  # Fixe
chunk_overlap = 150  # Fixe
# Découpage brutal par caractère
```

**Après (v2) :**
```python
# 3 stratégies disponibles :
1. RecursiveCharacterTextSplitter
   - Respecte paragraphes > phrases > mots
   - Préserve la cohésion sémantique

2. ChunkByTitle
   - Découpe par structure (titres, sections)
   - Idéal pour documents structurés

3. MarkdownHeaderSplitter
   - Spécialisé Markdown
   - Préservation des headers
```

### 3. Déduplication automatique

**Nouveau :**
- Hash SHA256 de chaque document
- Vérification avant indexation
- Skip automatique des doublons
- Économie de ressources

**Bénéfices :**
- Pas de réindexation inutile
- Base de données optimisée
- Coûts d'embedding réduits

### 4. Métadonnées enrichies

**Avant (v1) :**
```json
{
  "source": "document.pdf"
}
```

**Après (v2) :**
```json
{
  "filename": "document.pdf",
  "file_extension": ".pdf",
  "file_size": 524288,
  "created_at": "2025-01-15T10:30:00",
  "modified_at": "2025-01-15T11:00:00",
  "file_path": "/path/to/document.pdf",
  "document_hash": "abc123def456...",
  "chunk_index": 0,
  "total_chunks": 42,
  "chunk_type": "text",
  "indexed_at": "2025-01-15T11:05:00",
  "ingestion_version": "2.0"
}
```

### 5. Extraction de tables

**Nouveau :**
- Détection automatique des tables
- Structure préservée
- Indexation séparée pour recherche optimale
- Compteur de tables dans les réponses

### 6. Support OCR

**Nouveau :**
- Tesseract OCR intégré
- Support français et anglais
- Extraction de texte depuis :
  - Images (PNG, JPG, JPEG)
  - PDFs scannés
  - Documents photographiés

### 7. Pipeline asynchrone optimisé

**Améliorations :**
- Traitement par batches configurable
- Génération d'embeddings parallélisée
- Gestion de progression en temps réel
- Meilleure gestion des erreurs
- Logs structurés

---

## 🔧 Modifications techniques

### Fichiers modifiés

1. **app/requirements.txt**
   - `+ unstructured[all-docs]==0.15.13`
   - `+ langchain==0.3.7`
   - `+ langchain-text-splitters==0.3.2`
   - `+ langchain-community==0.3.5`
   - `+ python-magic==0.4.27`
   - `+ python-docx==1.1.2`
   - `+ openpyxl==3.1.5`
   - `+ Pillow==10.4.0`
   - `+ pytesseract==0.3.13`
   - `+ pdf2image==1.17.0`
   - `+ markdown==3.7`

2. **app/Dockerfile**
   ```dockerfile
   # Nouvelles dépendances système :
   - tesseract-ocr
   - tesseract-ocr-fra
   - tesseract-ocr-eng
   - poppler-utils
   - libmagic1
   - libgl1
   - libglib2.0-0
   - pandoc
   - libjpeg-dev
   - libpng-dev
   - gcc, g++
   ```

3. **app/ingest_v2.py** (NOUVEAU)
   - 580 lignes de code
   - 6 classes principales :
     - `DocumentParser` : Parsing avec Unstructured
     - `SemanticChunker` : Chunking intelligent
     - `DocumentDeduplicator` : Gestion duplicatas
     - `MetadataExtractor` : Enrichissement métadonnées
     - `EmbeddingGenerator` : Génération async
     - `AdvancedIngestionPipeline` : Orchestration

4. **app/main.py**
   - Import de `AdvancedIngestionPipeline`
   - Nouveau endpoint `POST /upload/v2`
   - Ancien endpoint `/upload` conservé pour compatibilité

5. **frontend/index.html**
   - Ajout des nouveaux formats acceptés
   - Message informatif mis à jour

6. **frontend/js/app.js**
   - Fonction `uploadFile()` utilise `/upload/v2`
   - Extensions autorisées étendues

7. **docs/INGESTION_V2.md** (NOUVEAU)
   - Documentation complète
   - Exemples d'utilisation
   - Best practices
   - Comparaison v1 vs v2

---

## 🚀 Nouvelles API

### POST /upload/v2

**Endpoint avancé avec toutes les nouvelles fonctionnalités**

**Paramètres :**
```
- file (FormData) : Fichier à uploader
- parsing_strategy (query) : 'auto', 'fast', 'hi_res', 'ocr_only'
- skip_duplicates (query) : true/false
- X-API-Key (header) : Authentification
```

**Exemple curl :**
```bash
curl -X POST "http://localhost:8080/upload/v2?parsing_strategy=hi_res" \
  -H "X-API-Key: change-me-in-production" \
  -F "file=@document.pdf"
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

---

## 📊 Comparaison Performance

| Métrique | v1 | v2 | Amélioration |
|----------|----|----|--------------|
| **Formats supportés** | 5 | 13 | +160% |
| **Qualité chunking** | Basique | Sémantique | ++++ |
| **Métadonnées** | 1 champ | 11 champs | +1000% |
| **OCR** | Non | Oui | ✅ |
| **Tables** | Non | Oui | ✅ |
| **Déduplication** | Non | Oui | ✅ |
| **Async** | Partiel | Complet | ++ |

---

## 🔄 Migration

### Compatibilité ascendante

Les deux systèmes coexistent :
- `/upload` → ancien système (ingest.py)
- `/upload/v2` → nouveau système (ingest_v2.py)

### Recommandations

1. **Nouveaux projets** : Utiliser exclusivement `/upload/v2`
2. **Projets existants** : Migration progressive
3. **Tests** : Les deux endpoints disponibles

### Checklist de migration

- [ ] Tester `/upload/v2` avec documents de production
- [ ] Vérifier qualité de chunking
- [ ] Comparer résultats RAG
- [ ] Mesurer performances
- [ ] Basculer frontend vers v2 (déjà fait)
- [ ] Réindexer base existante (optionnel)

---

## 🐛 Problèmes connus et solutions

### Build Docker long
**Cause** : Nombreuses dépendances système + Python
**Solution** : Première fois seulement, builds suivants en cache

### OCR lent sur grosses images
**Cause** : Tesseract OCR
**Solution** : Utiliser `parsing_strategy=fast` si OCR non nécessaire

### Erreur "libGL.so.1"
**Cause** : Dépendance système manquante
**Solution** : Déjà incluse dans Dockerfile (libgl1)

---

## 📈 Prochaines étapes

### v2.1 (court terme)
- [ ] Support de plus de langues OCR
- [ ] Chunking par similarité sémantique
- [ ] Compression des embeddings

### v2.2 (moyen terme)
- [ ] Support vidéo (extraction transcription)
- [ ] Support audio (Whisper)
- [ ] Extraction d'entités nommées

### v3.0 (long terme)
- [ ] RAG hybride (dense + sparse)
- [ ] Reranking automatique
- [ ] Fine-tuning des embeddings

---

## 🙏 Crédits

**Technologies utilisées :**
- [Unstructured.io](https://unstructured.io) - Document parsing
- [LangChain](https://langchain.com) - Semantic chunking
- [Tesseract](https://github.com/tesseract-ocr/tesseract) - OCR
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [Ollama](https://ollama.ai/) - Local LLM & embeddings

**Références :**
- [Best Chunking Strategies for RAG 2025](https://www.firecrawl.dev/blog/best-chunking-strategies-rag-2025)
- [Unstructured RAG Best Practices](https://unstructured.io/blog/unstructured-s-preprocessing-pipelines-enable-enhanced-rag-performance)
- [LangChain Text Splitters Guide](https://python.langchain.com/docs/modules/data_connection/document_transformers/)

---

**Version** : 2.0.0
**Date de release** : Décembre 2025
**Mainteneur** : MY-IA Team
