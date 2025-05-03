# create_database_with_chunking.py (New suggested filename)

import os
import requests
import fitz  # PyMuPDF
from io import BytesIO
import pymongo
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer # Import model here
from langchain_text_splitters import RecursiveCharacterTextSplitter # Import splitter

# --- Configuration ---
load_dotenv()
DATABASE_LOGIN = os.getenv("DATABASE_LOGIN")
if not DATABASE_LOGIN:
    raise ValueError("DATABASE_LOGIN environment variable not set.")

MONGO_URI = f"mongodb+srv://{DATABASE_LOGIN}@gdsc2025.cn3wt5n.mongodb.net/?retryWrites=true&w=majority&appName=GDSC2025"

# Source parsing (assuming this returns list of dicts with 'title', 'pdf' URL)
import parse_html # Make sure this file exists and works

# Embedding Model (Initialize once)
print("Loading embedding model...")
# Ensure this matches the model used at query time!
# 'all-MiniLM-L6-v2' -> 384 dimensions
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
print("Embedding model loaded.")

# Text Splitter Configuration
# Adjust chunk_size and chunk_overlap based on experimentation
# Larger chunk_size might capture more context (like definitions) but dilute specific rules
# Smaller chunk_size focuses on specifics but might lose broader context
# Overlap helps maintain context across chunk boundaries
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  # Max characters per chunk
    chunk_overlap=200, # Characters to overlap between chunks
    length_function=len,
    is_separator_regex=False,
    separators=["\n\n", "\n", ". ", " ", ""], # How to split
)

# Database and Collection Names
DATABASE_NAME = "bylaws"
# TARGET_COLLECTION_NAME = "all_bylaws" # Old collection (don't use for chunks)
TARGET_CHUNK_COLLECTION_NAME = "bylaw_chunks" # NEW collection for chunks
VECTOR_EMBEDDING_FIELD = "chunk_embedding" # Field name for embeddings in the new collection
VECTOR_INDEX_NAME = "chunk_vector_index" # Name for the vector index on the new collection

# --- Helper Functions ---

def extract_text_from_pdf(pdf_url: str) -> str:
    """Downloads PDF from URL and extracts text using PyMuPDF."""
    try:
        response = requests.get(pdf_url, timeout=30) # Added timeout
        response.raise_for_status()
        pdf_data = BytesIO(response.content)
        full_text = ""
        with fitz.open(stream=pdf_data, filetype="pdf") as doc:
            for page_num, page in enumerate(doc):
                full_text += page.get_text() + "\n" # Add newline between pages
        return full_text
    except requests.exceptions.RequestException as e:
        print(f"Error downloading PDF from {pdf_url}: {e}")
        return None
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_url}: {e}")
        return None

def embed_text_batch(texts: list[str]) -> list[list[float]]:
    """Embeds a batch of texts using the loaded SentenceTransformer model."""
    try:
        return embedding_model.encode(texts).tolist()
    except Exception as e:
        print(f"Error during batch embedding: {e}")
        # Handle appropriately - maybe return list of None or empty lists
        return [[] for _ in texts]


# --- Main Database Creation Function ---

def create_chunked_database(html_file_name: str, db_name: str, collection_name: str):
    """
    Parses HTML, downloads PDFs, extracts text, chunks text,
    embeds chunks, and stores them in MongoDB.
    """
    print(f"Connecting to MongoDB: {db_name}")
    try:
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000) # Added timeout
        client.admin.command('ping') # Verify connection
        db = client[db_name]
        chunk_collection = db[collection_name]
        print("MongoDB connection successful.")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return # Cannot proceed without DB connection

    # 1. Parse HTML to get list of bylaws (title, pdf url)
    print(f"Parsing HTML file: {html_file_name}")
    try:
        bylaw_list = parse_html.parse_html(html_file_name)
        if not bylaw_list:
            print("No bylaw data found from HTML parsing.")
            client.close()
            return
        print(f"Found {len(bylaw_list)} bylaws to process.")
    except Exception as e:
        print(f"Error parsing HTML file {html_file_name}: {e}")
        client.close()
        return

    total_chunks_added = 0
    processed_bylaws = 0

    # 2. Process each bylaw
    for i, bylaw_info in enumerate(bylaw_list):
        bylaw_title = bylaw_info.get("title", f"Untitled Bylaw {i+1}")
        pdf_url = bylaw_info.get("pdf")

        print(f"\nProcessing Bylaw {i+1}/{len(bylaw_list)}: {bylaw_title} ({pdf_url})")

        if not pdf_url:
            print("  Skipping - Missing PDF URL.")
            continue

        # 3. Extract text from PDF
        print("  Extracting text from PDF...")
        full_text = extract_text_from_pdf(pdf_url)
        if not full_text:
            print("  Skipping - Failed to extract text.")
            continue
        print(f"  Extracted ~{len(full_text)} characters.")

        # 4. Split text into chunks
        print("  Splitting text into chunks...")
        try:
            text_chunks = text_splitter.split_text(full_text)
            print(f"  Split into {len(text_chunks)} chunks.")
        except Exception as e:
            print(f"  Error splitting text for {bylaw_title}: {e}")
            continue # Skip to next bylaw if splitting fails

        if not text_chunks:
            print("  Skipping - No text chunks generated.")
            continue

        # 5. Embed chunks (in batches for efficiency if many chunks per PDF)
        print("  Embedding text chunks...")
        # For very large numbers of chunks per PDF, consider actual batching
        chunk_embeddings = embed_text_batch(text_chunks)
        if len(chunk_embeddings) != len(text_chunks) or not all(chunk_embeddings):
             print("  Skipping - Error during embedding generation.")
             continue # Skip if embeddings failed

        # 6. Prepare chunk documents for MongoDB
        chunk_docs_to_insert = []
        for chunk_index, (text, embedding) in enumerate(zip(text_chunks, chunk_embeddings)):
            chunk_doc = {
                "bylaw_title": bylaw_title,
                "bylaw_url": pdf_url,
                "chunk_index": chunk_index, # Order within the original PDF
                "chunk_text": text,
                VECTOR_EMBEDDING_FIELD: embedding # Use configured field name
            }
            chunk_docs_to_insert.append(chunk_doc)

        # 7. Insert chunk documents into the new collection
        if chunk_docs_to_insert:
            print(f"  Inserting {len(chunk_docs_to_insert)} chunk documents into '{collection_name}'...")
            try:
                result = chunk_collection.insert_many(chunk_docs_to_insert, ordered=False) # ordered=False might be faster if errors are okay
                print(f"  Successfully inserted {len(result.inserted_ids)} chunks.")
                total_chunks_added += len(result.inserted_ids)
                processed_bylaws += 1
            except pymongo.errors.BulkWriteError as bwe:
                print(f"  Error during bulk insert: {bwe.details}")
                # Potentially log which documents failed
            except Exception as e:
                print(f"  Error inserting chunks: {e}")
        else:
             print("  No valid chunks to insert.")


    print(f"\n--- Processing Complete ---")
    print(f"Successfully processed {processed_bylaws} bylaws.")
    print(f"Total chunks added to '{db_name}.{collection_name}': {total_chunks_added}")

    # 8. Initialize Vector Index (AFTER data insertion)
    # Make sure your vector_index script can handle the new collection and field name
    print(f"\nInitializing vector index '{VECTOR_INDEX_NAME}' on '{collection_name}'...")
    try:
        # You might need to modify vector_index.py to accept field name and index name
        import vector_index # Assuming this script exists
        vector_index.initalize_vector_index(
            db_name,
            collection_name,
            VECTOR_INDEX_NAME,      # Pass index name
            VECTOR_EMBEDDING_FIELD # Pass embedding field name
        )
        print("Vector index initialization process called.")
    except ImportError:
        print("Could not import 'vector_index.py'. Skipping index initialization.")
    except Exception as e:
        print(f"Error initializing vector index: {e}")


    client.close()
    print("MongoDB connection closed.")

# --- Run the Process ---
if __name__ == "__main__":
    HTML_SOURCE_FILE = "bylaws.html" # Or get from command line args
    create_chunked_database(
        HTML_SOURCE_FILE,
        DATABASE_NAME,
        TARGET_CHUNK_COLLECTION_NAME
    )