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

async def embed(texts: List[str]) -> List[List[float]]:
    """Génère les embeddings via Ollama"""
    async with httpx.AsyncClient(timeout=600) as s:
        r = await s.post(f"{OLLAMA}/api/embed", json={"model": EMBED_MODEL, "input": texts})
        r.raise_for_status()
        return r.json()["embeddings"]

async def embed_with_progress(texts: List[str], batch_size: int = 100, progress_callback=None):
    """Génère les embeddings par batches avec callback de progression"""
    all_embeddings = []
    total = len(texts)

    for i in range(0, total, batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = await embed(batch)
        all_embeddings.extend(batch_embeddings)

        if progress_callback:
            await progress_callback(min(i + batch_size, total), total)

    return all_embeddings

def read_jsonl(path: str):
    """Lit un fichier JSONL ligne par ligne"""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def extract_pdf_text(path: str) -> str:
    """Extrait le texte d'un PDF"""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"❌ Erreur PDF {path}: {e}")
        return ""

def extract_html_text(path: str) -> str:
    """Extrait le texte d'un HTML"""
    try:
        from bs4 import BeautifulSoup
        with open(path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
            return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        print(f"❌ Erreur HTML {path}: {e}")
        return ""

async def create_collection():
    """Créer la collection via l'API v1"""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                f"{CHROMA}/api/v1/collections",
                json={"name": COLLECTION}
            )
            if response.status_code == 200:
                print(f"✅ Collection '{COLLECTION}' créée")
            elif response.status_code == 409:
                print(f"ℹ️  Collection '{COLLECTION}' existe déjà")
            else:
                print(f"⚠️  Status: {response.status_code}")
        except Exception as e:
            print(f"❌ Erreur création collection: {e}")

async def add_to_collection(ids: List[str], embeddings: List[List[float]], documents: List[str], metadatas: List[dict]):
    """Ajouter des documents à la collection via l'API v1"""
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            response = await client.post(
                f"{CHROMA}/api/v1/collections/{COLLECTION}/add",
                json={
                    "ids": ids,
                    "embeddings": embeddings,
                    "documents": documents,
                    "metadatas": metadatas
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Erreur ajout documents: {e}")
            raise

async def get_collection_count():
    """Compter les documents dans la collection via l'API v1"""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(
                f"{CHROMA}/api/v1/collections/{COLLECTION}/count"
            )
            if response.status_code == 200:
                return response.json()
            return 0
        except:
            return 0

async def main():
    docs_dir = "/app/datasets"
    buffer_texts, buffer_ids, buffer_meta = [], [], []

    print("🔍 Recherche de documents...")

    # Créer la collection
    await create_collection()

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

    # Ingestion PDF
    for fp in glob.glob(os.path.join(docs_dir, "**/*.pdf"), recursive=True):
        print(f"📕 Processing PDF: {fp}")
        text = extract_pdf_text(fp)
        if text.strip():
            for j, ch in enumerate(chunk(text)):
                buffer_texts.append(ch)
                buffer_ids.append(f"{os.path.basename(fp)}-{j}")
                buffer_meta.append({"source": os.path.basename(fp)})

    # Ingestion HTML
    for fp in glob.glob(os.path.join(docs_dir, "**/*.html"), recursive=True):
        print(f"🌐 Processing HTML: {fp}")
        text = extract_html_text(fp)
        if text.strip():
            for j, ch in enumerate(chunk(text)):
                buffer_texts.append(ch)
                buffer_ids.append(f"{os.path.basename(fp)}-{j}")
                buffer_meta.append({"source": os.path.basename(fp)})

    if not buffer_texts:
        print("⚠️  Aucun document à indexer!")
        return

    print(f"\n📊 Total chunks à indexer: {len(buffer_texts)}")

    # Embeddings par batch
    BATCH = 64
    for i in range(0, len(buffer_texts), BATCH):
        batch = buffer_texts[i:i+BATCH]
        batch_num = i//BATCH + 1
        total_batches = (len(buffer_texts)-1)//BATCH + 1
        print(f"⚙️  Batch {batch_num}/{total_batches} - Generating embeddings...")

        vecs = await embed(batch)
        await add_to_collection(
            ids=buffer_ids[i:i+BATCH],
            embeddings=vecs,
            documents=batch,
            metadatas=buffer_meta[i:i+BATCH]
        )

    count = await get_collection_count()
    print(f"\n✅ Indexed {len(buffer_texts)} chunks in collection '{COLLECTION}'")
    print(f"📚 Total documents in database: {count}")

if __name__ == "__main__":
    asyncio.run(main())
