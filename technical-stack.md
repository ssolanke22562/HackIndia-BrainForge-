# Technical Stack & Component Logic Specification: SecondSelf

**Document Version:** 1.0.0  
**Project:** SecondSelf — Multi-Modal AI Second Brain  
**Status:** Approved Technical Stack Specification  
**Associated Documents:** [PRD.pdf](file:///c:/Users/scs/Desktop/hacton%20jaipur/PRD.pdf) | [architecture.md](file:///c:/Users/scs/Desktop/hacton%20jaipur/architecture.md) | [edge-case.md](file:///c:/Users/scs/Desktop/hacton%20jaipur/edge-case.md) | [implementation-plan.md](file:///c:/Users/scs/Desktop/hacton%20jaipur/implementation-plan.md)

---

## 1. Architectural Philosophy & Technology Foundations

SecondSelf is built as a high-performance, local-first multi-modal knowledge platform. The stack selection prioritizes four non-negotiable architectural mandates:
1. **Sub-Second Response Latency:** Sub-second LLM inference via Groq LPUs, local vector similarity compute ($< 150\text{ms}$), and pre-indexed SQLite FTS5 lexical matching.
2. **Zero Ingestion Data Loss:** Two-phase commit persisting incoming raw bytes and metadata manifests to disk (`raw/`) before any asynchronous extraction or AI classification pipeline begins.
3. **Multi-Tier Fault Tolerance:** Resilient fallback chains for all external dependencies (LLMs, OCR, audio transcription, web scraping) ensuring the system degrades gracefully rather than halting.
4. **Clean Web Separation:** An asynchronous Python ASGI backend (FastAPI) paired with a high-performance React 18 / TypeScript frontend, avoiding monolithic template rendering or demo frameworks like Streamlit.

---

## 2. Master Technology Matrix & Selection Rationale

| Category | Primary Technology | Secondary / Fallback | Selection Rationale & Alternatives Evaluated |
| :--- | :--- | :--- | :--- |
| **Backend Runtime** | Python 3.11+ | — | Superior asynchronous I/O performance (`asyncio`), native support for modern ML/NLP libraries (`sentence-transformers`, `faiss`, `PyMuPDF`). |
| **Application Framework** | **FastAPI 0.111+** | Starlette | Native async endpoints, strict runtime validation with Pydantic v2, automatic OpenAPI/Swagger documentation, lightweight footprint compared to Django/Flask. |
| **ASGI Web Server** | **Uvicorn 0.30+** | Gunicorn | High-throughput asynchronous event loop (`uvloop`), WebSocket capability, low-overhead HTTP request parsing. |
| **Primary LLM Provider** | **Groq API (`llama-3.1-70b-versatile` / `8b-instant`)** | **Google Gemini (`gemini-1.5-flash`)** | Groq delivers $\sim 500\text{ tokens/sec}$ on LPU hardware, crucial for real-time PARA classification and streaming RAG. Gemini 1.5 Flash provides seamless failover with generous free-tier limits. |
| **Embeddings Model** | **`sentence-transformers/all-MiniLM-L6-v2`** | `BAAI/bge-small-en-v1.5` | 384-dimensional dense vectors, runs locally on CPU with $< 15\text{ms}$ per chunk inference time. Zero API cost, zero network roundtrips. |
| **Vector Store** | **FAISS (Facebook AI Similarity Search - CPU)** | ChromaDB | Highly optimized C++ vector index (`IndexFlatIP`) supporting normalized inner product cosine similarity. Persisted to disk as an immutable binary index. |
| **Lexical Search (BM25)** | **SQLite FTS5 (Full-Text Search)** | Whoosh | Built directly into SQLite; enables zero-latency BM25 tokenized keyword search without running separate search clusters (Elasticsearch/Meilisearch). |
| **Relational Database** | **SQLite 3 (WAL Mode)** | PostgreSQL | Embedded zero-configuration database. Concurrency locks mitigated via Write-Ahead Logging (`PRAGMA journal_mode = WAL`) and `busy_timeout = 5000`. Managed via `aiosqlite` and SQLAlchemy 2.0. |
| **PDF Extraction** | **PyMuPDF (`fitz`)** | Tesseract OCR | C-based MuPDF engine extracts text blocks, bounding boxes, and document hierarchy $10\times$ faster than `pypdf`/`pdfplumber`. Falls back to OCR for scanned PDFs. |
| **DOCX Extraction** | **`python-docx`** | `docx2txt` | Direct OpenXML document tree traversal, preserving structural headings, bullet lists, and tabular cells. |
| **Image OCR & Vision** | **`pytesseract` / Tesseract 5.x** | Groq LLaMA-Vision / Gemini Flash | Local OCR engine with bilateral noise filtering via OpenCV; falls back to multimodal LLM vision when image is a non-text diagram or chart. |
| **Audio Transcription** | **`faster-whisper` (CTranslate2)** | Whisper API | Re-implementation of OpenAI Whisper using CTranslate2, achieving $4\times$ speedup and $50\%$ less VRAM/RAM than vanilla PyTorch Whisper. |
| **Tabular Summarization** | **`pandas` + `openpyxl`** | Built-in `csv` module | Automated dialect sniffing (`csv.Sniffer`), column data-type profiling, and markdown table serialization. |
| **Web Content Extraction** | **`trafilatura`** | `beautifulsoup4` + `httpx` | State-of-the-art web scraper that strips navigation menus, footers, and ads, extracting pure body markdown with 8.0s async timeout. |
| **Frontend Framework** | **React 18+ (Vite) + TypeScript** | Next.js (App Router) | Instant hot module replacement (HMR), strict type safety, zero server-side rendering complexity for hackathon portability. |
| **Graph Visualization** | **`vis-network` (Canvas WebGL)** | Cytoscape.js | High-framerate HTML5 canvas force-directed graph physics, custom node clustering, smooth zoom/pan, built-in physics stabilization to prevent UI freezing. |
| **UI Styling** | **Vanilla CSS Design System** | Tailwind CSS | Tailored dark-mode glassmorphic aesthetics, fluid CSS variables, neon violet/cyan accents, and zero CSS build purging issues. |
| **Icons & Micro-UI** | **`lucide-react`** | Heroicons | Clean, modular SVG iconography for file types, PARA category badges, and navigation controls. |
| **Containerization** | **Docker Multi-Stage Build** | Docker Compose | Combines Node.js static build stage and Python 3.11-slim runtime with pre-installed `tesseract-ocr` and `ffmpeg` libraries. |

---

## 3. Detailed File-by-File Technical Blueprint

Below is the complete architectural specification for every file in the SecondSelf ecosystem, detailing its specific role, required tools, I/O schemas, execution logic, and edge-case defenses.

---

### Backend Core & Ingestion Subsystem

```
backend/
├── config.py
├── main.py
├── capture.py
└── parsers/
    ├── __init__.py
    ├── pdf_parser.py
    ├── docx_parser.py
    ├── image_ocr.py
    ├── audio_transcribe.py
    ├── csv_parser.py
    └── link_extractor.py
```

#### 1. `backend/config.py`
* **System Responsibility:** Centralized runtime configuration, environment variable management, file size constraints, and path definitions.
* **Tools & Libraries:** `pydantic-settings`, `pydantic>=2.0`, `python-dotenv`, `pathlib.Path`.
* **Input / Output:**
  - *Input:* `.env` file and system environment variables (`GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `DATA_DIR`).
  - *Output:* Strongly-typed singleton `Settings` object accessible across the backend.
* **Execution Logic:**
  1. Define `Settings` class inheriting from `BaseSettings`.
  2. Declare directory paths: `BASE_DIR`, `RAW_DIR` (`raw/`), `WIKI_DIR` (`wiki/`), `DB_DIR` (`backend/db/`), `VECTOR_DIR` (`backend/db/vector_store/`). Automatically invoke `mkdir(parents=True, exist_ok=True)` on startup.
  3. Declare model names, cosine similarity threshold ($\tau = 0.70$), max degree cap ($K=5$), and file upload size limits (PDF: 25MB, Audio: 50MB, Image: 15MB, Text/CSV: 10MB).
  4. Validate presence of at least one valid LLM key (`GROQ_API_KEY` or `GEMINI_API_KEY`).
* **Edge Cases & Failure Recovery:**
  - Missing `.env` file $\rightarrow$ logs warning and initializes with safe defaults (SQLite local paths, offline heuristic mode flagged).

---

#### 2. `backend/main.py`
* **System Responsibility:** ASGI web server application entrypoint, CORS configuration, exception handling middleware, and route mounting.
* **Tools & Libraries:** `fastapi`, `fastapi.middleware.cors.CORSMiddleware`, `uvicorn`.
* **Input / Output:**
  - *Input:* Incoming HTTP REST requests from frontend.
  - *Output:* JSON payloads, multipart responses, server-sent events.
* **Execution Logic:**
  1. Instantiate `FastAPI(title="SecondSelf API", version="1.0.0")`.
  2. Configure `CORSMiddleware` with configurable allowed origins (defaults to `http://localhost:5173`, `http://localhost:3000`).
  3. Register lifespan handler:
     - *Startup:* Initialize SQLite tables (`database.init_db()`), load sentence-transformers embedding model, and verify vector store index readiness.
     - *Shutdown:* Safely flush and serialize FAISS index to disk.
  4. Mount sub-routers: `/capture`, `/classify`, `/link`, `/graph`, `/ask`, `/history`.
  5. Expose `GET /health` endpoint returning system health, active database connection, and model loading status.
* **Edge Cases & Failure Recovery:**
  - Unhandled server exceptions $\rightarrow$ Global exception handler catches errors and returns standardized `{ "error": true, "message": "...", "detail": "..." }` with appropriate HTTP 4xx/5xx status.

---

#### 3. `backend/capture.py`
* **System Responsibility:** Gateway for all multi-modal captures. Orchestrates raw file persistence, hash deduplication, parser delegation, and initial database registration.
* **Tools & Libraries:** `fastapi.UploadFile`, `hashlib.sha256`, `uuid.uuid4`, `aiofiles`, `aiosqlite`.
* **Input / Output:**
  - *Input:* Multipart file upload OR JSON body `{"type": "link" | "note", "content": "str", "title": "str?"}`.
  - *Output:* `CaptureResponse` JSON `{ "id": "uuid", "status": "captured", "source_type": "...", "extracted_snippet": "..." }`.
* **Execution Logic:**
  1. Read incoming payload byte stream into memory.
  2. Compute **SHA-256 fingerprint**: `hashlib.sha256(content).hexdigest()`.
  3. Query SQLite `notes` table for matching `sha256_hash`. If found:
     - Return HTTP 200 with status `"DUPLICATE_IDENTIFIED"` and existing `note_id`.
  4. Generate new `note_id = str(uuid.uuid4())`.
  5. **Two-Phase Write:**
     - Stash raw binary file to `raw/<note_id>.<ext>`.
     - Write manifest metadata to `raw/<note_id>.json`.
  6. Inspect MIME type / extension and route to appropriate parser in `parsers/`.
  7. Normalize output into unified `CaptureItem` schema.
  8. Insert base record into SQLite `notes` table with status `"captured"`.
  9. Trigger asynchronous background tasks: PARA classification (`classify.py`) and vector auto-linking (`link.py`).
* **Edge Cases & Failure Recovery:**
  - Client disconnects mid-upload $\rightarrow$ Asynchronous chunked streaming; if file transfer fails, remove partial file from `raw/` to prevent corruption.
  - Unsupported extension $\rightarrow$ Stash file in `raw/quarantine/` and return HTTP 422 with supported format list.

---

#### 4. `backend/parsers/pdf_parser.py`
* **System Responsibility:** High-fidelity layout-aware text extraction from PDF documents, with automatic fallback for scanned pages.
* **Tools & Libraries:** `pymupdf` (`fitz`), `pytesseract`, `PIL.Image`.
* **Input / Output:**
  - *Input:* File path to raw PDF `raw/<id>.pdf`.
  - *Output:* Dict `{ "text": "str", "page_count": int, "metadata": dict }`.
* **Execution Logic:**
  1. Open document with `doc = fitz.open(file_path)`.
  2. Inspect `doc.is_encrypted`: if true, attempt decryption with blank password; if still locked, raise `EncryptedFileError`.
  3. Iterate over pages and extract text using layout-aware blocks: `page.get_text("blocks")`.
  4. Sort blocks vertically and horizontally to prevent multi-column interleaving.
  5. **Scanned PDF Check:** If total extracted character count across document is $< 50$ characters:
     - Log warning: `"Zero or sparse selectable text detected. Triggering OCR fallback."`
     - Render each page to high-res pixmap: `pix = page.get_pixmap(dpi=200)`.
     - Convert pixmap to PIL Image and execute `pytesseract.image_to_string(img)`.
  6. Return combined text string along with page count and title metadata.
* **Edge Cases & Failure Recovery:**
  - Massive PDF ($> 100$ pages) $\rightarrow$ Stream page extraction in 10-page batches; extract Table of Contents (TOC) hierarchy.
  - Password-protected PDF $\rightarrow$ Caught and handled, returning 422 Unprocessable Entity with clear error message.

---

#### 5. `backend/parsers/docx_parser.py`
* **System Responsibility:** Linearization of OpenXML Word documents into clean, structured Markdown text.
* **Tools & Libraries:** `python-docx` (`docx.Document`), `zipfile`.
* **Input / Output:**
  - *Input:* File path `raw/<id>.docx`.
  - *Output:* Dict `{ "text": "str", "paragraph_count": int, "metadata": dict }`.
* **Execution Logic:**
  1. Wrap file open in `try...except zipfile.BadZipFile` to intercept corrupt archives.
  2. Traverse `doc.paragraphs`:
     - Map Word heading styles (`Heading 1`, `Heading 2`) to Markdown headings (`#`, `##`).
     - Preserve bullet items and numbered lists.
  3. Traverse `doc.tables`:
     - Linearize table rows and cells into standard Markdown table format (`| col1 | col2 |`).
  4. Concatenate paragraphs and tables in document sequence.
* **Edge Cases & Failure Recovery:**
  - Corrupt DOCX container $\rightarrow$ Raises descriptive error and marks note status as `parse_failed`.
  - Legacy `.doc` binary file uploaded $\rightarrow$ Intercept MIME type and inform user to upload `.docx` format.

---

#### 6. `backend/parsers/image_ocr.py`
* **System Responsibility:** Optical Character Recognition (OCR) and visual content understanding for screenshots, photos, and diagrams.
* **Tools & Libraries:** `pytesseract`, `PIL.Image`, `PIL.ImageOps`, `cv2` (OpenCV).
* **Input / Output:**
  - *Input:* File path `raw/<id>.<png|jpg|webp>`.
  - *Output:* Dict `{ "text": "str", "confidence": float, "caption": "str?" }`.
* **Execution Logic:**
  1. Load image using `PIL.Image.open(file_path)`. Standardize orientation via EXIF tags.
  2. **Dimension Guardrail:** If max dimension $> 2048\text{px}$, downscale proportionally using `LANCZOS` filter to prevent OOM spikes.
  3. Preprocess with OpenCV: convert to grayscale, apply bilateral filter for noise removal, and adaptive thresholding.
  4. Run Tesseract OCR: `pytesseract.image_to_data(processed_img, output_type=Output.DICT)`.
  5. Calculate mean OCR confidence score from word data.
  6. **Non-Text Diagram Check:** If extracted text $< 15$ characters and confidence $< 40\%$:
     - Invoke Vision LLM (Groq LLaMA-Vision or Gemini Flash) with prompt: *"Provide a detailed technical description and transcription of any diagrams, charts, or visual concepts in this image."*
     - Assign LLM visual description as `extracted_text`.
* **Edge Cases & Failure Recovery:**
  - Unsupported image format (HEIC/TIFF) $\rightarrow$ Pillow auto-converts to standard RGB in-memory.
  - Extremely blurry image $\rightarrow$ Returns extracted text with low-confidence flag for user review.

---

#### 7. `backend/parsers/audio_transcribe.py`
* **System Responsibility:** Speech-to-text conversion for voice memos, recorded meetings, and audio notes.
* **Tools & Libraries:** `faster-whisper` (`WhisperModel`), `numpy`, `wave` / `soundfile`.
* **Input / Output:**
  - *Input:* File path `raw/<id>.<mp3|wav|m4a>`.
  - *Output:* Dict `{ "text": "str", "duration_seconds": float, "language": "str" }`.
* **Execution Logic:**
  1. Open audio stream and compute Root Mean Square (RMS) energy across sample buffer:
     $$\text{RMS} = \sqrt{\frac{1}{N} \sum_{i=1}^N x_i^2}$$
  2. **Silence / Noise Floor Check:** If $\text{RMS} < 0.005$ (silent audio):
     - Abort Whisper model execution.
     - Return status `"empty_audio"` and text `"[Audio recording contains silence or background noise only]"`.
  3. Initialize `WhisperModel("base.en", device="cpu", compute_type="int8")`.
  4. Transcribe audio using Voice Activity Detection (VAD) filter:
     `segments, info = model.transcribe(file_path, vad_filter=True, vad_parameters=dict(min_silence_duration_ms=500))`.
  5. Concatenate segment texts with timestamp markers.
* **Edge Cases & Failure Recovery:**
  - Long audio file ($> 30$ minutes) $\rightarrow$ Chunk into sequential 30-second segments to prevent memory bloat.
  - Corrupt audio header $\rightarrow$ Caught via soundfile, rejecting with HTTP 422.

---

#### 8. `backend/parsers/csv_parser.py`
* **System Responsibility:** Structural summary, schema detection, and markdown conversion for tabular datasets.
* **Tools & Libraries:** `pandas`, `openpyxl`, `csv.Sniffer`.
* **Input / Output:**
  - *Input:* File path `raw/<id>.<csv|xlsx>`.
  - *Output:* Dict `{ "text": "str", "row_count": int, "col_count": int, "schema": dict }`.
* **Execution Logic:**
  1. If CSV: read first 4096 bytes and use `csv.Sniffer().sniff(sample)` to auto-detect delimiter (comma, semicolon, tab).
  2. Load dataset into pandas DataFrame (`df = pd.read_csv(...)` or `pd.read_excel(...)`).
  3. **Large Dataset Protection:** If rows $> 500$:
     - Do NOT serialize full raw table into text.
     - Generate structured schema summary: column names, data types, null counts, and summary statistics (`df.describe()`).
     - Render top 5 and bottom 5 sample rows as a Markdown table.
  4. If rows $\le 500$: convert entire table to formatted Markdown table using `df.to_markdown(index=False)`.
* **Edge Cases & Failure Recovery:**
  - Multi-sheet Excel workbook $\rightarrow$ Loop through all sheets; linearize each sheet as a distinct sub-section.
  - `#REF!` or formula errors $\rightarrow$ Use `data_only=True` in `openpyxl` to extract cached values.

---

#### 9. `backend/parsers/link_extractor.py`
* **System Responsibility:** Web bookmark ingestion, removing navigation boilerplate and extracting clean article markdown.
* **Tools & Libraries:** `trafilatura`, `httpx`, `beautifulsoup4`.
* **Input / Output:**
  - *Input:* URL string `https://...`.
  - *Output:* Dict `{ "text": "str", "title": "str", "url": "str", "metadata": dict }`.
* **Execution Logic:**
  1. Validate URL syntax and protocol (`http` / `https`).
  2. Asynchronously fetch web page using `httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers={"User-Agent": "SecondSelf-Archivist/1.0"})`.
  3. Pass raw HTML to `trafilatura.extract(html, include_links=True, include_images=False, output_format="txt")`.
  4. If `trafilatura` returns empty content (JavaScript SPA or paywall):
     - Parse with `BeautifulSoup4` to extract `<title>`, OpenGraph tags (`og:description`, `og:title`), and meta descriptions.
  5. Return sanitized article text with source URL and title.
* **Edge Cases & Failure Recovery:**
  - Unresponsive / hanging server $\rightarrow$ Hard 8.0s timeout catches exception, preventing worker starvation.
  - HTTP 403 Forbidden / Cloudflare gate $\rightarrow$ Extracts available OpenGraph metadata and flags note with warning.

---

### AI Intelligence & Knowledge Graph Subsystem

```
backend/
├── classify.py
├── link.py
└── build_graph.py
```

#### 10. `backend/classify.py`
* **System Responsibility:** Automated categorization of captures using the PARA method, tag generation, and 1-line operational summaries.
* **Tools & Libraries:** `groq.AsyncGroq`, `google.genai`, `pydantic`, `json_repair`.
* **Input / Output:**
  - *Input:* Note extracted text and metadata.
  - *Output:* Pydantic `ClassificationResult`:
    ```json
    {
      "category": "Projects",
      "tags": ["rag", "fastapi", "hackathon"],
      "summary": "Technical architecture and roadmap for SecondSelf second brain.",
      "confidence": 0.95
    }
    ```
* **Execution Logic:**
  1. Construct prompt containing strict definition of PARA framework:
     - **Projects:** Active, goal-oriented tasks with deadlines.
     - **Areas:** Long-term responsibilities, domains, and health/finances.
     - **Resources:** Topics of ongoing interest, reference material, cheatsheets.
     - **Archives:** Completed projects or inactive reference data.
  2. Send prompt to **Tier 1 Provider (Groq `llama-3.1-70b-versatile`)** with `response_format={"type": "json_object"}`.
  3. Parse returned JSON with Pydantic schema validation.
  4. If Groq encounters HTTP 429 rate limits or timeouts $\rightarrow$ Failover to **Tier 2 (Gemini 1.5 Flash)**.
  5. If LLM returns malformed JSON $\rightarrow$ Pass through `json_repair.repair_json()` to strip markdown fences and repair truncated brackets.
  6. If all cloud LLMs fail $\rightarrow$ Execute **Tier 3 (Offline Regex/Heuristic Classifier)**:
     - Regex match for "TODO", "deadline", "sprint" $\rightarrow$ `Projects`.
     - Assign default category `Resources` with `confidence: 0.30` and `requires_review: true`.
  7. Write synchronized Markdown note to `wiki/<Category>/<Title>.md` with YAML frontmatter.
  8. Update SQLite `notes` record with category, tags, and summary.
* **Edge Cases & Failure Recovery:**
  - Zero-byte extracted text $\rightarrow$ Assigns `Archives` with empty summary, avoiding wasted API calls.

---

#### 11. `backend/link.py`
* **System Responsibility:** Recursive text chunking, dense vector embedding calculation, FAISS vector indexing, and semantic auto-linking.
* **Tools & Libraries:** `sentence-transformers`, `faiss`, `numpy`, `aiosqlite`.
* **Input / Output:**
  - *Input:* Note extracted text and `note_id`.
  - *Output:* Vector chunk embeddings stored in FAISS; semantic links inserted into SQLite `links` table.
* **Execution Logic:**
  1. **Recursive Character Splitter:**
     - Split text into chunks of 500-800 characters with 15% overlap.
     - Store chunks in SQLite `chunks` table (`chunk_id`, `note_id`, `chunk_index`, `content`).
  2. **Embedding Generation:**
     - Compute 384-dimensional dense vectors using `sentence_transformers.SentenceTransformer("all-MiniLM-L6-v2")`.
     - Normalize vectors to unit length ($L_2$ norm) for inner product cosine similarity calculation:
       $$\vec{v}_{norm} = \frac{\vec{v}}{\|\vec{v}\|_2}$$
  3. **Vector Index Insertion:**
     - Add chunk vectors to FAISS `IndexFlatIP`.
  4. **Document-Level Semantic Auto-Linking:**
     - Compute average document vector $\vec{V}_{doc}$ across all chunks of the note.
     - Compute cosine similarity against all existing document vectors in database:
       $$\text{Cosine Similarity}(\vec{u}, \vec{v}) = \vec{u} \cdot \vec{v}$$
     - Filter pairs where $\text{Similarity} \ge \tau$ (Default threshold $\tau = 0.70$).
  5. **Hub Explosion / Supernode Mitigation:**
     - Sort candidate links by similarity score descending.
     - Cap maximum auto-generated edges per note at top-$K$ ($K=5$).
     - Prune mutual reciprocal duplicates.
     - Insert edges into SQLite `links` table with similarity score and timestamp.
* **Edge Cases & Failure Recovery:**
  - Isolated "Orphan" note (no neighbor meets $\tau = 0.70$) $\rightarrow$ Create special anchor link connecting note to its PARA category hub node.

---

#### 12. `backend/build_graph.py`
* **System Responsibility:** Serializing notes and auto-links into graph topology JSON format for interactive visual rendering.
* **Tools & Libraries:** `aiosqlite`, `pydantic`.
* **Input / Output:**
  - *Input:* Query filters (`category`, `source_type`).
  - *Output:* `GraphData` JSON:
    ```json
    {
      "nodes": [
        {
          "id": "uuid",
          "label": "Roadmap Q3",
          "category": "Projects",
          "source_type": "pdf",
          "summary": "Technical roadmap...",
          "val": 4,
          "color": "#8b5cf6"
        }
      ],
      "edges": [
        {
          "from": "uuid-1",
          "to": "uuid-2",
          "value": 0.84,
          "title": "Cosine similarity: 0.84"
        }
      ]
    }
    ```
* **Execution Logic:**
  1. Fetch all active notes from SQLite `notes` table.
  2. Compute degree centrality (number of connected links) for each note to determine node radius (`val`).
  3. Assign visual color scheme based on PARA category:
     - `Projects`: Neon Violet (`#8b5cf6`)
     - `Areas`: Neon Cyan (`#06b6d4`)
     - `Resources`: Emerald Green (`#10b981`)
     - `Archives`: Amber (`#f59e0b`)
  4. Assign node icons/shapes based on `source_type` (PDF, image, audio, etc.).
  5. Fetch all links from `links` table and format as edge array with `value = similarity_score`.
  6. Return serialized JSON.
* **Edge Cases & Failure Recovery:**
  - Graph with zero notes $\rightarrow$ Returns empty arrays `{ "nodes": [], "edges": [] }` without crashing; frontend handles zero-state.

---

### RAG, Conversational Memory & Persistence Subsystem

```
backend/
├── ask.py
├── history.py
└── db/
    ├── database.py
    ├── models.py
    └── vector_store.py
```

#### 13. `backend/ask.py`
* **System Responsibility:** Hybrid retrieval-augmented generation (RAG) query execution, grounded answer synthesis, and citation attribution.
* **Tools & Libraries:** `faiss`, `aiosqlite`, `groq.AsyncGroq`, `google.genai`, `sentence-transformers`.
* **Input / Output:**
  - *Input:* JSON `{"question": "str", "session_id": "uuid?"}`.
  - *Output:* `AnswerResponse` JSON:
    ```json
    {
      "answer": "Based on your notes, the roadmap was approved on June 1st [Note: c7b8e1a2]...",
      "citations": [
        {
          "note_id": "c7b8e1a2",
          "chunk_id": "9f3d4c8e",
          "title": "Roadmap_2026.pdf",
          "category": "Projects",
          "snippet": "Quarterly Technical Strategy..."
        }
      ],
      "session_id": "uuid"
    }
    ```
* **Execution Logic:**
  1. Embed user question using `sentence-transformers/all-MiniLM-L6-v2`.
  2. **Dense Vector Search:** Query FAISS index for top-$K_1$ candidate chunks ($K_1=8$).
  3. **Sparse Lexical Search:** Query SQLite FTS5 table `notes_fts` using tokenized BM25 query for top-$K_2$ candidate chunks ($K_2=8$).
  4. **Reciprocal Rank Fusion (RRF):** Combine rankings from both retrievers:
     $$RRF(d) = \sum_{m \in \{\text{dense}, \text{sparse}\}} \frac{1}{60 + r_m(d)}$$
  5. Take top $N=5$ highest-ranked unique chunks.
  6. **Knowledge Void Guardrail:** If maximum retrieval similarity score $S_{max} < 0.45$:
     - Return honest response: *"I couldn't find any information about this in your captured notes."* with 0 citations, preventing hallucinations.
  7. **Prompt Injection & Grounding Isolation:**
     - Wrap context chunks in explicit delimiters:
       ```
       <user_knowledge_context id="note_id" title="filename" date="timestamp">
       [Chunk Text]
       </user_knowledge_context>
       ```
  8. If `session_id` provided, fetch conversation history from `history.py` (sliding window of last 4 turns).
  9. Invoke LLM with strict system instructions:
     *"Answer exclusively based on the provided context tags. For every statement of fact, cite the source note using `[Note: <note_id>]`. Do not invent citations."*
  10. Persist Q&A interaction to SQLite via `history.py`.
* **Edge Cases & Failure Recovery:**
  - Conflicting facts across notes $\rightarrow$ LLM system prompt prioritizes more recent notes based on injected `date` metadata and alerts user to discrepancy.

---

#### 14. `backend/history.py`
* **System Responsibility:** Multi-session conversational memory persistence, thread retrieval, and citation snapshotting.
* **Tools & Libraries:** `aiosqlite`, `uuid`, `datetime`.
* **Input / Output:**
  - *Input:* Session IDs, user queries, assistant responses, and retrieved chunk metadata.
  - *Output:* Session list summaries, full message history threads.
* **Execution Logic:**
  1. Create or load session from SQLite `sessions` table.
  2. On each turn:
     - Insert user prompt into `messages` table (`role: "user"`).
     - Insert assistant response into `messages` table (`role: "assistant"`).
     - Snapshot exact retrieved chunks into `retrievals` table linking `message_id`, `note_id`, `chunk_id`, and excerpt text.
  3. **Sliding Context Window:**
     - When continuing a session, fetch the last 4 turns.
     - If thread length $> 8$ turns, generate a 2-sentence summary of earlier turns and prepend to prompt context.
  4. Expose endpoints:
     - `GET /history`: Returns list of all sessions sorted by `updated_at` descending.
     - `GET /history/{session_id}`: Returns complete thread with message details and cited chunks.
* **Edge Cases & Failure Recovery:**
  - Cited note deleted after conversation $\rightarrow$ `retrievals` table preserves historical snapshot of chunk text, so citations in history view never break.

---

#### 15. `backend/db/database.py`
* **System Responsibility:** Asynchronous SQLite database connection pool management, PRAGMA configuration, and schema initialization.
* **Tools & Libraries:** `aiosqlite`, `sqlalchemy.ext.asyncio`.
* **Input / Output:**
  - *Output:* Asynchronous database session context manager.
* **Execution Logic:**
  1. Set SQLite file path: `backend/db/secondself.db`.
  2. Configure connection hook to execute essential concurrency PRAGMAs on every connection:
     ```sql
     PRAGMA journal_mode = WAL;
     PRAGMA busy_timeout = 5000;
     PRAGMA synchronous = NORMAL;
     PRAGMA foreign_keys = ON;
     ```
  3. Execute DDL script on startup to create all required tables and FTS5 index if not present.
* **Edge Cases & Failure Recovery:**
  - High concurrency write collisions (`SQLITE_BUSY`) $\rightarrow$ Mitigated by WAL mode and 5000ms busy timeout.

---

#### 16. `backend/db/models.py`
* **System Responsibility:** Declarative data models and schema definitions for relational data and search indices.
* **Tools & Libraries:** `sqlalchemy.orm`, `pydantic`.
* **Schema Definitions:**
  - `notes`: `id` (PK, UUID), `source_type`, `raw_path`, `wiki_path`, `title`, `category`, `tags_json`, `summary`, `sha256_hash`, `confidence`, `created_at`, `updated_at`.
  - `chunks`: `id` (PK, UUID), `note_id` (FK), `chunk_index`, `content`, `embedding_id`, `created_at`.
  - `links`: `id` (PK, UUID), `source_note_id` (FK), `target_note_id` (FK), `similarity_score`, `link_type`, `created_at`.
  - `sessions`: `id` (PK, UUID), `title`, `created_at`, `updated_at`.
  - `messages`: `id` (PK, UUID), `session_id` (FK), `role`, `content`, `created_at`.
  - `retrievals`: `id` (PK, UUID), `message_id` (FK), `note_id`, `chunk_id`, `snippet_text`, `relevance_score`.
  - `notes_fts`: Virtual SQLite FTS5 table indexed on `(title, summary, extracted_text)`.

---

#### 17. `backend/db/vector_store.py`
* **System Responsibility:** FAISS vector index abstraction, vector normalization, disk persistence, and nearest neighbor search.
* **Tools & Libraries:** `faiss`, `numpy`, `pathlib.Path`.
* **Input / Output:**
  - *Input:* 384-dimensional numpy float32 vectors.
  - *Output:* Top-K indices and inner product similarity scores.
* **Execution Logic:**
  1. On startup: check for existing index file `backend/db/vector_store/index.faiss`.
  2. If exists, load via `faiss.read_index()`; otherwise, instantiate `faiss.IndexFlatIP(384)`.
  3. Maintain an in-memory mapping `chunk_id_map: List[str]` to translate FAISS integer IDs to UUID chunk IDs.
  4. `add_vectors(vectors, chunk_ids)`: Normalize vectors ($L_2$ norm) and add to FAISS index.
  5. `search(query_vector, top_k)`: Normalize query vector, execute `index.search()`, and return mapped UUIDs with scores.
  6. `save()`: Serialize index and ID mapping to disk.
* **Edge Cases & Failure Recovery:**
  - Index corruption on disk $\rightarrow$ Automatically rebuilds vector index by scanning all chunks stored in SQLite `chunks` table.

---

### Frontend UI & Client Components Subsystem

```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── pages/
│   │   ├── CapturePage.tsx
│   │   ├── GraphPage.tsx
│   │   ├── AskPage.tsx
│   │   └── HistoryPage.tsx
│   ├── components/
│   │   ├── Navbar.tsx
│   │   ├── Dropzone.tsx
│   │   ├── GraphView.tsx
│   │   ├── ChatBox.tsx
│   │   └── CitationModal.tsx
│   └── styles/
│       ├── index.css
│       └── components.css
```

#### 18. `frontend/src/App.tsx`
* **System Responsibility:** Application root shell, global state management, client-side routing, and notifications.
* **Tools & Libraries:** `react`, `react-router-dom` (or tab state router), `lucide-react`.
* **Execution Logic:**
  1. Maintain active navigation tab state: `"capture" | "graph" | "ask" | "history"`.
  2. Render sticky `Navbar` with knowledge base stats (total notes, auto-links, system health).
  3. Render active page component with smooth fade-in transitions.
  4. Global toast notification container for capture feedback and error handling.

---

#### 19. `frontend/src/pages/CapturePage.tsx`
* **System Responsibility:** Unified multi-modal ingestion studio.
* **Tools & Libraries:** `react`, `lucide-react`, `Dropzone.tsx`.
* **Execution Logic:**
  1. Render tabbed capture interface:
     - **File Upload Tab:** Drag-and-drop zone accepting PDF, DOCX, PNG, JPG, MP3, WAV, CSV, XLSX.
     - **Web Link Tab:** URL input field with "Fetch & Ingest" button.
     - **Quick Note Tab:** Rich text scratchpad for typing or pasting quick notes.
  2. Display real-time progress indicators:
     - "Uploading..." $\rightarrow$ "Extracting text..." $\rightarrow$ "Classifying PARA..." $\rightarrow$ "Auto-linking...".
  3. Render recently captured items list with source format badges and PARA category chips.

---

#### 20. `frontend/src/pages/GraphPage.tsx`
* **System Responsibility:** Full-screen interactive knowledge graph explorer view.
* **Tools & Libraries:** `react`, `GraphView.tsx`, `lucide-react`.
* **Execution Logic:**
  1. Fetch graph topology from `GET /graph`.
  2. Render `GraphView` with force-directed layout.
  3. Provide interactive control bar:
     - PARA category filter toggles (Projects, Areas, Resources, Archives).
     - Source format filter toggles.
     - Search input to zoom into and highlight a specific node by name.
     - Physics stabilization toggle & reset view button.
  4. Render side drawer / inspector card when a node is clicked, showing its summary, tags, and connected neighbors.

---

#### 21. `frontend/src/pages/AskPage.tsx`
* **System Responsibility:** Conversational RAG Q&A interface with interactive source citations.
* **Tools & Libraries:** `react`, `ChatBox.tsx`, `CitationModal.tsx`, `lucide-react`.
* **Execution Logic:**
  1. Render chat stream with question input bar.
  2. On submission: send query to `POST /ask`, show animated typing / retrieval pulse.
  3. Parse assistant answer markdown and replace `[Note: <id>]` tokens with clickable citation pills.
  4. Clicking a citation pill opens `CitationModal` displaying the exact context chunk, original source file name, and similarity score.
  5. Provide "Save to History" status and session resumption controls.

---

#### 22. `frontend/src/pages/HistoryPage.tsx`
* **System Responsibility:** Session memory browser allowing users to revisit, inspect, and continue past Q&A sessions.
* **Tools & Libraries:** `react`, `lucide-react`.
* **Execution Logic:**
  1. Fetch list of past sessions from `GET /history`.
  2. Render left sidebar with session titles and relative timestamps.
  3. Clicking a session loads its complete message thread and retrieval references from `GET /history/{session_id}`.
  4. Render bottom follow-up input allowing the user to continue the conversation thread via `POST /history/{session_id}/continue`.

---

#### 23. `frontend/src/components/Navbar.tsx`
* **System Responsibility:** Top navigation bar displaying brand identity, route switcher, and live backend telemetry.
* **Tools & Libraries:** `react`, `lucide-react`.
* **Execution Logic:**
  1. Display SecondSelf logo with glowing neural icon.
  2. Tab navigation buttons: Capture Studio, Knowledge Graph, Ask Brain, Chat History.
  3. Polls `GET /health` to display real-time connection status (green pulse for online, amber for offline/fallback mode).
  4. Display live counter pills: Total Notes & Graph Edges.

---

#### 24. `frontend/src/components/Dropzone.tsx`
* **System Responsibility:** Reusable drag-and-drop file ingestion area with format validation and preview thumbnails.
* **Tools & Libraries:** `react`, HTML5 Drag & Drop API, `lucide-react`.
* **Execution Logic:**
  1. Handle `onDragOver`, `onDragLeave`, `onDrop` events with visual border glow.
  2. Validate file size against configured caps before dispatching upload.
  3. **PII / Secret Pre-Check:** Simple regex scan checking for exposed API keys (`sk-...`) in text files, alerting user before transmission.
  4. Render upload progress bar and format badge (e.g., PDF icon, Audio waveform icon).

---

#### 25. `frontend/src/components/GraphView.tsx`
* **System Responsibility:** Canvas-accelerated force-directed graph renderer wrapping `vis-network`.
* **Tools & Libraries:** `vis-network/standalone`, `react`.
* **Execution Logic:**
  1. Initialize `Network` instance on HTML container ref.
  2. Configure physics solver:
     - `barnesHut` gravitational model with damping $0.09$.
     - **Auto-Stabilization:** Freeze physics after 150 iterations or 1.5 seconds (`stabilization: { iterations: 150 }`) to prevent browser frame drops.
  3. Bind network events:
     - `click`: Select node and notify parent component.
     - `hoverNode`: Display floating popover with note title, PARA category, and 1-line summary.
  4. Handle window resize to automatically refit graph canvas.

---

#### 26. `frontend/src/components/ChatBox.tsx`
* **System Responsibility:** Message feed renderer supporting markdown, syntax highlighting, and inline citation pills.
* **Tools & Libraries:** `react`, `react-markdown` or custom lightweight regex markdown parser.
* **Execution Logic:**
  1. Render alternating user and assistant message bubbles.
  2. Parse citation markers `[Note: <id>]` into interactive cyan badge elements.
  3. Maintain auto-scroll to latest message during streaming or response arrival.

---

#### 27. `frontend/src/components/CitationModal.tsx`
* **System Responsibility:** Slide-over modal / popover inspecting the exact source text chunk supporting an answer.
* **Tools & Libraries:** `react`, `lucide-react`.
* **Execution Logic:**
  1. Display note title, PARA category badge, and creation timestamp.
  2. Render the exact verbatim text snippet retrieved from the vector/lexical index.
  3. Provide a direct link to open or inspect the original file in `raw/` or note in `wiki/`.

---

#### 28. `frontend/src/styles/index.css` & `components.css`
* **System Responsibility:** Global design system tokens, typography, dark-mode color palette, and component styling.
* **Tools & Libraries:** Modern Vanilla CSS (CSS Variables, Flexbox/Grid, Glassmorphism `backdrop-filter`).
* **Design Specifications:**
  - **Background:** Deep space slate (`#0a0d14`, `#0f172a`).
  - **Cards & Surfaces:** Glassmorphic translucent cards (`rgba(30, 41, 59, 0.7)` with `backdrop-filter: blur(12px)` and `1px solid rgba(255, 255, 255, 0.08)`).
  - **Accent Colors:** Neon Violet (`#8b5cf6`), Electric Cyan (`#06b6d4`), Emerald (`#10b981`), Amber (`#f59e0b`).
  - **Typography:** `Inter` for clean interface readability, `JetBrains Mono` for code blocks and citation tags.
  - **Interactions:** Subtle hover lifts, smooth button scale transforms, pulse animations for background tasks.

---

### Infrastructure & Deployment Subsystem

```
secondself/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── package.json
└── .env.example
```

#### 29. `Dockerfile`
* **System Responsibility:** Multi-stage production container build packaging the complete application for cloud deployment.
* **Tools & Libraries:** Docker, Node.js 20, Python 3.11-slim, Debian package manager (`apt`).
* **Execution Logic:**
  1. **Stage 1 (Frontend Build):**
     - Base `node:20-alpine`.
     - Copy `frontend/`, run `npm ci && npm run build`.
  2. **Stage 2 (Production Runtime):**
     - Base `python:3.11-slim`.
     - Install system binaries: `tesseract-ocr`, `tesseract-ocr-eng`, `ffmpeg`, `libmagic1`.
     - Install Python dependencies from `requirements.txt`.
     - Copy static build assets from Stage 1 to `backend/static/`.
     - Expose port `8000`.
     - Define volume mount at `/app/data` for persistent storage of `raw/`, `wiki/`, and SQLite database.
     - Entrypoint: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`.

---

#### 30. `docker-compose.yml`
* **System Responsibility:** Local development and single-command deployment orchestration.
* **Execution Logic:**
  1. Define service `secondself`.
  2. Mount local directory `./data:/app/data` for persistence across container rebuilds.
  3. Map host port `8000:8000`.
  4. Load environment variables from `.env`.

---

## 4. End-to-End Component Flow & Interaction Matrix

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Frontend (Capture Studio)
    participant API as FastAPI (backend/main.py)
    participant Cap as backend/capture.py
    participant Parser as backend/parsers/*
    participant Classify as backend/classify.py
    participant Link as backend/link.py
    participant DB as SQLite + FAISS
    participant Graph as backend/build_graph.py
    participant RAG as backend/ask.py

    %% Ingestion Flow
    User->>UI: Upload File (PDF/Image/Audio/etc)
    UI->>API: POST /capture (multipart/form-data)
    API->>Cap: Ingest & Check SHA-256 Hash
    Cap->>Parser: Route by format to specialized extractor
    Parser-->>Cap: Clean Extracted Text + Metadata
    Cap->>DB: Save raw stash (raw/) & insert notes record
    Cap-->>UI: 201 Created (note_id)

    %% Async Intelligence Flow
    par PARA Classification
        Cap->>Classify: Classify text (Groq / Gemini)
        Classify->>DB: Write wiki/ markdown & update category/tags
    and Vector Embeddings & Auto-Linking
        Cap->>Link: Chunk text & compute embeddings
        Link->>DB: Insert into FAISS & SQLite FTS5
        Link->>DB: Cosine similarity check (τ >= 0.70, top 5)
    end

    %% Graph Exploration
    User->>UI: Open Knowledge Graph Explorer
    UI->>API: GET /graph
    API->>Graph: Build topology from notes & links
    Graph-->>UI: Nodes & Edges JSON (Color & Shape styled)
    UI-->>User: Render Canvas Force-Directed Network

    %% Cited RAG Query
    User->>UI: Ask Question ("What was decided in the roadmap?")
    UI->>API: POST /ask {"question": "...", "session_id": "uuid"}
    API->>RAG: Hybrid Search (Dense FAISS + Sparse FTS5)
    RAG->>DB: Fetch top-ranked chunks via RRF
    RAG->>API: Synthesize Answer + Citations [Note: <id>]
    API->>DB: Persist chat session, messages & retrievals
    API-->>UI: Answer with interactive citation pills
    UI-->>User: Display cited response with preview overlays
```

---

## 5. Verification Checklist & Success Criteria

- [ ] Every backend parser possesses a dedicated fallback strategy (e.g., PDF $\rightarrow$ OCR, Audio $\rightarrow$ VAD silence check, URL $\rightarrow$ OpenGraph).
- [ ] LLM classification enforces strict JSON parsing via Pydantic and recovers from formatting errors via `json_repair`.
- [ ] Auto-linking enforces both cosine similarity threshold ($\tau \ge 0.70$) and Top-5 degree capping to eliminate hub explosion.
- [ ] Knowledge Graph UI maintains $\ge 60\text{ FPS}$ by freezing physics simulation after 150 iterations.
- [ ] Hybrid RAG query execution merges FAISS vector ranking and SQLite FTS5 BM25 ranking using Reciprocal Rank Fusion (RRF).
- [ ] Answers strictly reference real context chunks and format citations as clickable pills `[Note: <id>]`.
- [ ] Out-of-domain questions trigger the knowledge void guardrail with zero hallucinations.
- [ ] Chat history is persisted in SQLite with historical chunk snapshots, ensuring past conversations remain intact.
