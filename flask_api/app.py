'''
This is the main flask file that holds the api endpoint code.

Endpoints:
===================================================================
/api/query/ 
The main endpoint that orchestrates the RAG pipeline, retrieving and explaining to user.
takes:
    user_query:             what the user is actually asking
    city                    the city to retrieve for, each city has its own collection in the DB
    conversation_context:   previous messages to give context
    timestamp:              time sent, mostly for logging
===================================================================
/api/feedback/
Takes any user feedback and optional email and sends myself an email alert.
takes: 
    feedback_text:          user feedback string
    email:                  optional user email, to be notified when I recieve and make updates
===================================================================
/api/request-city/
Takes user requests for a city to be added to paralegal, sends myself an email alert
    city:                   The Actual city being requested
    email:                  Optional user email to be notified when I add the city
    notes:                  Any extra notes the user adds
===================================================================

Other Features:
- Logging: local file of logs saved to file and console prints.
    - Logs also sync to google sheet in my google drive so I have backups and can see from anywhere

'''

# app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os

# RAG utils
import flask_api.rag_pipeline.get_explanation as get_explanation
from flask_api.rag_pipeline.embed_and_query import query_hybrid

# Our utilities
from utils.config import ALLOWED_URLS, DB_NAME
from utils.logging import log_event
from utils.send_email import send_email

# City name from frontend to collection name in backend; 
# they should be the same but from legacy some werent so I added this mapper just to be safe/flexible
city_to_collection = {
    "Toronto": "bylaw_chunks",
    "Waterloo": "Waterloo",
    'Guelph': 'guelph'
}

app = Flask(__name__)
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": ALLOWED_URLS,
            "supports_credentials": True,
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type"],
            "max_age": 86400,
        }
    },
)

# ===================================================================
# Request a City 
@app.route("/api/request-city", methods=["POST"])
def request_city():
    data = request.get_json(force=True, silent=True) or {}
    city = data.get("city")
    email = data.get("email")
    notes = data.get("notes")

    if not city:
        return jsonify({"error": "City is required"}), 400

    body = f"City request:\n\nCity: {city}\nEmail: {email or 'N/A'}\nNotes: {notes or 'N/A'}"
    emailed = send_email("New City Request", body)

    # Always log, and if email failed, also keep a pretty block in submissions.log
    pretty_block = f"[request-city]\n{body}\n{'-'*40}\n" if not emailed else None
    log_event(
        query=f"[request-city] {city}",
        response=f"emailed={emailed}",
        other_logs={"email": email, "notes": notes},
        also_submissions_block=pretty_block,
    )

    return jsonify({"status": "ok", "emailed": emailed})

# ===================================================================
# Feedback
@app.route("/api/feedback", methods=["POST"])
def feedback():
    data = request.get_json(force=True, silent=True) or {}
    feedback_text = data.get("feedback")
    email = data.get("email")

    if not feedback_text:
        return jsonify({"error": "Feedback is required"}), 400

    body = f"Feedback:\n\n{feedback_text}\n\nFrom: {email or 'Anonymous'}"
    emailed = send_email("New Feedback", body)

    log_event(
        query="[feedback]",
        response=f"emailed={emailed}",
        other_logs={"from": email, "feedback": feedback_text},
        also_submissions_block=(f"[feedback]\n{body}\n{'-'*40}\n" if not emailed else None),
    )

    return jsonify({"status": "ok", "emailed": emailed})

# ===================================================================
# MAIN QUERY ENDPOINT
@app.route("/api/query", methods=["POST"])
def handle_query():
    if not request.is_json:
        return jsonify({"status": "error", "error": {"message": "Request must be JSON"}}), 400

    data = request.get_json() or {}
    user_query = (data.get("query") or "").strip()
    city = data.get("city", "Unknown City")
    conversation_context = data.get("conversation_context", [])
    timestamp = data.get("timestamp")  # client time okay; logger will default if None

    # error checking
    if city not in city_to_collection:
        return jsonify({"status": "error", "error": {"message": "City Not found"}}), 400
    if not user_query:
        return jsonify({"status": "error", "error": {"message": "Missing 'query' in request body"}}), 400

    # Vector + BM25 semantic and keyword search 
    db_name = DB_NAME
    col_name = city_to_collection[city]
    try:
        # embed, query, and return most relevant chunks from the database
        results = query_hybrid(
            mongodb_uri=f"mongodb+srv://{os.getenv('DATABASE_LOGIN')}@paralegal-rag.ujgail4.mongodb.net/?retryWrites=true&w=majority&appName=Paralegal-RAG",
            query_text=user_query,
            db_name=db_name,
            col_name=col_name,
        )
    except Exception as e:
        results = []
        vector_err = str(e)
    else:
        vector_err = None

    # Handle DB failure, log, email me immediately, notify user.
    if not results:
        degraded_msg = "DB Error, could not connect to mongodb atlas cluster."
        ai_response = (
            "I apologize, the bylaw database is currently down.\n"
            "I've been sent an email automatically and I'll fix the issue as soon as I can.\n"
            "Thanks for your patience."
        )
        log_obj = {
            "status": "degraded",
            "message": degraded_msg,
            "ai_response": ai_response,
            "ai_error": None,
            "retrieved_sources": [],
            "city": city,
            "timestamp": timestamp,
            "vector_error": vector_err,
        }
        log_event(
            query=user_query,
            response=ai_response,
            other_logs=log_obj,
            timestamp=timestamp,
        )
        send_email(
            subject="[DB FAILURE] Paralegal Mongo Cluster failed",
            body=f"DB: {db_name}.{col_name}\nUser query: {user_query}\nError: {vector_err}"
        )
        return jsonify({
            "status": "degraded",
            "message": degraded_msg,
            "ai_response": ai_response,
            "ai_error": None,
            "retrieved_sources": [],
            "city": city,
            "timestamp": timestamp,
        }), 200

    # Prepare bylaw chunks / source_info to be passed to GPT

    # combine found DB chunks to one string
    context_text = "\n\n---\n\n".join(
        [chunk.get("chunk_text", "") for chunk in results if chunk.get("chunk_text")]
    )

    # get the info for each city, slightly different for now
    if city == "Toronto":
        source_info = [{"title": c.get("title"),
                        "bylaw_id": c.get("original_bylaw_id"),
                        "pdf_url": c.get("pdf_url")} for c in results]
    else:
        # Waterloo & Guelph normalized to these keys
        source_info = [{"title": c.get("bylaw_title"),
                        "bylaw_id": c.get("bylaw_id"),
                        "pdf_url": c.get("url")} for c in results]

    # create context from past messages
    conversation_context_text = "\n".join(
        [f"{'User' if msg.get('fromMe') else 'AI'}: {msg.get('text')}" for msg in conversation_context]
    )

    # LLM step, pass to GPT to explain
    try:
        ai_response = get_explanation.generate(
            user_query,
            context_text if context_text else "No relevant information found in bylaws.",
            city=city,
            context=conversation_context_text,
        )
        status = "ok"
        ai_error = None
    except Exception as e:
        status = "degraded"
        ai_response = None
        ai_error = str(e)

    # Log every query purely for performance evauation
    log_event(
        query=user_query,
        response=ai_response if isinstance(ai_response, str) else json.dumps(ai_response, ensure_ascii=False),
        other_logs={
            "city": city,
            "ai_error": ai_error,
            "retrieved_sources": source_info,
        },
        timestamp=timestamp,
    )

    # Response
    if status == "degraded":
        fallback_text = (
            "Sorry, we couldn't generate a natural-language answer right now.\n"
            "The server for our AI is too busy. Please try again later.\n"
            "Nevertheless, here are the most relevant bylaw sources we found."
        )
        log_event(
            query=user_query,
            response=fallback_text,
            other_logs={"city": city, "ai_error": ai_error, "retrieved_sources": source_info, "status": "degraded"},
            timestamp=timestamp,
        )
        return jsonify({
            "status": "degraded",
            "message": "LLM API error, likely server busy.",
            "ai_response": fallback_text,
            "ai_error": ai_error,
            "retrieved_sources": source_info,
            "city": city,
            "timestamp": timestamp,
        }), 200

    # all went well, return ai response, found relevant sources, etc.
    return jsonify({
        "status": "ok",
        "ai_response": ai_response,
        "retrieved_sources": source_info,
        "city": city,
        "timestamp": timestamp,
    }), 200
