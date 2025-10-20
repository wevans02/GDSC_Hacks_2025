# 🧑‍⚖️ Paralegal AI – Multi-City Municipal Bylaw Assistant

Paralegal AI is an intelligent legal assistant that helps users query and understand **municipal bylaws** across multiple cities using natural language. It combines automated web scraping, structured LLM extraction, hybrid semantic search, and AI-powered summarization to make complex local legislation accessible and transparent.

---

## ✨ Features

* **Natural Language Queries**
  Ask questions like “Can I park overnight in Guelph?” or “What’s the fine for noise violations in Waterloo?”

* **Hybrid Search (Vector + Keyword)**
  Combines **Gemini 768‑dim embeddings** for semantic similarity and **BM25 keyword search** for precision.

* **Multi‑City Support**
  Each city’s bylaws are stored in separate MongoDB collections, allowing the assistant to expand easily to new municipalities.

* **Automated Data Pipeline**
  Scrapes city websites using **Playwright** and a custom **best‑first search crawler**, then extracts and chunks text using **GPT‑5**.

* **AI‑Generated Extraction**
  Uses GPT‑5 via the `/responses` API to structure and summarize bylaw text into self‑contained, JSON‑formatted chunks.

* **Source Linking and Metadata**
  Every answer cites its source document (URL or PDF) and includes metadata like page numbers, section titles, and scrape timestamps.

* **User‑Friendly Web Interface**
  Built in **Flutter** and hosted on **Firebase**, the interface provides a clean, responsive chat‑style UI.

---

## 🧰 Technology Stack

| Layer                 | Technology                                                             |
| --------------------- | ---------------------------------------------------------------------- |
| **Frontend**          | Flutter Web (hosted via Firebase Hosting)                              |
| **Backend**           | Flask (Python) – modular API with hybrid search and answer generation  |
| **Database**          | MongoDB Atlas – BM25 + Vector Indexes (768‑dim)                        |
| **Scraper**           | Playwright + custom Best‑First crawler                                 |
| **LLM Extraction**    | GPT‑5 (Responses API)                                                  |
| **Embeddings**        | Gemini `textembedding-001` (768‑dim)                                   |
| **Answer Generation** | GPT‑4o for synthesis and reasoning                                     |
| **Deployment**        | Cloudflare Tunnel (for backend exposure) + Firebase Hosting (frontend) |

Python libraries: `requests`, `pymongo`, `Flask`, `python-dotenv`, `tqdm`, `hashlib`, `re`, `json`, `time`
Flutter libraries: `http`, `flutter_markdown`, `url_launcher`, `google_fonts`, `flutter_animate`

---

## 🧩 System Overview

```text
                ┌────────────────────────────┐
                │  City Websites (HTML/PDF)  │
                └────────────┬───────────────┘
                             │
               (1) Scrape via Playwright BFS
                             │
                ┌────────────▼────────────┐
                │ Markdown & Metadata Out │
                │  (crawl_out/markdown)   │
                └────────────┬────────────┘
                             │
              (2) GPT‑5 Extraction Pass
        → structured JSON chunks (llm_chunks_out/)
                             │
                ┌────────────▼────────────┐
                │ Gemini Embeddings (768) │
                │ MongoDB Hybrid Index    │
                └────────────┬────────────┘
                             │
            (3) Flask Hybrid Search API
                             │
                ┌────────────▼────────────┐
                │   Flutter Web Client    │
                │   (Firebase Hosting)    │
                └─────────────────────────┘
```

---

## ⚙️ Pipeline Stages

### **1. Scraping & Preprocessing**

* Uses **Playwright** for dynamic rendering (JS‑enabled pages).
* A **best‑first search** algorithm crawls pages by relevance score and link depth.
* HTML and PDF pages are handled separately:

  * **HTML** → Markdown conversion.
  * **PDFs** → Extracted via PyMuPDF.

### **2. Chunk Extraction (LLM Pass)**

* Each page is processed by **GPT‑5** using the `/responses` API.
* Produces rich JSON objects containing sections, summaries, cross‑references, and contextual metadata.
* All invalid JSON is automatically cleaned and retried.

### **3. Embedding & Database Ingestion**

* Chunks are embedded using **Gemini `textembedding-001`**.
* Stored in MongoDB with schema:

  ```json
  {
    "combined_text": "...",
    "embedding": [...],
    "city": "Waterloo",
    "page_title": "Nuisance Bylaw",
    "url": "https://...",
    "scraped_at": "2025-10-18T03:12:00Z",
    "section_title": "Definitions",
    "content_type": "bylaw",
    "chunk_hash": "abc123",
    ...
  }
  ```

### **4. Query & Response Generation**

* The **Flask API** performs hybrid retrieval using `$search.knnBeta` (vector) and BM25 keyword clauses.
* The top results are passed to **GPT‑4o**, which synthesizes a concise, well‑cited answer.
* Responses include source citations, links, and optional page numbers.

---

## 🧠 Example Query Flow

1. User: *“Can I have a fire pit in my backyard in Waterloo?”*
2. Flask API retrieves top chunks via hybrid search.
3. GPT‑4o analyzes retrieved text and generates an answer:

   > “Backyard fires are prohibited unless approved by the Fire Chief. Permits are required for contained recreational fires.”
4. Sources displayed with links to the official bylaw pages.

---

## 🧾 Setup Instructions

### ✅ Prerequisites

* Python 3.9+
* Flutter SDK
* MongoDB Atlas account (free M0 tier)
* Google API key for **Gemini**
* OpenAI API key for **GPT‑4o**

### 1. Clone & Environment

```bash
git clone https://github.com/<yourname>/Paralegal-AI.git
cd Paralegal-AI/flask_api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```bash
DATABASE_LOGIN=username:password
DB_NAME=Bylaws
COLLECTION_NAME=Waterloo
CITY=Waterloo
GEMINI_API_KEY=your_google_api_key
OPENAI_API_KEY=your_openai_api_key
```

### 2. Run Extraction & Embedding

```bash
python chunk_llm_pass.py    # Extract structured chunks with GPT‑5
python ingest_embeddings.py # Embed & upload to MongoDB
```

### 3. Run the Backend

```bash
flask run --host=0.0.0.0 --port=5000
```

### 4. Run the Frontend

```bash
cd ../flutter_frontend
flutter pub get
flutter run -d chrome
```

---

## 🚀 Deployment

**Frontend:** Firebase Hosting (auto‑deployed Flutter build)

```bash
flutter build web --release
firebase deploy
```

**Backend:** Dockerized Flask app exposed securely via **Cloudflare Tunnel**.

* Run `docker compose up -d`
* Ensure `.env` secrets are included via Docker environment variables.

**Security Recommendations:**

* Limit CORS origins to your Firebase domain.
* Restrict MongoDB Atlas IP whitelist to your backend host.
* Enable HTTPS and Cloudflare DDoS protection.
* Add request‑rate limiting middleware (Flask‑Limiter or NGINX).

---

## 📊 Benchmarking & Testing

* **Manual Testing:** Currently verified using curated QA questions for each city.
* **Planned Metrics:**

  * Recall @ top‑k for hybrid retrieval
  * Extraction JSON validity rate
  * Average latency (scrape → answer)
  * Cost per document for embedding + LLM extraction

---

## 🗺 Future Roadmap

* ✅ Expand to more Ontario cities (Toronto, Guelph, Waterloo, etc.)
* ⚙️ Add automatic re‑scraping and incremental updates
* 📈 Build benchmarking suite for QA validation
* 🎙 Voice‑enabled access for hands‑free bylaw lookup
* 🧑‍💼 City partnership integration (data synchronization + co‑branding)

---

**Paralegal AI** — Making municipal law accessible, transparent, and searchable for everyone.
