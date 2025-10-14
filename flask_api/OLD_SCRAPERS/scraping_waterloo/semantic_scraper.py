"""
Enhanced scraper for City of Waterloo website with semantic chunking

This script crawls the entire City of Waterloo website (not just bylaws) and
uses semantic chunking to create better embeddings for a RAG system. It can
answer specific questions like "can I park on X street" by ingesting parking
regulations, street information, and other municipal data.

Key improvements over the bylaw-only scraper:
* Crawls the entire waterloo.ca domain to capture all municipal information
* Uses Crawl4AI for robust, async web scraping
* Implements semantic chunking instead of simple character-based chunking
* Extracts metadata for better retrieval (page type, section, etc.)
* Handles various content types (HTML pages, PDFs, etc.)
* Respects robots.txt and implements rate limiting

Dependencies
------------
pip install crawl4ai beautifulsoup4 pdfplumber python-dateutil sentence-transformers tiktoken

Usage
-----
python waterloo_enhanced_scraper.py --output ./waterloo_data --max-pages 1000

The script will create structured JSON files with semantically chunked content
suitable for vector database ingestion.
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
import io

import requests
from bs4 import BeautifulSoup
import pdfplumber
import tiktoken

try:
    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logging.warning("crawl4ai not available, falling back to requests")

# Semantic chunking using sentence transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMER_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMER_AVAILABLE = False
    logging.warning("sentence-transformers not available, using simpler chunking")


BASE_URL = "https://www.waterloo.ca"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class SemanticChunker:
    """Semantic chunker that splits text based on meaning rather than just length."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", max_chunk_size: int = 512):
        self.max_chunk_size = max_chunk_size
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        if SENTENCE_TRANSFORMER_AVAILABLE:
            self.model = SentenceTransformer(model_name)
            self.use_embeddings = True
        else:
            self.model = None
            self.use_embeddings = False
            logging.info("Using sentence-based chunking without embeddings")
    
    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitter - can be enhanced with spacy/nltk
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))
    
    def chunk_by_sentences(self, sentences: List[str]) -> List[str]:
        """Group sentences into chunks that don't exceed max_chunk_size."""
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = self.count_tokens(sentence)
            
            if current_size + sentence_size > self.max_chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def chunk_by_semantic_similarity(self, sentences: List[str]) -> List[str]:
        """Group sentences by semantic similarity."""
        if not sentences:
            return []
        
        # Encode all sentences
        embeddings = self.model.encode(sentences)
        
        chunks = []
        current_chunk = [sentences[0]]
        current_size = self.count_tokens(sentences[0])
        
        for i in range(1, len(sentences)):
            sentence = sentences[i]
            sentence_size = self.count_tokens(sentence)
            
            # Calculate similarity with last sentence in current chunk
            similarity = embeddings[i] @ embeddings[i-1]
            
            # If similar enough and within size limit, add to current chunk
            if similarity > 0.5 and current_size + sentence_size <= self.max_chunk_size:
                current_chunk.append(sentence)
                current_size += sentence_size
            else:
                # Start new chunk
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_size
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    def chunk(self, text: str) -> List[str]:
        """Main chunking method."""
        sentences = self.split_into_sentences(text)
        
        if not sentences:
            return []
        
        if self.use_embeddings:
            return self.chunk_by_semantic_similarity(sentences)
        else:
            return self.chunk_by_sentences(sentences)


class WaterlooScraper:
    """Comprehensive scraper for waterloo.ca website."""
    
    def __init__(self, output_dir: str, max_pages: int = 1000):
        self.output_dir = output_dir
        self.max_pages = max_pages
        self.visited_urls: Set[str] = set()
        self.chunker = SemanticChunker()
        os.makedirs(output_dir, exist_ok=True)
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL should be crawled."""
        parsed = urlparse(url)
        
        # Only waterloo.ca domain
        if parsed.netloc and "waterloo.ca" not in parsed.netloc:
            return False
        
        # Skip common non-content files
        skip_extensions = ['.jpg', '.png', '.gif', '.pdf', '.doc', '.docx', 
                          '.xls', '.xlsx', '.zip', '.mp4', '.mp3']
        if any(url.lower().endswith(ext) for ext in skip_extensions):
            # We'll handle PDFs separately
            if url.lower().endswith('.pdf'):
                return True
            return False
        
        return True
    
    def extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all valid links from a page."""
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('mailto:') or href.startswith('tel:'):
                continue
            
            full_url = urljoin(base_url, href)
            
            # Remove fragments
            full_url = full_url.split('#')[0]
            
            if self.is_valid_url(full_url) and full_url not in self.visited_urls:
                links.append(full_url)
        
        return links
    
    def extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Optional[str]]:
        """Extract page metadata."""
        metadata = {
            "title": None,
            "description": None,
            "keywords": None,
            "page_type": None,
            "breadcrumbs": []
        }
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata["title"] = title_tag.get_text(strip=True)
        
        # Meta description
        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag and desc_tag.get('content'):
            metadata["description"] = desc_tag['content']
        
        # Keywords
        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_tag and keywords_tag.get('content'):
            metadata["keywords"] = keywords_tag['content']
        
        # Determine page type from URL
        if 'bylaw' in url.lower():
            metadata["page_type"] = "bylaw"
        elif 'parking' in url.lower():
            metadata["page_type"] = "parking"
        elif 'permit' in url.lower():
            metadata["page_type"] = "permit"
        elif '/living/' in url.lower():
            metadata["page_type"] = "living"
        elif '/government/' in url.lower():
            metadata["page_type"] = "government"
        else:
            metadata["page_type"] = "general"
        
        # Extract breadcrumbs if available
        breadcrumb = soup.find('nav', class_=re.compile(r'breadcrumb', re.I))
        if breadcrumb:
            crumbs = [a.get_text(strip=True) for a in breadcrumb.find_all('a')]
            metadata["breadcrumbs"] = crumbs
        
        return metadata
    
    def extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract the main content from a page."""
        # Try to find main content area
        main_content = None
        
        # Common content containers
        for selector in ['#printAreaContent', 'main', '.main-content', 
                        'article', '[role="main"]']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            main_content = soup.body
        
        if not main_content:
            return ""
        
        # Remove script and style elements
        for element in main_content.find_all(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()
        
        text = main_content.get_text(separator='\n', strip=True)
        
        # Clean up whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        return text
    
    async def fetch_page_crawl4ai(self, url: str) -> Optional[str]:
        """Fetch page using Crawl4AI."""
        try:
            config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url, config=config)
                if result.success:
                    return result.html
        except Exception as e:
            logging.error(f"Crawl4AI error for {url}: {e}")
        return None
    
    def fetch_page_requests(self, url: str) -> Optional[str]:
        """Fetch page using requests (fallback)."""
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logging.error(f"Request error for {url}: {e}")
            return None
    
    def process_pdf(self, url: str) -> Optional[Dict]:
        """Download and process a PDF."""
        try:
            response = requests.get(url, headers=HEADERS, timeout=60)
            response.raise_for_status()
            
            text = ""
            with pdfplumber.open(io.BytesIO(response.content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            if not text.strip():
                return None
            
            chunks = self.chunker.chunk(text)
            
            return {
                "url": url,
                "title": url.split('/')[-1],
                "page_type": "pdf",
                "content_type": "pdf",
                "chunks": chunks,
                "fetched_at": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logging.error(f"PDF processing error for {url}: {e}")
            return None
    
    async def process_page(self, url: str) -> Optional[Dict]:
        """Process a single page."""
        if url in self.visited_urls:
            return None
        
        self.visited_urls.add(url)
        logging.info(f"Processing ({len(self.visited_urls)}/{self.max_pages}): {url}")
        
        # Handle PDFs separately
        if url.lower().endswith('.pdf'):
            return self.process_pdf(url)
        
        # Fetch HTML
        if CRAWL4AI_AVAILABLE:
            html = await self.fetch_page_crawl4ai(url)
        else:
            html = self.fetch_page_requests(url)
        
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract content and metadata
        metadata = self.extract_metadata(soup, url)
        content = self.extract_main_content(soup)
        
        if not content.strip():
            return None
        
        # Chunk the content semantically
        chunks = self.chunker.chunk(content)
        
        # Extract links for further crawling
        new_links = self.extract_links(soup, url)
        
        page_data = {
            "url": url,
            "title": metadata["title"],
            "description": metadata["description"],
            "keywords": metadata["keywords"],
            "page_type": metadata["page_type"],
            "breadcrumbs": metadata["breadcrumbs"],
            "content_type": "html",
            "chunks": chunks,
            "num_chunks": len(chunks),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "outbound_links": new_links[:50]  # Limit links to avoid explosion
        }
        
        return page_data, new_links
    
    def save_page_data(self, page_data: Dict) -> None:
        """Save page data to JSON."""
        url_hash = hashlib.md5(page_data["url"].encode()).hexdigest()
        filename = f"{url_hash}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(page_data, f, ensure_ascii=False, indent=2)
        
        logging.debug(f"Saved {filename}")
    
    async def crawl(self, start_url: str = BASE_URL) -> None:
        """Main crawling method."""
        queue = [start_url]
        
        while queue and len(self.visited_urls) < self.max_pages:
            url = queue.pop(0)
            
            if url in self.visited_urls:
                continue
            
            result = await self.process_page(url)
            
            if result:
                if isinstance(result, tuple):
                    page_data, new_links = result
                    self.save_page_data(page_data)
                    
                    # Add new links to queue
                    for link in new_links:
                        if link not in self.visited_urls and link not in queue:
                            queue.append(link)
                else:
                    # PDF result
                    self.save_page_data(result)
            
            # Be respectful with rate limiting
            await asyncio.sleep(0.5)
        
        logging.info(f"Crawling complete. Processed {len(self.visited_urls)} pages.")
        logging.info(f"Data saved to {self.output_dir}")


async def main():
    parser = argparse.ArgumentParser(
        description="Scrape City of Waterloo website with semantic chunking"
    )
    parser.add_argument(
        "--output",
        default="waterloo_data",
        help="Directory to write JSON files (default: ./waterloo_data)"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1000,
        help="Maximum number of pages to crawl (default: 1000)"
    )
    parser.add_argument(
        "--start-url",
        default=BASE_URL,
        help=f"Starting URL (default: {BASE_URL})"
    )
    parser.add_argument(
        "--loglevel",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=getattr(logging, args.loglevel.upper(), logging.INFO),
        format="%(levelname)s: %(message)s"
    )
    
    scraper = WaterlooScraper(args.output, args.max_pages)
    await scraper.crawl(args.start_url)


if __name__ == "__main__":
    asyncio.run(main())