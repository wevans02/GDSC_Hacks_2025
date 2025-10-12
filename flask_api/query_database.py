import embed_vectors
import pymongo
from clients import get_mongo_client

def query_database(query_text: str, database_name: str, collection_name: str):
    mongo_client, error = get_mongo_client() # <-- Get the client here
    if not mongo_client:
        print("Error: MongoDB client is not available.")
        return [], error
    
    # This will now use the lazy-loading version of the model
    print("EMBEDDING")
    query_vector = embed_vectors.embed_text(query_text)
    print("DONE EMBEDDING AAH")
    if not query_vector:
        print("Error: Could not generate query vector.")
        return [], error

    vector_index_name = "vector_index"
    if collection_name == "bylaw_chunks":
        embedding_path = "chunk_embedding_cpu"
    else:
        embedding_path = "chunk_embedding"
    # ---- Define pipeline for the NEW collection ----
    # Vector index name (ensure it matches the one created)
    vector_index_name = "vector_index" # Or whatever name is used in vector_index.py
    # Field containing embeddings
    #embedding_path = "chunk_embedding_cpu" # Or "chunk_embedding" if you changed it

    pipeline = [
        {
            '$vectorSearch': {
                'index': vector_index_name,
                'path': embedding_path,
                'queryVector': query_vector,
                'numCandidates': 200, # Adjust as needed
                'limit': 4 # Adjust as needed - number of chunks to return
            }
        }, {
            '$project': {
                '_id': 0, # Exclude MongoDB default ID
                'original_bylaw_id': 1, # Keep original bylaw ID
                'title': 1, # Keep original bylaw title
                'pdf_url': 1, # Keep original PDF URL
                'url': 1,
                'bylaw_id': 1,
                'bylaw_title': 1,
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
        # Use the imported client directly
        result = list(mongo_client[database_name][collection_name].aggregate(pipeline))
        print("results:: ", result)
        return result, "No Error"
    except pymongo.errors.OperationFailure as op_fail:
         print(f"Error during vector search aggregation: {op_fail}")
         print("  * Check if the vector index '{vector_index_name}' exists on collection '{collection_name}' and field '{embedding_path}'.")
         return [], "No Error"
    except Exception as e:
         print(f"An unexpected error occurred during database query: {e}")
         return [], "No Error"
    # -----------------------------------------

# Example Call:
# results = query_database("can i park on bartly drive?", "bylaws", "bylaw_chunks")
# print(results)