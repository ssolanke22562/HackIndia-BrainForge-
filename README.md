# SecondSelf — Multi-Modal AI Second Brain & PKM Platform

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776ab.svg?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18.3-61dafb.svg?style=flat&logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5.4-646cff.svg?style=flat&logo=vite&logoColor=white)](https://vitejs.dev)
[![FAISS](https://img.shields.io/badge/FAISS-Dense%20Vector%20Store-blue.svg?style=flat)](https://github.com/facebookresearch/faiss)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **SecondSelf** is an intelligent Personal Knowledge Management (PKM) and multi-modal Retrieval-Augmented Generation (RAG) platform. It resolves the core failure of modern note-taking: capturing information is frictionless, but downstream retrieval, cross-format linking, and grounded synthesis fail as notes accumulate.

---

## 🌟 Key Features

1. **Heterogeneous Multi-Modal Ingestion Matrix**:
   - **PDFs**: Layout-aware PyMuPDF block extraction + automatic Tesseract OCR fallback for scanned pages.
   - **DOCX**: Structured heading hierarchy preservation and Markdown table linearization.
   - **Images & Screenshots**: OpenCV preprocessing (grayscale, bilateral noise filter) + Tesseract OCR / Vision description.
   - **Audio & Voice Memos**: RMS energy silence filter + faster-whisper / Groq Whisper ASR transcription.
   - **Spreadsheets / CSV**: Dialect sniffing, statistical profiling, and Markdown tables.
   - **Web Articles**: 8.0s timeout async HTTP fetch + `trafilatura` readability extraction.
   - **Scratchpad Notes**: UTF-8 markdown normalizer with title extraction.

2. **Two-Phase Raw Stash & SHA-256 Deduplication**:
   - Zero data loss: raw streams written to `raw/<uuid>.<ext>` with JSON metadata manifests before triggering parsers.
   - Instant cryptographic deduplication preventing duplicate ingestion.

3. **Multi-Tier AI PARA Framework Classifier**:
   - Automatically categorizes captures into **Projects**, **Areas**, **Resources**, and **Archives**.
   - Multi-tier resilience: **Groq LPUs** (`llama-3.1-8b-instant`) $\rightarrow$ **Gemini Flash** $\rightarrow$ **Offline regex heuristics**.
   - Guaranteed valid output via `json_repair` and live synchronization to Markdown Wiki Vault (`wiki/<Category>/<Title>.md`) with YAML frontmatter.

4. **FAISS Dense Vector Store & Semantic Auto-Linking**:
   - 384-dimensional dense embeddings (`sentence-transformers/all-MiniLM-L6-v2`) in `faiss.IndexFlatIP`.
   - Cosine similarity thresholding ($\tau \ge 0.70$) with Top-5 degree capping ($K=5$) and mutual link pruning.

5. **Living Brain Explorer (Canvas-Accelerated Force Graph)**:
   - Interactive 60 FPS force-directed knowledge graph via `vis-network`.
   - Category color schemes (Projects: `#8b5cf6`, Areas: `#06b6d4`, Resources: `#10b981`, Archives: `#f59e0b`).
   - 150-iteration physics auto-stabilization and interactive side drawer node inspector.

6. **Hybrid RAG & Grounded Q&A Engine**:
   - Reciprocal Rank Fusion (RRF) merging Dense FAISS ($K_1=8$) and Sparse SQLite FTS5 BM25 ($K_2=8$).
   - Knowledge void guardrail ($S_{max} < 0.40$) preventing hallucinations on out-of-domain queries.
   - Strict inline citation pills `[Note: <id>]` opening interactive source snippet inspectors.
   - Persistent conversational memory with sliding context window and retrieval snapshotting.

---

## 🏗️ Architecture Overview

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

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend dev server)

### 1. Backend Setup
```bash
# Clone repository
git clone https://github.com/ssolanke22562/HackIndia-BrainForge-.git
cd HackIndia-BrainForge-

# Install dependencies
pip install -r backend/requirements.txt

# (Optional) Add API keys in .env
cp .env.example .env
# Set GROQ_API_KEY or GEMINI_API_KEY for cloud LLMs (offline mode works out-of-the-box)

# Run Automated Test Battery (35/35 passing)
python -m pytest backend/tests -v

# Seed Demo Knowledge Base
python -m backend.seed_demo_data

# Start FastAPI ASGI Server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run build   # Production bundle (auto-served by FastAPI at port 8000)
# OR for live development:
npm run dev     # Starts Vite dev server at http://localhost:5173
```

Access the application in your browser at **`http://localhost:8000`** (or `http://localhost:5173`).

---

## 📡 API Reference Summary

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/capture/upload` | Ingest multi-modal files (PDF, DOCX, Image, Audio, CSV) with two-phase stashing & SHA-256 dedup |
| `POST` | `/capture/link` | Ingest web URL with 8s timeout and readability markdown extraction |
| `POST` | `/capture/note` | Ingest raw scratchpad note or typed memo |
| `GET` | `/capture` | List recently captured notes with metadata and category badges |
| `POST` | `/classify` | Classify note via PARA framework and synchronize to Markdown Wiki Vault |
| `POST` | `/link` | Recursive chunking, dense vector indexing, and cosine auto-linking |
| `GET` | `/graph` | Topology serializer returning nodes, edges, and degree centrality for vis-network |
| `POST` | `/ask` | Conversational RAG with hybrid FAISS+FTS5 RRF retrieval and grounded citations |
| `GET` | `/history` | List all saved chat sessions with message counts and timestamps |
| `GET` | `/history/{id}` | Retrieve complete conversation thread with snapshot retrievals |
| `POST` | `/history/{id}/continue` | Append follow-up question and receive cited response in thread |
| `GET` | `/health` | Health probe returning database, vector store count, and note metrics |

---

## 🧪 Automated Test Suite (35 Tests)

Run the full automated test suite covering all phases and edge cases:
```bash
python -m pytest backend/tests -v
```
- `test_phase0.py`: Database initialization, WAL mode verification, vector store, and health probe.
- `test_parsers.py`: Ingestion fidelity across all 7 formats.
- `test_dedup.py`: SHA-256 cryptographic collision and duplicate prevention.
- `test_classify.py`: PARA categorization rules, JSON repair, and YAML frontmatter writing.
- `test_linking.py`: Recursive splitting, L2 vector normalization, cosine threshold ($\tau \ge 0.70$).
- `test_rag.py`: Hybrid RRF ranking, citation injection, and knowledge void guardrail.
- `test_edge_cases.py`: Corrupted PDFs, bad DOCX archives, silent audio, complex CSVs, out-of-domain queries.

---

## 📜 License
MIT License. Built for HackIndia Hackathon 2026.
