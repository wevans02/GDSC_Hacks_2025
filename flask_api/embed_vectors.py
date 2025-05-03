from sentence_transformers import SentenceTransformer

from dotenv import load_dotenv
import os
import pymongo

model = SentenceTransformer('all-MiniLM-L6-v2')  # 384 dimensions

def embed_text(text: str) -> list[float]:
    return model.encode(text).tolist()

def update_documents_with_embeddings(database_name: str, collection_name: str):
    load_dotenv()

    DATABASE_LOGIN = os.getenv("DATABASE_LOGIN") #DATABASE_LOGIN is in the form username:password

    uri = f"mongodb+srv://{DATABASE_LOGIN}@gdsc2025.cn3wt5n.mongodb.net/?retryWrites=true&w=majority&appName=GDSC2025"

    client = pymongo.MongoClient(uri)
    collection = client[database_name][collection_name]
    
    for doc in collection.find({"plot_embedding": {"$exists": False}}):
        if "pdf" in doc:
            vector = embed_text(doc["pdf"])  # or use another field
            collection.update_one({"_id": doc["_id"]}, {"$set": {"plot_embedding": vector}})
            print(f"Updated document {doc['_id']}")
    
    client.close()