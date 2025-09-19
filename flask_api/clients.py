# file: clients.py

import os
import pymongo
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set in environment variables!")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# Use "private" global variables
_mongo_client = None

def get_mongo_client():
    """Gets the MongoDB client, initializing it on the first call."""
    global _mongo_client
    if _mongo_client is None:
        print(f"Process {os.getpid()}: Initializing MongoDB client for the first time...")
        DATABASE_LOGIN = os.getenv("DATABASE_LOGIN")
        print("logging in with:", DATABASE_LOGIN)
        uri = f"mongodb+srv://{DATABASE_LOGIN}@gdsc2025.cn3wt5n.mongodb.net/?retryWrites=true&w=majority&appName=GDSC2025"
        try:
            _mongo_client = pymongo.MongoClient(uri, tls=True, tlsAllowInvalidCertificates=False)
            print("got client I think")
            _mongo_client.admin.command('ping')
            print(f"Process {os.getpid()}: MongoDB connection successful.")
        except pymongo.errors.ConnectionFailure as e:
            print(f"MongoDB connection failed: {e}")
            _mongo_client = None # Ensure it remains None on failure
    return _mongo_client

# def configure_gemini():
#     GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
#     if GEMINI_API_KEY:
#         genai.configure(api_key=GEMINI_API_KEY)
#         print("Gemini client configured.")
# # Call the configuration once on module import
# gemini_client = genai.Client()
# configure_gemini()