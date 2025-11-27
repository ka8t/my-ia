#!/usr/bin/env python3
"""
Script d'ingestion pour ChromaDB utilisant uniquement l'API HTTP v2
"""
import os
import json
import glob
import asyncio
import httpx
from typing import List, Dict, Any

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

async def create_collection(client: httpx.AsyncClient, name: str) -> bool:
    """Crée une collection dans ChromaDB via API v2"""
    try:
        # Essayer de créer la collection
        response = await client.post(
            f"{CHROMA_HOST}/api/v2/collections",
            json={
                "name": name,
                "metadata": {"description": "Knowledge base for MY-IA RAG system"}
            }
        )
        if response.status_code == 200:
            print(f"✅ Collection '{name}' créée")
            return True
        elif response.status_code == 409:
            # Collection existe déjà
            print(f"ℹ️  Collection '{name}' existe déjà")
            # Supprimer et recréer
            print("⚠️  Suppression de l'ancienne collection...")
            await client.delete(f"{CHROMA_HOST}/api/v2/collections/{name}")
            response = await client.post(
                f"{CHROMA_HOST}/api/v2/collections",
                json={
                    "name": name,
                    "metadata": {"description": "Knowledge base for MY-IA RAG system"}
                }
            )
            print(f"✅ Collection '{name}' recréée")
            return True
        else:
            print(f"❌ Erreur création collection: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception création collection: {e}")
        return False

async def add_documents(
    client: httpx.AsyncClient,
    collection_name: str,
    ids: List[str],
    documents: List[str],
    embeddings: List[List[float]],
    metadatas: List[Dict[str, Any]]
) -> bool:
    """Ajoute des documents à une collection via API v2"""
    try:
        response = await client.post(
            f"{CHROMA_HOST}/api/v2/collections/{collection_name}/add",
            json={
                "ids": ids,
                "documents": documents,
                "embeddings": embeddings,
                "metadatas": metadatas
            }
        )
        if response.status_code == 200:
            return True
        else:
            print(f"❌ Erreur ajout documents: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception ajout documents: {e}")
        return False

async def get_collection_count(client: httpx.AsyncClient, collection_name: str) -> int:
    """Récupère le nombre de documents dans une collection"""
    try:
        response = await client.get(f"{CHROMA_HOST}/api/v2/collections/{collection_name}")
        if response.status_code == 200:
            data = response.json()
            return data.get("count", 0)
        return 0
    except:
        return 0

async def main():
    docs_dir = "/app/datasets"

    print("🔍 Connexion à ChromaDB...")

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Vérifier la santé de ChromaDB
        try:
            response = await client.get(f"{CHROMA_HOST}/api/v1/heartbeat")
            if response.status_code == 200:
                print("✅ ChromaDB est accessible")
            else:
                print(f"⚠️  ChromaDB heartbeat: {response.status_code}")
        except Exception as e:
            print(f"❌ ChromaDB non accessible: {e}")
            return

        # Créer la collection
        if not await create_collection(client, COLLECTION_NAME):
            print("❌ Impossible de créer la collection")
            return

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
            if await add_documents(client, COLLECTION_NAME, batch_ids, batch_texts, embeddings, batch_meta):
                print(f"   ✅ Batch {batch_num} ajouté")
            else:
                print(f"   ❌ Échec ajout Batch {batch_num}")

        # Vérifier le nombre total de documents
        final_count = await get_collection_count(client, COLLECTION_NAME)
        print(f"\n✅ Ingestion terminée!")
        print(f"📚 Total documents dans la collection: {final_count}")

        # Test de recherche
        print("\n🔍 Test de recherche...")
        test_query = "bonjour"
        print(f"   Query: '{test_query}'")

        test_embedding = await get_embedding(test_query)

        try:
            response = await client.post(
                f"{CHROMA_HOST}/api/v2/collections/{COLLECTION_NAME}/query",
                json={
                    "query_embeddings": [test_embedding],
                    "n_results": 3
                }
            )
            if response.status_code == 200:
                results = response.json()
                docs = results.get("documents", [[]])[0]
                print(f"   Résultats trouvés: {len(docs)}")
                if docs:
                    print(f"   Premier résultat: {docs[0][:100]}...")
            else:
                print(f"   ❌ Erreur recherche: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"   ❌ Exception recherche: {e}")

if __name__ == "__main__":
    asyncio.run(main())
