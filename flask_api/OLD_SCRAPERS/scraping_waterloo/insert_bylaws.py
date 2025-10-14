import argparse
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pymongo
from dotenv import load_dotenv
from tqdm import tqdm

# ---- Your existing embedder (lazy, CPU) --------------------
import torch
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from sentence_transformers import SentenceTransformer
_model = None

def get_embedding_model():
    global _model
    if _model is None:
        print(f"PID {os.getpid()}: Init sentence-transformer on CPU...")
        torch.set_num_threads(1)
        _model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        print(f"PID {os.getpid()}: Model ready (dim=384).")
    return _model

def embed_text(text: str) -> Optional[List[float]]:
    if not text or not text.strip():
        return None
    try:
        m = get_embedding_model()
        return m.encode(text).tolist()
    except Exception as e:
        print(f"[embed] error: {e}")
        return None

# ---- Helpers ----------------------------------------------

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha256_text(s: str) -> str:
    return sha256_bytes(s.encode("utf-8", errors="ignore"))

def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# Chunking: ~1k chars with ~150 char overlap, sentence-aware packer
def chunk_text(
    text: str,
    target_size: int = 1000,
    overlap: int = 150,
    min_size: int = 600,
) -> List[str]:
    # Normalize whitespace
    cleaned = re.sub(r"\r\n?", "\n", text)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)

    # Split into paragraphs first
    paras = re.split(r"\n{2,}", cleaned)
    chunks = []
    buf = ""

    def flush_buf():
        nonlocal buf
        if buf.strip():
            chunks.append(buf.strip())
        buf = ""

    for p in paras:
        p = p.strip()
        if not p:
            continue
        if len(buf) + len(p) + 1 <= target_size:
            buf = (buf + "\n\n" + p) if buf else p
        else:
            # If current buffer is too small, but adding p would overshoot a lot,
            # still flush to keep coherence.
            if len(buf) >= min_size:
                flush_buf()
                buf = p
            else:
                # Try sentence-level packing
                sentences = re.split(r"(?<=[.!?])\s+", p)
                for s in sentences:
                    if len(buf) + len(s) + 1 <= target_size:
                        buf = (buf + " " + s) if buf else s
                    else:
                        if len(buf) >= min_size:
                            flush_buf()
                            buf = s
                        else:
                            # Force split if we have a very long sentence
                            # Hard wrap at target_size
                            while len(s) > 0:
                                space_left = target_size - (len(buf) + (1 if buf else 0))
                                if space_left <= 0:
                                    flush_buf()
                                    buf = ""
                                    space_left = target_size
                                take = s[:space_left]
                                buf = (buf + " " + take).strip() if buf else take
                                s = s[space_left:]
                                if len(buf) >= min_size:
                                    flush_buf()
                                    buf = ""
    if buf:
        flush_buf()

    # Add overlap by repeating tail of previous chunk at start of next
    if overlap > 0 and len(chunks) > 1:
        overlapped = []
        for i, ch in enumerate(chunks):
            if i == 0:
                overlapped.append(ch)
            else:
                prev_tail = chunks[i - 1][-overlap:]
                merged = (prev_tail + "\n" + ch).strip()
                overlapped.append(merged)
        chunks = overlapped

    return chunks

# ---- Input loaders -----------------------------------------

def load_txt(path: Path) -> Dict:
    return {
        "title": path.stem,
        "url": None,
        "text": path.read_text(encoding="utf-8", errors="ignore"),
        "bylaw_number": None,
        "fetched_at": None,
    }

def load_json(path: Path) -> Dict:
    data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    # enforce keys
    return {
        "title": data.get("title") or path.stem,
        "url": data.get("url"),
        "text": data.get("text") or "",
        "bylaw_number": data.get("bylaw_number"),
        "fetched_at": data.get("fetched_at"),
    }

def iter_bylaw_docs(input_dir: Path):
    for p in input_dir.rglob("*"):
        if p.is_file():
            if p.suffix.lower() == ".txt":
                yield load_txt(p), p
            elif p.suffix.lower() == ".json":
                yield load_json(p), p

# ---- Mongo operations --------------------------------------

def make_mongo_client():
    load_dotenv()
    login = os.getenv("DATABASE_LOGIN")
    if not login:
        raise ValueError("DATABASE_LOGIN not set in .env (URL-encoded username:password).")
    uri = f"mongodb+srv://{login}@gdsc2025.cn3wt5n.mongodb.net/?retryWrites=true&w=majority&appName=GDSC2025"
    return pymongo.MongoClient(uri)

def ensure_indexes(col: pymongo.collection.Collection):
    # Unique identity to avoid dupes if re-running: (bylaw_id, chunk_index, content_sha256)
    col.create_index(
        [("bylaw_id", 1), ("chunk_index", 1), ("content_sha256", 1)],
        unique=True,
        name="uniq_bylaw_chunk_sha"
    )
    # Helpful secondary indexes
    col.create_index([("bylaw_title", 1)])
    col.create_index([("bylaw_number", 1)])
    col.create_index([("url", 1)])

def build_bylaw_id(city: str, title: str, bylaw_number: Optional[str]) -> str:
    # Stable id: city + bylaw_number if present, else slug of title
    if bylaw_number and str(bylaw_number).strip():
        return f"{slugify(city)}::{slugify(bylaw_number)}"
    return f"{slugify(city)}::{slugify(title)}"

def doc_for_chunk(
    city: str,
    base: Dict,
    chunk_text_val: str,
    chunk_index: int,
) -> Dict:
    content_sha = sha256_text(chunk_text_val)
    return {
        "city": city,
        "bylaw_title": base["title"],
        "bylaw_number": base.get("bylaw_number"),
        "url": base.get("url"),
        "fetched_at": base.get("fetched_at"),
        "ingested_at": now_iso(),
        "bylaw_id": build_bylaw_id(city, base["title"], base.get("bylaw_number")),
        "chunk_index": chunk_index,
        "chunk_text": chunk_text_val,
        "content_sha256": content_sha,
        # filled later:
        "chunk_embedding": None,
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "embedding_dim": 384,
        "similarity": "cosine",
    }

def upsert_chunks_with_embeddings(
    client: pymongo.MongoClient,
    database: str,
    collection: str,
    city: str,
    input_dir: Path,
    target_chunk_chars: int = 1000,
    overlap_chars: int = 150,
    min_chunk_chars: int = 600,
    batch_size: int = 64,
):
    col = client[database][collection]
    ensure_indexes(col)

    to_write = []
    total_docs = 0
    total_chunks = 0

    for base_doc, path in iter_bylaw_docs(input_dir):
        total_docs += 1
        text = (base_doc.get("text") or "").strip()
        if not text:
            print(f"[skip] empty text in: {path}")
            continue

        chunks = chunk_text(
            text,
            target_size=target_chunk_chars,
            overlap=overlap_chars,
            min_size=min_chunk_chars,
        )
        if not chunks:
            print(f"[skip] no chunks extracted: {path}")
            continue

        # Embed in small batches
        for i, ch in enumerate(chunks):
            doc = doc_for_chunk(city, base_doc, ch, i)
            vec = embed_text(ch)
            if vec is None:
                print(f"[warn] embedding failed for {doc['bylaw_id']}#{i}, skipping")
                continue
            doc["chunk_embedding"] = vec
            to_write.append(pymongo.UpdateOne(
                {
                    "bylaw_id": doc["bylaw_id"],
                    "chunk_index": doc["chunk_index"],
                    "content_sha256": doc["content_sha256"],
                },
                {"$set": doc},
                upsert=True
            ))
            total_chunks += 1

            if len(to_write) >= batch_size:
                try:
                    col.bulk_write(to_write, ordered=False)
                except pymongo.errors.BulkWriteError as bwe:
                    print(f"[bulk] write error: {bwe.details}")
                to_write = []

    if to_write:
        try:
            col.bulk_write(to_write, ordered=False)
        except pymongo.errors.BulkWriteError as bwe:
            print(f"[bulk] write error: {bwe.details}")

    print(f"Done. Processed {total_docs} files; upserted {total_chunks} chunks.")

def main():
    ap = argparse.ArgumentParser(description="Chunk, embed (CPU), and ingest bylaws into MongoDB Atlas.")
    ap.add_argument("--db", required=True, help="Database name, e.g., bylaws")
    ap.add_argument("--collection", required=True, help="Collection name, e.g., waterloo")
    ap.add_argument("--city", required=True, help="City label for metadata, e.g., Waterloo")
    ap.add_argument("--input", required=True, help="Folder with .json/.txt bylaw files")
    ap.add_argument("--chunk", type=int, default=1000, help="Target chunk size in characters (default 1000)")
    ap.add_argument("--overlap", type=int, default=150, help="Overlap size in characters (default 150)")
    ap.add_argument("--minchunk", type=int, default=600, help="Minimum chunk size before forcing split (default 600)")
    ap.add_argument("--batch", type=int, default=64, help="Bulk write batch size (default 64)")
    args = ap.parse_args()

    input_dir = Path(args.input).resolve()
    if not input_dir.exists():
        raise FileNotFoundError(f"Input dir not found: {input_dir}")

    client = make_mongo_client()
    try:
        upsert_chunks_with_embeddings(
            client=client,
            database=args.db,
            collection=args.collection,
            city=args.city,
            input_dir=input_dir,
            target_chunk_chars=args.chunk,
            overlap_chars=args.overlap,
            min_chunk_chars=args.minchunk,
            batch_size=args.batch,
        )
    finally:
        client.close()

if __name__ == "__main__":
    main()
