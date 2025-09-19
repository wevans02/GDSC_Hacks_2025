# to reembed using the minilm cpu version to keep embedding model same as production RAG embedding model
import os
import pymongo
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import torch
from tqdm import tqdm  # progress bars

load_dotenv()

# ---- MongoDB setup ----
DATABASE_LOGIN = os.getenv("DATABASE_LOGIN")
uri = f"mongodb+srv://{DATABASE_LOGIN}@gdsc2025.cn3wt5n.mongodb.net/?retryWrites=true&w=majority&appName=GDSC2025"
print("Database login:", DATABASE_LOGIN)
client = pymongo.MongoClient(uri, tls=True, tlsAllowInvalidCertificates=False)
print("MongoDB connection successful ✅")

db = client["bylaws"]          # <-- your DB name
collection = db["bylaw_chunks"]  # <-- your collection

# ---- Embedding model (force CPU) ----
print("Loading embedding model (all-MiniLM-L6-v2) on CPU...")
model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
torch.set_num_threads(1)  # stay lightweight on Render
print("Model loaded ✅")

# ---- Pipeline ----
def reembed_documents(batch_size=100):
    query = {"chunk_text": {"$exists": True}}  # only docs with text
    total_docs = collection.count_documents(query)
    print(f"Found {total_docs} documents to re-embed.")

    cursor = collection.find(query, {"_id": 1, "chunk_text": 1}).batch_size(batch_size)

    count = 0
    updates = []

    for doc in tqdm(cursor, total=total_docs, desc="Re-embedding"):
        text = doc["chunk_text"].strip()
        if not text:
            continue

        try:
            vec = model.encode(text).tolist()
            updates.append(
                pymongo.UpdateOne(
                    {"_id": doc["_id"]},
                    {"$set": {"chunk_embedding_cpu": vec}}
                )
            )
        except Exception as e:
            tqdm.write(f"⚠️ Error embedding doc {doc['_id']}: {e}")

        # Commit in batches
        if len(updates) >= batch_size:
            collection.bulk_write(updates, ordered=False)
            count += len(updates)
            tqdm.write(f"✅ Committed {count}/{total_docs} documents...")
            updates = []

    # Final batch
    if updates:
        collection.bulk_write(updates, ordered=False)
        count += len(updates)
        tqdm.write(f"✅ Committed {count}/{total_docs} documents (final batch).")

    print("🎉 Re-embedding complete!")

if __name__ == "__main__":
    reembed_documents(batch_size=100)
    client.close()
