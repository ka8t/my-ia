import os, json, glob
import httpx
from typing import List
import asyncio

OLLAMA = os.getenv("OLLAMA_HOST", "http://localhost:11434")
CHROMA = os.getenv("CHROMA_HOST", "http://localhost:8000")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
COLLECTION = "knowledge_base"

CHUNK_SIZE = 900
CHUNK_OVERLAP = 150

def chunk(text: str, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Découpe le texte en chunks avec overlap"""
    spans = []
    i = 0
    while i < len(text):
        spans.append(text[i:i+size])
        i += size - overlap
    return spans

async def get_embedding(text: str) -> List[float]:
    """Génère un embedding via Ollama"""
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{OLLAMA}/api/embeddings",
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
    buffer_texts, buffer_ids, buffer_meta = [], [], []

    print("🔍 Recherche de documents...")

    # Ingestion JSONL
    for fp in glob.glob(os.path.join(docs_dir, "**/*.jsonl"), recursive=True):
        print(f"📄 Processing JSONL: {fp}")
        for row in read_jsonl(fp):
            text = row.get("text") or row.get("content") or ""
            if not text.strip():
                continue
            for j, ch in enumerate(chunk(text)):
                buffer_texts.append(ch)
                buffer_ids.append(f"{row.get('id', os.path.basename(fp))}-{j}")
                buffer_meta.append({
                    "source": row.get("metadata", {}).get("source", os.path.basename(fp)),
                    "tags": ",".join(row.get("metadata", {}).get("tags", []))
                })

    # Ingestion fichiers texte/markdown
    for ext in ("*.md", "*.txt"):
        for fp in glob.glob(os.path.join(docs_dir, "**/" + ext), recursive=True):
            print(f"📝 Processing {ext.upper()}: {fp}")
            with open(fp, "r", encoding="utf-8") as f:
                text = f.read()
            for j, ch in enumerate(chunk(text)):
                buffer_texts.append(ch)
                buffer_ids.append(f"{os.path.basename(fp)}-{j}")
                buffer_meta.append({"source": os.path.basename(fp)})

    if not buffer_texts:
        print("⚠️  Aucun document à indexer!")
        return

    print(f"\n📊 Total chunks à indexer: {len(buffer_texts)}")

    # Créer la collection via HTTP simple
    print("\n✅ Création de la collection...")
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(f"{CHROMA}/api/v1/collections/{COLLECTION}")
            if response.status_code == 200:
                print(f"ℹ️  Collection '{COLLECTION}' existe déjà")
            else:
                # Créer la collection
                response = await client.post(
                    f"{CHROMA}/api/v1/collections",
                    json={"name": COLLECTION, "metadata": {}}
                )
                if response.status_code in [200, 201]:
                    print(f"✅ Collection '{COLLECTION}' créée")
                else:
                    print(f"⚠️  Status création: {response.status_code}")
        except Exception as e:
            print(f"ℹ️  Info collection: {e}")

    # Générer embeddings et ajouter par batch
    BATCH = 16
    for i in range(0, len(buffer_texts), BATCH):
        batch = buffer_texts[i:i+BATCH]
        batch_ids = buffer_ids[i:i+BATCH]
        batch_meta = buffer_meta[i:i+BATCH]

        batch_num = i//BATCH + 1
        total_batches = (len(buffer_texts)-1)//BATCH + 1
        print(f"⚙️  Batch {batch_num}/{total_batches} - Generating embeddings...")

        # Générer embeddings un par un (plus lent mais plus stable)
        vecs = []
        for text in batch:
            vec = await get_embedding(text)
            vecs.append(vec)

        # Ajouter à ChromaDB via upsert HTTP
        print(f"   Adding {len(batch)} chunks to ChromaDB...")
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                response = await client.post(
                    f"{CHROMA}/api/v1/collections/{COLLECTION}/upsert",
                    json={
                        "ids": batch_ids,
                        "embeddings": vecs,
                        "documents": batch,
                        "metadatas": batch_meta
                    }
                )
                if response.status_code in [200, 201]:
                    print(f"   ✅ Batch {batch_num} ajouté")
                else:
                    print(f"   ⚠️  Batch {batch_num} status: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"   ❌ Erreur batch {batch_num}: {e}")

    # Compter les documents
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(f"{CHROMA}/api/v1/collections/{COLLECTION}/count")
            if response.status_code == 200:
                count = response.json()
                print(f"\n✅ Indexed {len(buffer_texts)} chunks in collection '{COLLECTION}'")
                print(f"📚 Total documents in database: {count}")
        except:
            print(f"\n✅ Indexed {len(buffer_texts)} chunks in collection '{COLLECTION}'")

if __name__ == "__main__":
    asyncio.run(main())
