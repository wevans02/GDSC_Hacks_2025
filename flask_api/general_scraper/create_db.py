"""
create_bylaw_database.py
Creates a MongoDB collection with both semantic (OpenAI embeddings)
and keyword (BM25) retrieval capabilities.
"""

import os
import json
from tqdm import tqdm
from dotenv import load_dotenv
from openai import OpenAI
from rank_bm25 import BM25Okapi
import pymongo

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------- MongoDB setup ----------------
DATABASE_LOGIN = os.getenv("DATABASE_LOGIN")
MONGO_URI = f"mongodb+srv://{DATABASE_LOGIN}@paralegal-RAG.cn3wt5n.mongodb.net/?retryWrites=true&w=majority"
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["bylaws"]
collection = db["bylaw_chunks_gpt"]

# Optional: Drop old collection
# collection.drop()

# ---------------- Load extracted files ----------------
data_dir = "llm_extracted_data"
files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith(".json")]

print(f"Found {len(files)} extracted files.")

all_docs = []

for file_path in tqdm(files, desc="Loading JSON files"):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for chunk in data.get("chunks", []):
        text = chunk.get("text", "")
        summary = chunk.get("contextual_summary", "")
        context = f"{summary}\n{text}"  # combine for richer embeddings

        # Add to Mongo insert batch
        doc = {
            "city": "Toronto",
            "page_title": data.get("page_title"),
            "url": data.get("url"),
            "section_title": chunk.get("section_title"),
            "content_type": chunk.get("content_type"),
            "page_numbers": chunk.get("page_numbers", []),
            "contextual_summary": summary,
            "text": text,
            "combined_text": context,
        }
        all_docs.append(doc)

print(f"Prepared {len(all_docs)} chunks for embedding and insertion.")

# ---------------- Compute OpenAI embeddings ----------------
batch_size = 100
for i in tqdm(range(0, len(all_docs), batch_size), desc="Embedding in batches"):
    batch = all_docs[i : i + batch_size]
    texts = [d["combined_text"] for d in batch]

    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=texts
    )
    embeddings = [item.embedding for item in response.data]

    for j, emb in enumerate(embeddings):
        batch[j]["embedding"] = emb

    collection.insert_many(batch)

print("✅ All documents inserted with OpenAI embeddings.")

# ---------------- BM25 Keyword Index (in-memory) ----------------
# Optional: build a BM25 index you can serialize to disk for keyword fallback

corpus = [d["combined_text"] for d in all_docs]
tokenized = [doc.lower().split() for doc in corpus]
bm25 = BM25Okapi(tokenized)
print("✅ BM25 index ready (not stored in DB, but can be dumped if needed).")
