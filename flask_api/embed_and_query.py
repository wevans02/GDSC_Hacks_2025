import pymongo, os, requests

def openai_embed(query: str, api_key: str, model="text-embedding-3-small"):
    r = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "input": query},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]

def query_hybrid(mongodb_uri, db_name, col_name, query_text):
    client = pymongo.MongoClient(mongodb_uri)
    col = client[db_name][col_name]

    qvec = openai_embed(query_text, os.getenv("OPENAI_API_KEY"))  # 1536-dim
    pipeline = [
        {
            "$search": {
                "index": "default",
                "compound": {
                    "should": [
                        { "knnBeta": { "path": "embedding", "vector": qvec, "k": 10 } },
                        { "text": {
                            "query": query_text,
                            "path": ["text", "contextual_summary", "section_title", "page_title"],
                            "score": { "boost": { "value": 5 } }
                        } }
                    ],
                    "minimumShouldMatch": 1
                }
            }
        },
        { "$addFields": { "score": { "$meta": "searchScore" } } },
        { "$limit": 5 },
        { "$project": {
            "_id": 0,
            "chunk_text": { "$ifNull": ["$chunk_text", "$text"] },
            "section_title": 1,
            "url": 1,
            "page_numbers": 1,
            "score": 1
        } }
    ]
    return list(col.aggregate(pipeline))
