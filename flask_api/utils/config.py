# centralized config file with config variables


import os
from dotenv import load_dotenv

load_dotenv() 

# ========================================================
# Google Sheets for cloud synced logs
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")  # path to JSON
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")             # the file ID
SHEET_NAME = os.getenv("SHEET_NAME", "Paralegal_Logs")   # overrideable
SHEETS_APPEND_RANGE = SHEET_NAME  # e.g. "Paralegal_Logs"

# ========================================================
# Local logs synced with sheets, incase cloud fails or smthn
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOCAL_JSONL = os.path.join(LOG_DIR, "query_log.jsonl")
LOCAL_SUBMISSIONS = os.path.join(LOG_DIR, "submissions.log")

# ========================================================
# SMTP / Email
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
FEEDBACK_EMAIL = os.getenv("FEEDBACK_EMAIL", SMTP_USER)  # fallback to from

# ========================================================
# MongoDB variables/creds
DB_NAME = os.getenv("DB_NAME")
DB_LOGIN = os.getenv("DATABASE_LOGIN")
# ========================================================
# CORS, yeah there may be a more efficient way to manage the localhost mkay
ALLOWED_URLS = [
    "http://localhost:59259",
    "http://localhost:58722",
    "http://localhost:56703",
    "https://gdsc-2025.firebaseapp.com",
    "https://gdsc-2025.web.app",
    "https://paralegalbylaw.org",
    "https://api.paralegalbylaw.org",
    "http://localhost:55974",
    "http://localhost:58150",
]
