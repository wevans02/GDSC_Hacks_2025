# vector_index.py
from dotenv import load_dotenv
import os
from pymongo.mongo_client import MongoClient
from pymongo.operations import SearchIndexModel
import time

def initalize_vector_index(database_name: str,
                           collection_name: str,
                           index_name: str, # New parameter
                           vector_field_path: str, # New parameter
                           num_dimensions: int = 384, # Default dimension for all-MiniLM-L6-v2
                           similarity: str = "cosine" # Changed default similarity
                           ):
    """
    Initializes or updates an Atlas Vector Search index on the specified collection.

    Args:
        database_name: Name of the MongoDB database.
        collection_name: Name of the collection to index.
        index_name: The desired name for the vector search index.
        vector_field_path: The document field containing the vectors (e.g., "chunk_embedding").
        num_dimensions: The dimensionality of the vectors.
        similarity: The similarity metric to use ('cosine', 'dotProduct', 'euclidean').
    """
    print(f"\n--- Initializing Vector Index ---")
    print(f"Database: {database_name}, Collection: {collection_name}")
    print(f"Index Name: {index_name}, Field: {vector_field_path}")
    print(f"Dimensions: {num_dimensions}, Similarity: {similarity}")

    load_dotenv()
    DATABASE_LOGIN = os.getenv("DATABASE_LOGIN")
    if not DATABASE_LOGIN:
        print("Error: DATABASE_LOGIN environment variable not set.")
        return

    uri = f"mongodb+srv://{DATABASE_LOGIN}@gdsc2025.cn3wt5n.mongodb.net/?retryWrites=true&w=majority&appName=GDSC2025"

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping') # Verify connection
        database = client[database_name]
        collection = database[collection_name]
        print("MongoDB connection successful.")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return

    # Check if index already exists
    try:
        existing_indexes = list(collection.list_search_indexes(name=index_name))
        if existing_indexes:
            print(f"Index '{index_name}' already exists. Verifying configuration...")
            # Optional: Add logic here to check if the existing index definition matches
            # If it doesn't match, you might want to drop and recreate it (use with caution!)
            # collection.drop_search_index(index_name)
            # print(f"Dropped existing index '{index_name}' to recreate.")
            print("Skipping index creation as it already exists.")
            client.close()
            return # Exit if index exists and you don't want to modify it
    except Exception as e:
        print(f"Error checking for existing index '{index_name}': {e}")
        # Continue to attempt creation, might fail if it exists but listing failed

    # Define the index model using the parameters
    search_index_model = SearchIndexModel(
        definition={
            "fields": [
                {
                    "type": "vector",
                    "path": vector_field_path, # Use parameter
                    "numDimensions": num_dimensions, # Use parameter
                    "similarity": similarity # Use parameter
                    # "quantization": "scalar" # Removed for broader compatibility, add if needed
                }
                # You could add other fields here for filtering if needed
                # e.g., { "type": "filter", "path": "bylaw_title" }
            ]
        },
        name=index_name, # Use parameter
        type="vectorSearch"
    )

    try:
        print(f"Creating search index '{index_name}'...")
        result_name = collection.create_search_index(model=search_index_model)
        print(f"Request submitted for index '{result_name}'. Building...")

        # Wait for index to become queryable
        print("Polling to check if the index is ready (up to several minutes)...")
        while True:
            try:
                index_status = list(collection.list_search_indexes(name=index_name))
                if index_status and index_status[0].get("queryable") is True and index_status[0].get("status") == "READY":
                    print(f"Index '{index_name}' is ready for querying.")
                    break
                elif index_status and index_status[0].get("status") == "FAILED":
                     print(f"Error: Index '{index_name}' failed to build.")
                     print(index_status[0].get("statusMessage"))
                     break # Stop polling on failure
                else:
                    print(f"  Index status: {index_status[0].get('status') if index_status else 'Not Found'}. Waiting...")

            except Exception as poll_error:
                print(f"  Error polling index status: {poll_error}")
                # Decide whether to continue polling or break

            time.sleep(10) # Increase poll interval

    except Exception as e:
        print(f"Error creating search index '{index_name}': {e}")
    finally:
        client.close()
        print("MongoDB connection closed.")

# Example usage (if run directly)
# if __name__ == "__main__":
#     DB = "bylaws"
#     COLL = "bylaw_chunks" # Target the new collection
#     INDEX = "chunk_vector_index" # New index name
#     FIELD = "chunk_embedding" # New field name
#     initalize_vector_index(DB, COLL, INDEX, FIELD)
