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
GPT_MODEL = "gpt-4o-mini"          # Default model for extraction


# TUNABLE EXTRACTION PROMPT
# This is where you control what gets extracted and how it's chunked
EXTRACTION_PROMPT = """
You are an expert data extractor for a Retrieval-Augmented Generation (RAG) system focused on municipal information for the City of Toronto (bylaws, parking, city services, etc.). Your output will be used directly to create embeddings for a vector database.

Your task:
1.  Analyze the provided webpage to determine if it contains useful municipal information (e.g., bylaws, regulations, services, procedures, fees, contact info).
2.  If the page is NOT useful (e.g., a simple navigation page, an empty page, an irrelevant form), you MUST return: {"relevant": false, "reason": "Provide a brief explanation for why the page is not relevant."}
3.  If the page IS useful, you must extract the content into logical, self-contained chunks based on the page's structure and topics.

CRITICAL RULES FOR EXTRACTION:
-   **ACCURACY IS PARAMOUNT**: The extracted data is the foundation of the RAG system. Do not include any information that is not explicitly present in the provided text.
-   **PRESERVE VERBATIM TEXT**: All extracted text must be an exact copy from the webpage. Do not paraphrase, summarize, or reword the original content. Maintain all original formatting, including tables and lists.
-   **CHUNK LOGICALLY**: Group related information into a single chunk. For example, rules for parking on a specific street, details about a city service and how to book it, or a single bylaw's section should each be one chunk. Create separate chunks for different services, bylaws, or distinct topics.
-   **SELF-CONTAINED CHUNKS**: Each chunk must be understandable on its own without requiring information from other chunks.

For each useful page, provide a JSON output with the following structure. For each chunk, you will provide:
-   "text": **Verbatim Content**: The EXACT verbatim text from the page.
-   "contextual_summary": A short, succinct sentence to situate the chunk within the overall document. Summarize or make clear anything that the chunk refers to that is outside the chunk.
    Example format: "This chunk details overnight parking regulations. Overnight parking is not permitted on city streets between 2:30 a.m. and 6:00 a.m. unless you have registered your vehicle for an exemption."
-   "section_title": The most relevant heading or topic for this chunk of text (e.g., "Overnight Parking Exemptions", "Garbage Collection Schedule").
-   "content_type": The type of information in the chunk. Choose from: bylaw, regulation, service_description, procedure, fee_schedule, contact_info, public_notice, meeting_minutes, general_info.

OUTPUT JSON FORMAT:
{
  "relevant": true,
  "page_title": "Page title from the webpage",
  "page_type": "bylaw|regulation|service|general_info|etc",
  "chunks": [
    {
      "text": "Verbatim text from the page...",
      "contextual_summary" : "succinct, contextual summary here."
      "section_title": "Section heading or topic",
      "content_type": "service_description",
    }
  ]
}

Your final output must be ONLY the raw, valid JSON.

NOW EXTRACT FROM THIS PAGE:
"""

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
                "https://api.openai.com/v1/chat/completions",
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

    filename = f"{hash(url) % 100000:05d}.json"
    filepath = os.path.join(output_dir, filename)
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

    # quality debugging
    # print("WHAHHA:", os.environ.get("OPENAI_API_KEY"))
    
    # uses gpt 4 with promt to extract context. needs a valid and paid api key
    extraction_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="openai/gpt-4o-mini",
            api_token=os.environ.get("OPENAI_API_KEY"),
            temperature=0.1,
        ),
        instruction=EXTRACTION_PROMPT,
    )
    
    # setup crawling, Passing caching for now but maybe we can come back to it.
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        extraction_strategy=extraction_strategy,
        # min 10 words, else we skip
        word_count_threshold=10,
    )
    
    # rubn the crawler - best first search priority
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
                # print("POUTPUT", result.url)
                # print("TYPE", type(result))
                
                if not result.success:
                    print(f"  ❌ Failed to fetch")
                    continue

                # Parse extracted content
                extracted = json.loads(result.extracted_content)
                
                # if url ends with pdf, handle separately

                # go through each part
                # if relevant, write the chunk:
                # write chunk with: URL, 

                # for now we save them.
                if result.url.endswith(".pdf"):
                    await scrape_pdf_with_llm(result.url)
                    continue
                else:
                    # extrscted is a list of json
                    for document in extracted:
                        if not document.get("relevant", False):
                            reason = document.get("reason", "Unknown")
                            print(f"Not relevant: {reason}")
                        else:
                            chunks = document.get("chunks", [])
                            print(f"Extracted {len(chunks)} chunks")

                            # Add URL and timestamp to this document
                            document["url"] = url
                            document["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                            # Save this document
                            filename = f"{hash(url) % 100000:05d}.json"
                            filepath = os.path.join(output_dir, filename)

                            with open(filepath, "w", encoding="utf-8") as f:
                                json.dump(document, f, indent=2, ensure_ascii=False)

                            print(f"  💾 Saved to {filename}")

                            if chunks:
                                preview = chunks[0]["text"][:100]
                                print(f"  📄 Preview: {preview}")

                    
                    # Extract links for crawling
                    new_links = extract_links(result.html, url)
                    added = 0
                    
                    for link in new_links:
                        if link not in visited and link not in [u for _, u in queue]:
                            # Calculate priority based on keywords in URL
                            priority = calculate_priority(link, keywords) if use_best_first else 0
                            queue.append((priority, link))
                            added += 1
                    
                    print(f"Found {added} new links (queue: {len(queue)})")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
            
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
        max_pages=1500,
        use_best_first=True,  # Set False for breadth-first search
        keywords=keywords
    )
    
    print("\n✅ Done! Check the 'llm_extracted_data_toronto' folder for results.")


if __name__ == "__main__":
    asyncio.run(main())
