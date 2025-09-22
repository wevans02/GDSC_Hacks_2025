# app.py
from flask import Flask, jsonify, request

# --- Import functions from your new utility files ---
# from gemini_utils import ask_gemini_with_context
# from rag_utils import get_embedding, find_relevant_bylaw_chunks
from flask_cors import CORS # Import CORS

import query_database
import python_to_gemini
# app.py modifications

from flask import Flask, jsonify, request
from flask_cors import CORS
import query_database
import python_to_gemini
# ... (other potential imports) ...
allowed_urls = [
    "https://gdsc-2025.firebaseapp.com",
    "https://gdsc-2025.web.app",
    "https://paralegalbylaw.org"
]

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": allowed_urls}}) # Simplified CORS setup

# --- API ENDPOINT ---
@app.route('/api/query', methods=['POST'])
def handle_query():
    print(f"Received request at /api/query ({request.method})")

    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    user_query = data.get('query')

    if not user_query:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    # ---- Query the NEW collection ----
    database_name = "bylaws"
    collection_name = "bylaw_chunks" # Use the new chunk collection
    print(f"Querying {database_name}.{collection_name} for: '{user_query}'")
    results = query_database.query_database(user_query, database_name, collection_name)
    # --------------------------------

    # ---- Prepare context from CHUNKS ----
    context_text = ""
    source_info = [] # Optional: Track sources
    if results:
        print(f"Retrieved {len(results)} relevant chunks.")
        # Concatenate the text of the retrieved chunks
        context_text = "\n\n---\n\n".join([chunk.get('chunk_text', '') for chunk in results if chunk.get('chunk_text')])

        # Optional: Prepare source info for display or logging
        source_info = [
            {
                "title": chunk.get("title"),
                "bylaw_id": chunk.get("original_bylaw_id"),
                "pdf_url": chunk.get("pdf_url"),
                "chunk": chunk.get("chunk_sequence"),
                "score": chunk.get("score")
            } for chunk in results
        ]
    else:
        print("No relevant chunks found.")
    # -----------------------------------

    # ---- Call Gemini with CHUNK context ----
    print("Sending query and context to Gemini...")
    # Ensure python_to_gemini.generate can handle potentially empty context_text
    ai_response = python_to_gemini.generate(user_query, context_text if context_text else "No relevant information found in bylaws.")
    print("Received response from Gemini.")
    # --------------------------------------

    # ---- Return AI response and optionally source info ----
    return jsonify({
        'ai_response': ai_response,
        'retrieved_sources': source_info # Optional: send sources back to frontend
        # 'result': context_text # Probably don't send the raw context back
    })
    # -----------------------------------------------------

# if __name__ == '__main__':
    # Make sure debug=False for production deployments
    # app.run(host='0.0.0.0', port=5000, debug=False)
    # pass
