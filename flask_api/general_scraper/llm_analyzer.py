"""
LLM Chunking Pass for Municipal Corpus

Reads crawler outputs (manifest.json + markdown/*.md),
then calls GPT-5 to extract self-contained chunks per page.

- Auto batching for long pages (e.g., 75k tokens)
- Heuristic 'reasoning_effort' bump for long/complex docs
- Saves one JSON per source with rich metadata

Env:
  OPENAI_API_KEY    = your key
  MODEL_NAME        = gpt-5  (or gpt-5-mini)
  OUTPUT_DIR        = llm_chunks_out
  CRAWL_DIR         = crawl_out
"""

from __future__ import annotations
import os, json, time, math, hashlib, logging, re, glob
from pathlib import Path
from datetime import datetime
import requests
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# -------------------- Config --------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME     = os.getenv("MODEL_NAME", "gpt-5")       # or "gpt-5-mini"
CRAWL_DIR      = Path(os.getenv("CRAWL_DIR", "crawl_out"))
MD_DIR         = CRAWL_DIR / "markdown"
MANIFEST_PATH  = CRAWL_DIR / "manifest.json"
OUT_DIR        = Path(os.getenv("OUTPUT_DIR", "llm_chunks_out"))
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Target budget per call. These are conservative approximations:
# (we estimate tokens ~ chars/4)
MAX_INPUT_TOKENS     = 100_000          # safe chunk size per request
BATCH_OVERLAP_TOKENS = 1_000            # overlap to avoid split seams
TARGET_OUTPUT_TOKENS = 16000            # model will often produce far less; this is just a planning number

# Reasoning effort thresholds (heuristics)
REASONING_LEN_HIGH   = 30_000           # if est input > this, bump to "high"
REASONING_DEFAULT    = "minimal"         # "minimal" | "low" | "medium" | "high"

# Retry config
HTTP_TIMEOUT_SEC     = 240
MAX_RETRIES          = 3
RETRY_BACKOFF_SEC    = 5

# -------------------- Prompt --------------------
EXTRACTION_PROMPT = """
You are extracting municipal bylaw and related city-governance content for a RAG system.

Each chunk MUST be self-contained and not rely on other chunks.

RULES
- Do NOT invent facts. Preserve statutory/official text VERBATIM in `text`.
- Prefer whole sections as chunks when feasible.
- Split long sections at natural boundaries (subsections, numbered clauses, topic changes).
- Target 200-500 words per chunk; max 800; min 50 (merge tiny fragments if needed).
- If a clause depends on a clause not included in the chunk, set `requires_context=true` and list it in `cross_refs`.

DE-REFERENCING (do not edit `text`)
- If the text says “this bylaw,” “herein,” “section X,” etc., keep the original `text`.
- Provide a short `contextual_summary` clarifying those references (based only on the provided page batch).

DATA MODEL — return ONLY valid JSON (no extra text):

{
  "relevant": boolean,
  "reason": string | null,                 // if relevant=false, short reason
  "page_title": string,
  "bylaw_number": string | null,
  "primary_subject": "parking" | "traffic" | "pool_enclosures" | "trees" | "noise" | "property_standards" | "animals" | "zoning" | "water_backflow" | "business_licensing" | "waste" | "signage" | "other",
  "applies_to": string | null,             // e.g., "City of Waterloo" or "unspecified"
  "subject_tags": string[],                // 1-5 short tags
  "chunks": [
    {
      "section_title": string | null,
      "section_path": string | null,       // e.g., "§21 → 21.3"
      "content_type": "bylaw" | "regulation" | "procedure" | "fee_schedule" | "contact_info" | "general_info",
      "page_numbers": number[],            // [] for HTML; list pages if PDF context is indicated by markers
      "requires_context": boolean,
      "cross_refs": string[],              // e.g., ["19.1", "18(2)"]; [] if none
      "contextual_summary": string,        // MUST start: "From {page_title} ({primary_subject}) — Scope: {applies_to or 'unspecified'}. Section: {section_path or 'n/a'}."
      "text": string                       // VERBATIM source text
    }
  ]
}

CONSTRAINTS
- Keep `contextual_summary` concise and factual.
- If not relevant to municipal bylaws/regulations/services, return relevant=false with reason.
- Output MUST be valid JSON. No markdown/code fences. No commentary.
""".strip()

# -------------------- Utils --------------------

def sha8(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]

def est_tokens_from_text(t: str) -> int:
    # very rough: ~4 chars/token
    return max(1, math.ceil(len(t) / 4))

def split_text_to_batches(text: str, max_tokens: int, overlap_tokens: int) -> List[str]:
    """
    Splits a long text into overlapping batches by character count (approx tokens*4).
    """
    per_batch_chars = max_tokens * 4
    overlap_chars   = overlap_tokens * 4
    n = len(text)
    if n <= per_batch_chars:
        return [text]

    batches = []
    start = 0
    while start < n:
        end = min(n, start + per_batch_chars)
        chunk = text[start:end]
        batches.append(chunk)
        if end >= n:
            break
        start = end - overlap_chars  # overlap
        if start < 0:
            start = 0
    return batches

def clean_for_json(text: str) -> str:
    # remove control characters except newlines and tabs
    return re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]", "", text)


def looks_complex(page_text: str) -> bool:
    # Borrowing your earlier signals
    signals = 0
    if re.search(r'\b(section|§|subject to|notwithstanding|despite|except as provided)\b', page_text, re.I):
        signals += 1
    if re.search(r'\b\d+(\.\d+){2,}', page_text):  # 1.2.3
        signals += 1
    if re.search(r'\b(schedule|appendix|fee table|table\s+\d+)\b', page_text, re.I):
        signals += 1
    if len(re.findall(r'\b(despite|notwithstanding|however|except)\b', page_text, re.I)) >= 6:
        signals += 1
    return signals >= 2

def pick_reasoning_effort(text: str, default_effort: str = REASONING_DEFAULT) -> str:
    # tokens = est_tokens_from_text(text)
    # if tokens >= REASONING_LEN_HIGH or looks_complex(text):
    #     return "high"
    
    # honestly medium reasoning is more than enough, high is overkill, slow, expensive and soemtimes hits max tokens cap
    return default_effort

def load_manifest(path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Returns a dict keyed by URL-hash filename (8), value = manifest row.
    We’ll match files by sha8(url).md
    """
    by_hash: Dict[str, Dict[str, Any]] = {}
    if not path.exists():
        return by_hash
    data = json.loads(path.read_text(encoding="utf-8"))
    # manifest rows are arbitrary list of dicts from the crawler
    for row in data:
        url = row.get("url")
        if not url: 
            continue
        by_hash[sha8(url)] = row
    return by_hash

def build_prompt(url: str, page_title: str, content: str, source_type: str) -> str:
    """
    Wraps the page content with a small header so the model can pick up title/URL context easily.
    If the content came from a PDF and you marked pages with '=== PAGE X START ===', the model can fill page_numbers.
    """
    header = f"""
URL: {url}
PAGE TITLE: {page_title or "unspecified"}
SOURCE TYPE: {source_type}

The following is the page content to extract from:
""".strip()

    return f"{EXTRACTION_PROMPT}\n\n{header}\n\n{content}"

def _extract_output_text_from_responses_payload(j: Dict[str, Any]) -> Optional[str]:
    """
    Responses API canonical parse:
    - Prefer j["output"] list: find first message item; concat its output_text parts.
    - Fallbacks: j["output_text"] (SDKs sometimes flatten), chat-like shapes.
    Returns the text or None if not found.
    """
    # 1) Canonical Responses shape
    out = j.get("output")
    if isinstance(out, list):
        for item in out:
            if item.get("type") == "message" and item.get("content"):
                parts = []
                for c in item["content"]:
                    if c.get("type") == "output_text":
                        parts.append(c.get("text", ""))
                text = "\n".join(p for p in parts if p).strip()
                if text:
                    return text

    # 2) Some SDKs flatten here
    if isinstance(j.get("output_text"), str) and j["output_text"].strip():
        return j["output_text"].strip()

    # 3) Extremely rare chat-like fallback
    try:
        c = j["choices"][0]["message"]["content"]
        if isinstance(c, str) and c.strip():
            return c.strip()
    except Exception:
        pass

    return None


def call_openai_responses(prompt: str, model: str, reasoning_effort: str) -> str:
    """
    Calls the OpenAI Responses API and returns the raw content string (expected to be JSON).
    """
    payload = {
        "model": model,
        "reasoning": {"effort": reasoning_effort},
        "input": prompt,
        "max_output_tokens": TARGET_OUTPUT_TOKENS,
        # tip: stream=false by default; leaving it explicit for clarity
        "stream": False,
    }

    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=HTTP_TIMEOUT_SEC,
            )

            if r.status_code == 200:
                j = r.json()

                # Only treat "error" as an error when it's non-empty/non-null
                if j.get("error"):
                    raise RuntimeError(f"API internal error: {j['error']}")

                text = _extract_output_text_from_responses_payload(j)
                if text and text.strip():
                    return text

                # If we got here with 200 but no text, that's a soft failure
                last_err = "200 OK but no textual output in payload"
            else:
                # Helpful hints on 429/5xx
                if r.status_code in (429, 500, 502, 503, 504):
                    last_err = f"HTTP {r.status_code}: transient error: {r.text[:400]}"
                else:
                    last_err = f"HTTP {r.status_code}: {r.text[:400]}"

        except Exception as e:
            last_err = str(e)

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_BACKOFF_SEC * attempt)

    raise RuntimeError(f"OpenAI call failed after retries: {last_err}")


def extract_title_from_markdown(md_text: str) -> str:
    # Try to use first markdown H1 or the header line "URL:" block
    m = re.search(r"^#\s*(.+)", md_text, flags=re.M)
    if m:
        return m.group(1).strip()
    return ""

def safe_json_parse(s: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(s)
    except Exception:
        return None

# -------------------- Main processing --------------------

def process_one_file(md_path: Path, manifest_idx: Dict[str, Dict[str, Any]]):


    md_text = md_path.read_text(encoding="utf-8", errors="ignore")
    # Our crawler prepends header lines "# URL: ..." — try to recover URL
    m_url = re.search(r"^# URL:\s*(\S+)", md_text, flags=re.M)
    url   = m_url.group(1) if m_url else "unknown"
    page_title = extract_title_from_markdown(md_text)
    body_start = md_text.find("\n\n")
    content = md_text[body_start:].strip() if body_start != -1 else md_text

    # remove control characters except newlines and tabs
    content = clean_for_json(content)



    # Manifest metadata (depth/score/source_type/word_count)
    url_key = sha8(url) if url != "unknown" else md_path.stem
    meta = manifest_idx.get(url_key, {})
    source_type = meta.get("source_type", "html")

    if (OUT_DIR / f"{md_path.stem}_{sha8(url)}.json").exists():
        logging.info(f"↩️ Skipping already processed {md_path.name}")
        return

    # Batch if needed
    total_tokens = est_tokens_from_text(content)
    batches = split_text_to_batches(content, MAX_INPUT_TOKENS, BATCH_OVERLAP_TOKENS)

    # Decide reasoning once (can also do per-batch, but page-level is fine)
    effort = pick_reasoning_effort(content)

    all_doc_chunks: List[Dict[str, Any]] = []
    doc_level = {
        "url": url,
        "scraped_at": datetime.fromtimestamp(meta.get("timestamp", time.time())).isoformat(),
        "depth": meta.get("depth"),
        "score": meta.get("score"),
        "word_count": meta.get("word_count"),
        "source_type": source_type,
        "filename": md_path.name,
        "model": MODEL_NAME,
        "reasoning_effort": effort,
        "batches": len(batches),
        "total_input_tokens_est": total_tokens,
        "chunks": []  # filled below
    }

    logging.info(f"LLM extracting: {md_path.name} | {len(batches)} batch(es) | effort={effort}")

    for i, chunk in enumerate(batches, start=1):
        prompt = build_prompt(url=url, page_title=page_title, content=chunk, source_type=source_type)
        raw = call_openai_responses(prompt, MODEL_NAME, effort)
        parsed = safe_json_parse(raw)

        # If the model replies non-JSON (rare), try once to nudge by trimming
        if parsed is None:
            # Heuristic clean: remove leading/trailing junk lines
            cleaned = raw.strip()
            # Remove code fences if present
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned.strip(), flags=re.I|re.M)
            parsed = safe_json_parse(cleaned)

        if parsed is None:
            logging.warning(f"⚠️  Non-JSON response for {md_path.name} batch {i}; skipping.")
            fail_path = OUT_DIR / "failed" / f"{md_path.stem}_batch{i}.txt"
            fail_path.parent.mkdir(exist_ok=True)
            fail_path.write_text(raw, encoding="utf-8")
            continue

        if parsed.get("relevant") and isinstance(parsed.get("chunks"), list):
            # Ensure page_numbers present for HTML (empty list)
            for ch in parsed["chunks"]:
                ch.setdefault("page_numbers", [])
            all_doc_chunks.extend(parsed["chunks"])

    doc_level["total_chunks"] = len(all_doc_chunks)
    doc_level["chunks"] = all_doc_chunks

    out_name = f"{md_path.stem}_{sha8(url)}.json"
    (OUT_DIR / out_name).write_text(json.dumps(doc_level, indent=2, ensure_ascii=False), encoding="utf-8")
    logging.info(f"💾 Saved {out_name} ({len(all_doc_chunks)} chunks)")

def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not OPENAI_API_KEY:
        raise SystemExit("Missing OPENAI_API_KEY")

    if not MD_DIR.exists():
        raise SystemExit(f"Markdown dir not found: {MD_DIR}")

    manifest_idx = load_manifest(MANIFEST_PATH)

    md_files = sorted(glob.glob(str(MD_DIR / "*.md")))
    if not md_files:
        raise SystemExit(f"No markdown files in {MD_DIR}")

    logging.info(f"Found {len(md_files)} markdown files. Writing to {OUT_DIR.resolve()}")
    for fp in md_files:

        try:
            process_one_file(Path(fp), manifest_idx)
        except Exception as e:
            logging.warning(f"❌ Error processing {fp}: {e}")
        time.sleep(1.2)


    logging.info("✅ Done.")

if __name__ == "__main__":
    main()
