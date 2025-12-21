# ChromaDB - Base de données vectorielle

## Introduction

ChromaDB est une base de données vectorielle open-source conçue pour stocker des embeddings.

## Caractéristiques

- **Simplicité**: API Python intuitive
- **Performance**: Recherche rapide par similarité cosine
- **Persistance**: Stockage sur disque
- **Métadonnées**: Support des filtres sur métadonnées

## Installation

```bash
pip install chromadb
```

## Exemple d'utilisation

```python
import chromadb

client = chromadb.Client()
collection = client.create_collection("documents")

collection.add(
    documents=["Document 1", "Document 2"],
    ids=["id1", "id2"]
)

results = collection.query(
    query_texts=["recherche"],
    n_results=2
)
```

## Architecture

ChromaDB utilise:
- HNSW pour l'indexation vectorielle
- SQLite pour les métadonnées
- Optimisations SIMD pour le calcul de similarité

## Conclusion

ChromaDB est idéal pour les projets RAG de petite à moyenne échelle.
