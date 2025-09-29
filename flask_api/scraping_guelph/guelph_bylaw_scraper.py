# another chatgpt agent mode banger
"""
Scraper for the City of Guelph bylaws

This script targets the City of Guelph's official “Bylaws and policies”
page (https://guelph.ca/city-hall/by-laws-and-policies-2/) and
downloads each by‑law document linked there.  Unlike Waterloo,
Guelph publishes most of its bylaws directly as PDFs hosted
in the ``wp-content/uploads`` directory.  The table on the
bylaw page lists each by‑law name and, when available, the year
and by‑law number.

The scraper performs the following steps:

* Fetch the main bylaw directory page and parse it with
  BeautifulSoup.
* Locate all anchor tags within the table whose ``href`` contains
  ``/wp-content/uploads/`` and ends with ``.pdf``.  These are the
  by‑law PDF links.
* For each link, extract the bylaw title and attempt to parse the
  bylaw number and year from the surrounding cell text.
* Download each PDF and extract its text using pdfplumber.
* Compute a SHA‑256 hash of the extracted text for change detection.
* Save each bylaw as a JSON file containing metadata and the
  extracted text.  Filenames are derived from slugified titles.

Dependencies:

    pip install requests beautifulsoup4 pdfplumber python-dateutil

Usage:

    python guelph_bylaw_scraper.py --output ./guelph_bylaws

"""

import argparse
import hashlib
import io
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import pdfplumber

# Constants
BASE_URL = "https://guelph.ca"
DIRECTORY_URL = "https://guelph.ca/city-hall/by-laws-and-policies-2/"

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
    """Fetch the content of a web page using a browser‑like user agent.

    Raises ``requests.HTTPError`` on failure.
    """
    logging.debug("Fetching %s", url)
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def find_bylaw_links(directory_html: str) -> List[Dict[str, str]]:
    """Parse the by‑law directory page and return a list of dictionaries.

    Each dictionary contains ``title``, ``pdf_url``, ``year`` (if
    parsable) and ``bylaw_number`` (if parsable).  We locate
    anchor tags whose ``href`` contains ``/wp-content/uploads/`` and
    ends with ``.pdf``.  The text of the parent ``th`` cell often
    includes the year and by‑law number in the format ``(YEAR)-NUMBER``.
    """
    soup = BeautifulSoup(directory_html, "html.parser")
    results: List[Dict[str, str]] = []
    # The table with bylaws uses the WP block table structure.  Find
    # all anchor tags linking to PDFs under wp-content/uploads.
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/wp-content/uploads/" in href and href.lower().endswith(".pdf"):
            # Build absolute URL
            pdf_url = href if href.startswith("http") else f"{BASE_URL}{href}"
            # Title is the anchor text
            title = a.get_text(strip=True)
            # The table cell may contain year/number after the anchor
            cell_text = a.parent.get_text(separator=" ", strip=True)
            # Attempt to extract year and bylaw number
            year = None
            bylaw_number = None
            m = re.search(r"\((\d{4})\)\s*-\s*([0-9]+)", cell_text)
            if m:
                year = m.group(1)
                bylaw_number = m.group(2)
            results.append({
                "title": title,
                "pdf_url": pdf_url,
                "year": year,
                "bylaw_number": bylaw_number,
            })
    # Remove duplicates (some links may appear multiple times)
    unique: List[Dict[str, str]] = []
    seen_urls = set()
    for item in results:
        if item["pdf_url"] not in seen_urls:
            unique.append(item)
            seen_urls.add(item["pdf_url"])
    logging.info("Found %d by‑law PDF links", len(unique))
    return unique


def extract_pdf_text(pdf_url: str) -> str:
    """Download a PDF and extract its text using pdfplumber.

    Returns an empty string on error.  Because many Guelph bylaws
    contain scanned text, this function may return an empty string.
    Consider adding OCR (pytesseract) if needed.
    """
    logging.debug("Downloading PDF %s", pdf_url)
    try:
        resp = requests.get(pdf_url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
    except Exception as e:
        logging.warning("Failed to download %s: %s", pdf_url, e)
        return ""
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"
    except Exception as e:
        logging.warning("Failed to parse %s: %s", pdf_url, e)
    return text.strip()


def slugify(value: str) -> str:
    """Create a filesystem‑friendly slug from a title."""
    value = re.sub(r"[\s\xa0]+", "_", value.strip())
    value = re.sub(r"[^A-Za-z0-9_]+", "", value)
    return value.lower()


def save_bylaw_data(data: Dict[str, object], output_dir: str) -> None:
    """Save the by‑law metadata and text as a JSON file."""
    title = data.get("title") or "untitled_bylaw"
    slug = slugify(title)
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{slug}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logging.info("Saved %s", path)


def scrape_bylaws(output_dir: str) -> None:
    """Scrape the Guelph bylaw directory and save each bylaw."""
    logging.info("Fetching Guelph bylaw directory")
    html = fetch_page(DIRECTORY_URL)
    items = find_bylaw_links(html)
    for item in items:
        title = item["title"]
        pdf_url = item["pdf_url"]
        year = item.get("year")
        bylaw_number = item.get("bylaw_number")
        logging.info("Processing %s", title)
        text = extract_pdf_text(pdf_url)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        bylaw_data = {
            "title": title,
            "pdf_url": pdf_url,
            "year": year,
            "bylaw_number": bylaw_number,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "text": text,
            "hash": content_hash,
        }
        save_bylaw_data(bylaw_data, output_dir)


def main():
    parser = argparse.ArgumentParser(description="Scrape City of Guelph bylaws")
    parser.add_argument(
        "--output",
        default="guelph_bylaws",
        help="Output directory for bylaw JSON files",
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

# TODO: why this:
# [skip] empty text in: /Users/colewesterveld/Desktop/Coding Projects/GDSC_Hacks_2025/flask_api/scraping_guelph/guelph_bylaws/chief_administrative_officer_appointment_bylaw.json
# [skip] empty text in: /Users/colewesterveld/Desktop/Coding Projects/GDSC_Hacks_2025/flask_api/scraping_guelph/guelph_bylaws/outside_water_use_bylaw.json
# [skip] empty text in: /Users/colewesterveld/Desktop/Coding Projects/GDSC_Hacks_2025/flask_api/scraping_guelph/guelph_bylaws/brooklyn_and_college_hill_heritage_conservation_district_bylaw.json
# [skip] empty text in: /Users/colewesterveld/Desktop/Coding Projects/GDSC_Hacks_2025/flask_api/scraping_guelph/guelph_bylaws/accessible_parking_bylaw.json
# [skip] empty text in: /Users/colewesterveld/Desktop/Coding Projects/GDSC_Hacks_2025/flask_api/scraping_guelph/guelph_bylaws/meeting_investigation_bylaw.json