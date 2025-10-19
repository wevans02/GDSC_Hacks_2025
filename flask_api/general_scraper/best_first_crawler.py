"""
Best first search crawler ; scrapes main body content with playwright,
takes any links from the site and adds them to priority queue,
weighted by prevalence of keywords
priority queue ordered by url keyword score (higher first)
deduped frontier + visited set
same-domain crawl with robots.txt respect
markdown output per page + JSON manifest

special domain profiles for Waterloo/Kitchener, to be added for each city to optimize scraping on that citys page specifically
We do have a generic fallback though, but it might take in too much or lose some content.
"""

import asyncio, os, re, json, time, logging, hashlib
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, urljoin, urldefrag
from urllib import robotparser
from pathlib import Path

from bs4 import BeautifulSoup
from markdownify import markdownify as md
from playwright.async_api import async_playwright


# for pdfs
import httpx
from io import BytesIO
from pdfminer.high_level import extract_text as pdf_extract_text
import pdfplumber
from itertools import zip_longest
from statistics import median


START_URL = os.getenv("START_SCRAPE_URL", "https://www.waterloo.ca/en/living/bylaw-directory.aspx")
ALLOWED_DOMAINS = None  # e.g. ["www.waterloo.ca"]  (None => infer from START_URL)
OUT_DIR = Path(os.getenv("OUTPUT_DIR", "crawl_out"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "200"))
MAX_DEPTH = int(os.getenv("MAX_DEPTH", "5"))
CONCURRENCY = int(os.getenv("CONCURRENCY", "4"))
HEADLESS = os.getenv("HEADLESS", "1") != "0"

# Keywords - prioritize scraping urls with these keywords
SCRAPER_KEYWORDS = [
    "bylaw", "by-law", "regulation", "ordinance", "municipal code",
    "parking", "traffic", "zoning", "noise", "property",
    "animal", "business license", "permit", "waste",
    "water", "sign", "pool", "fence", "building", "fine", "enforcement"
]

# Skip patterns (don’t enqueue)  — note: PDF is intentionally NOT excluded
URL_EXCLUDE_PATTERNS = [
    r"/(login|signin|sign-in)/", r"/(admin|editor)/", r"/search", r"/careers",
    r"/events", r"/news", r"/calendar", r"/subscribe", r"/feedback",
    r"\.(jpg|jpeg|png|gif|svg|webp|ico|css|js|zip|rar|7z|tar|gz|mp4|mp3|wav|mov|avi)$",
]

# Per-domain content selectors (extend as you add cities)
DOMAIN_SELECTORS: Dict[str, Dict[str, List[str]]] = {
    "www.waterloo.ca": {   # eSolutions CMS (Waterloo)
        "prefer": ["#mainContent #printAreaContent"],
        "drop": [
            "#EmergencyBannerWrapperOuter", "#BrowserBannerWrapperOuter",
            "#actions", "#breadcrumbs", "footer", ".share",
            "#contactMainContainer", "#subNavContainer"
        ],
    },
    "www.kitchener.ca": {  # eSolutions CMS (Kitchener)
        "prefer": ["#mainContent #printAreaContent", "main [role=main]", "main"],
        "drop": [
            "#EmergencyBannerWrapperOuter", "#BrowserBannerWrapperOuter",
            "#actions", "#breadcrumbs", "footer", ".share",
            "#contactMainContainer", "#subNavContainer"
        ],
    },
}

GENERIC_PREFER = [
    "main [role=main]", "main article", "#main-content", "#mainContent", "main",
    "#content, .content, .article, .rich-text"
]
GENERIC_DROP = ["header", "footer", "nav", ".breadcrumbs", ".share", ".social", ".cookie-banner"]


# ------------------------- URL / text utils -------------------------

def norm_url(base: str, href: str) -> Optional[str]:
    """Normalize relative URLs, drop mailto/tel/js and strip fragments."""
    if not href:
        return None
    href = href.strip()
    if href.startswith(("mailto:", "tel:", "javascript:")):
        return None
    u = urljoin(base, href)
    u, _ = urldefrag(u)
    return u

def allowed_by_domain(u: str, allowed: List[str]) -> bool:
    """Keep crawler on allowed domains."""
    net = urlparse(u).netloc.lower()
    return any(net == d or net.endswith(f".{d}") for d in allowed)

def matches_any(patterns: List[str], text: str) -> bool:
    """Return True if text matches any blacklist regex."""
    return any(re.search(p, text, re.I) for p in patterns)

def sha_name(s: str, n: int = 8) -> str:
    """Short, deterministic filename from URL hash."""
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:n]

def score_keywords(text: str, keywords: List[str]) -> float:
    """Simple keyword frequency score (sum of counts)."""
    tl = text.lower()
    return float(sum(tl.count(k.lower()) for k in keywords))

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def html_to_markdown(html: str) -> str:
    """HTML → Markdown; strip noisy tags and collapse excess newlines."""
    m = md(html, heading_style="ATX", strip=["script", "style", "noscript"])
    m = re.sub(r"\n{3,}", "\n\n", m).strip()
    return m

def extract_with_selectors(full_html: str, domain: str) -> Tuple[str, str]:
    """Return (markdown, plain_text). Uses domain-specific selectors then generic fallback."""
    soup = BeautifulSoup(full_html, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()

    prof = DOMAIN_SELECTORS.get(domain, {})
    drop = prof.get("drop", []) or GENERIC_DROP
    for sel in drop:
        for n in soup.select(sel):
            n.decompose()

    prefer = prof.get("prefer", []) or GENERIC_PREFER

    chosen = None
    for sel in prefer:
        el = soup.select_one(sel)
        if el and el.get_text(strip=True):
            chosen = el
            break
    if not chosen:
        chosen = soup.body or soup

    html_sel = str(chosen)
    md_out = html_to_markdown(html_sel)
    plain = chosen.get_text("\n", strip=True)
    return md_out, plain

def looks_like_pdf(url: str) -> bool:
    return url.lower().endswith(".pdf")


# ------------------------- PDF pipeline -------------------------
def _extract_pdf_page_markdown(page: "pdfplumber.page.Page") -> Tuple[str, str]:
    """
    Returns (markdown_for_page, plain_text_for_page).
    - Tries table extraction first; renders each found table as Markdown.
    - Also extracts free text with word-level grouping to respect columns.
    """
    md_chunks = []
    plain_chunks = []

    # 1) Try tables
    try:
        # table_settings tuned for bordered gov tables
        tables = page.extract_tables(table_settings={
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "intersection_tolerance": 5,
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "edge_min_length": 20,
            "min_words_vertical": 1,
            "min_words_horizontal": 1,
            "keep_blank_chars": True,
            "text_x_tolerance": 2,
            "text_y_tolerance": 2,
        })
    except Exception:
        tables = []

    if tables:
        for idx, t in enumerate(tables, 1):
            if not t or not any(any(c for c in row) for row in t):
                continue
            md_table = _table_to_markdown(t)
            md_chunks.append(f"**Table {idx}**\n\n{md_table}\n")
            # for plain text we add a compacted CSV-ish representation
            txt_rows = [", ".join("" if c is None else str(c).strip() for c in row) for row in t]
            plain_chunks.append("\n".join(txt_rows))

    # 2) Free text (word grouping helps preserve columns/order better than simple page.extract_text)
    try:
        words = page.extract_words(keep_blank_chars=False, use_text_flow=True)
        free_text = _join_blocks_with_spacing(words)
    except Exception:
        # fallback: simple text
        free_text = (page.extract_text() or "").strip()

    if free_text:
        md_chunks.append(f"{free_text}\n")
        plain_chunks.append(free_text)

    md_page = "\n".join(md_chunks).strip()
    plain_page = "\n\n".join(plain_chunks).strip()
    return md_page, plain_page


async def fetch_pdf_text(url: str, timeout: int = 60_000) -> Tuple[bool, Optional[str], Optional[str], Optional[str], Optional[int]]:
    """
    Download PDF and extract page-marked Markdown + plain text with tables preserved where possible.
    Returns: (ok, markdown_all, plain_all, error, page_count)
    - Every page is wrapped with:  === PAGE {n} START === / === PAGE {n} END ===
    - Tables are rendered as Markdown where detected.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; MunicipalCrawler/1.1; +https://example.org)",
        "Accept": "*/*",
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout/1000) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            data = r.content
    except Exception as e:
        return False, None, None, f"download_failed: {e}", None

    try:
        md_pages = []
        plain_pages = []
        with pdfplumber.open(BytesIO(data)) as pdf:
            page_count = len(pdf.pages)
            if page_count == 0:
                return False, None, None, "empty_pdf", 0

            for i, page in enumerate(pdf.pages, start=1):
                md_page, plain_page = _extract_pdf_page_markdown(page)

                # Wrap with explicit page markers (for GPT to set page_numbers)
                md_pages.append(f"=== PAGE {i} START ===\n{md_page}\n=== PAGE {i} END ===")
                plain_pages.append(f"=== PAGE {i} START ===\n{plain_page}\n=== PAGE {i} END ===")

        md_text = "\n\n".join(md_pages).strip()
        plain_text = "\n\n".join(plain_pages).strip()
        if not md_text.strip():
            return False, None, None, "no_text_extracted", page_count

        return True, md_text, plain_text, None, page_count

    except Exception as e:
        # Hard fallback to pdfminer text (no table layout, but still page-marked)
        try:
            from pdfminer.high_level import extract_text as pdfminer_extract_text
            text = pdfminer_extract_text(BytesIO(data)) or ""
            if not text.strip():
                return False, None, None, f"pdf_parse_failed: {e}", None

            # naive page marker split (pdfminer loses page breaks; so add a single page marker)
            md_text = f"=== PAGE 1 START ===\n{text.strip()}\n=== PAGE 1 END ==="
            return True, md_text, text.strip(), None, 1
        except Exception as e2:
            return False, None, None, f"pdf_parse_failed(pdfminer): {e2}", None



def _table_to_markdown(rows):
    """
    Turn a list-of-lists (strings) into a Markdown table.
    Cleans up None cells and normalizes column widths.
    """
    if not rows:
        return ""

    # Coerce to strings + strip
    rows = [[("" if c is None else str(c)).strip() for c in r] for r in rows]

    # Some tables have ragged rows; pad to max width
    max_cols = max(len(r) for r in rows)
    rows = [r + [""] * (max_cols - len(r)) for r in rows]

    header = rows[0]
    sep = ["---"] * max_cols
    body = rows[1:] if len(rows) > 1 else []

    def line(cells): return "| " + " | ".join(cells) + " |"
    parts = [line(header), line(sep)]
    for r in body:
        parts.append(line(r))
    return "\n".join(parts)

def _join_blocks_with_spacing(words, x_gap=2.0, y_gap=4.0):
    """
    pdfplumber approach for multi-column pages:
    Group words into lines, then join lines honoring vertical gaps.
    Not perfect, but better than naive join.
    """
    if not words:
        return ""

    # Group by y (line) using median height tolerance
    ys = [ (w["top"] + w["bottom"]) / 2.0 for w in words ]
    line_tol = median([w["height"] for w in words]) * 0.8

    lines = []
    current = []
    current_y = None

    for w in sorted(words, key=lambda w: ( (w["top"] + w["bottom"])/2.0, w["x0"] )):
        wy = (w["top"] + w["bottom"]) / 2.0
        if current is None or current_y is None:
            current, current_y = [w], wy
            continue
        if abs(wy - current_y) <= line_tol:
            current.append(w)
        else:
            lines.append(sorted(current, key=lambda w: w["x0"]))
            current, current_y = [w], wy
    if current:
        lines.append(sorted(current, key=lambda w: w["x0"]))

    # Join tokens within lines; inject newlines between lines
    out_lines = []
    for line in lines:
        pieces = [line[0]["text"]]
        for left, right in zip(line, line[1:]):
            gap = right["x0"] - left["x1"]
            if gap > x_gap:
                pieces.append(" ")
            pieces.append(right["text"])
        out_lines.append("".join(pieces).strip())

    # Merge lines with blank line when vertical gaps are large – already grouped; simple join
    return "\n".join(out_lines).strip()



# ------------------------- Crawler -------------------------

@dataclass(order=True)
class FrontierItem:
    # Negated score so Python's heapq (min-heap) acts like max-heap by score
    neg_score: float
    depth: int
    url: str

class BestFirstCrawler:
    """
    Asynchronous best-first web crawler using Playwright.

    Core design:
    - Maintains a priority queue (frontier) of URLs ordered by keyword relevance.
    - Expands highest-scoring URLs first (best-first search).
    - Respects robots.txt rules and same-domain restriction.
    - Extracts and converts main body HTML → Markdown using domain-specific selectors.
    - Records metadata for each visited page in a JSON manifest.

    Attributes:
        frontier: A heap-based priority queue (max-heap via negated scores)
        visited:  A set of normalized URLs already processed
        browser/context: Playwright browser objects (shared across pages)
        meta_rows: Collected metadata for manifest.json
        page_sem: Async semaphore controlling max concurrent tabs
    """

    def __init__(self, start_url: str):
        self.start_url = start_url
        self.origin = urlparse(start_url)
        self.allowed_domains = ALLOWED_DOMAINS or [self.origin.netloc]
        self.robots = robotparser.RobotFileParser()
        self.robots.set_url(urljoin(f"{self.origin.scheme}://{self.origin.netloc}", "/robots.txt"))
        with contextlib_silent():
            self.robots.read()

        self.visited: set[str] = set()
        self.frontier: List[FrontierItem] = []
        self.browser = None
        self.context = None
        self.page_sem = asyncio.Semaphore(CONCURRENCY)

        # output
        self.meta_rows = []
        ensure_dir(OUT_DIR)
        ensure_dir(OUT_DIR / "markdown")

    async def __aenter__(self):
        self._pw = await async_playwright().start()
        self.browser = await self._pw.chromium.launch(headless=HEADLESS)
        self.context = await self.browser.new_context()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        await self._pw.stop()

    def allowed(self, url: str) -> bool:
        # domain restriction
        if not allowed_by_domain(url, self.allowed_domains):
            return False
        # robots
        with contextlib_silent():
            if not self.robots.can_fetch("*", url):
                return False
        # basic excludes
        if matches_any(URL_EXCLUDE_PATTERNS, url):
            return False
        return True

    def push_frontier(self, url: str, score: float, depth: int):
        if url in self.visited:
            return
        import heapq
        heapq.heappush(self.frontier, FrontierItem(neg_score=-score, depth=depth, url=url))

    def pop_frontier(self) -> Optional[FrontierItem]:
        import heapq
        if not self.frontier:
            return None
        return heapq.heappop(self.frontier)

    async def fetch_and_extract_html(self, url: str, prefer_inner_selector: Optional[str]) -> Dict:
        """HTML path via Playwright; returns dict with markdown/plain/links."""
        async with self.page_sem:
            page = await self.context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                if prefer_inner_selector:
                    await page.wait_for_selector(prefer_inner_selector, timeout=12000)
                    inner = await page.locator(prefer_inner_selector).inner_html()
                    content_html = f"<div id='__inner__'>{inner}</div>"
                else:
                    content_html = await page.content()

                md_out, plain = extract_with_selectors(content_html, urlparse(url).netloc)

                # Harvest links (after DOM ready)
                hrefs = await page.eval_on_selector_all("a", "els => els.map(e => e.getAttribute('href'))")
                await page.close()
                return {"success": True, "source_type": "html", "markdown": md_out, "plain": plain, "links": hrefs or []}
            except Exception as e:
                with contextlib_silent():
                    await page.close()
                return {"success": False, "error": str(e), "links": []}

    async def fetch_and_extract_pdf(self, url: str) -> Dict:
        ok, md_text, plain, err, page_count = await fetch_pdf_text(url)
        if not ok:
            return {"success": False, "error": err or "pdf_error", "links": []}
        return {
            "success": True,
            "source_type": "pdf",
            "markdown": md_text,
            "plain": plain,
            "links": [],
            "page_count": page_count or 0,
        }

    def domain_prefer_selector(self, url: str) -> Optional[str]:
        prof = DOMAIN_SELECTORS.get(urlparse(url).netloc)
        prefs = prof.get("prefer") or [] if prof else []
        return prefs[0] if prefs else None

    def save_markdown(self, url: str, depth: int, score: float, md_text: str):
        name = f"{sha_name(url)}.md"
        p = OUT_DIR / "markdown" / name
        with p.open("w", encoding="utf-8") as f:
            f.write(f"# URL: {url}\n\nDepth: {depth} | Score: {score:.2f}\n\n")
            f.write(md_text)

    def record_meta(self, row: Dict):
        self.meta_rows.append(row)

    def flush_manifest(self):
        manifest = OUT_DIR / "manifest.json"
        with manifest.open("w", encoding="utf-8") as f:
            json.dump(self.meta_rows, f, indent=2, ensure_ascii=False)

    async def crawl(self):
        # seed
        seed_selector = self.domain_prefer_selector(self.start_url)
        self.push_frontier(self.start_url, score=1.0, depth=0)

        pages_done = 0
        while self.frontier and pages_done < MAX_PAGES:
            item = self.pop_frontier()
            if not item:
                break
            url, depth = item.url, item.depth
            if url in self.visited:
                continue
            if depth > MAX_DEPTH:
                continue
            if not self.allowed(url):
                continue

            self.visited.add(url)

            # Branch: PDF vs HTML
            if looks_like_pdf(url):
                res = await self.fetch_and_extract_pdf(url)
                prefer_sel = None
            else:
                prefer_sel = self.domain_prefer_selector(url) or seed_selector
                res = await self.fetch_and_extract_html(url, prefer_inner_selector=prefer_sel)

            if not res["success"]:
                logging.warning(f"❌ [{depth}] {url} | {res.get('error','')}")
                self.record_meta({
                    "url": url, "depth": depth, "ok": False,
                    "error": res.get("error", ""), "timestamp": time.time()
                })
                continue

            plain = res["plain"]
            md_text = res["markdown"]
            source_type = res.get("source_type", "html")

            # score and persist
            score = score_keywords(plain, SCRAPER_KEYWORDS)
            word_count = len(plain.split())
            logging.info(f"✅ [{depth}] {url} | type={source_type} | score={score:.2f}, words={word_count}")

            if word_count >= 50 and len(md_text.strip()) >= 50:
                self.save_markdown(url, depth, score, md_text)
                self.record_meta({
                    "url": url,
                    "depth": depth,
                    "ok": True,
                    "source_type": source_type,
                    "score": round(score, 2),
                    "word_count": word_count,
                    "timestamp": time.time(),
                    **({"page_count": res.get("page_count", 0)} if source_type == "pdf" else {}),
                })


            pages_done += 1

            # Only HTML pages contribute new links (PDFs have none)
            for h in (res["links"] or []):
                child = norm_url(url, h)
                if not child:
                    continue
                if not self.allowed(child):
                    continue
                if child in self.visited:
                    continue
                if matches_any(URL_EXCLUDE_PATTERNS, child):
                    continue
                anchor_bonus = 0.0
                if any(k in (h or "").lower() for k in ("bylaw","by-law","parking","zoning","regulation")):
                    anchor_bonus = 0.5
                self.push_frontier(child, score=score + anchor_bonus, depth=depth + 1)

        self.flush_manifest()


# ------------------------- Helpers -------------------------

from contextlib import contextmanager
@contextmanager
def contextlib_silent():
    """
    Suppresses exceptions within its context (used for best-effort cleanup/robots).
    """
    try:
        yield
    except Exception:
        pass


# ------------------------- Entry -------------------------

async def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    async with BestFirstCrawler(START_URL) as crawler:
        await crawler.crawl()
    print(f"\n📦 Output saved under: {OUT_DIR.resolve()}")

if __name__ == "__main__":
    asyncio.run(main())
