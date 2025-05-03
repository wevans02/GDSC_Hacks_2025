# OLD --- NOT USED


# this will get the documents from the existing collection, go to each pdf url and parse the text.
# parsed text will be returned as a json:
# [
#     {
#         "_id": "19-2025",
#         "original_url": "https://www.toronto.ca/legdocs/bylaws/2025/law0019.pdf",
#         "extracted_text": "City of Toronto By-law 19-2025\n\nTo amend City of Toronto Municipal Code Chapter 925, Permit Parking, regarding implementation\nof permit parking on Lappin Avenue between Lansdowne Avenue and Ford Street.\n\nWhereas under section 7(1) of the City of Toronto Act, 2006, City Council has been granted...\n\n...[rest of the extracted text from the PDF]...\n\nEnacted and passed on January 1, 2025.\nFrances Nunziata, Mike Williams,\nSpeaker City Clerk\n(Seal of the City)"
#     },
#     {
#         "_id": "20-2025",
#         "original_url": "https://www.toronto.ca/legdocs/bylaws/2025/law0020.pdf",
#         "extracted_text": "City of Toronto By-law 20-2025\n\nTo adopt Official Plan Amendment No. 543 regarding lands municipally known in the year\n2024 as 123 Main Street.\n\nWhereas authority is given to Council under the Planning Act, R.S.O. 1990, c. P.13, as amended...\n\n...[rest of the extracted text from the PDF]..."
#     }
#     // ... more documents
# ]

# this will later be used to create an embedding for the vector store

import pymongo
import requests
import fitz  # PyMuPDF
import json
import io # To handle PDF bytes in memory
import os

# --- Configuration ---
MONGO_URI = "mongodb+srv://<db_username>:<db_password>@gdsc2025.cn3wt5n.mongodb.net/?retryWrites=true&w=majority&appName=GDSC2025/"  # Replace with your MongoDB connection string if different
DB_NAME = "your_database_name"          # Replace with your database name
COLLECTION_NAME = "your_collection_name"  # Replace with your collection name
OUTPUT_JSON_FILE = "pdf_texts.json"
REQUEST_TIMEOUT = 30 # Timeout in seconds for downloading PDFs

# --- Optional: Create directory for failed downloads (for debugging) ---
FAILED_PDF_DIR = "failed_pdfs"
# os.makedirs(FAILED_PDF_DIR, exist_ok=True) # Uncomment if you want to save failed PDFs

# --- Main Script ---

def extract_text_from_pdf_url(pdf_url, doc_id):
    """Downloads a PDF from a URL and extracts text using PyMuPDF."""
    try:
        print(f"  Downloading: {pdf_url}")
        response = requests.get(pdf_url, stream=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        # Read PDF content into memory
        pdf_bytes = response.content

        print(f"  Parsing PDF content...")
        text = ""
        # Use a try-except block specifically for PyMuPDF operations
        try:
            # Open the PDF from bytes
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")

            # Iterate through pages and extract text
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                text += page.get_text() + "\n\n" # Add newline between pages for clarity

            pdf_document.close()
            print(f"  Successfully extracted text (approx {len(text)} chars).")
            return text.strip() # Remove leading/trailing whitespace

        except Exception as pdf_err:
            print(f"  ERROR parsing PDF for doc_id {doc_id} from {pdf_url}: {pdf_err}")
            # Optionally save the problematic PDF for inspection
            # with open(os.path.join(FAILED_PDF_DIR, f"{doc_id}_error.pdf"), "wb") as f:
            #     f.write(pdf_bytes)
            return None # Indicate failure

    except requests.exceptions.RequestException as req_err:
        print(f"  ERROR downloading PDF for doc_id {doc_id} from {pdf_url}: {req_err}")
        return None # Indicate failure
    except Exception as e:
        print(f"  UNEXPECTED ERROR processing doc_id {doc_id} ({pdf_url}): {e}")
        return None

def process_documents():
    """Connects to MongoDB, fetches documents, extracts PDF text, and saves to JSON."""
    results = []
    processed_count = 0
    error_count = 0

    try:
        print(f"Connecting to MongoDB ({MONGO_URI})...")
        client = pymongo.MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        print(f"Connected to DB: '{DB_NAME}', Collection: '{COLLECTION_NAME}'")

        total_docs = collection.count_documents({})
        print(f"Found {total_docs} documents to process.")

        for doc in collection.find({}, {"_id": 1, "pdf": 1}): # Only fetch necessary fields
            doc_id = doc.get('_id')
            pdf_url = doc.get('pdf')
            processed_count += 1

            print(f"\nProcessing document {processed_count}/{total_docs} | ID: {doc_id}")

            if not doc_id:
                print("  Skipping document with missing '_id'.")
                error_count += 1
                continue

            if not pdf_url or not pdf_url.startswith(('http://', 'https://')):
                print(f"  Skipping doc_id {doc_id}: Invalid or missing 'pdf' URL ('{pdf_url}').")
                error_count += 1
                continue

            # Extract text
            extracted_text = extract_text_from_pdf_url(pdf_url, doc_id)

            if extracted_text is not None:
                results.append({
                    "_id": doc_id,
                    "original_url": pdf_url,
                    "extracted_text": extracted_text
                    # Add other fields from the original doc if needed
                    # "title": doc.get("title")
                })
            else:
                error_count += 1
                # Optionally add placeholder for failed docs
                # results.append({"_id": doc_id, "original_url": pdf_url, "extracted_text": None, "error": True})


        print(f"\n--- Processing Complete ---")
        print(f"Successfully processed: {len(results)}")
        print(f"Errors/Skipped: {error_count}")

        # Save results to JSON file
        print(f"\nSaving extracted text to {OUTPUT_JSON_FILE}...")
        try:
            with open(OUTPUT_JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
            print("Successfully saved JSON file.")
        except IOError as io_err:
            print(f"ERROR saving JSON file: {io_err}")

    except pymongo.errors.ConnectionFailure as conn_err:
        print(f"FATAL: Could not connect to MongoDB: {conn_err}")
    except Exception as e:
        print(f"An unexpected error occurred during processing: {e}")
    finally:
        if 'client' in locals() and client:
            client.close()
            print("MongoDB connection closed.")

if __name__ == "__main__":
    process_documents()