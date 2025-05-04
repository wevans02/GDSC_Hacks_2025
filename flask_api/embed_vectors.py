from sentence_transformers import SentenceTransformer

from dotenv import load_dotenv
import os
import pymongo
# embed_vectors.py modifications

from sentence_transformers import SentenceTransformer
# ... (other imports: load_dotenv, os, pymongo) ...

model = SentenceTransformer('all-MiniLM-L6-v2')  # 384 dimensions

def embed_text(text: str) -> list[float]:
     # Handle potential empty strings gracefully
     if not text or not text.strip():
         print("Warning: Attempting to embed empty or whitespace-only text. Returning None.")
         return None # Or return a zero vector if your index requires it
     try:
        return model.encode(text).tolist()
     except Exception as e:
        print(f"Error during embedding: {e}")
        return None


def update_documents_with_embeddings(database_name: str, collection_name: str): # No changes needed here if called correctly
    load_dotenv()
    DATABASE_LOGIN = os.getenv("DATABASE_LOGIN")
    uri = f"mongodb+srv://{DATABASE_LOGIN}@gdsc2025.cn3wt5n.mongodb.net/?retryWrites=true&w=majority&appName=GDSC2025"
    client = pymongo.MongoClient(uri)
    collection = client[database_name][collection_name] # Uses the passed collection name (e.g., 'bylaw_chunks')

    # ---- Find documents (chunks) needing embedding ----
    # Embedding field name (ensure consistency with index creation and query)
    embedding_field_name = "chunk_embedding"
    # Text field to embed
    text_field_to_embed = "chunk_text"

    query = {embedding_field_name: {"$exists": False}}
    docs_to_update = collection.count_documents(query)
    print(f"Found {docs_to_update} documents in {collection_name} without embeddings.")

    updated_count = 0
    batch_size = 100 # Process in batches
    documents = list(collection.find(query).limit(batch_size)) # Fetch a batch

    while documents:
        updates = []
        for doc in documents:
            # ---- Embed the CHUNK text ----
            if text_field_to_embed in doc and doc[text_field_to_embed]:
                vector = embed_text(doc[text_field_to_embed])
                if vector: # Only update if embedding was successful
                    updates.append(
                        pymongo.UpdateOne(
                            {"_id": doc["_id"]},
                            {"$set": {embedding_field_name: vector}}
                        )
                    )
                    updated_count += 1
            else:
                 print(f"Warning: Document {doc['_id']} missing '{text_field_to_embed}' field or field is empty. Skipping embedding.")
            # ---------------------------

        if updates:
             try:
                 collection.bulk_write(updates, ordered=False)
                 print(f"  Processed batch, updated {len(updates)} embeddings (Total: {updated_count}/{docs_to_update}).")
             except pymongo.errors.BulkWriteError as bwe:
                 print(f"  Bulk write error during embedding update: {bwe.details}")
             except Exception as e:
                 print(f"  An error occurred during embedding bulk update: {e}")

        if updated_count >= docs_to_update:
             break # Exit if all documents initially found have been processed

        # Fetch the next batch
        documents = list(collection.find(query).limit(batch_size))


    print(f"Finished updating embeddings for {collection_name}. Total updated: {updated_count}")
    client.close()

# Example call (usually called from create_database.py):
# update_documents_with_embeddings("bylaws", "bylaw_chunks")