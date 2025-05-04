import embed_vectors
#for git
from dotenv import load_dotenv
import os
#pymango
import pymongo

# query_database.py modifications

import embed_vectors
# ... (other imports: load_dotenv, os, pymongo) ...

def query_database(query_text: str, database_name: str, collection_name: str): # Changed collection_name param usage
    load_dotenv()
    DATABASE_LOGIN = os.getenv("DATABASE_LOGIN")
    uri = f"mongodb+srv://{DATABASE_LOGIN}@gdsc2025.cn3wt5n.mongodb.net/?retryWrites=true&w=majority&appName=GDSC2025"
    client = pymongo.MongoClient(uri)

    query_vector = embed_vectors.embed_text(query_text)
    if not query_vector:
        print("Error: Could not generate query vector.")
        client.close()
        return [] # Return empty list on error

    # ---- Define pipeline for the NEW collection ----
    # Vector index name (ensure it matches the one created)
    vector_index_name = "vector_index" # Or whatever name is used in vector_index.py
    # Field containing embeddings
    embedding_path = "chunk_embedding" # Or "chunk_embedding" if you changed it

    pipeline = [
        {
            '$vectorSearch': {
                'index': vector_index_name,
                'path': embedding_path,
                'queryVector': query_vector,
                'numCandidates': 200, # Adjust as needed
                'limit': 7 # Adjust as needed - number of chunks to return
            }
        }, {
            '$project': {
                '_id': 0, # Exclude MongoDB default ID
                'original_bylaw_id': 1, # Keep original bylaw ID
                'title': 1, # Keep original bylaw title
                'pdf_url': 1, # Keep original PDF URL
                'chunk_sequence': 1, # Keep chunk sequence number
                'chunk_text': 1, # <<< RETURN THE CHUNK TEXT
                'score': { # Keep the search score
                    '$meta': 'vectorSearchScore'
                }
                # 'pdf_content': 0 # <<< DO NOT return full content anymore
            }
        }
    ]
    # ---------------------------------------------

    # ---- Run pipeline on the NEW collection ----
    try:
        result = list(client[database_name][collection_name].aggregate(pipeline)) # Use the passed collection_name
        client.close()
        print("results:: ", result)
        return result
    except pymongo.errors.OperationFailure as op_fail:
         print(f"Error during vector search aggregation: {op_fail}")
         print("  * Check if the vector index '{vector_index_name}' exists on collection '{collection_name}' and field '{embedding_path}'.")
         client.close()
         return []
    except Exception as e:
         print(f"An unexpected error occurred during database query: {e}")
         client.close()
         return []
    # -----------------------------------------

# Example Call:
# results = query_database("can i park on bartly drive?", "bylaws", "bylaw_chunks")
# print(results)