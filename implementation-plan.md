# Implementation Plan: SecondSelf — Multi-Modal AI Second Brain

**Document Version:** 1.1.0 (Synchronized with Technical Stack Specification)  
**Status:** Approved Phase-Wise Roadmap  
**Target Platform:** Modern Web (React 18 / Vite / TypeScript) + Python 3.11 (FastAPI 0.111+ ASGI Server)  
**Associated Documents:** [technical-stack.md](file:///c:/Users/scs/Desktop/hacton%20jaipur/technical-stack.md) | [PRD.pdf](file:///c:/Users/scs/Desktop/hacton%20jaipur/PRD.pdf) | [architecture.md](file:///c:/Users/scs/Desktop/hacton%20jaipur/architecture.md) | [edge-case.md](file:///c:/Users/scs/Desktop/hacton%20jaipur/edge-case.md) | [SecondSelf_ProblemStatement_v2.md](file:///c:/Users/scs/Desktop/hacton%20jaipur/SecondSelf_ProblemStatement_v2.md)

---

## 1. Executive Summary & Core Architectural Tenets

SecondSelf is an intelligent personal knowledge management (PKM) and multi-modal retrieval-augmented generation (RAG) platform. It resolves the core breakdown of modern note-taking: capturing information is frictionless, but downstream retrieval, cross-format linking, and grounded synthesis fail as notes accumulate.

SecondSelf ingests heterogeneous input modalities (PDFs, DOCX files, raw notes, web bookmarks, screenshots/images, audio voice memos, spreadsheets/CSV), normalizes them into an immutable schema, automatically classifies them via the **PARA framework** (Projects, Areas, Resources, Archives), connects related notes into a living force-directed knowledge graph, and delivers context-grounded, cited answers through a hybrid RAG engine with persistent multi-turn conversational memory.

```
Heterogeneous Ingestion (PDF, Audio, Image, DOCX, CSV, Web, Notes)
                             │
                             ▼
     Two-Phase Raw Storage (raw/<uuid>.<ext> + <uuid>.json) & SHA-256 Dedup
                             │
                             ▼
          Dedicated Parser Matrix & Schema Normalizer (CaptureItem)
                             │
             ┌───────────────┴───────────────┐
             ▼                               ▼
  PARA Classification (Groq / Gemini)   Recursive Text Splitter & Embeddings
             │                               (sentence-transformers all-MiniLM-L6-v2)
             ▼                               │
   Markdown Wiki Vault (wiki/)               ▼
  (YAML Frontmatter & Backlinks)      FAISS Vector Store + SQLite FTS5 BM25
             │                               │
             └───────────────┬───────────────┘
                             ▼
     Semantic Knowledge Graph Engine (Cosine Threshold τ >= 0.70 & Top-5 Cap)
                             │
             ┌───────────────┴───────────────┐
             ▼                               ▼
    Living Brain Explorer             Hybrid RAG Engine (Reciprocal Rank Fusion)
   (vis-network Canvas 60 FPS)               │
                                             ▼
                               Grounded Answers + Inline Citations [Note: <id>]
                                             │
                                             ▼
                               Persistent Conversational Memory (SQLite Sessions)
```

---

## 2. Complete Project Directory & File Manifest

The implementation strictly adheres to the 30-file architecture specified in [technical-stack.md](file:///c:/Users/scs/Desktop/hacton%20jaipur/technical-stack.md):

```
secondself/
├── backend/
│   ├── config.py                 # Pydantic Settings, environment variables, directory paths & constraints
│   ├── main.py                   # FastAPI ASGI entrypoint, CORS, lifespan handlers, router mounting & health probe
│   ├── capture.py                # Multi-modal capture API, SHA-256 dedup, raw stashing & background task trigger
│   ├── parsers/                  # Dedicated multi-modal file parsers
│   │   ├── __init__.py           # Parser registry & format resolver
│   │   ├── pdf_parser.py         # PyMuPDF block extraction, layout preservation & Tesseract OCR fallback
│   │   ├── docx_parser.py        # python-docx parser with heading hierarchy & markdown table linearization
│   │   ├── image_ocr.py          # Pillow + OpenCV preprocessing + Tesseract OCR / Vision LLM fallback
│   │   ├── audio_transcribe.py   # RMS energy silence check + faster-whisper int8 ASR transcription
│   │   ├── csv_parser.py         # pandas / openpyxl dialect sniffing, schema profiling & table formatting
│   │   └── link_extractor.py     # trafilatura async fetch (8s timeout) + BeautifulSoup OpenGraph fallback
│   ├── classify.py               # PARA LLM classification (Groq -> Gemini -> Regex) + json_repair
│   ├── link.py                   # Recursive text chunking, all-MiniLM-L6-v2 embeddings & cosine auto-linking
│   ├── build_graph.py            # Graph topology serializer, PARA color styling & Top-5 degree capping
│   ├── ask.py                    # Hybrid RAG (Dense FAISS + SQLite FTS5 BM25 via RRF) + citation mapping
│   ├── history.py                # Conversational session management, sliding window & chunk snapshotting
│   ├── db/
│   │   ├── database.py           # SQLite connection pool, Write-Ahead Logging (WAL) & busy_timeout
│   │   ├── models.py             # SQLAlchemy 2.0 ORM schemas & SQLite FTS5 virtual table
│   │   └── vector_store.py       # FAISS IndexFlatIP abstraction, vector normalization & persistence
│   ├── tests/                    # Automated test suites
│   │   ├── test_parsers.py       # Ingestion fidelity tests across all 7 formats
│   │   ├── test_dedup.py         # SHA-256 fingerprint deduplication verification
│   │   ├── test_classify.py      # PARA schema enforcement and JSON repair resilience
│   │   ├── test_linking.py       # Cosine thresholding and degree capping verification
│   │   └── test_rag.py           # Hybrid retrieval, RRF scoring, citations & knowledge void check
│   └── requirements.txt          # Frozen Python backend dependencies
├── frontend/
│   ├── index.html                # HTML5 root shell, Google Fonts (Inter, JetBrains Mono)
│   ├── package.json              # React 18, Vite, TypeScript, vis-network, lucide-react
│   ├── vite.config.ts            # Vite bundler configuration & backend API proxy
│   ├── src/
│   │   ├── main.tsx              # React DOM root bootstrapping
│   │   ├── App.tsx               # Navigation shell, telemetry polling & global toast container
│   │   ├── pages/
│   │   │   ├── CapturePage.tsx   # Multi-modal dropzone, URL fetcher, scratchpad & capture feed
│   │   │   ├── GraphPage.tsx     # Full-screen force-directed visual graph explorer & node inspector
│   │   │   ├── AskPage.tsx       # Conversational RAG Q&A with interactive inline citation pills
│   │   │   └── HistoryPage.tsx   # Multi-session memory browser & conversational thread continuation
│   │   ├── components/
│   │   │   ├── Navbar.tsx        # Top navigation bar with active route pills, status pulse & counters
│   │   │   ├── Dropzone.tsx      # Drag-and-drop file upload with format validation & PII scanning
│   │   │   ├── GraphView.tsx     # vis-network canvas wrapper with 150-iteration physics stabilization
│   │   │   ├── ChatBox.tsx       # Markdown message stream with auto-scroll & citation badge renderer
│   │   │   └── CitationModal.tsx # Interactive source chunk & original raw file inspector
│   │   └── styles/
│   │       ├── index.css         # Dark-mode design system tokens, CSS variables, typography & resets
│   │       └── components.css    # Glassmorphism cards, buttons, badges, dropzone & modal overlays
├── raw/                          # Immutable raw file stash (<uuid>.<ext> and <uuid>.json manifests)
│   └── quarantine/               # Corrupt / unsupported file quarantine
├── wiki/                         # Living knowledge base (Projects, Areas, Resources, Archives)
│   ├── Projects/
│   ├── Areas/
│   ├── Resources/
│   └── Archives/
├── Dockerfile                    # Multi-stage production container specification (Node.js + Python 3.11)
├── docker-compose.yml            # Local orchestration with persistent volume mounts
├── .env.example                  # Environment variable configuration template
└── README.md                     # Comprehensive setup, architecture & usage guide
```

---

## 3. Phase-Wise Implementation Roadmap

### Phase 0: Environment Setup, Scaffolding & Core Foundations
* **Estimated Scope:** Directory setup, backend dependencies, SQLite WAL database initialization, vector store scaffolding, and frontend Vite setup.
* **Detailed Tasks:**
  1. **Directory Tree Creation:**
     - Initialize `backend/parsers/`, `backend/db/`, `backend/tests/`.
     - Initialize `frontend/src/pages/`, `frontend/src/components/`, `frontend/src/styles/`.
     - Initialize `raw/`, `raw/quarantine/`, `wiki/Projects/`, `wiki/Areas/`, `wiki/Resources/`, `wiki/Archives/`.
  2. **Backend Dependency Management (`backend/requirements.txt`):**
     - Framework & Concurrency: `fastapi==0.111.0`, `uvicorn[standard]==0.30.1`, `pydantic>=2.7.0`, `pydantic-settings>=2.2.0`, `python-multipart>=0.0.9`, `aiofiles>=23.2.1`, `aiosqlite>=0.20.0`, `sqlalchemy>=2.0.30`
     - Extractors: `pymupdf>=1.24.0`, `python-docx>=1.1.0`, `pillow>=10.3.0`, `pytesseract>=0.3.10`, `opencv-python-headless>=4.9.0.80`, `faster-whisper>=1.0.2`, `pandas>=2.2.2`, `openpyxl>=3.1.2`, `trafilatura>=1.8.0`, `beautifulsoup4>=4.12.3`, `httpx>=0.27.0`
     - AI, Vector & Search: `sentence-transformers>=3.0.0`, `faiss-cpu>=1.8.0`, `groq>=0.9.0`, `google-genai>=0.1.1`, `openai>=1.30.0`, `json-repair>=0.25.0`, `tabulate>=0.9.0`
  3. **Configuration Module (`backend/config.py`):**
     - Define `Settings` class with Pydantic v2 loading `.env`.
     - Enforce file size limits: PDF/DOCX (max 25MB), Audio (max 50MB), Image (max 15MB), CSV/Text (max 10MB).
     - Configure paths, default cosine threshold ($\tau = 0.70$), and max link degree ($K = 5$).
  4. **Database & Model Layer (`backend/db/database.py`, `models.py`):**
     - Setup SQLite connection hook with mandatory Write-Ahead Logging (WAL) PRAGMAs:
       ```sql
       PRAGMA journal_mode = WAL;
       PRAGMA busy_timeout = 5000;
       PRAGMA synchronous = NORMAL;
       PRAGMA foreign_keys = ON;
       ```
     - Define SQLAlchemy declarative models: `Note`, `Chunk`, `Link`, `Session`, `Message`, `Retrieval`.
     - Create SQLite FTS5 virtual table `notes_fts` for BM25 full-text indexing.
  5. **Vector Store Scaffolding (`backend/db/vector_store.py`):**
     - Implement `VectorStore` class wrapping `faiss.IndexFlatIP(384)` with $L_2$ normalization and disk serialization to `backend/db/vector_store/index.faiss`.
  6. **Frontend Bootstrap (`frontend/`):**
     - Initialize Vite React TypeScript app with `package.json` (`react`, `react-dom`, `lucide-react`, `vis-network`).
     - Configure `vite.config.ts` server proxy forwarding `/api` to `http://localhost:8000`.
     - Create design system baseline in `frontend/src/styles/index.css`.
  7. **Application Shell (`backend/main.py`):**
     - Setup FastAPI app with CORS middleware, lifespan startup/shutdown hooks, and `GET /health` endpoint.
* **Verification Gate:**
  - Running `python -c "import fitz, docx, PIL, pytesseract, pandas, trafilatura, sentence_transformers, faiss; print('All core libs imported successfully')"` passes without missing modules.
  - SQLite database creates all tables and confirms WAL journal mode: `PRAGMA journal_mode;` returns `wal`.
  - Frontend runs via `npm run dev` and renders a clean dark-mode test layout.

---

### Phase 1: Multi-Modal Ingestion Engine & Normalization (Week 1 — The Archivist)
* **Estimated Scope:** Parser matrix, two-phase raw stashing, SHA-256 deduplication, and unified normalization schema.
* **Detailed Tasks:**
  1. **Two-Phase Raw Storage & Deduplication (`backend/capture.py`):**
     - Enforce zero data loss: write incoming byte streams immediately to `raw/<uuid>.<ext>` and metadata manifest to `raw/<uuid>.json` before triggering parsers.
     - Compute SHA-256 fingerprint: check against SQLite `notes.sha256_hash`. If an identical file exists, return HTTP 200 with status `"DUPLICATE_IDENTIFIED"` and existing `note_id`.
  2. **Multi-Modal Extractors (`backend/parsers/`):**
     - **PDF Parser (`pdf_parser.py`):** Layout-aware block extraction via PyMuPDF (`page.get_text("blocks")`). Intercept `fitz.EncryptedFileError`. If extracted text $< 50$ characters, automatically trigger OCR fallback on high-DPI rendered pixmaps via Tesseract.
     - **DOCX Parser (`docx_parser.py`):** Traverse OpenXML paragraphs, preserve `#` / `##` headings, and linearize table cells into Markdown table format. Catch `zipfile.BadZipFile`.
     - **Image OCR & Vision (`image_ocr.py`):** Auto-downscale large images ($> 2048\text{px}$) to prevent OOM. Preprocess with OpenCV (grayscale, bilateral noise filter, adaptive threshold). Run Tesseract OCR. If text $< 15$ chars and confidence $< 40\%$, trigger Vision LLM (Groq LLaMA-Vision or Gemini Flash) for technical visual description.
     - **Audio Transcriber (`audio_transcribe.py`):** Calculate sample RMS energy level:
       $$\text{RMS} = \sqrt{\frac{1}{N} \sum_{i=1}^N x_i^2}$$
       If $\text{RMS} < 0.005$, mark status as `empty_audio` without halting. Initialize `WhisperModel("base.en", compute_type="int8")` and transcribe with Voice Activity Detection (VAD) filter.
     - **CSV & Spreadsheet Structurer (`csv_parser.py`):** Dialect sniffing (`csv.Sniffer`), column schema profiling, and Markdown table conversion. For datasets $> 500$ rows, generate statistical summary + top/bottom 5 sample rows.
     - **Web Content Extractor (`link_extractor.py`):** Async HTTP fetch via `httpx` with 8.0s timeout and custom User-Agent. Extract main content via `trafilatura`. If empty (SPA or paywall), fallback to BeautifulSoup OpenGraph metadata.
     - **Plain Text / Notes:** UTF-8 normalizer with title extraction.
  3. **Schema Normalization (`CaptureItem`):**
     - Normalize all captures into immutable JSON: `{ id, timestamp, source_type, raw_path, extracted_text, metadata }`.
  4. **Capture API Endpoint:**
     - `POST /capture`: Supports multipart file uploads and JSON payloads (for links and typed notes). Returns `CaptureResponse` with `note_id` and normalized text snippet.
* **Verification Gate:**
  - Automated test `test_parsers.py` passes for all 7 formats (PDF, DOCX, Image, Audio, CSV, Link, Plain text).
  - Test `test_dedup.py` confirms that uploading the same file twice triggers SHA-256 match and skips re-processing.
  - Ingest 10+ real pieces of personal knowledge across multiple formats into `raw/`.

---

### Phase 2: AI Intelligence & Classification Engine (Week 2.1 — The Sorting Hat)
* **Estimated Scope:** Multi-tier LLM classification, PARA framework categorizer, tag synthesis, and Markdown Wiki vault synchronization.
* **Detailed Tasks:**
  1. **Multi-Tier LLM Architecture (`backend/classify.py`):**
     - **Tier 1:** Groq API (`llama-3.1-70b-versatile` / `8b-instant`) with `response_format={"type": "json_object"}`.
     - **Tier 2:** Google Gemini (`gemini-1.5-flash`) automatic failover on HTTP 429 rate limits or timeouts.
     - **Tier 3:** Offline heuristic & regex rule-based classifier (e.g., presence of "TODO", "deadline" $\rightarrow$ `Projects`, default $\rightarrow$ `Resources`) if cloud APIs are unavailable.
  2. **Structured JSON Output Schema:**
     - Enforce Pydantic schema: `category` (`Projects`, `Areas`, `Resources`, `Archives`), `tags` (array of lowercase strings), `summary` (concise 1-line operational summary), `confidence` (float).
     - Mitigate malformed responses using `json_repair.repair_json()` to strip markdown fences and repair unclosed brackets.
  3. **Markdown Wiki Vault Synchronization (`wiki/`):**
     - Write classified notes to `wiki/<Category>/<Title>.md` with formatted YAML frontmatter containing `id`, `created_at`, `source_type`, `tags`, `summary`, and `links`.
  4. **Classification Endpoint:**
     - `POST /classify`: Classifies a note by `note_id`, updates SQLite `notes` record, and updates the Wiki file.
* **Verification Gate:**
  - Test `test_classify.py` validates that 30 distinct test captures are properly categorized with valid JSON schema.
  - All files in `wiki/` contain valid YAML frontmatter readable by standard markdown parsers.

---

### Phase 3: Embeddings, Vector Store & Semantic Auto-Linking (Week 2.2 — Connect the Dots)
* **Estimated Scope:** Recursive text chunking, local sentence-transformers vectorization, FAISS indexing, SQLite FTS5 lexical indexing, and cross-format auto-linking with degree capping.
* **Detailed Tasks:**
  1. **Recursive Text Splitter (`backend/link.py`):**
     - Split extracted text into 500-800 character chunks with 15% overlap.
     - Attach chunk metadata: `chunk_id`, `parent_note_id`, `source_type`, `chunk_index`.
     - Save chunks to SQLite `chunks` table.
  2. **Dense Vector Embedding Pipeline:**
     - Compute 384-dimensional embeddings using `sentence-transformers/all-MiniLM-L6-v2`.
     - Normalize vectors to unit $L_2$ norm and add to FAISS `IndexFlatIP`.
  3. **Lexical Indexing (SQLite FTS5):**
     - Insert note titles, summaries, and chunk contents into `notes_fts` virtual table for BM25 search.
  4. **Document-Level Semantic Auto-Linking:**
     - Compute average document vector for new note; compute cosine similarity against all existing note vectors:
       $$\text{Cosine Similarity}(\vec{u}, \vec{v}) = \vec{u} \cdot \vec{v}$$
     - Apply strict similarity threshold: $\tau \ge 0.70$.
     - **Supernode / Hub Explosion Mitigation:** Sort candidate links descending, cap maximum links per note at top-$K$ ($K=5$) strongest neighbors, prune mutual reciprocal links, and store edges in SQLite `links` table.
     - **Orphan Node Handling:** If note has no neighbors meeting $\tau \ge 0.70$, establish an anchor link to its PARA category hub node.
  5. **Auto-Link Endpoint:**
     - `POST /link`: Computes similarity for a note, creates semantic edges, and returns connected note IDs with scores.
* **Verification Gate:**
  - Test `test_linking.py` confirms that related notes across formats (e.g., a PDF and an audio memo on the same topic) are automatically linked.
  - Verify that no node in the database exceeds degree $K = 5$ auto-generated links.

---

### Phase 4: Knowledge Graph Engine & Visual Graph UI (Week 3 — The Cartographer)
* **Estimated Scope:** Graph topology serializer, `GET /graph` endpoint, and canvas-accelerated force-directed visual graph UI.
* **Detailed Tasks:**
  1. **Graph Topology Serializer (`backend/build_graph.py`):**
     - Query SQLite `notes` and `links` tables.
     - Assign node visual properties:
       - Category color palette: Projects (`#8b5cf6`), Areas (`#06b6d4`), Resources (`#10b981`), Archives (`#f59e0b`).
       - Source format indicator (PDF, DOCX, Image, Audio, CSV, Link, Note).
       - Node radius `val` proportional to degree centrality.
     - Assign edge properties: `from`, `to`, `value` (similarity score), `title`.
  2. **Graph API Endpoint:**
     - `GET /graph`: Serves clean JSON `{ nodes: [...], edges: [...] }` with optional filters (`category`, `source_type`, `search`).
  3. **Interactive Graph UI (`frontend/src/pages/GraphPage.tsx`, `components/GraphView.tsx`):**
     - Integrate `vis-network` canvas-accelerated graph renderer inside React.
     - **Physics Auto-Stabilization:** Disable physics simulation after 150 iterations or 1.5 seconds (`stabilization: { iterations: 150 }`) to guarantee 60 FPS performance even with 100+ nodes.
     - Implement interactive node popovers on hover (title, PARA category, 1-line summary, format badge).
     - Click node to open inspector side drawer displaying full metadata and connected neighbors.
     - Control bar: zoom in/out, fit view, search node by title, and filter by PARA category.
* **Verification Gate:**
  - Graph loads and stabilizes under 2.0 seconds with 100+ nodes.
  - Hovering and clicking nodes smoothly reveals note previews and metadata.

---

### Phase 5: Hybrid RAG, Citation Engine & Chat Memory (Week 4 — The Oracle)
* **Estimated Scope:** Hybrid retrieval (Dense FAISS + Sparse SQLite FTS5 via RRF), strict citation synthesis, and multi-turn conversational memory.
* **Detailed Tasks:**
  1. **Hybrid Retrieval Engine (`backend/ask.py`):**
     - Dense Vector Search: Query FAISS for top-$K_1$ chunks ($K_1 = 8$).
     - Sparse Lexical Search: Query SQLite FTS5 for top-$K_2$ chunks ($K_2 = 8$).
     - **Reciprocal Rank Fusion (RRF):** Merge dense and sparse candidate rankings:
       $$RRF(d) = \sum_{m \in \{\text{dense}, \text{sparse}\}} \frac{1}{60 + r_m(d)}$$
     - Select top $N = 5$ highest scoring chunks.
  2. **Knowledge Void & Faithfulness Guardrail:**
     - If maximum retrieval similarity score $S_{max} < 0.45$: return explicit notice: *"I couldn't find any information about this in your captured notes."* with zero fabricated citations.
  3. **Grounded Synthesis with Citation Mapping:**
     - Wrap retrieved chunks in explicit `<user_knowledge_context id="...">` delimiters to prevent prompt injection.
     - Inject chronological date metadata (`[Date: YYYY-MM-DD]`) so LLM resolves conflicting notes by recency.
     - System prompt strictly enforces: *"Answer exclusively based on the provided context tags. For every factual assertion, append the source note citation `[Note: <note_id>]`."*
  4. **Conversational Memory & Session Persistence (`backend/history.py`):**
     - Manage sessions in SQLite tables: `sessions`, `messages`, `retrievals`.
     - Implement sliding context window: retain system prompt + last 4 turns; auto-summarize older turns.
     - Store exact snapshots of cited chunks in `retrievals` table so citations remain inspectable even if original notes are modified.
  5. **Endpoints:**
     - `POST /ask`: Executes hybrid RAG, returns answer + cited notes + session ID.
     - `GET /history`: Lists all chat sessions sorted by `updated_at` descending.
     - `GET /history/{session_id}`: Retrieves complete message thread and retrieval references.
     - `POST /history/{session_id}/continue`: Appends follow-up question and continues conversation thread.
* **Verification Gate:**
  - Test `test_rag.py` validates that cross-modal questions (e.g., querying across a PDF and an audio memo) return answers citing both source notes accurately.
  - Out-of-domain questions trigger the knowledge void disclaimer with zero hallucinations.
  - Sessions persist across page reloads and can be reopened and continued.

---

### Phase 6: Frontend UI/UX Integration & Design Polish
* **Estimated Scope:** Polish the 4 core views (Capture Studio, Knowledge Graph, Ask Brain, History Browser), navigation shell, and dark-mode glassmorphic design system.
* **Detailed Tasks:**
  1. **Design System & Aesthetics (`frontend/src/styles/index.css`, `components.css`):**
     - Dark-mode palette: deep space backgrounds (`#0a0d14`, `#111827`), glassmorphic translucent cards (`backdrop-filter: blur(12px)` with subtle `rgba(255,255,255,0.08)` borders).
     - Vibrant neon accents: Violet (`#8b5cf6`), Cyan (`#06b6d4`), Emerald (`#10b981`), Amber (`#f59e0b`).
     - Google Fonts typography (`Inter` for UI, `JetBrains Mono` for code and citation tags).
  2. **Navigation Shell (`Navbar.tsx` & `App.tsx`):**
     - Sticky top navigation bar with active route highlighting, system health status indicator, and live note/link counters.
  3. **Capture Studio (`CapturePage.tsx` & `Dropzone.tsx`):**
     - Drag-and-drop zone supporting all file formats with format icons.
     - Tabs for File Upload, Web Link, and Quick Scratchpad Note.
     - Real-time processing progress bars with status badges ("Extracting...", "Classifying...", "Linking...").
     - Client-side credential scanner warning before upload.
  4. **Ask / Second Brain Q&A (`AskPage.tsx`, `ChatBox.tsx`, `CitationModal.tsx`):**
     - Interactive chat interface with Markdown rendering and syntax-highlighted code blocks.
     - Clickable inline citation pills `[Note: <id>]` opening `CitationModal` displaying exact extracted excerpt, note title, PARA category, and source file path.
  5. **History Browser (`HistoryPage.tsx`):**
     - Multi-session sidebar, complete message thread inspection, and "Continue this conversation" input.
  6. **Onboarding Empty States:**
     - Empty-state screens with a "Load Demo Knowledge Base (5 Notes Across Formats)" action for immediate testing and judge evaluation.
* **Verification Gate:**
  - Complete application renders with fluid responsiveness, zero layout shift, and intuitive navigation.
  - All interactive elements respond with smooth micro-interactions and transitions.

---

### Phase 7: Local Verification & Edge Case Battery
* **Estimated Scope:** Rigorously validate the system against the 10 failure modes from [edge-case.md](file:///c:/Users/scs/Desktop/hacton%20jaipur/edge-case.md).
* **Test Battery:**
  1. **Scanned / Bitmap PDF:** Ingest raster PDF with zero text layer $\rightarrow$ verify automatic Tesseract OCR fallback extracts content.
  2. **Encrypted PDF:** Ingest password-protected PDF $\rightarrow$ verify HTTP 422 with descriptive decryption guidance.
  3. **Corrupted DOCX:** Ingest malformed zip archive $\rightarrow$ verify graceful error handling toast without server crash.
  4. **Silent Audio:** Ingest empty audio memo $\rightarrow$ verify RMS energy check flags note as `empty_audio`.
  5. **Complex CSV:** Ingest multi-column spreadsheet $\rightarrow$ verify clean schema summary and markdown table representation.
  6. **Duplicate Ingestion:** Ingest identical file twice $\rightarrow$ verify SHA-256 hash match returns existing note with zero redundant processing.
  7. **LLM Rate Limit (429):** Simulate Groq rate limit $\rightarrow$ verify seamless failover to Gemini 1.5 Flash / offline heuristic mode.
  8. **Graph Hub Explosion:** Ingest common stopword notes $\rightarrow$ verify Top-5 degree cap prevents hairball visualization.
  9. **Out-of-Domain Query:** Ask unrelated trivia $\rightarrow$ verify zero hallucinations and explicit "not found" response.
  10. **Concurrency Stress Test:** Trigger concurrent uploads and RAG queries $\rightarrow$ verify SQLite WAL mode prevents `SQLITE_BUSY` database locking.
* **Verification Gate:**
  - All 10 edge case scenarios pass cleanly with zero server crashes or unhandled exceptions.

---

### Phase 8: Containerization & Cloud Deployment Architecture
* **Estimated Scope:** Multi-stage production Docker container, local Docker Compose, and cloud deployment configuration.
* **Detailed Tasks:**
  1. **Multi-Stage `Dockerfile`:**
     - Stage 1 (Node.js 20): Build static React/Vite frontend bundle (`npm run build`).
     - Stage 2 (Python 3.11-slim): Install system dependencies (`tesseract-ocr`, `ffmpeg`, `libmagic1`), install Python requirements, copy frontend static build to FastAPI static files.
  2. **Local Orchestration (`docker-compose.yml`):**
     - Define service `secondself` mapping port `8000:8000`.
     - Mount local directory `./data:/app/data` to persist `raw/`, `wiki/`, and SQLite databases across container rebuilds.
  3. **Cloud Deployment Config:**
     - Configure for Render, Railway, or Hugging Face Spaces with persistent volume mount.
     - Ensure environment variables are loaded securely (`GROQ_API_KEY`, `GEMINI_API_KEY`).
  4. **Health Probe:**
     - Verify `GET /health` returns `{ "status": "healthy", "models_loaded": true, "notes_count": N, "graph_nodes": M }`.
* **Verification Gate:**
  - Container builds cleanly via `docker build -t secondself .` and runs with full multi-modal parsing and graph functionality.

---

### Phase 9: Evaluation, Documentation & 3-Minute Demo Run
* **Estimated Scope:** Benchmark against PRD metrics, prepare the 3-minute hackathon demo script, and complete judge-facing documentation.
* **Detailed Tasks:**
  1. **Evaluation Benchmarks (PRD Section 10):**
     - Extraction accuracy: 10 sample files across 7 formats verified.
     - Classification accuracy: 30 notes verified for PARA correctness.
     - Retrieval & Faithfulness: 20 Q/A pairs evaluated for Recall@5 and citation precision.
     - Latency: p95 `/ask` $< 8.0\text{s}$, graph rendering $< 2.0\text{s}$.
     - Cost: $< \$0.01$ per query using free-tier LLM endpoints.
  2. **3-Minute Live Demo Execution (PRD Section 11):**
     - `0:00 - 0:30`: Problem hook ("I have 200 scattered notes across formats...").
     - `0:30 - 1:00`: Drag-and-drop live capture of a PDF, an image, and a voice memo.
     - `1:00 - 1:30`: Reveal the living knowledge graph, hover previews, and auto-linked relationships across formats.
     - `1:30 - 2:15`: Ask a cross-modal question ("What did we decide in the roadmap PDF and the audio sync?") $\rightarrow$ answer cites both.
     - `2:15 - 2:45`: Open History view, inspect cited chunks, continue the conversation.
     - `2:45 - 3:00`: Present live deployed URL and architecture summary.
  3. **Documentation:**
     - Write a comprehensive, judge-ready [README.md](file:///c:/Users/scs/Desktop/hacton%20jaipur/README.md) with architecture diagram, feature screenshots, quick-start guide, and API documentation.
* **Verification Gate:**
  - Complete 3-minute demo flow runs seamlessly end-to-end without errors or delays.

---

## 4. Verification Plan Summary

### Automated Tests
- `pytest backend/tests/test_parsers.py`: Multi-format text extraction for PDF, DOCX, Image, Audio, CSV, Link, and plain notes.
- `pytest backend/tests/test_dedup.py`: SHA-256 hash collision and duplicate suppression.
- `pytest backend/tests/test_classify.py`: PARA category schema validation and JSON repair.
- `pytest backend/tests/test_linking.py`: Cosine threshold filtering ($\tau \ge 0.70$) and Top-5 degree capping.
- `pytest backend/tests/test_rag.py`: Hybrid RAG retrieval, RRF ranking, citation accuracy, and knowledge void guardrail.

### Manual Verification
- Ingest real files across all supported formats via the Capture Studio UI.
- Verify that the Knowledge Graph renders smoothly with interactive hover cards and category color codes.
- Ask questions requiring cross-modal synthesis and verify that inline citation pills open exact source chunks.
- Inspect session persistence in the History view across browser restarts.
