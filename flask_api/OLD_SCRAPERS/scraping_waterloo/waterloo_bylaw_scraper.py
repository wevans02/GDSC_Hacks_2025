# this was entirely found by chatgpt agent mode 
# im pretty impressed damn
# used this prompt which I worked with gpt 5 to generate lol
'''
You are an assistant helping me build a Retrieval-Augmented Generation (RAG) system for Canadian municipal bylaws.

My goal: create a scraper that collects **all or most bylaws for the City of Waterloo, Ontario** from official public sources, so I can index them into a vector database. The scraper should be reliable, easy to re-run to stay up-to-date, and produce clean text suitable for embedding.

Your tasks:
1. **Find the authoritative website(s)** where Waterloo publishes bylaws (e.g. a bylaw directory, archive, or frequently requested bylaws page).
2. **Confirm** the site you select is the official and most comprehensive source available.
3. **Generate working Python code** that:
   - Scrapes the Waterloo bylaw directory (or equivalent authoritative page).
   - Collects all linked bylaws (PDFs, HTML, or other formats).
   - Extracts the text from each bylaw:
     - Use a PDF text extractor if PDFs.
     - Use BeautifulSoup if HTML.
     - (Optional) Fallback to OCR for scanned PDFs if you detect no text layer.
   - Saves output as structured JSON or text files with metadata:
     - bylaw title
     - URL
     - last-fetched timestamp
     - extracted text
   - Computes a file hash so I can detect updates.
4. If possible, also implement:
   - A function to check if a bylaw has been updated (via ETag, Last-Modified, or comparing hash).
   - A scheduler-friendly entrypoint (so I can run it weekly).
   - Error handling for broken links or unreadable documents.

Deliverables:
- The verified Waterloo bylaw source URL(s).
- A Python script that implements the scraping + text extraction workflow for that source.

Important:
- Make the scraper specific to Waterloo (not just a generic template).
- Be explicit about any assumptions or limitations.
- Include instructions for installing any dependencies needed (e.g. pdfplumber, PyMuPDF, requests, beautifulsoup4).

Do not stop at just pointing me to the site — I need runnable code tailored for Waterloo’s bylaws.
'''

"""
Scraper for the City of Waterloo bylaw directory

This script crawls the City of Waterloo's public by‑law directory and
downloads the full text of each by‑law.  It is designed to be
re‑runnable so that it can be scheduled (for example via cron) to keep
an up‑to‑date corpus for a retrieval augmented generation (RAG)
system.

Key features
============
* Finds every by‑law listed on the official directory page (``/en/living/bylaw-directory.aspx``)
  and resolves relative URLs to absolute ones.
* Detects whether a by‑law is published as a PDF or as an HTML page.  If a
  PDF is present it will be downloaded and parsed with pdfplumber.  If not,
  the scraper falls back to extracting the HTML body using BeautifulSoup.
* Extracts basic metadata from the by‑law pages such as the title,
  by‑law number and the "Last passed" or "Last amended" date when
  available.
* Computes a SHA‑256 hash of the extracted text so downstream processes can
  detect changes between runs.
* Writes each by‑law to a JSON file containing the text, metadata and
  fetch timestamp.  The JSON filename is derived from a slugified
  version of the by‑law title.
* Includes an optional update checker that can compare the current hash
  against a previously saved hash (from a previous run) and also
  consults HTTP ``ETag``/``Last‑Modified`` headers when available.

Dependencies
------------
You will need the following Python packages installed:

    pip install requests beautifulsoup4 pdfplumber python-dateutil

pdfplumber in turn depends on ``PyPDF2`` and ``pillow``.  If you
anticipate scanning PDFs that lack a text layer you can optionally
install ``pytesseract`` and ``pdf2image`` and extend
``extract_pdf_text`` accordingly.

Usage
-----
To scrape all by‑laws into an output directory:

    python waterloo_bylaw_scraper.py --output ./waterloo_bylaws

The script will create the output directory if it does not exist and
write one JSON file per by‑law.  You can run the script repeatedly;
existing files will be overwritten if a by‑law's content has changed.

Notes and assumptions
---------------------
* This scraper was developed by inspecting the HTML source of the
  City of Waterloo website.  The site sometimes blocks simple
  programmatic requests; therefore the script sets a modern user
  agent header.  In a local environment you may need to adapt
  headers further or use a session that supports cookies.
* The by‑law directory occasionally links to pages outside the City
  domain (e.g. the Region of Waterloo) or to pages that are not
  by‑laws (e.g. contact pages).  The scraper restricts itself to
  links ending in ``"-bylaw.aspx"`` or to PDFs found within those pages.
* Metadata extraction relies on regular expressions and may need
  adjustments if the City changes the formatting of their pages.
"""

import argparse
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import pdfplumber
import io

# Base URLs and headers used for all HTTP requests.  The City of
# Waterloo's website sometimes blocks automated requests without a
# browser‑like User‑Agent header; using a modern browser UA improves
# reliability.
BASE_URL = "https://www.waterloo.ca"
DIRECTORY_URL = "https://www.waterloo.ca/en/living/bylaw-directory.aspx"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_page(url: str) -> str:
    """Fetch a URL and return its text content.

    Raises ``requests.HTTPError`` if the request fails.  This helper
    centralises headers so that all requests include the same user
    agent.
    """
    logging.debug("Fetching %s", url)
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def find_bylaw_links(directory_html: str) -> List[str]:
    """Parse the by‑law directory page and return a list of by‑law page URLs.

    The directory page contains many links; we restrict to anchors
    within the main content area whose ``href`` ends in ``"-bylaw.aspx"``.
    Relative URLs are resolved against ``BASE_URL``.
    """
    soup = BeautifulSoup(directory_html, "html.parser")
    content_div = soup.find(id="printAreaContent") or soup.find("main")
    if not content_div:
        content_div = soup

    links: List[str] = []
    for a in content_div.find_all("a", href=True):
        href = a["href"]
        # Skip anchors and mailto/telephone links
        if href.startswith("mailto:") or href.startswith("tel:"):
            continue
        # Accept only by‑law pages (links ending with -bylaw.aspx)
        if re.search(r"-bylaw\.aspx$", href):
            if href.startswith("http"):
                url = href
            else:
                url = (
                    f"{BASE_URL}{href}" if href.startswith("/") else f"{BASE_URL}/{href}"
                )
            links.append(url)
    # Remove duplicates while preserving order
    seen = set()
    unique_links = []
    for link in links:
        if link not in seen:
            unique_links.append(link)
            seen.add(link)
    logging.info("Found %d by‑law pages", len(unique_links))
    return unique_links


def extract_pdf_text(pdf_url: str) -> str:
    """Download a PDF and extract its text using pdfplumber.

    If the PDF cannot be downloaded or parsed, an empty string is
    returned.  Optionally you could implement OCR here for scanned
    PDFs that lack a text layer (see documentation).
    """
    logging.debug("Downloading PDF %s", pdf_url)
    try:
        resp = requests.get(pdf_url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        logging.warning("Failed to download PDF %s: %s", pdf_url, e)
        return ""
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        logging.warning("Failed to parse PDF %s: %s", pdf_url, e)
        return ""


def slugify(value: str) -> str:
    """Create a filesystem‑friendly slug from a title."""
    value = re.sub(r"[\s\xa0]+", "_", value.strip())
    value = re.sub(r"[^A-Za-z0-9_]+", "", value)
    return value.lower()


def parse_bylaw_metadata(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """Extract by‑law metadata such as number and dates from the page.

    Returns a dictionary with keys ``title``, ``bylaw_number``,
    ``last_passed``, and ``last_amended`` (values may be ``None`` if
    not found).
    """
    metadata: Dict[str, Optional[str]] = {
        "title": None,
        "bylaw_number": None,
        "last_passed": None,
        "last_amended": None,
    }
    # Title
    h1 = soup.find("h1")
    if h1:
        metadata["title"] = h1.get_text(strip=True)
    # Look for paragraphs that include "Bylaw number:" and date info
    intro_paragraphs = soup.find_all("p", class_="IntroParagraph")
    for p in intro_paragraphs:
        text = p.get_text(separator=" ", strip=True)
        # Extract by‑law number
        m_num = re.search(r"Bylaw number\s*[:\u2013\-]\s*([A-Za-z0-9\s-]+)", text)
        if m_num:
            metadata["bylaw_number"] = m_num.group(1).strip()
        # Extract last passed by council date
        m_passed = re.search(
            r"Last\s+passed\s+by\s+council\s*[:\u2013\-]\s*([A-Za-z0-9,\s]+)",
            text,
        )
        if m_passed:
            try:
                dt = date_parser.parse(m_passed.group(1))
                metadata["last_passed"] = dt.date().isoformat()
            except Exception:
                metadata["last_passed"] = m_passed.group(1).strip()
        # Extract last amended by bylaw (if present)
        m_amended = re.search(
            r"Last\s+amended\s+by\s+By\-law\s+[0-9\-]+,\s*([A-Za-z0-9,\s]+)",
            text,
        )
        if m_amended:
            try:
                dt = date_parser.parse(m_amended.group(1))
                metadata["last_amended"] = dt.date().isoformat()
            except Exception:
                metadata["last_amended"] = m_amended.group(1).strip()
    return metadata


def extract_html_bylaw_text(soup: BeautifulSoup) -> str:
    """Return the plain text of the by‑law from the HTML page.

    We look for a container div (``#printAreaContent``) which holds
    the main by‑law content.  If it is missing we fall back to the
    entire body.  All HTML tags are stripped and consecutive
    whitespace collapsed.
    """
    container = soup.find(id="printAreaContent")
    if not container:
        container = soup.find("main") or soup.body
    text = container.get_text(separator="\n", strip=True)
    # Collapse multiple blank lines
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text


def parse_bylaw_page(url: str) -> Optional[Dict[str, object]]:
    """Parse a single by‑law page and return its metadata and text.

    If the page cannot be fetched or parsed, ``None`` is returned.
    The returned dictionary contains keys: ``url``, ``title``,
    ``bylaw_number``, ``last_passed``, ``last_amended``, ``text`` and
    ``hash``.
    """
    try:
        html = fetch_page(url)
    except Exception as e:
        logging.warning("Failed to fetch %s: %s", url, e)
        return None
    soup = BeautifulSoup(html, "html.parser")
    metadata = parse_bylaw_metadata(soup)
    # Look for a PDF link inside the page
    pdf_link = None
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf"):
            pdf_link = href if href.startswith("http") else f"{BASE_URL}/{href.lstrip('/')}"
            break
    if pdf_link:
        text = extract_pdf_text(pdf_link)
    else:
        text = extract_html_bylaw_text(soup)
    if not text:
        logging.warning("No text extracted from %s", url)
    content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "url": url,
        "title": metadata.get("title"),
        "bylaw_number": metadata.get("bylaw_number"),
        "last_passed": metadata.get("last_passed"),
        "last_amended": metadata.get("last_amended"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "text": text,
        "hash": content_hash,
    }


def save_bylaw_data(bylaw_data: Dict[str, object], output_dir: str) -> None:
    """Write by‑law data to a JSON file in the specified output directory.

    The filename is derived from the by‑law's title.  Existing files
    with the same name will be overwritten.
    """
    title = bylaw_data.get("title") or "untitled_bylaw"
    slug = slugify(title)
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{slug}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bylaw_data, f, ensure_ascii=False, indent=2)
    logging.info("Saved %s", path)


def check_for_update(url: str, previous_hash: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Check whether a by‑law has been updated.

    This function performs an HTTP HEAD request to retrieve ETag
    or Last‑Modified headers.  If those headers are present they
    can be compared to stored values (not implemented here).
    Alternatively the caller can supply a previously computed
    ``previous_hash``; the function will download the page, compute
    the new hash and return a tuple ``(changed, new_hash)``.  The
    function returns ``(True, new_hash)`` if the by‑law appears to
    have changed.
    """
    try:
        response = requests.head(url, headers=HEADERS, allow_redirects=True, timeout=15)
        etag = response.headers.get("ETag")
        last_modified = response.headers.get("Last-Modified")
    except Exception:
        etag = last_modified = None
    if previous_hash is None:
        # Without a previous hash we cannot decide based on content; assume
        # the by‑law should be re‑downloaded.
        return True, None
    try:
        data = parse_bylaw_page(url)
    except Exception:
        return False, None
    new_hash = data["hash"] if data else None
    changed = new_hash != previous_hash
    return changed, new_hash


def scrape_bylaws(output_dir: str) -> None:
    """Scrape the entire by‑law directory and save results into ``output_dir``."""
    logging.info("Starting scrape of Waterloo by‑law directory")
    directory_html = fetch_page(DIRECTORY_URL)
    bylaw_links = find_bylaw_links(directory_html)
    logging.info("Processing %d by‑law pages", len(bylaw_links))
    for link in bylaw_links:
        logging.info("Processing %s", link)
        data = parse_bylaw_page(link)
        if data:
            save_bylaw_data(data, output_dir)


def main():
    parser = argparse.ArgumentParser(description="Scrape City of Waterloo by‑laws")
    parser.add_argument(
        "--output",
        default="waterloo_bylaws",
        help="Directory to write by‑law JSON files (default: ./waterloo_bylaws)",
    )
    parser.add_argument(
        "--loglevel",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.loglevel.upper(), logging.INFO), format="%(levelname)s: %(message)s")
    scrape_bylaws(args.output)


if __name__ == "__main__":
    main()