# short script to go back and add fields that i forgot to the first time

import os, glob, json, hashlib, pymongo
from tqdm import tqdm
from dotenv import load_dotenv

def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()

def backfill_pages(input_dir: str, mongodb_uri: str, db_name: str, col_name: str):
    client = pymongo.MongoClient(mongodb_uri)
    col = client[db_name][col_name]

    files = glob.glob(os.path.join(input_dir, "*.json"))
    updated, missing = 0, 0

    for p in tqdm(files, desc="Backfilling pages", unit="file"):
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        for ch in data.get("chunks", []):
            title   = (ch.get("section_title") or "").strip()
            summary = (ch.get("contextual_summary") or "").strip()
            text    = (ch.get("text") or "").strip()
            if not text and not summary:
                continue

            combined = f"{title}\n{summary}\n{text}".strip()
            h = sha1(combined)

            page_numbers = ch.get("page_numbers")
            page_number  = ch.get("page_number")
            if page_numbers is None and page_number is not None:
                page_numbers = [page_number]

            if page_numbers:
                res = col.update_one(
                    {"chunk_hash": h},
                    {"$set": {
                        "page_numbers": page_numbers,
                        "page_start": min(page_numbers),
                        "page_end":   max(page_numbers),
                    }}
                )
                if res.matched_count:
                    updated += res.modified_count  # modified_count is 0 if already set the same
                else:
                    missing += 1  # couldn’t find a doc with this hash (e.g., filtered out earlier)
    client.close()
    print(f"[INFO] Backfill complete. Docs updated: {updated}, chunks not found: {missing}")


if __name__ == "__main__":
    load_dotenv()
    login = os.getenv("DATABASE_LOGIN")
    if not login:
        raise RuntimeError("[ERROR] Set DATABASE_LOGIN in .env")

    MONGODB_URI = f"mongodb+srv://{login}@paralegal-rag.ujgail4.mongodb.net/?retryWrites=true&w=majority&appName=Paralegal-RAG"

    INPUT_DIR = os.getenv("EXTRACTED_DIR", "llm_chunks_out")
    DB_NAME = os.getenv("DB_NAME", "Bylaws")
    COLLECTION = os.getenv("COLLECTION_NAME", "Waterloo")
    CITY = os.getenv("CITY", "Waterloo")


    backfill_pages(
        input_dir=os.getenv("EXTRACTED_DIR", "llm_chunks_out"),
        mongodb_uri=MONGODB_URI,
        db_name=DB_NAME,
        col_name=COLLECTION,
    )