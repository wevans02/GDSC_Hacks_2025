# rag_utils.py
import os
import pymongo
from dotenv import load_dotenv
import certifi # Import certifi

# Import the specific embedding function from your embed_vectors module
from flask_api.embed_vectors import embed_text as generate_embedding_vector

# --- Initialization ---
print("Initializing RAG Utils...")
load_dotenv() # Load environment variables from .env file

DATABASE_LOGIN = os.getenv("DATABASE_LOGIN")
if not DATABASE_LOGIN:
    raise ValueError("DATABASE_LOGIN environment variable not set.")

# Construct MongoDB URI
MONGO_URI = f"mongodb+srv://{DATABASE_LOGIN}@gdsc2025.cn3wt5n.mongodb.net/?retryWrites=true&w=majority&appName=GDSC2025"

# Initialize MongoDB client once, explicitly providing TLS CA file
try:
    print("Connecting to MongoDB using certifi...")
    # Pass tlsCAFile=certifi.where() to use certifi's certificate bundle
    client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())

    # Test connection with a ping command right after connecting
    client.admin.command('ping')
    print("MongoDB connection successful (ping successful).")

except pymongo.errors.ConfigurationError as e:
     print(f"MongoDB Configuration Error (check URI or credentials): {e}")
     client = None
except pymongo.errors.ServerSelectionTimeoutError as e:
     print(f"MongoDB Connection Failed (Timeout/SSL Handshake): {e}")
     client = None
except Exception as e:
    print(f"An unexpected error occurred connecting to MongoDB: {e}")
    client = None # Indicate failure

# Define default database/collection - adjust as needed
DEFAULT_DB_NAME = "bylaws"
DEFAULT_COLLECTION_NAME = "1-304" # Example - you might need logic to select the right collection

# Define the name of the vector index in MongoDB Atlas
VECTOR_INDEX_NAME = 'vector_index'
# Define the path to the vector field in your documents
VECTOR_FIELD_PATH = 'plot_embedding' # Make sure this matches your DB schema and index config

print("RAG Utils Initialized.")
# --------------------

def get_embedding(text: str) -> list[float]:
    """
    Generates an embedding vector for the user's query text.
    (This function now directly calls the real embedding logic).

    Args:
        text: The user's query string.

    Returns:
        A list of floats representing the embedding vector.
    """
    print(f"Generating embedding for query: '{text[:50]}...'")
    # Add error handling for embedding generation if needed
    try:
        return generate_embedding_vector(text)
    except Exception as e:
        print(f"Error during text embedding: {e}")
        # Decide how to handle - return None, empty list, or raise
        return None


def find_relevant_bylaw_chunks(query_vector: list[float],
                               database_name: str = DEFAULT_DB_NAME,
                               collection_name: str = DEFAULT_COLLECTION_NAME,
                               limit: int = 5,
                               candidates: int = 200 # Adjusted numCandidates
                               ) -> list[dict]:
    """
    Queries the MongoDB vector store to find relevant document chunks.

    Args:
        query_vector: The embedding vector of the user's query.
        database_name: The name of the database to query.
        collection_name: The name of the collection to query.
        limit: The maximum number of relevant chunks to return.
        candidates: The number of candidates to consider during the search.

    Returns:
        A list of dictionaries, where each dictionary represents a relevant chunk
        and includes 'title', 'text' (mapped from 'pdf'), and 'score'.
        Returns an empty list if the DB connection failed or no results found.
    """
    if client is None:
        print("MongoDB client not initialized. Cannot query database.")
        return []
    # Check if query_vector is valid before proceeding
    if not query_vector:
        print("Invalid or empty query vector provided. Cannot query database.")
        return []


    print(f"Searching DB '{database_name}.{collection_name}' with vector starting: {query_vector[:3]}...")

    # Define the MongoDB Atlas Vector Search pipeline
    pipeline = [
        {
            '$vectorSearch': {
                'index': VECTOR_INDEX_NAME,
                'path': VECTOR_FIELD_PATH,
                'queryVector': query_vector,
                'numCandidates': candidates,
                'limit': limit
            }
        },
        {
            # Project the fields needed for context and scoring
            # IMPORTANT: Adjust field names ('title', 'pdf') to match your actual schema.
            # We are assuming 'pdf' contains the text chunk here.
            '$project': {
                '_id': 0, # Exclude the default MongoDB ID
                'title': 1, # Assuming this holds bylaw ID / section title
                'text': '$pdf', # Map the 'pdf' field to 'text' for consistency
                'score': {
                    '$meta': 'vectorSearchScore' # Include the relevance score
                }
            }
        }
    ]

    try:
        # Select the database and collection
        db = client[database_name]
        collection = db[collection_name]

        # Execute the aggregation pipeline
        results = list(collection.aggregate(pipeline))
        print(f"Found {len(results)} relevant chunks.")
        return results

    except Exception as e:
        print(f"Error during MongoDB vector search: {e}")
        return [] # Return empty list on error

