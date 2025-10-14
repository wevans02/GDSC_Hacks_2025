'''
main function query hybrid retrieves relevant chunks from database given query
1. creates and returns embedding from openAI using openai_embed
2. does a keyword (BM25) search, along with vector semantic search on the embedding to retrieve relevant chunks
3. merges results from the two queries and returns the top 5 most relevant chunks.
'''

import pymongo, os, requests
from heapq import nlargest
import json

# use API to embed query. give query and api key, returns list of float embedding, 1536 dim.
def openai_embed(query: str, api_key: str, model="text-embedding-3-small"):
    r = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "input": query},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]


# manual hybrid search cuz im poor
# queries with vector, then with bm25, then merges. mongodb can do this all in one search but its too expensive for me
# honestly too this doesnt add THAT much overhead for now.
def query_hybrid(mongodb_uri, db_name, col_name, query_text):
    """
    Perform hybrid retrieval:
      1. Text-based (BM25 keyword)
      2. Vector-based (semantic)
    Then merge both by normalized score and return top 5.
    """

    client = pymongo.MongoClient(mongodb_uri, tls=True)
    col = client[db_name][col_name]
    api_key = os.getenv("OPENAI_API_KEY")

    # Step 1: Get embedding for query
    qvec = openai_embed(query_text, api_key)

    # Step 2: Run text (BM25) search
    text_pipeline = [
        {
            "$search": {
                "index": "default",
                "text": {
                    "query": query_text,
                    "path": ["text", "contextual_summary", "section_title", "page_title"],
                    "score": {"boost": {"value": 3}}
                }
            }
        },
        {"$addFields": {"bm25_score": {"$meta": "searchScore"}}},
        {"$limit": 10},
        {"$project": {
            "_id": 0,
            "chunk_text": {"$ifNull": ["$chunk_text", "$text"]},
            "section_title": 1,
            "url": 1,
            "page_numbers": 1,
            "bm25_score": 1
        }}
    ]
    # list of results with relevant keywords
    text_results = list(col.aggregate(text_pipeline))

    # Step 3: Run vector search
    vector_pipeline = [
        {
            "$search": {
                "index": "default",
                "knnBeta": {
                    "vector": qvec,
                    "path": "embedding",
                    "k": 10
                }
            }
        },
        {"$addFields": {"vector_score": {"$meta": "searchScore"}}},
        {"$project": {
            "_id": 0,
            "chunk_text": {"$ifNull": ["$chunk_text", "$text"]},
            "section_title": 1,
            "url": 1,
            "page_numbers": 1,
            "vector_score": 1
        }}
    ]

    vector_results = list(col.aggregate(vector_pipeline))

    # debug prints
    # print(f"🔎 Query: {query_text}")
    # print(f"→ BM25 results: {len(text_results)} | Vector results: {len(vector_results)}")
    # if text_results:
    #     print("  BM25 top hit sample:", json.dumps(text_results[0], indent=2)[:300])
    # if vector_results:
    #     print("  Vector top hit sample:", json.dumps(vector_results[0], indent=2)[:300])


    # Step 4: Normalize + Merge
    merged = {}

    def add_or_update(entry, score, score_type):
        url = entry.get("url", "unknown")
        key = (url, entry.get("chunk_text", ""))
        if key not in merged:
            merged[key] = entry.copy()
            merged[key]["bm25_score"] = 0
            merged[key]["vector_score"] = 0
        merged[key][score_type] = score

    for r in text_results:
        add_or_update(r, r.get("bm25_score", 0), "bm25_score")

    for r in vector_results:
        add_or_update(r, r.get("vector_score", 0), "vector_score")

    # Normalize scores to [0, 1] to combine fairly-ish
    all_bm25 = [r.get("bm25_score", 0) for r in merged.values()]
    all_vec = [r.get("vector_score", 0) for r in merged.values()]
    max_bm25 = max(all_bm25 or [1])
    max_vec = max(all_vec or [1])
    epsilon = 0.0000001

    for r in merged.values():
        norm_bm25 = r.get("bm25_score", 0) / (max_bm25 + epsilon)
        norm_vec = r.get("vector_score", 0) / (max_vec + epsilon)
        # weighted combination: 0.6 vector + 0.4 keyword
        r["hybrid_score"] = 0.6 * norm_vec + 0.4 * norm_bm25

    # Step 5: Return Top 5 
    top5 = nlargest(5, merged.values(), key=lambda x: x["hybrid_score"])

    # debug prints
    # print("Hybrid top 5 (scores):")
    # for i, doc in enumerate(top5, 1):
    #     print(f"  {i}. hybrid={doc['hybrid_score']:.3f} | bm25={doc['bm25_score']:.3f} | vector={doc['vector_score']:.3f}")
    #     print(f"     {doc.get('section_title') or '—'}")
    #     print(f"     {doc.get('url') or ''}")
    #     print()

    client.close()
    return top5