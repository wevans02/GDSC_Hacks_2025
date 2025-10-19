'''
I was getting tired of have customized scrapers for each city, and still getting only mediocre results
this one should scrape the whole city website, starting from the root URL and then using Crawl4AI and 
an LLM Extraction Strategy to extract anything useful. I noticed people asking other specific things 
not only found in bylaws on the city site. eg, can I park on X specific street at this time, which sometimes the model didnt know.
Hoping this way I fix a few problems:

1. scraper is general, easily adaptable to multiple cities
2. brings in more useful information that may be found beyond strictly city's /bylaws/ directory
3. more quality data - I can have LLM make chunks more semantically chunked, 
      and also Ima try something along the lines of what was describe here by Anthropic about maintaining context in RAG:
      https://www.anthropic.com/engineering/contextual-retrieval
enables both vector semanticsearch and BM25 keyword search
'''

# ----------------------------
# Standard Library Imports
# ----------------------------
from __future__ import annotations  # Forward reference support
from datetime import datetime       # For timestamps
import asyncio                      # For asynchronous crawling
import json                         # For JSON I/O
import os                           # For environment variables & file paths
import io                           # For PDF byte streams
import hashlib                      # For potential hashing (if needed)
import requests                     # For HTTP requests (PDFs, API calls)
from typing import List, Dict       # For type hints
import regex as re

# ----------------------------
# Third-Party Libraries
# ----------------------------
from dotenv import load_dotenv                         # To load .env credentials
from pypdf import PdfReader                             # For PDF text extraction
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, LLMConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy  # For LLM-based extraction

# ----------------------------
# Environment Setup
# ----------------------------
load_dotenv()                      # Load environment variables from .env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # OpenAI API key
GPT_MODEL = "gpt-5-mini"          # Default model for extraction

# number of pages to scrape
MAX_PAGES=300

# TUNABLE EXTRACTION PROMPT
# This is where you control what gets extracted and how it's chunked
EXTRACTION_PROMPT = """
You are extracting municipal bylaw content for a RAG system.

Each chunk MUST be self-contained and must NOT rely on seeing any other chunk.

RULES
- Do NOT invent facts. Preserve bylaw text VERBATIM in `text`.
- Prefer whole sections as chunks. If a section is long, split at natural boundaries (subsections, numbered clauses, topic changes).
- Target 200-500 words per chunk; max 800; min 50 (merge tiny fragments if needed).
- If a clause depends on another clause that is NOT included in the chunk, set `requires_context=true` and list the referenced sections in `cross_refs`.

DE-REFERENCING (without editing the text)
- When the text says “this bylaw,” “herein,” “section X,” etc., do NOT change `text`.
- Instead, write a brief `contextual_summary` explaining what those references point to (based only on the provided page).

OUTPUT
Return ONLY JSON (no Markdown, no commentary) with this exact schema:

{
  "relevant": boolean,
  "reason": string | null,                 // if relevant=false, say why briefly
  "page_title": string,
  "bylaw_number": string | null,
  "primary_subject": "parking" | "traffic" | "pool_enclosures" | "trees" | "noise" | "property_standards" | "animals" | "zoning" | "water_backflow" | "business_licensing" | "waste" | "signage" | "other",
  "applies_to": string | null,             // e.g., "City of Waterloo" or "unspecified"
  "subject_tags": string[],                // short tags, 1-5 items
  "chunks": [
    {
      "section_title": string | null,
      "section_path": string | null,       // e.g., "§21 → 21.3"
      "content_type": "bylaw" | "regulation" | "procedure" | "fee_schedule" | "contact_info" | "general_info",
      "requires_context": boolean,
      "cross_refs": string[],              // e.g., ["19.1", "18(2)"]; [] if none
      "contextual_summary": string,        // 1-2 sentences. MUST start: "From {page_title} ({primary_subject}) — Scope: {applies_to or 'unspecified'}. Section: {section_path or 'n/a'}."
      "text": string                       // VERBATIM law text
    }
  ]
}

CONSTRAINTS
- Keep `contextual_summary` short and factual (no restating the full text).
- If the page is not a bylaw/regulation (e.g., news, contact-only), return `"relevant": false` with a short reason.
- Output MUST be valid JSON. No trailing commas, no extra keys.
"""

def needs_reasoning(page_text: str, draft_meta) -> bool:
    # A) cross-ref density
    refs = re.findall(r'\b(section|§|subject to|notwithstanding|despite|except as provided)\b', page_text, flags=re.I)
    if len(refs) >= 5:
        return True

    # B) nested numbering patterns
    if re.search(r'\b\d+(\.\d+){2,}', page_text):  # 1.2.3 or deeper
        return True

    # C) schedules / tables keywords
    if re.search(r'\b(schedule|appendix|fee table|table\s+\d+)\b', page_text, flags=re.I):
        return True

    # D) exception chains
    if len(re.findall(r'\b(despite|notwithstanding|however|except)\b', page_text, flags=re.I)) >= 6:
        return True

    # E) fallback from a quick dry-run validator (e.g., bad JSON twice)
    if draft_meta.get("json_failures", 0) >= 2 or draft_meta.get("many_requires_context", False):
        return True

    return False


# this function is called when we hit a pdf, special pipleine to handle pdfs
# at the end, the result is funneled into the same json as the html pages end up as. 
# we also save page number to make it easer for user to find in large pdfs.
async def scrape_pdf_with_llm(url: str, output_dir=os.getenv("EXTRACTED_DIR", "llm_extracted_data_toronto"), pages_per_batch=5):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Download PDF
    print(f"📄 Downloading PDF: {url}")
    try:
        resp = requests.get(url, timeout=90)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to fetch PDF: {e}")
        return

    # 2. Extract text 
    pdf_bytes = io.BytesIO(resp.content)
    reader = PdfReader(pdf_bytes)
    pages = [page.extract_text() or "" for page in reader.pages]
    total_pages = len(pages)

    if not any(p.strip() for p in pages):
        print(f"[WARN] No text found in PDF {url}")
        return

    print(f"[INFO] Extracted text from {total_pages} pages")

    # 3. Process in batches of 5
    all_chunks = []

    for i in range(0, total_pages, pages_per_batch):
        batch_start = i + 1
        batch_end = min(i + pages_per_batch, total_pages)
        batch_pages = pages[i:batch_end]

        # Label each page clearly in the text
        combined_text = "\n\n".join(
            f"=== PAGE {page_num} START ===\n{page_text}\n=== PAGE {page_num} END ==="
            for page_num, page_text in zip(range(batch_start, batch_end + 1), batch_pages)
        )

        # Add to prompt that we want page numbers reflected
        prompt = f"""
{EXTRACTION_PROMPT.strip()}

IMPORTANT:
- You must include a "page_numbers" field for each chunk, listing the page(s) where the text was found.
- If a chunk spans multiple pages, include all of them, e.g. "page_numbers": [12, 13].
- Do not omit or guess page numbers — base them on the markers in the provided text.

Return ONLY valid JSON.
Do not include any markdown formatting such as ```json or ``` fences.
Do not include any text before or after the JSON.

NOW EXTRACT FROM THE FOLLOWING PDF PAGES ({batch_start}-{batch_end}):
{combined_text}
        """

        # send contstructed pages with prompt to GPT
        print(f"[INFO] Sending pages {batch_start}-{batch_end} to GPT...")

        try:
            llm_response = requests.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                },
                json={
                    "model": GPT_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                },
                timeout=180,
            )
            llm_response.raise_for_status()
            raw_text = llm_response.json()["choices"][0]["message"]["content"]
            extracted = json.loads(raw_text)

            # fallback in case LLM forgot page_numbers
            for ch in extracted.get("chunks", []):
                if "page_numbers" not in ch:
                    ch["page_numbers"] = list(range(batch_start, batch_end + 1))

            all_chunks.extend(extracted.get("chunks", []))

        except Exception as e:
            print(f"⚠️ Batch {batch_start}-{batch_end} failed: {e}")
            print("llm resonse: ", llm_response.json()["choices"][0]["message"]["content"])
            continue

    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"{hash(url) % 100000:05d}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    # 4. Combine + save
    output = {
        "url": url,
        "scraped_at": timestamp,
        "page_count": total_pages,
        "page_ranges": [
            {"start": i + 1, "end": min(i + pages_per_batch, total_pages)}
            for i in range(0, total_pages, pages_per_batch)
        ],
        "chunks": all_chunks,
        "relevant": bool(all_chunks),
        "source_type": "pdf",
        "filename": os.path.basename(url),
    }

    # filepath = f"{hash(url) % 100000:05d}.json"
    # filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(all_chunks)} chunks from {total_pages} pages → {filename}")

# branches off of baseurl, and explores further pages based on prevalence of keywords
# uses an LLM (in our case gpt 4o mini) to extract relevant chunks for the RAG. 
async def scrape_with_llm_extraction(
    start_url: str, 
    output_dir: str = "llm_extracted_data_toronto",
    max_pages: int = 300,
    use_best_first: bool = True,
    keywords: List[str] = None
):
    os.makedirs(output_dir, exist_ok=True)
    
    # default keywords
    if keywords is None:
        keywords = ["bylaw", "parking", "permit", "regulation", "service"]
    
    # Track visited and queued URLs
    visited = set()
    queue = [(0, start_url)]  # (priority, url) for best-first search

    # FIX: Use the correct model name - you had "gpt-4o-mini" but defined GPT_MODEL as "gpt-5-mini"
    extraction_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider=f"openai/{GPT_MODEL}",  # Use your defined model
            api_token=os.environ.get("OPENAI_API_KEY"),
            temperature=0.1,
        ),
        instruction=EXTRACTION_PROMPT,
        
    )
    
    # setup crawling
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        extraction_strategy=extraction_strategy,
        word_count_threshold=10,
        
    )
    
    async with AsyncWebCrawler() as crawler:
        while queue and len(visited) < max_pages:
            # Get next URL (best-first if enabled, otherwise FIFO)
            if use_best_first:
                queue.sort()  # Sort by priority
            _, url = queue.pop(0)
            
            # dedupe
            if url in visited:
                continue
            visited.add(url)

            print(f"\n[{len(visited)}/{max_pages}] Processing: {url}")
            
            try:
                result = await crawler.arun(url, config=config)
                
                if not result.success:
                    print(f"  ❌ Failed to fetch")
                    continue

                # Handle PDFs separately
                if result.url.endswith(".pdf"):
                    await scrape_pdf_with_llm(result.url)
                    continue
                
                # FIX: Combine ALL chunks from ALL documents on this page into one file
                parsed_extracted = json.loads(result.extracted_content)
                
                # Handle case where extracted_content is a single document or list of documents
                if isinstance(parsed_extracted, dict):
                    documents = [parsed_extracted]
                else:
                    documents = parsed_extracted
                
                all_chunks_from_page = []
                relevant_document_count = 0
                
                for document in documents:
                    if document.get("relevant", False):
                        chunks = document.get("chunks", [])
                        all_chunks_from_page.extend(chunks)
                        relevant_document_count += 1
                        print(f"  ✅ Relevant document with {len(chunks)} chunks")
                    else:
                        reason = document.get("reason", "Unknown")
                        print(f"  ❌ Not relevant: {reason}")
                
                # Only save if we found relevant chunks
                if all_chunks_from_page:
                    output_document = {
                        "url": url,
                        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "total_chunks": len(all_chunks_from_page),
                        "relevant_documents": relevant_document_count,
                        "chunks": all_chunks_from_page
                    }
                    
                    # Create unique filename with timestamp
                    timestamp = datetime.now().strftime("%H%M%S")
                    filename = f"{hash(url) % 100000:05d}_{timestamp}.json"
                    filepath = os.path.join(output_dir, filename)
                    
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(output_document, f, indent=2, ensure_ascii=False)
                    
                    print(f"  💾 Saved {len(all_chunks_from_page)} total chunks to {filename}")
                    
                    # Show preview of first few chunks
                    for i, chunk in enumerate(all_chunks_from_page[:3]):
                        preview = chunk["text"][:100] + "..." if len(chunk["text"]) > 100 else chunk["text"]
                        print(f"  📄 Chunk {i+1}: {preview}")
                else:
                    print(f"  ⚠️  No relevant chunks found on this page")
                
                # Extract links for crawling
                new_links = extract_links(result.html, url)
                added = 0
                
                for link in new_links:
                    if link not in visited and link not in [u for _, u in queue]:
                        priority = calculate_priority(link, keywords) if use_best_first else 0
                        queue.append((priority, link))
                        added += 1
                
                print(f"  🔗 Found {added} new links (queue: {len(queue)})")
                
            except Exception as e:
                print(f"  ❌ Error processing {url}: {e}")
                import traceback
                traceback.print_exc()
            
            await asyncio.sleep(0.5)
    
    print(f"\n✅ Crawled {len(visited)} pages")

def extract_links(html: str, base_url: str) -> List[str]:
    """Extract valid links from HTML."""
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin, urlparse
    
    soup = BeautifulSoup(html, 'html.parser')
    links = []
    base_domain = urlparse(base_url).netloc
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        
        # Skip non-http links
        if href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
            continue
        
        # Make absolute URL
        full_url = urljoin(base_url, href)
        
        # Only same domain
        if urlparse(full_url).netloc != base_domain:
            continue
        
        # Skip non-content files
        if full_url.lower().endswith(('.pdf', '.jpg', '.png', '.zip', '.doc', '.xls')):
            continue
        
        # Remove fragment
        full_url = full_url.split('#')[0]
        
        links.append(full_url)
    
    return list(set(links))


def calculate_priority(url: str, keywords: List[str]) -> int:
    """
    Calculate priority for best-first search.
    Lower number = higher priority (visited sooner).
    
    URLs matching keywords get higher priority.
    """
    url_lower = url.lower()
    
    # Count keyword matches
    matches = sum(1 for kw in keywords if kw.lower() in url_lower)
    
    # Negative priority (lower = better)
    # More matches = higher priority (lower number)
    return -matches * 10


async def main():
    """
    Example usage with intelligent crawling
    """
    
    # We will start from the byklaw page to make sure we get it then we will continue out to other pages maybe. 
    start_url = os.getenv("START_SCRAPE_URL")
    
    # Keywords to prioritize (best-first search)
    keywords = [
        "bylaw", "parking", "permit", "regulation", 
        "noise", "property", "zoning", "license"
    ]
    
    await scrape_with_llm_extraction(
        start_url=start_url,
        max_pages=MAX_PAGES,
        use_best_first=True,  # Set False for breadth-first search
        keywords=keywords,
        output_dir=os.getenv("EXTRACTED_DIR")
    )
    
    print("\n✅ Done! Check the 'llm_extracted_data_toronto' folder for results.")


if __name__ == "__main__":
    asyncio.run(main())
