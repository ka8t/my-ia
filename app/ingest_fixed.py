#!/usr/bin/env python3
"""
Script d'ingestion optimisé pour ChromaDB
Utilise le client Python officiel au lieu de l'API HTTP
"""
import os
import json
import glob
import asyncio
import httpx
from typing import List
import chromadb
from chromadb.config import Settings

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
CHROMA_HOST = os.getenv("CHROMA_HOST", "http://localhost:8000")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
COLLECTION_NAME = "knowledge_base"

CHUNK_SIZE = 900
CHUNK_OVERLAP = 150

def chunk_text(text: str, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP) -> List[str]:
    """Découpe le texte en chunks avec overlap"""
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+size])
        i += size - overlap
    return chunks

async def get_embedding(text: str) -> List[float]:
    """Génère un embedding via Ollama"""
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{OLLAMA_HOST}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text}
        )
        response.raise_for_status()
        return response.json()["embedding"]

def read_jsonl(path: str):
    """Lit un fichier JSONL ligne par ligne"""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

async def main():
    docs_dir = "/app/datasets"

    print("🔍 Connexion à ChromaDB...")

    # Connexion au serveur ChromaDB distant
    client = chromadb.HttpClient(
        host="chroma",  # Nom du service dans docker-compose
        port=8000,
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )

    print(f"✅ Connecté à ChromaDB")

    # Créer ou récupérer la collection
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
        print(f"ℹ️  Collection '{COLLECTION_NAME}' existe déjà ({collection.count()} documents)")

        # Demander si on veut réinitialiser
        print("⚠️  Suppression de l'ancienne collection pour recommencer...")
        client.delete_collection(name=COLLECTION_NAME)
        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Knowledge base for MY-IA RAG system"}
        )
        print(f"✅ Collection '{COLLECTION_NAME}' recréée")
    except:
        collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Knowledge base for MY-IA RAG system"}
        )
        print(f"✅ Collection '{COLLECTION_NAME}' créée")

    # Buffer pour les documents à indexer
    all_texts = []
    all_ids = []
    all_metadata = []

    print("\n🔍 Recherche de documents...")

    # Ingestion JSONL
    for fp in glob.glob(os.path.join(docs_dir, "**/*.jsonl"), recursive=True):
        print(f"📄 Processing JSONL: {fp}")
        for row in read_jsonl(fp):
            text = row.get("text") or row.get("content") or ""
            if not text.strip():
                continue

            for j, ch in enumerate(chunk_text(text)):
                all_texts.append(ch)
                all_ids.append(f"{row.get('id', os.path.basename(fp))}-{j}")
                all_metadata.append({
                    "source": row.get("metadata", {}).get("source", os.path.basename(fp)),
                    "tags": ",".join(row.get("metadata", {}).get("tags", []))
                })

    # Ingestion fichiers texte/markdown
    for ext in ("*.md", "*.txt"):
        for fp in glob.glob(os.path.join(docs_dir, "**/" + ext), recursive=True):
            print(f"📝 Processing {ext.upper()}: {fp}")
            with open(fp, "r", encoding="utf-8") as f:
                text = f.read()

            for j, ch in enumerate(chunk_text(text)):
                all_texts.append(ch)
                all_ids.append(f"{os.path.basename(fp)}-{j}")
                all_metadata.append({"source": os.path.basename(fp)})

    if not all_texts:
        print("⚠️  Aucun document à indexer!")
        return

    print(f"\n📊 Total chunks à indexer: {len(all_texts)}")

    # Générer les embeddings par batch
    BATCH_SIZE = 16
    total_batches = (len(all_texts) - 1) // BATCH_SIZE + 1

    for i in range(0, len(all_texts), BATCH_SIZE):
        batch_texts = all_texts[i:i+BATCH_SIZE]
        batch_ids = all_ids[i:i+BATCH_SIZE]
        batch_meta = all_metadata[i:i+BATCH_SIZE]

        batch_num = i // BATCH_SIZE + 1
        print(f"\n⚙️  Batch {batch_num}/{total_batches} - Generating embeddings...")

        # Générer embeddings
        embeddings = []
        for text in batch_texts:
            emb = await get_embedding(text)
            embeddings.append(emb)

        print(f"   Adding {len(batch_texts)} chunks to ChromaDB...")

        # Ajouter à la collection
        collection.add(
            ids=batch_ids,
            embeddings=embeddings,
            documents=batch_texts,
            metadatas=batch_meta
        )

        print(f"   ✅ Batch {batch_num} ajouté")

    # Vérifier le nombre total de documents
    final_count = collection.count()
    print(f"\n✅ Ingestion terminée!")
    print(f"📚 Total documents dans la collection: {final_count}")

    # Test de recherche
    print("\n🔍 Test de recherche...")
    test_query = "bonjour"
    print(f"   Query: '{test_query}'")

    test_embedding = await get_embedding(test_query)
    results = collection.query(
        query_embeddings=[test_embedding],
        n_results=3
    )

    print(f"   Résultats trouvés: {len(results['documents'][0])}")
    if results['documents'][0]:
        print(f"   Premier résultat: {results['documents'][0][0][:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
