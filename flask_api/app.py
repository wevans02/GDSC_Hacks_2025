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

import os, smtplib
from email.mime.text import MIMEText


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

import datetime

def send_email(subject, body):
    """Try to send an email. Fallback to writing into a log file."""
    from_addr = os.getenv("SMTP_USER")
    to_addr = os.getenv("FEEDBACK_EMAIL", from_addr)
    password = os.getenv("SMTP_PASS")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    if not (from_addr and password and to_addr):
        print("⚠️ Email not configured, logging to file instead.")
        _write_to_file(subject, body)
        return False

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(from_addr, password)
            server.sendmail(from_addr, [to_addr], msg.as_string())
        print(f"✅ Sent email: {subject}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}, logging to file instead.")
        _write_to_file(subject, body)
        return False


def _write_to_file(subject, body):
    """Fallback: save submissions into a log file inside the container."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {subject}\n{body}\n{'-'*40}\n"
    try:
        with open("submissions.log", "a", encoding="utf-8") as f:
            f.write(log_entry)
        print("📝 Saved submission to submissions.log")
    except Exception as e:
        print(f"❌ Failed to write to log file: {e}")


# --- Request a City ---
@app.route("/api/request-city", methods=["POST"])
def request_city():
    data = request.get_json()
    city = data.get("city")
    email = data.get("email")
    notes = data.get("notes")

    print("RECIEVED CITY REQ")

    if not city:
        return jsonify({"error": "City is required"}), 400

    body = f"City request:\n\nCity: {city}\nEmail: {email or 'N/A'}\nNotes: {notes or 'N/A'}"
    sent = send_email("New City Request", body)

    return jsonify({"status": "ok", "emailed": sent})

# --- Feedback ---
@app.route("/api/feedback", methods=["POST"])
def feedback():
    data = request.get_json()
    feedback_text = data.get("feedback")
    email = data.get("email")

    print("RECIEVED FEEDBACK REQ")


    if not feedback_text:
        return jsonify({"error": "Feedback is required"}), 400

    body = f"Feedback:\n\n{feedback_text}\n\nFrom: {email or 'Anonymous'}"
    sent = send_email("New Feedback", body)

    return jsonify({"status": "ok", "emailed": sent})

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
