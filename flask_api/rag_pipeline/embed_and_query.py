import pymongo, os, requests
from heapq import nlargest
import json

# --- Gemini query embedding (matches your document embeddings) ---
def gemini_embed_query(query: str, api_key: str):
    """
    Returns a 768-dim embedding vector for the query,
    matching your database embeddings.
    """
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-embedding-001:embedContent"
    )
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "model": "models/gemini-embedding-001",
        "content": {"parts": [{"text": query}]},
        # Match corpus embeddings
        "output_dimensionality": 768,
        # Mark as query-type vector (slightly different internal projection)
        "task_type": "RETRIEVAL_QUERY"
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()

    vec = r.json()["embedding"]["values"]
    if len(vec) != 768:
        print(f"[WARN] Query embedding dim mismatch: {len(vec)} (expected 768)")
    return vec

# If you ever decide to switch DB embeddings to OpenAI instead, you can still keep this:
def openai_embed(query: str, api_key: str, model="text-embedding-3-small"):
    r = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "input": query},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]  # 1536-d for text-embedding-3-small

def query_hybrid(mongodb_uri, db_name, col_name, query_text, city: str = None, k_each: int = 10):
    """
    Hybrid retrieval:
      1) Text (BM25) leg via $search.text
      2) Vector (semantic) leg via $search.knnBeta (Gemini vecs)
      3) Normalize+blend (0.6 vector + 0.4 text) and return top 5 documents
    """
    client = pymongo.MongoClient(mongodb_uri, tls=True)
    col = client[db_name][col_name]

    # Embed the query with GEMINI to match your stored embeddings
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise RuntimeError("Set GEMINI_API_KEY in env for query embeddings")
    qvec = gemini_embed_query(query_text, gemini_key)  # matches corpus vectors

    # ---- Text (BM25) leg ----
    text_search = {
        "$search": {
            "index": "default",
            "compound": {
                **({
                    "filter": [{
                        "equals": {"path": "city", "value": city}
                    }]
                } if city else {}),
                "should": [
                    {
                        "text": {
                            "query": query_text,
                            "path": ["contextual_summary", "section_title", "page_title"],
                            "score": {"boost": {"value": 3}}
                        }
                    },
                    {
                        "text": {
                            "query": query_text,
                            "path": ["text", "combined_text"]
                        }
                    },
                ],
            },
        }
    }

    text_pipeline = [
        text_search,
        {"$addFields": {"bm25_score": {"$meta": "searchScore"}}},
        {"$limit": k_each},
        {"$project": {"embedding": 0}}  # drop large vector
    ]
    text_results = list(col.aggregate(text_pipeline, allowDiskUse=True))

    # ---- Vector (semantic) leg ----
    # knnBeta can't be nested in compound.should in the same stage; use a separate leg.
    vector_search = {
        "$search": {
            "index": "default",
            "knnBeta": {
                "path": "embedding",
                "vector": qvec,
                "k": k_each,
                **({
                    "filter": {
                        "equals": {"path": "city", "value": city}
                    }
                } if city else {})
            }
        }
    }
    vector_pipeline = [
        vector_search,
        {"$addFields": {"vector_score": {"$meta": "searchScore"}}},
        {"$limit": k_each},
        {"$project": {"embedding": 0}}
    ]
    vector_results = list(col.aggregate(vector_pipeline, allowDiskUse=True))

    # Full detailed BM25 results
    print("\n📘 BM25 RESULTS (FULL DETAILS):")
    for i, r in enumerate(text_results, 1):
        print(r)

    print("VECTOR===============")
    for i, r in enumerate(vector_results, 1):
        print(r)

    # ---- Normalize + merge (by URL + text) ----
    merged = {}

    def add(entry, score_field):
        key = (entry.get("url", "unknown"), entry.get("combined_text") or entry.get("text") or "")
        if key not in merged:
            merged[key] = {**entry, "bm25_score": 0.0, "vector_score": 0.0}
        merged[key][score_field] = float(entry.get(score_field, 0.0))

    for r in text_results:
        add(r, "bm25_score")
    for r in vector_results:
        add(r, "vector_score")

    # Normalize to [0,1]
    all_bm25 = [v["bm25_score"] for v in merged.values()]
    all_vec  = [v["vector_score"] for v in merged.values()]
    max_bm25 = max(all_bm25) if all_bm25 else 1.0
    max_vec  = max(all_vec)  if all_vec  else 1.0
    eps = 1e-9
    for v in merged.values():
        nb = v["bm25_score"] / (max_bm25 + eps)
        nv = v["vector_score"] / (max_vec + eps)
        v["hybrid_score"] = 0.6 * nv + 0.4 * nb

    top5 = nlargest(5, merged.values(), key=lambda x: x["hybrid_score"])

    client.close()
    # print("TOP 5:", top5)
    return top5
