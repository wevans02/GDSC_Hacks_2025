#!/usr/bin/env python3
"""
Cross-project migration: Copy Toronto & Guelph from OLD cluster to NEW cluster,
reshape to the new schema used by Bylaws.Waterloo.

OLD (cluster/project: GDSC2025)
  DB: bylaws
    • all_bylaws  (Toronto)
    • guelph      (Guelph)

NEW (cluster/project: Paralegal_RAG)
  DB: Bylaws
    • Toronto     (target)
    • Guelph      (target)

Embeddings left empty; you'll re-embed later.

Run:
  DRY_RUN=1 python migrate_bylaws_cross_project.py
  # then:
  python migrate_bylaws_cross_project.py
"""

import os
import sys
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from pymongo import MongoClient, UpdateOne, ASCENDING
from pymongo.errors import BulkWriteError

# =========================
# CONNECTIONS / CONSTANTS
# =========================
# Use the URIs you provided (pointing to the correct clusters/projects).
OLD_MONGO_URI = os.getenv(
    "OLD_MONGO_URI",
    "mongodb+srv://{LOGIN}@gdsc2025.cn3wt5n.mongodb.net/?retryWrites=true&w=majority&appName=GDSC2025"
)
NEW_MONGO_URI = os.getenv(
    "NEW_MONGO_URI",
    "mongodb+srv://{LOGIN}@paralegal-rag.ujgail4.mongodb.net/?retryWrites=true&w=majority&appName=Paralegal-RAG"
)

# *** IMPORTANT: these are DATABASE names (not cluster/project names) ***
OLD_DB_NAME = os.getenv("OLD_DB_NAME", "bylaws")       # <-- old DB is "bylaws"
NEW_DB_NAME = os.getenv("NEW_DB_NAME", "Bylaws")       # <-- new DB is "Bylaws"

# *** Source collections in OLD DB ***
OLD_TORONTO_COLL = os.getenv("OLD_TORONTO_COLL", "bylaw_chunks")
OLD_GUELPH_COLL  = os.getenv("OLD_GUELPH_COLL",  "guelph")

# *** Destination collections in NEW DB ***
NEW_TORONTO_COLL = os.getenv("NEW_TORONTO_COLL", "Toronto")
NEW_GUELPH_COLL  = os.getenv("NEW_GUELPH_COLL",  "Guelph")

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"

TARGET_EMBEDDING_MODEL = os.getenv("TARGET_EMBEDDING_MODEL", "gemini-embedding-001@dim-768")

# =========================
# UTILS
# =========================
def sha1(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def safe_str(x) -> str:
    return "" if x is None else str(x)

def build_chunk_hash(city: str, url: str, seq: Any, text: str) -> str:
    """
    Stable, idempotent hash used for upsert key and unique index.
    Combines (city | url | sequence | sha1(text)).
    """
    payload = f"{city}|{url}|{safe_str(seq)}|{sha1(text)}"
    return sha1(payload)

# =========================
# TRANSFORM (old -> new)
# =========================
def transform_old_doc_to_new(doc: Dict[str, Any], city: str, old_db_label: str, src_collection_name: str) -> Optional[Dict[str, Any]]:
    """
    Old doc example:
      {
        _id: ObjectId(...),
        original_bylaw_id: "Chapter 1",
        title: "General Provisions",
        pdf_url: "http://www.toronto.ca/legdocs/municode/1184_001.pdf",
        chunk_sequence: 2,
        chunk_text: "...",
        ...
      }

    New schema (like Bylaws.Waterloo):
      {
        combined_text: "<title>\\n\\n<chunk_text>",
        section_title: <title>,
        contextual_summary: f"From PDF: <pdf_url>" (or original bylaw id),
        text: <chunk_text>,
        content_type: "bylaw",
        page_title: null,
        url: <pdf_url>,
        filename: "<short-hash>_<seq>.pdf",
        scraped_at: <now>,
        source_type: "pdf",
        chunk_hash: <sha1>,
        city: <City>,
        bm25_joined: "<title>\\n<chunk_text>",
        embedding: None,
        embedding_model: "gemini-embedding-001@dim-768",
        original: { provenance ... }
      }
    """
    title = safe_str(doc.get("title"))
    url = safe_str(doc.get("pdf_url"))
    text = safe_str(doc.get("chunk_text"))
    seq  = doc.get("chunk_sequence", 0)

    if not url and not text:
        return None  # nothing useful to migrate

    filename = f"{sha1(url)[:8]}_{safe_str(seq)}.pdf"
    chunk_hash = build_chunk_hash(city, url, seq, text)

    new_doc = {
        "combined_text": (f"{title}\n\n{text}").strip() if (title or text) else "",
        "section_title": title or None,
        "contextual_summary": f"From PDF: {url}"[:500] if url else safe_str(doc.get("original_bylaw_id")) or None,
        "text": text,
        "content_type": "bylaw",
        "page_title": None,
        "url": url or None,
        "filename": filename,
        "scraped_at": now_iso(),
        "source_type": "pdf",
        "chunk_hash": chunk_hash,
        "city": city,
        "bm25_joined": (f"{title}\n{text}").strip(),
        "embedding": None,                        # intentionally blank (re-embed later)
        "embedding_model": TARGET_EMBEDDING_MODEL,
        "original": {
            "source_cluster": "GDSC2025",
            "source_db": old_db_label,           # should be "bylaws"
            "source_collection": src_collection_name,
            "source_id": safe_str(doc.get("_id")),
            "original_bylaw_id": safe_str(doc.get("original_bylaw_id")),
            "chunk_sequence": seq,
        },
    }
    return new_doc

# =========================
# MIGRATION CORE
# =========================
def ensure_indexes(coll):
    # unique index on chunk_hash for idempotent upserts
    try:
        coll.create_index([("chunk_hash", ASCENDING)], unique=True, name="uniq_chunk_hash")
    except Exception as e:
        print(f"Index create warning on {coll.full_name}: {e}")

def migrate_collection(
    src_coll,
    dst_coll,
    city: str,
    old_db_label: str,
    src_collection_name: str,
    limit: Optional[int] = None
):
    ensure_indexes(dst_coll)

    total = 0
    buf: list[UpdateOne] = []

    # IMPORTANT: no 'no_cursor_timeout' (Atlas free tier disallows noTimeout)
    cursor = src_coll.find({}).batch_size(BATCH_SIZE)

    try:
        for i, doc in enumerate(cursor, start=1):
            new_doc = transform_old_doc_to_new(doc, city, old_db_label, src_collection_name)
            if not new_doc:
                continue

            # upsert by chunk_hash
            op = UpdateOne(
                {"chunk_hash": new_doc["chunk_hash"]},
                {"$set": new_doc},
                upsert=True
            )
            buf.append(op)

            if len(buf) >= BATCH_SIZE:
                if not DRY_RUN:
                    try:
                        dst_coll.bulk_write(buf, ordered=False)
                    except BulkWriteError as bwe:
                        # ignore duplicates / partial failures; unique index guards us
                        pass
                total += len(buf)
                buf.clear()
                print(f"[{city}] migrated: {total} ...", flush=True)

            if limit and i >= limit:
                break

        if buf:
            if not DRY_RUN:
                try:
                    dst_coll.bulk_write(buf, ordered=False)
                except BulkWriteError:
                    pass
            total += len(buf)
            buf.clear()
    finally:
        try:
            cursor.close()
        except Exception:
            pass

    print(f"[{city}] ✅ done. total migrated (attempted): {total}")

def main():
    # Basic sanity checks
    if not OLD_DB_NAME or not NEW_DB_NAME:
        print("ERROR: database names cannot be empty. Set OLD_DB_NAME and NEW_DB_NAME.")
        sys.exit(2)

    print("Starting migration (Toronto + Guelph)...")
    print(f"OLD_MONGO_URI  -> DB={OLD_DB_NAME}")
    print(f"NEW_MONGO_URI  -> DB={NEW_DB_NAME}")
    print(f"DRY_RUN={DRY_RUN}, BATCH_SIZE={BATCH_SIZE}\n")

    # Connect to both clusters
    old_client = MongoClient(OLD_MONGO_URI)
    new_client = MongoClient(NEW_MONGO_URI)

    old_db = old_client[OLD_DB_NAME]   # "bylaws"
    new_db = new_client[NEW_DB_NAME]   # "Bylaws"

    # Source collections (OLD)
    src_toronto = old_db[OLD_TORONTO_COLL]   # bylaws.all_bylaws -> actually DB=bylaws, coll=all_bylaws
    src_guelph  = old_db[OLD_GUELPH_COLL]    # bylaws.guelph    -> DB=bylaws, coll=guelph

    # Destination collections (NEW)
    dst_toronto = new_db[NEW_TORONTO_COLL]   # Bylaws.Toronto   -> DB=Bylaws, coll=Toronto
    dst_guelph  = new_db[NEW_GUELPH_COLL]    # Bylaws.Guelph    -> DB=Bylaws, coll=Guelph

    # Toronto
    migrate_collection(
        src_coll=src_toronto,
        dst_coll=dst_toronto,
        city="Toronto",
        old_db_label=OLD_DB_NAME,
        src_collection_name=OLD_TORONTO_COLL
    )

    # Guelph
    migrate_collection(
        src_coll=src_guelph,
        dst_coll=dst_guelph,
        city="Guelph",
        old_db_label=OLD_DB_NAME,
        src_collection_name=OLD_GUELPH_COLL
    )

    print("\nAll done ✅")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)
