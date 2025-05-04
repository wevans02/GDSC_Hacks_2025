import parse_html
# import vector_index
import embed_vectors
from chunk_text import chunk_text
from dotenv import load_dotenv
import os
#for pdf
import requests
import fitz  # PyMuPDF
from io import BytesIO

import pymongo

# create_database.py modifications

import parse_html
# import vector_index # Assuming this handles index creation
import embed_vectors
# ... (other imports: load_dotenv, os, requests, fitz, BytesIO, pymongo) ...


# -----------------------------------------------------------------------------

def create_chunked_database(html_file_name: str, database_name: str, new_collection_name: str): # Changed function name and param
    load_dotenv()
    DATABASE_LOGIN = os.getenv("DATABASE_LOGIN")
    uri = f"mongodb+srv://{DATABASE_LOGIN}@gdsc2025.cn3wt5n.mongodb.net/?retryWrites=true&w=majority&appName=GDSC2025"
    client = pymongo.MongoClient(uri)
    database = client[database_name]

    # ---- Use the NEW collection ----
    collection = database[new_collection_name]
    # Optional: Drop existing collection if recreating
    # collection.drop()
    # print(f"Dropped existing collection: {new_collection_name}")
    # -----------------------------

    data = parse_html.parse_html(html_file_name)
    chunk_docs_to_insert = []
    processed_count = 0

    print(f"Processing {len(data)} bylaws from {html_file_name}...")

    for law in data:
        processed_count += 1
        print(f"Processing bylaw {processed_count}/{len(data)}: ID {law['_id']}")
        try:
            url = law["pdf"]
            response = requests.get(url, timeout=30) # Added timeout
            response.raise_for_status()

            pdf_data = BytesIO(response.content)
            doc = fitz.open(stream=pdf_data, filetype="pdf")

            full_text = ""
            for page_num, page in enumerate(doc):
                 try:
                     full_text += page.get_text()
                 except Exception as page_err:
                     print(f"  Warning: Error extracting text from page {page_num + 1} of {law['_id']}. Skipping page. Error: {page_err}")
            doc.close()

            if not full_text.strip():
                 print(f"  Warning: No text extracted from {law['_id']}. Skipping.")
                 continue

            # ---- Chunk the extracted text ----
            chunk_size = 1000  # Example size
            chunk_overlap = 100 # Example overlap
            text_chunks = chunk_text(full_text, chunk_size, chunk_overlap)
            print(f"  Extracted text, generated {len(text_chunks)} chunks.")
            # --------------------------------

            # ---- Create documents for each chunk ----
            for i, chunk in enumerate(text_chunks):
                 chunk_doc = {
                     "original_bylaw_id": law["_id"],
                     "title": law["title"],
                     "pdf_url": law["pdf"],
                     "chunk_sequence": i + 1,
                     "chunk_text": chunk,
                     # plot_embedding will be added later by embed_vectors.py
                 }
                 chunk_docs_to_insert.append(chunk_doc)
            # ---------------------------------------

        except requests.exceptions.RequestException as req_err:
             print(f"  Error downloading {law['_id']} from {url}: {req_err}")
        except fitz.fitz.FitzError as pdf_err: # More specific fitz error
             print(f"  Error opening or processing PDF {law['_id']}: {pdf_err}")
        except Exception as e:
             print(f"  An unexpected error occurred processing {law['_id']}: {e}")

    # ---- Insert all chunk documents ----
    if chunk_docs_to_insert:
        print(f"\nInserting {len(chunk_docs_to_insert)} chunk documents into {database_name}.{new_collection_name}...")
        try:
            collection.insert_many(chunk_docs_to_insert, ordered=False) # ordered=False might speed up bulk inserts
            print("Insertion complete.")
        except pymongo.errors.BulkWriteError as bwe:
            print(f"  Bulk write error during insertion: {bwe.details}")
        except Exception as insert_err:
            print(f"  An error occurred during bulk insertion: {insert_err}")
    else:
        print("\nNo chunk documents were generated to insert.")
    # ----------------------------------

    # ---- Initialize Vector Index on the NEW collection ----
    print(f"Initializing vector index on {database_name}.{new_collection_name}...")
    # Ensure vector_index.initialize_vector_index is adapted for the new collection
    # and the embedding field name (e.g., 'plot_embedding' or maybe 'chunk_embedding')
    # vector_index.initialize_vector_index(database_name, new_collection_name, embedding_field="plot_embedding") # Example adaptation
    print("(Skipping actual index initialization call as 'vector_index.py' is not provided)")
    # ----------------------------------------------------

    # ---- Update NEW collection documents with embeddings ----
    print(f"Updating documents with embeddings in {database_name}.{new_collection_name}...")
    # Ensure embed_vectors.update_documents_with_embeddings uses the new collection
    embed_vectors.update_documents_with_embeddings(database_name, new_collection_name)
    # -------------------------------------------------------

    client.close()
    print("Database creation process finished.")

# --- Call the updated function with a new collection name ---
# create_chunked_database("lawmcode.htm", "bylaws", "bylaw_chunks")
# print("Run the above line uncommented to start the process.")
# ---------------------------------------------------------
create_chunked_database("lawmcode.htm", "bylaws", "bylaw_chunks") # <-- Make sure this line is NOT commented out
