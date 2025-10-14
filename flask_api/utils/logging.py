# utilities to add logs to google spreadsheet so theyre cloud synced and backed up
# Google sheets was just super easy to setuop and easy for
# me to see on my phone from anywhere, anytime if something is going wrong
# utils/logging.py

import os
import json
import datetime
from typing import Any, Dict, Optional

# config has all constants/ env vars
from . import config

# Create log dir
os.makedirs(config.LOG_DIR, exist_ok=True)

# Google Sheets (lazy -- built and cache the Google Sheets client on first use.)
_sheet = None
def _get_sheet_client():
    global _sheet
    if _sheet is not None:
        return _sheet

    # If not configured, just skip
    if not (config.SERVICE_ACCOUNT_FILE and config.SPREADSHEET_ID):
        _sheet = False
        print("[WARN] Google sheets not configured, no cloud sync logs.")
        return _sheet

    try:
        # create sheet client on first use
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = service_account.Credentials.from_service_account_file(
            config.SERVICE_ACCOUNT_FILE,
            scopes=scopes
        )
        service = build("sheets", "v4", credentials=creds)
        _sheet = service.spreadsheets().values()
        return _sheet
    
    except Exception:
        _sheet = False
        return _sheet

# appends a single row to google sheet client for logs
def _append_to_sheet(row_values: list[str]) -> bool:
    sheet = _get_sheet_client()
    if not sheet:
        return False
    try:
        sheet.append(
            spreadsheetId=config.SPREADSHEET_ID,
            range=config.SHEETS_APPEND_RANGE,
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row_values]},
        ).execute()
        return True
    except Exception:
        return False

# simple, writes to local file, should stay synced with google sheet
# writes to logs/query_log.jsonl
def _append_to_local_jsonl(obj: Dict[str, Any]) -> bool:
    try:
        with open(config.LOCAL_JSONL, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
        return True
    except Exception:
        return False

# log feedback/submission - I will also get an email, this is basically a local backup/record
def _append_to_local_submissions_block(text_block: str) -> bool:
    try:
        with open(config.LOCAL_SUBMISSIONS, "a", encoding="utf-8") as f:
            f.write(text_block)
        return True
    except Exception:
        return False


#Single public entrypoint:
# - Always writes a JSONL log locally (idempotent, safe).
# - Also attempts to append to Google Sheets (best-effort).
# - Optionally writes a pretty multi-line block to submissions.log.
def log_event(
    *,
    query: str = "",
    response: Optional[str] = None,
    other_logs: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None,
    also_submissions_block: Optional[str] = None
) -> None:

    ts = timestamp or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "timestamp": ts,
        "query": query,
        "response": response,
        "other_logs": other_logs or {},
    }

    # local JSONL
    _append_to_local_jsonl(payload)

    # sheets (flatten the dict to a compact string for the fourth col)
    other_str = json.dumps(other_logs or {}, ensure_ascii=False, default=str)
    _append_to_sheet([ts, query, (response or ""), other_str])

    # optional pretty block
    if also_submissions_block:
        _append_to_local_submissions_block(also_submissions_block)
