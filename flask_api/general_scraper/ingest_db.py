"""
Re-embeds LLM-extracted JSON chunks with Gemini 'gemini-embedding-001'
at 768 dimensions (fits Atlas Search), then uploads to MongoDB.

Setup:
  - pip install requests pymongo python-dotenv tqdm
  - export GEMINI_API_KEY="..."
"""

import os, json, glob, hashlib, time, requests
from typing import List, Dict
from dotenv import load_dotenv
import pymongo
from pymongo.errors import BulkWriteError
from tqdm import tqdm

# ==============================================================
# CONFIG
# Gemini Developer API (x-goog-api-key header, not Bearer)
GEMINI_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-embedding-001:embedContent"
)

EMBED_DIM = 768  # <= Atlas UI limit; recommended in Gemini docs
BATCH_SIZE = 32

BM25_FIELDS = ["text", "contextual_summary", "section_title", "page_title"]
SKIP_CONTENT_TYPES = {"general_info"}

# ==============================================================

def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()

def iter_json_files(input_dir: str):
    for p in glob.glob(os.path.join(input_dir, "*.json")):
        yield p

def load_chunks(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    url         = data.get("url")
    filename    = data.get("filename") or os.path.basename(url or path)
    scraped_at  = data.get("scraped_at")
    source_type = data.get("source_type", "unknown")

    out = []
    for ch in data.get("chunks", []):
        ctype = (ch.get("content_type") or "general_info").strip().lower()
        if ctype in SKIP_CONTENT_TYPES:
            continue

        title   = (ch.get("section_title") or "").strip()
        summary = (ch.get("contextual_summary") or "").strip()
        text    = (ch.get("text") or "").strip()
        if not text and not summary:
            continue

        combined = f"{title}\n{summary}\n{text}".strip()

        # ✅ NEW: carry page info through
        page_numbers = ch.get("page_numbers")
        page_number  = ch.get("page_number")  # some extractors use singular
        if page_numbers is None and page_number is not None:
            page_numbers = [page_number]

        out.append({
            "combined_text": combined,
            "section_title": title,
            "contextual_summary": summary,
            "text": text,
            "content_type": ctype,
            "page_title": data.get("page_title"),
            "url": url,
            "filename": filename,
            "scraped_at": scraped_at,
            "source_type": source_type,
            # ✅ include page fields
            "page_numbers": page_numbers,
            "page_start": min(page_numbers) if isinstance(page_numbers, list) and page_numbers else None,
            "page_end":   max(page_numbers) if isinstance(page_numbers, list) and page_numbers else None,
        })
    return out


# ==============================================================
# Gemini Embedding (768-dim)
# ==============================================================

def gemini_embed_batch(texts: List[str], api_key: str) -> List[List[float]]:
    """
    One request per text (simple & robust).
    Uses output_dimensionality=EMBED_DIM so vectors fit Atlas.
    """
    vectors: List[List[float]] = []
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }

    for t in tqdm(texts, desc="Embedding", unit="chunk"):
        payload = {
            "model": "models/gemini-embedding-001",
            "content": {"parts": [{"text": t}]},
            # Let Gemini produce exactly EMBED_DIM dims (MRL downsizing)
            "output_dimensionality": EMBED_DIM,
            # (Optional but good practice) tell the model this is a document vector:
            "task_type": "RETRIEVAL_DOCUMENT"
        }

        pause = 1.0
        for attempt in range(4):
            try:
                r = requests.post(GEMINI_EMBED_URL, headers=headers, json=payload, timeout=60)
                if r.status_code == 200:
                    data = r.json()
                    vec = data["embedding"]["values"]
                    # Defensive check
                    if len(vec) != EMBED_DIM:
                        print(f"[WARN] Got {len(vec)} dims, expected {EMBED_DIM}. Padding/truncating.")
                        vec = (vec + [0.0]*EMBED_DIM)[:EMBED_DIM]
                    vectors.append(vec)
                    break
                elif r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(pause); pause = min(pause * 2, 8)
                else:
                    print(f"[WARN] Gemini HTTP {r.status_code}: {r.text[:200]}")
                    vectors.append([0.0] * EMBED_DIM)
                    break
            except Exception as e:
                print(f"[ERROR] Gemini embed error: {e}")
                time.sleep(pause); pause = min(pause * 2, 8)
        else:
            vectors.append([0.0] * EMBED_DIM)

    return vectors

# ==============================================================
# Mongo Upload
# ==============================================================

def ingest_dir(input_dir: str, mongodb_uri: str, db_name: str, collection_name: str, city: str,
               gemini_api_key: str, drop_if_exists=False):
    client = pymongo.MongoClient(mongodb_uri)
    db = client[db_name]
    if drop_if_exists and collection_name in db.list_collection_names():
        db[collection_name].drop()
        print(f"[INFO] Dropped {db_name}.{collection_name}")
    col = db[collection_name]

    # Helpful indexes
    col.create_index([("chunk_hash", pymongo.ASCENDING)], unique=True, name="uniq_chunk_hash")
    col.create_index([("city", pymongo.ASCENDING)], name="idx_city")
    col.create_index([("url", pymongo.ASCENDING)], name="idx_url")
    col.create_index([("content_type", pymongo.ASCENDING)], name="idx_type")

    files = list(iter_json_files(input_dir))
    print(f"[INFO] Found {len(files)} JSON files in {input_dir}")
    all_chunks = []
    seen = set()

    for fp in files:
        chunks = load_chunks(fp)
        for ch in chunks:
            h = sha1(ch["combined_text"])
            if h in seen:
                continue
            seen.add(h)
            ch["chunk_hash"] = h
            ch["city"] = city
            ch["bm25_joined"] = " | ".join(str(ch.get(f, "") or "") for f in BM25_FIELDS).strip(" |")
            all_chunks.append(ch)

    print(f"[INFO] Unique chunks to embed: {len(all_chunks)}")

    inserted = 0
    for i in tqdm(range(0, len(all_chunks), BATCH_SIZE), desc="Batches", unit="batch"):
        batch = all_chunks[i:i+BATCH_SIZE]
        texts = [b["combined_text"] for b in batch]
        embeddings = gemini_embed_batch(texts, gemini_api_key)

        for doc, emb in zip(batch, embeddings):
            doc["embedding"] = emb
            doc["embedding_model"] = f"gemini-embedding-001@dim-{EMBED_DIM}"

        try:
            col.insert_many(batch, ordered=False)
            inserted += len(batch)
        except BulkWriteError as bwe:
            dup = sum(1 for e in bwe.details.get("writeErrors", []) if e.get("code") == 11000)
            inserted += (len(batch) - dup)
            print(f"[WARN] Duplicates skipped ({dup})")

    print(f"[INFO] ✅ Inserted {inserted} documents into {db_name}.{collection_name}")
    client.close()

# ==============================================================
# Entry
# ==============================================================

if __name__ == "__main__":
    load_dotenv()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise RuntimeError("Set GEMINI_API_KEY in .env (Google AI Studio API key)")

    login = os.getenv("DATABASE_LOGIN")
    if not login:
        raise RuntimeError("[ERROR] Set DATABASE_LOGIN in .env")
    MONGODB_URI = f"mongodb+srv://{login}@paralegal-rag.ujgail4.mongodb.net/?retryWrites=true&w=majority&appName=Paralegal-RAG"

    INPUT_DIR = os.getenv("EXTRACTED_DIR", "llm_chunks_out")
    DB_NAME = os.getenv("DB_NAME", "Bylaws")
    COLLECTION = os.getenv("COLLECTION_NAME", "Waterloo")
    CITY = os.getenv("CITY", "Waterloo")

    # Set drop_if_exists=True to re-upload cleanly
    ingest_dir(
        input_dir=INPUT_DIR,
        mongodb_uri=MONGODB_URI,
        db_name=DB_NAME,
        collection_name=COLLECTION,
        city=CITY,
        gemini_api_key=GEMINI_API_KEY,
        drop_if_exists=True,
    )
