import os, json, glob, hashlib, time
from typing import List, Dict, Generator
from dotenv import load_dotenv
import requests
import pymongo
from pymongo.errors import BulkWriteError

# ---------------- Config ----------------
# Pick the model you want:
EMBED_MODEL = "text-embedding-3-small"   # 1536-dim (cheap/fast)
# EMBED_MODEL = "text-embedding-3-large" # 3072-dim (more accurate)

OPENAI_URL = "https://api.openai.com/v1/embeddings"
BATCH_SIZE = 128

# Which fields will be text-indexed for BM25:
BM25_FIELDS = ["text", "contextual_summary", "section_title", "page_title"]

SKIP_CONTENT_TYPES = {"general_info"}   # <- add anything else you want to exclude

# ---------------- Utils ----------------
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
    page_count  = data.get("page_count")
    scraped_at  = data.get("scraped_at")
    source_type = data.get("source_type", "unknown")
    page_title  = data.get("page_title")

    out = []
    for ch in data.get("chunks", []):
        ctype = (ch.get("content_type") or "general_info").strip().lower()
        if ctype in SKIP_CONTENT_TYPES:
            continue  # <-- skip here

        raw_text = ch.get("text", "")
        if isinstance(raw_text, list):
            text = "\n".join(map(str, raw_text)).strip()
        elif isinstance(raw_text, (int, float)):
            text = str(raw_text).strip()
        else:
            text = (raw_text or "").strip()

        raw_sum = ch.get("contextual_summary", "")
        if isinstance(raw_sum, list):
            summ = " ".join(map(str, raw_sum)).strip()
        else:
            summ = (raw_sum or "").strip()
        if not text and not summ:
            continue

        combined = (summ + "\n" + text).strip() if summ else text

        out.append({
            "text": text,
            "contextual_summary": summ,
            "combined_text": combined,
            "section_title": ch.get("section_title"),
            "content_type": ctype,
            "page_numbers": ch.get("page_numbers") or ch.get("page_number") or [],
            "page_title": page_title,
            "url": url,
            "filename": filename,
            "page_count": page_count,
            "scraped_at": scraped_at,
            "source_type": source_type,
        })
    return out


def embed_texts(texts: List[str], api_key: str, model: str) -> List[List[float]]:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "input": texts}
    r = requests.post(OPENAI_URL, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return [d["embedding"] for d in data["data"]]

# --------------- Main -------------------
def ingest_dir(
    input_dir: str,
    mongodb_uri: str,
    db_name: str,
    collection_name: str,
    city: str,
    openai_api_key: str,
    drop_if_exists: bool = False,
):
    client = pymongo.MongoClient(mongodb_uri)
    db = client[db_name]
    if drop_if_exists and collection_name in db.list_collection_names():
        db[collection_name].drop()
        print(f"🧹 Dropped {db_name}.{collection_name}")
    col = db[collection_name]

    # Unique on chunk_hash, and helpful query indexes
    col.create_index([("chunk_hash", pymongo.ASCENDING)], unique=True, name="uniq_chunk_hash")
    col.create_index([("city", pymongo.ASCENDING)], name="idx_city")
    col.create_index([("url", pymongo.ASCENDING)], name="idx_url")
    col.create_index([("content_type", pymongo.ASCENDING)], name="idx_content_type")

    # Collect & dedupe
    to_insert = []
    seen = set()
    files = list(iter_json_files(input_dir))
    print(f"📂 Found {len(files)} JSON files in {input_dir}")

    total_chunks = 0
    for path in files:
        chunks = load_chunks(path)
        total_chunks += len(chunks)
        for d in chunks:
            # hash on combined_text (or text) to dedupe
            h = sha1(d["combined_text"] or d["text"])
            if h in seen:
                continue
            seen.add(h)
            d["chunk_hash"] = h
            d["city"] = city
            to_insert.append(d)

    print(f"🧮 Unique chunks to embed: {len(to_insert)} (from {total_chunks} total)")

    # Embed in batches and insert
    inserted = 0
    for i in range(0, len(to_insert), BATCH_SIZE):
        batch = to_insert[i:i+BATCH_SIZE]
        inputs = [b["combined_text"] for b in batch]
        try:
            vectors = embed_texts(inputs, openai_api_key, EMBED_MODEL)
        except Exception as e:
            print(f"❌ Embedding failed for batch {i}-{i+len(batch)}: {e}")
            continue

        for doc, vec in zip(batch, vectors):
            doc["embedding"] = vec
            doc["embedding_model"] = EMBED_MODEL

        try:
            col.insert_many(batch, ordered=False)
            inserted += len(batch)
        except BulkWriteError as bwe:
            # count non-dup errors
            dup = sum(1 for e in bwe.details.get("writeErrors", []) if e.get("code") == 11000)
            inserted += (len(batch) - dup)
            others = [e for e in bwe.details.get("writeErrors", []) if e.get("code") != 11000]
            if others:
                print(f"⚠️ Non-dup write errors: {others[:2]} ...")
        except Exception as e:
            print(f"❌ Insert failed: {e}")

    print(f"✅ Inserted {inserted} docs → {db_name}.{collection_name}")
    client.close()

if __name__ == "__main__":
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise RuntimeError("Set OPENAI_API_KEY in .env")

    # Atlas connection:
    # Prefer a full URI via MONGODB_URI. Fallback builds from DATABASE_LOGIN (username:password@cluster)
    MONGODB_URI = os.getenv("MONGODB_URI")
    if not MONGODB_URI:
        login = os.getenv("DATABASE_LOGIN")
        if not login:
            raise RuntimeError("Set MONGODB_URI or DATABASE_LOGIN in .env")
        # Adjust cluster host to your actual Atlas cluster

        # print("LOGION:", login)
        MONGODB_URI = f"mongodb+srv://{login}@paralegal-rag.ujgail4.mongodb.net/?retryWrites=true&w=majority&appName=Paralegal-RAG"

    INPUT_DIR = os.getenv("EXTRACTED_DIR", "llm_extracted_data")

    # Your target DB/collection (e.g., Bylaws.Waterloo)
    DB_NAME = os.getenv("DB_NAME", "Bylaws")
    COLLECTION = os.getenv("COLLECTION_NAME", "Waterloo")
    CITY = os.getenv("CITY", "Waterloo")

    ingest_dir(
        input_dir=INPUT_DIR,
        mongodb_uri=MONGODB_URI,
        db_name=DB_NAME,
        collection_name=COLLECTION,
        city=CITY,
        openai_api_key=OPENAI_API_KEY,
        drop_if_exists=False,  # set True only if you want to recreate
    )
