#!/usr/bin/env python3
"""
Re-embed documents in-place for Paralegal_RAG / Bylaws.{Toronto,Guelph}
using Gemini 'gemini-embedding-001' at 768 dims.

- No JSON files; reads & updates MongoDB directly.
- Respects DRY_RUN, can process only docs missing 'embedding',
  or force re-embed everything.
- Rebuilds combined_text if missing.

Env you should set:
  GEMINI_API_KEY="..."
  MONGODB_URI="mongodb+srv://<user>:<pass>@paralegal-rag.ujgail4.mongodb.net/?retryWrites=true&w=majority&appName=Paralegal-RAG"

Optional env:
  DB_NAME=Bylaws
  TORONTO_COLL=Toronto
  GUELPH_COLL=Guelph
  EMBED_DIM=768
  BATCH_SIZE=64
  DRY_RUN=0
  ONLY_MISSING=1          # if 1, only docs with missing/empty embedding
  CITY_FILTER=""          # "", "Toronto", or "Guelph" to restrict run
"""

import os
import time
import math
import requests
from typing import List, Dict, Any, Iterable, Tuple

from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from tqdm import tqdm

from dotenv import load_dotenv

load_dotenv()

# -------------------------
# Config (env-driven)
# -------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Set GEMINI_API_KEY in env")

MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise RuntimeError("Set MONGODB_URI in env (your Paralegal-RAG cluster)")

DB_NAME       = os.getenv("DB_NAME", "Bylaws")
TORONTO_COLL  = os.getenv("TORONTO_COLL", "Toronto")
GUELPH_COLL   = os.getenv("GUELPH_COLL", "Guelph")

EMBED_DIM     = int(os.getenv("EMBED_DIM", "768"))
BATCH_SIZE    = int(os.getenv("BATCH_SIZE", "16"))
DRY_RUN       = os.getenv("DRY_RUN", "0") == "1"
ONLY_MISSING  = os.getenv("ONLY_MISSING", "1") == "1"  # default: only fill missing embeddings
CITY_FILTER   = os.getenv("CITY_FILTER", "").strip()   # "", "Toronto", "Guelph"

EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent"
EMBED_MODEL_TAG = f"gemini-embedding-001@dim-{EMBED_DIM}"

# Which fields to combine for BM25 and embedding when combined_text missing
BM25_FIELDS = ["text", "contextual_summary", "section_title", "page_title"]

# -------------------------
# Helpers
# -------------------------
def build_combined_text(doc: Dict[str, Any]) -> str:
    """
    Prefer stored combined_text; otherwise synthesize from key fields.
    """
    if isinstance(doc.get("combined_text"), str) and doc["combined_text"].strip():
        return doc["combined_text"].strip()

    title   = (doc.get("section_title") or "").strip()
    summ    = (doc.get("contextual_summary") or "").strip()
    text    = (doc.get("text") or "").strip()
    parts = [p for p in [title, summ, text] if p]
    return "\n".join(parts).strip()

def build_bm25_joined(doc: Dict[str, Any]) -> str:
    return " | ".join(str(doc.get(f, "") or "") for f in BM25_FIELDS if doc.get(f)).strip(" |")

def needs_embedding(doc: Dict[str, Any]) -> bool:
    """
    Decide whether this doc needs embedding.
    - ONLY_MISSING=True: embed if no 'embedding' or empty list
    - ONLY_MISSING=False: always embed (force)
    """
    if not ONLY_MISSING:
        return True
    emb = doc.get("embedding")
    if emb is None:
        return True
    if isinstance(emb, list) and len(emb) == 0:
        return True
    return False

def gemini_embed_many(texts: List[str]) -> List[List[float]]:
    """
    Simple robust loop: one HTTP request per text (avoids batch payload limits).
    Exponential backoff on 429/5xx. Guarantees EMBED_DIM length.
    """
    headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
    out: List[List[float]] = []

    for t in texts:
        payload = {
            "model": "models/gemini-embedding-001",
            "content": {"parts": [{"text": t}]},
            "output_dimensionality": EMBED_DIM,
            "task_type": "RETRIEVAL_DOCUMENT"
        }

        pause = 1.0
        for attempt in range(6):
            try:
                r = requests.post(EMBED_URL, headers=headers, json=payload, timeout=60)
                if r.status_code == 200:
                    data = r.json()
                    vec = data.get("embedding", {}).get("values", [])
                    if not isinstance(vec, list):
                        vec = []
                    if len(vec) != EMBED_DIM:
                        # pad/truncate defensively
                        vec = (vec + [0.0] * EMBED_DIM)[:EMBED_DIM]
                    out.append(vec)
                    break
                elif r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(pause)
                    pause = min(pause * 2, 10)
                    continue
                else:
                    # Hard failure for this chunk; keep placeholder
                    print(f"[WARN] Gemini {r.status_code}: {r.text[:200]}")
                    out.append([0.0] * EMBED_DIM)
                    break
            except Exception as e:
                print(f"[WARN] Gemini error: {e}")
                time.sleep(pause)
                pause = min(pause * 2, 10)
        else:
            out.append([0.0] * EMBED_DIM)

    return out

def reembed_collection(col, city_label: str):
    """
    Iterate the collection for the specified city and update embeddings in place.
    """
    # Filter: city match (defensive) + missing/empty embedding (if ONLY_MISSING)
    base_filter: Dict[str, Any] = {"city": city_label}
    if ONLY_MISSING:
        base_filter = {
            "city": city_label,
            "$or": [
                {"embedding": {"$exists": False}},
                {"embedding": None},
                {"embedding": {"$size": 0}},
                {"embedding": []},
            ],
        }


    total = col.count_documents(base_filter)
    if total == 0:
        print(f"[{city_label}] Nothing to embed (filter={base_filter})")
        return

    print(f"[{city_label}] To embed: {total:,} documents")

    projection = {
        "_id": 1,
        "combined_text": 1,
        "section_title": 1,
        "contextual_summary": 1,
        "text": 1,
        "page_title": 1,
        "bm25_joined": 1,
        "embedding": 1,
    }

    processed = 0
    cursor = col.find(base_filter, projection=projection).batch_size(BATCH_SIZE)

    try:
        while True:
            batch_docs = []
            try:
                for _ in range(BATCH_SIZE):
                    batch_docs.append(next(cursor))
            except StopIteration:
                pass

            if not batch_docs:
                break

            # Build combined_text and ensure bm25_joined
            texts: List[str] = []
            ids: List[Any] = []
            bm25s: List[str] = []

            for d in batch_docs:
                ct = build_combined_text(d)
                texts.append(ct if ct else " ")  # never empty
                ids.append(d["_id"])
                bm25s.append(d.get("bm25_joined") or build_bm25_joined(d))

            # Embed
            if DRY_RUN:
                embeddings = [[0.0] * EMBED_DIM for _ in texts]
            else:
                embeddings = gemini_embed_many(texts)

            # Build bulk updates
            ops: List[UpdateOne] = []
            for _id, emb, bm25 in zip(ids, embeddings, bm25s):
                update_doc = {
                    "embedding": emb,
                    "embedding_model": EMBED_MODEL_TAG,
                    "bm25_joined": bm25,
                    # also store combined_text if we synthesized it (helpful consistency)
                    # we can detect by comparing with doc? We’ll just trust existing combined_text presence.
                }
                ops.append(UpdateOne({"_id": _id}, {"$set": update_doc}))

            if not DRY_RUN and ops:
                try:
                    col.bulk_write(ops, ordered=False)
                except BulkWriteError as bwe:
                    # If there are write races, ignore and continue
                    print(f"[{city_label}] BulkWrite warning: {bwe.details.get('writeErrors', [])[:2]}")

            processed += len(batch_docs)
            pct = (processed / total) * 100.0
            print(f"[{city_label}] Embedded {processed}/{total} ({pct:.1f}%)")

            if len(batch_docs) < BATCH_SIZE:
                break

    finally:
        try:
            cursor.close()
        except Exception:
            pass

    print(f"[{city_label}] ✅ Done re-embedding.")

# -------------------------
# Entry
# -------------------------
if __name__ == "__main__":
    print(f"DB={DB_NAME}  DRY_RUN={DRY_RUN}  ONLY_MISSING={ONLY_MISSING}  BATCH_SIZE={BATCH_SIZE}  CITY_FILTER='{CITY_FILTER or 'ALL'}'")
    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]

    targets: List[Tuple[str, str]] = []
    if CITY_FILTER.lower() == "toronto":
        targets = [(TORONTO_COLL, "Toronto")]
    elif CITY_FILTER.lower() == "guelph":
        targets = [(GUELPH_COLL, "Guelph")]
    else:
        targets = [(TORONTO_COLL, "Toronto"), (GUELPH_COLL, "Guelph")]

    for coll_name, city in targets:
        col = db[coll_name]
        print(f"\n=== Processing {DB_NAME}.{coll_name} (city={city}) ===")
        # (Optional) helpful indexes if not present:
        try:
            col.create_index("city")
            col.create_index("url")
        except Exception:
            pass

        reembed_collection(col, city)

    print("\nAll cities finished.")
