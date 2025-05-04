# app.py
from flask import Flask, jsonify, request

# --- Import functions from your new utility files ---
# from gemini_utils import ask_gemini_with_context
# from rag_utils import get_embedding, find_relevant_bylaw_chunks
from flask_cors import CORS # Import CORS

import query_database
import python_to_gemini

# ----------------------------------------------------

app = Flask(__name__)
#CORS(app) # Enable CORS for all routes and origins by default

CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},   # or your real origin
    allow_headers=[
        "Content-Type",        # JSON payload
        "Authorization",       # Bearer / API key (if you send it)
        "Accept",              # Flutter/axios often adds this
        "X-Requested-With"     # common in some JS libs
    ],
    expose_headers=["Content-Length"]          # anything clients need to read
)

# (Remove the definitions of the functions you moved out)

# --- API ENDPOINT ---
@app.route('/api/query', methods=['POST'])
def handle_query():
    """Receives user query, performs mock RAG, returns answer and sources."""
    print(f"Received request at /api/query ({request.method})")


    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    user_query = data.get('query')

    result = query_database.query_database(user_query, "bylaws", "all_bylaws")

    extra_info_text = ""

    # Loop through bylaws_data and concatenate all the information into extra_info_text
    for i in result:
        extra_info_text += "\n" + i["pdf"]  # Concatenate each item to the string

    ai_response = python_to_gemini.generate(user_query,result)


   
    return jsonify({
        'result': extra_info_text,
        'ai_response': ai_response
    })


# --- Main execution block ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

# 4. Serving for Production (Using a WSGI Server)

# Flask's built-in server is not suitable for production. It's not designed to handle many requests efficiently or securely. You need a production-grade WSGI (Web Server Gateway Interface) server. Popular choices are Gunicorn (Linux/macOS) and Waitress (cross-platform).

# Option A: Using Gunicorn (Common on Linux/macOS)

# Install Gunicorn:

# Bash

# pip install gunicorn
# Run Gunicorn:
# Make sure app.py does not have debug=True set in app.run() if you were using that method (Gunicorn ignores app.run() anyway, but it's good practice to remove it or wrap it in if __name__ == '__main__':).

# The command tells Gunicorn where to find your Flask app instance. The format is module_name:variable_name.

# Bash

# # Basic command - runs on 127.0.0.1:8000 with 1 worker
# gunicorn app:app

# # More typical command:
# # -w 4: Use 4 worker processes (adjust based on your server's CPU cores)
# # -b 0.0.0.0:8000: Bind to all network interfaces on port 8000
# gunicorn -w 4 -b 0.0.0.0:8000 app:app
# Your API is now served by Gunicorn on http://<your-server-ip>:8000.

# Option B: Using Waitress (Works on Windows, Linux, macOS)

# Install Waitress:
# Bash

# pip install waitress
# Run Waitress:
# Bash

# # Basic command - runs on 0.0.0.0:8080 by default
# waitress-serve app:app

# # Specify host and port
# waitress-serve --host 0.0.0.0 --port 8000 app:app
# Your API is now served by Waitress on http://<your-server-ip>:8000.
# Further Production Steps (Beyond the Scope of "Simple")

# In a real production deployment, you would typically:

# Run the WSGI server (Gunicorn/Waitress) behind a reverse proxy like Nginx or Apache. The reverse proxy handles incoming connections, can serve static files, manage SSL/TLS encryption (HTTPS), and distribute requests to one or more WSGI server processes.
# Manage the WSGI server process using a process manager like systemd (Linux) or Supervisor to ensure it restarts if it crashes and runs in the background.
# Configure logging properly.
# Secure your API (authentication, authorization, rate limiting, etc.).