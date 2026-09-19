import os
import io
import wave
import struct
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import pandas as pd
import fitz  # PyMuPDF

BASE_DIR = Path(__file__).resolve().parent

def ensure_dirs():
    dirs = [
        BASE_DIR / "01_markdown_notes",
        BASE_DIR / "02_pdf_documents",
        BASE_DIR / "03_word_documents",
        BASE_DIR / "04_csv_data",
        BASE_DIR / "05_images_and_diagrams",
        BASE_DIR / "06_audio_voice_memos",
        BASE_DIR / "07_web_bookmarks",
        BASE_DIR / "08_quick_scratchpads",
        BASE_DIR / "09_voice_inputs_and_transcripts",
        BASE_DIR / "10_ask_brain_prompts",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print("All directories created successfully.")

# -------------------------------------------------------------
# 01. MARKDOWN NOTES
# -------------------------------------------------------------
def generate_markdown_notes():
    md1 = """# RFC-042: Event-Driven Async Processing Pipeline Architecture

**Status:** Approved  
**Author:** Lead Backend Architect  
**Target Delivery:** 2026-Q3  
**Components:** Redis Streams, RabbitMQ, Celery Worker Fleet, FastAPI Gateway

## 1. Problem Statement
Currently, document ingestion and OCR extraction operate synchronously on API worker threads. When users upload multi-page PDFs or high-resolution images, HTTP requests block for 4-12 seconds, exhausting ASGI worker pools and triggering HTTP 504 Gateway Timeouts under burst load.

## 2. Proposed Architecture
We will decouple ingestion into a two-phase async pipeline:
1. **Phase 1 (Stash & Acknowledge):** Ingest raw binary directly to disk/object store (`/raw/<uuid>.<ext>`), compute SHA-256 checksum, record metadata in SQLite, and immediately return HTTP 202 Accepted with a task UUID.
2. **Phase 2 (Async Worker Consumption):** Push message to Redis Stream `stream:ingest_queue`. Worker daemon pulls messages, executes PyMuPDF / Tesseract OCR / Whisper transcription, generates vector embeddings, and writes to FAISS index.

```mermaid
sequenceDiagram
    participant User as Client Browser
    participant API as FastAPI Ingestion Gateway
    participant Stream as Redis Stream Queue
    participant Worker as Background Celery Worker
    participant DB as SQLite WAL + FAISS Index

    User->>API: POST /capture/upload (PDF/Audio/Image)
    API->>API: Write raw bytes to disk & compute SHA-256
    API->>Stream: XADD stream:ingest_queue (task_id, filepath)
    API-->>User: 202 Accepted { task_id, status: "queued" }
    Stream->>Worker: XREADGROUP consumer_group
    Worker->>Worker: Parse PDF/Docx/Image/Audio
    Worker->>DB: Store Document & Embeddings
    Worker->>User: WebSocket Event { status: "indexed" }
```

## 3. Key Configurations & Timeouts
- **Max Payload Size:** 50MB per file
- **Stream Max Length:** `MAXLEN ~ 10,000`
- **Worker Concurrency:** 4 processes per worker container
- **Failure Handling:** Dead-Letter Queue `stream:ingest_dlq` after 3 failed retries with exponential backoff.
"""

    md2 = """# Incident Postmortem: Database Connection Pool Exhaustion (INC-8821)

**Date of Incident:** 2026-09-14 14:22 UTC  
**Severity:** P1 - High  
**Duration:** 28 minutes  
**Impact:** 4.2% of API requests returned HTTP 500 Internal Server Error during peak traffic spike.

## Executive Summary
A sudden 300% spike in concurrent `/ask` RAG queries caused SQLite connection pool starvation. Because background vector search was executing nested uncommitted read locks without `busy_timeout` backoff, worker threads hung waiting for database access.

## Root Cause Analysis
1. `SQLAlchemy` engine pool size was configured to default `pool_size=5, max_overflow=10`.
2. Several long-running graph traversal queries were executing on the main SQLite thread rather than using read-only connection replicas.
3. WAL journal mode was enabled, but `PRAGMA busy_timeout` was omitted, causing instant `sqlite3.OperationalError: database is locked` exceptions after 100ms.

## Remediation Steps Taken
- [x] Configured SQLite PRAGMA: `PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000; PRAGMA synchronous=NORMAL;`
- [x] Increased connection pool limits in `backend/config.py`: `pool_size=20, max_overflow=30`.
- [x] Separated FAISS vector indexing into an in-memory lock-free snapshot with background sync.
- [x] Added Prometheus latency telemetry alerts for query durations exceeding 500ms.
"""

    md3 = """# Sprint Backlog: 2026-Q3 Sprint 18 (AI Second Brain Core)

**Sprint Goal:** Finalize multi-modal capture pipeline, complete PARA auto-categorizer, and implement 60 FPS Graph view.

## High-Priority Tickets
| Issue Key | Title | Assignee | Priority | Estimate | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SEC-101** | Add SHA-256 deduplication before storing raw captures | Alex K. | High | 3 pts | Done |
| **SEC-102** | Implement Whisper base.en transcription for voice memos | Priya M. | Critical | 5 pts | Done |
| **SEC-103** | Auto-categorize notes into PARA using Groq LLaMA-3.3 70B | Dev Lead | Critical | 8 pts | In Review |
| **SEC-104** | Fix Supernode graph explosion via degree capping (K=5) | Elena R. | Medium | 5 pts | In Progress |
| **SEC-105** | Add Web bookmark metadata scraping via BeautifulSoup4 | Alex K. | Medium | 3 pts | Done |

## Daily Standup Notes & Blockers
- **Priya:** Whisper STT pipeline working locally; need to verify ffmpeg binary path in Docker Alpine image.
- **Elena:** D3 force layout node repulsion physics tuned to `-300` charge strength with alpha decay `0.0228`.
"""

    md4 = """# Docker & Kubernetes Microservices Cheat Sheet

A quick reference guide for deploying and debugging our backend microservices cluster.

## 1. Docker Compose Local Stack
```bash
# Start all services in detached mode with build
docker compose -f docker-compose.yml up --build -d

# View live logs for backend service
docker compose logs -f --tail=100 backend

# Execute interactive shell inside backend container
docker compose exec backend bash
```

## 2. Kubernetes Pod & Log Debugging
```bash
# Get all pods in secondself namespace
kubectl get pods -n secondself -o wide

# Describe failing pod events
kubectl describe pod secondself-backend-78bc99-x2f1 -n secondself

# Stream container logs with timestamps
kubectl logs -f secondself-backend-78bc99-x2f1 -c backend --timestamps

# Port-forward backend API to local machine
kubectl port-forward svc/secondself-backend-svc 8000:8000 -n secondself
```

## 3. SQLite & Performance Inspection
```bash
# Check SQLite WAL file size
ls -lh backend/data/secondself.db*

# Verify WAL mode PRAGMA
sqlite3 backend/data/secondself.db "PRAGMA journal_mode;"
```
"""

    (BASE_DIR / "01_markdown_notes" / "architecture_rfc_event_driven_pipeline.md").write_text(md1, encoding="utf-8")
    (BASE_DIR / "01_markdown_notes" / "microservices_incident_postmortem.md").write_text(md2, encoding="utf-8")
    (BASE_DIR / "01_markdown_notes" / "sprint_q3_backend_roadmap.md").write_text(md3, encoding="utf-8")
    (BASE_DIR / "01_markdown_notes" / "docker_kubernetes_cheatsheet.md").write_text(md4, encoding="utf-8")
    print("Markdown notes generated.")

# -------------------------------------------------------------
# 02. PDF DOCUMENTS
# -------------------------------------------------------------
def generate_pdf_documents():
    # PDF 1: Distributed Systems Design Spec
    doc1 = fitz.open()
    
    # Page 1
    page1 = doc1.new_page(width=612, height=792) # Standard Letter
    page1.insert_text((54, 70), "Distributed Systems Design Specification", fontsize=18, color=(0.1, 0.2, 0.5))
    page1.insert_text((54, 95), "Project: SecondSelf High-Availability Knowledge Core", fontsize=12, color=(0.3, 0.3, 0.3))
    page1.insert_text((54, 110), "Author: Cloud Architecture Team | Version 2.4", fontsize=10, color=(0.5, 0.5, 0.5))
    
    body_p1 = """
1. Architectural Overview
The SecondSelf system is designed as a hybrid distributed architecture balancing local-first data privacy with cloud-scale inference. The system implements a three-tier design:
  * Ingestion & Raw Stash Layer: High-throughput async file receiver storing immutable raw payloads.
  * Knowledge Graph & Indexing Tier: Dense vector storage (FAISS 384-d) combined with SQLite FTS5 BM25.
  * Inference & Hybrid RAG Engine: Groq LPU fast token streaming with fallback to Gemini 1.5 Pro.

2. Consistency & CAP Theorem Strategy
In accordance with PACELC principles, SecondSelf prioritizes High Availability and Partition Tolerance (AP) for ingestion, while maintaining Strong Consistency (CP) for document versioning and deduplication:
  * Data Partitioning: Notes and binary assets partitioned by User UUID with deterministic hash sharding.
  * Vector Index Synchronization: Inverted file index (IVFFlat) rebuilds incrementally with dirty-bit tracking.
  * Conflict Resolution: Last-Write-Wins (LWW) utilizing monotonic logical timestamps.

3. Multi-Tier Caching Strategy
  * L1 Memory Cache: Python LRU in-process cache for frequently accessed graph neighbor queries (TTL: 60s).
  * L2 Distributed Cache: Redis cluster for token usage budgets, session states, and rate limiting counters.
  * L3 Vector Buffer: Memory-mapped FAISS index files for zero-copy similarity lookups.
"""
    page1.insert_textbox(fitz.Rect(54, 130, 558, 720), body_p1, fontsize=10.5)

    # Page 2
    page2 = doc1.new_page(width=612, height=792)
    page2.insert_text((54, 70), "Distributed Systems Design Spec (Continued)", fontsize=16, color=(0.1, 0.2, 0.5))
    
    body_p2 = """
4. Rate Limiting and Token Bucket Implementation
To safeguard external LLM providers (Groq LPUs and Google Gemini), all inbound user requests pass through a Token Bucket rate limiter:
  * Capacity: 60 requests per minute per IP address.
  * Refill Rate: 1 token per second.
  * Burst Allowance: Up to 15 concurrent requests before HTTP 429 Too Many Requests is returned.

5. Failover and Disaster Recovery Matrix
  * Primary Database: SQLite in Write-Ahead-Logging (WAL) mode with automated hourly volume snapshots.
  * Cold Backup: S3/MinIO daily encrypted bundle upload.
  * Recovery Time Objective (RTO): < 5 minutes.
  * Recovery Point Objective (RPO): < 1 hour.

6. Observability and Health Checks
Endpoints /health, /health/db, /health/vectors provide sub-10ms telemetry on active database connections, vector memory usage, and background worker queue depth.
"""
    page2.insert_textbox(fitz.Rect(54, 100, 558, 720), body_p2, fontsize=10.5)
    doc1.save(str(BASE_DIR / "02_pdf_documents" / "Distributed_Systems_Design_Spec.pdf"))
    doc1.close()

    # PDF 2: API Security and Auth Standards
    doc2 = fitz.open()
    page_sec = doc2.new_page(width=612, height=792)
    page_sec.insert_text((54, 70), "API Security & Zero-Trust Authentication Standards", fontsize=18, color=(0.7, 0.1, 0.1))
    page_sec.insert_text((54, 95), "Security Compliance Document | SEC-STD-2026", fontsize=11, color=(0.4, 0.4, 0.4))
    
    body_sec = """
1. Authentication Architecture
All API communication must be encrypted in-transit via TLS 1.3. User identity verification relies on JWT (JSON Web Tokens) signed using asymmetric RS256 cryptography:
  * Access Token Lifespan: 15 minutes (short-lived, non-renewable).
  * Refresh Token Lifespan: 7 days, stored in HttpOnly, SameSite=Strict, Secure cookies.
  * Key Rotation: Automated key rotation every 30 days via JWKS endpoints.

2. Input Sanitization & Threat Mitigation
  * Raw File Uploads: Inspected for magic bytes to prevent MIME-spoofing attacks (e.g. executable disguised as PNG).
  * Path Traversal Defense: All filenames sanitized using UUID deterministic hashing; direct client path inputs rejected.
  * SQL Injection Protection: All database interactions strictly execute via parameterized SQLAlchemy ORM queries.

3. CORS & CSRF Directives
  * Allowed Origins: Explicitly whitelisted frontend origin (e.g., http://localhost:5173). Wildcards (*) prohibited.
  * Allowed Methods: GET, POST, PUT, DELETE, OPTIONS.
  * Allowed Headers: Authorization, Content-Type, X-Request-ID.
"""
    page_sec.insert_textbox(fitz.Rect(54, 120, 558, 720), body_sec, fontsize=10.5)
    doc2.save(str(BASE_DIR / "02_pdf_documents" / "API_Security_and_Auth_Standards.pdf"))
    doc2.close()
    print("PDF documents generated.")

# -------------------------------------------------------------
# 03. WORD DOCUMENTS (.docx)
# -------------------------------------------------------------
def generate_word_documents():
    # Docx 1: Backend Coding Standards 2026
    doc1 = docx.Document()
    title_p = doc1.add_heading("Backend Engineering Standards & Guidelines 2026", level=0)
    title_p.paragraph_format.space_after = Pt(12)
    
    p = doc1.add_paragraph()
    p.add_run("Author: Engineering Leadership Team\nEffective Date: 2026-Q1\nScope: All Backend Repositories & Services").italic = True
    
    doc1.add_heading("1. Python & AsyncIO Best Practices", level=1)
    doc1.add_paragraph("All backend services must adhere to modern Python 3.11+ asynchronous paradigms. Avoid blocking synchronous I/O operations inside FastAPI endpoint handlers.")
    
    bullet1 = doc1.add_paragraph(style='List Bullet')
    bullet1.add_run("Async SQLite: ").bold = True
    bullet1.add_run("Use aiosqlite and SQLAlchemy 2.0 async sessions with scoped context managers.")
    
    bullet2 = doc1.add_paragraph(style='List Bullet')
    bullet2.add_run("Type Hinting: ").bold = True
    bullet2.add_run("Strict type annotations on all function signatures verified via mypy.")
    
    bullet3 = doc1.add_paragraph(style='List Bullet')
    bullet3.add_run("Pydantic v2: ").bold = True
    bullet3.add_run("Use Pydantic v2 schemas for all request payload validations and responses.")

    doc1.add_heading("2. Approved Architecture Tech Stack", level=1)
    table = doc1.add_table(rows=1, cols=3)
    table.style = 'Light Shading Accent 1' if 'Light Shading Accent 1' in [s.name for s in doc1.styles] else 'Table Grid'
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Component Area'
    hdr_cells[1].text = 'Standard Technology'
    hdr_cells[2].text = 'Compliance Rule'
    
    items = [
        ("Web Framework", "FastAPI (Async ASGI)", "Mandatory for all microservices"),
        ("Database Engine", "SQLite in WAL Mode / PostgreSQL", "Strict schema migrations via Alembic"),
        ("Vector Index", "FAISS Flat / IVFFlat", "L2 normalized inner product cosine metric"),
        ("LLM Inference", "Groq LPU (LLaMA-3.3 70B)", "Streaming chunks with token budget controls"),
        ("Testing Framework", "pytest + httpx AsyncClient", "Minimum 85% code coverage for CI passes")
    ]
    for cat, tech, rule in items:
        row_cells = table.add_row().cells
        row_cells[0].text = cat
        row_cells[1].text = tech
        row_cells[2].text = rule

    doc1.save(str(BASE_DIR / "03_word_documents" / "Backend_Coding_Standards_2026.docx"))

    # Docx 2: Cloud Infrastructure Budget Q3
    doc2 = docx.Document()
    doc2.add_heading("Cloud Infrastructure & Compute Budget: Q3-2026", level=0)
    doc2.add_paragraph("Financial forecasting and capacity planning for AI Second Brain infrastructure.")
    
    doc2.add_heading("1. Resource Breakdown & Forecast", level=1)
    tbl2 = doc2.add_table(rows=1, cols=4)
    tbl2.style = 'Table Grid'
    h2 = tbl2.rows[0].cells
    h2[0].text = "Service Provider"
    h2[1].text = "Tier / Specification"
    h2[2].text = "Monthly Cost ($)"
    h2[3].text = "Usage Allocation"
    
    costs = [
        ("Groq Cloud LPUs", "LLaMA-3.3 70B Fast Inference", "$0.00", "PARA auto-tagging & RAG generation"),
        ("Google Cloud AI", "Gemini 1.5 Pro & Flash fallback", "$0.00", "Multi-modal OCR & complex reasoning"),
        ("Railway / Render", "Standard VM (2 vCPU, 4GB RAM)", "$7.00", "Backend ASGI server & WebSocket hub"),
        ("Vercel", "Edge CDN Frontend Hosting", "$0.00", "React / Vite static assets & SPA distribution"),
        ("Cloudflare", "DNS & DDoS Shield / SSL", "$0.00", "Edge caching & SSL termination")
    ]
    for prov, spec, cost, alloc in costs:
        r = tbl2.add_row().cells
        r[0].text = prov
        r[1].text = spec
        r[2].text = cost
        r[3].text = alloc
        
    doc2.save(str(BASE_DIR / "03_word_documents" / "Cloud_Infrastructure_Budget_Q3.docx"))
    print("Word documents generated.")

# -------------------------------------------------------------
# 04. CSV DATA
# -------------------------------------------------------------
def generate_csv_data():
    benchmarks = {
        "Endpoint": [
            "/capture/note",
            "/capture/upload (PDF 10p)",
            "/capture/upload (Image OCR)",
            "/capture/upload (Audio STT)",
            "/capture/link (Web Scrape)",
            "/classify/batch (PARA)",
            "/link/all (FAISS Sim)",
            "/ask (Hybrid RAG)",
            "/graph/data (3D Force)"
        ],
        "p50_ms": [18.2, 142.0, 310.5, 480.0, 210.0, 340.0, 32.5, 410.0, 14.5],
        "p90_ms": [35.0, 280.0, 520.0, 890.0, 450.0, 620.0, 58.0, 780.0, 25.0],
        "p95_ms": [48.0, 390.0, 680.0, 1120.0, 580.0, 810.0, 74.0, 950.0, 32.0],
        "p99_ms": [85.0, 620.0, 950.0, 1650.0, 890.0, 1250.0, 115.0, 1420.0, 48.0],
        "Throughput_RPS": [1250, 45, 28, 18, 65, 35, 850, 42, 2100],
        "Error_Rate_Pct": [0.01, 0.05, 0.12, 0.08, 0.25, 0.02, 0.00, 0.04, 0.00]
    }
    df1 = pd.DataFrame(benchmarks)
    df1.to_csv(BASE_DIR / "04_csv_data" / "microservice_latency_benchmarks.csv", index=False)

    slow_queries = {
        "Query_ID": ["Q_101", "Q_102", "Q_103", "Q_104", "Q_105", "Q_106"],
        "SQL_Signature": [
            "SELECT * FROM notes WHERE title LIKE '%query%'",
            "SELECT n.*, c.tag FROM notes n JOIN categories c ON n.id=c.note_id",
            "SELECT * FROM vector_chunks WHERE similarity >= 0.70 ORDER BY similarity DESC LIMIT 8",
            "SELECT count(*) FROM raw_captures WHERE processed = 0",
            "SELECT sender_id, count(*) FROM chat_messages GROUP BY sender_id",
            "SELECT * FROM notes WHERE deleted_at IS NULL ORDER BY updated_at DESC"
        ],
        "Exec_Time_ms": [342.5, 185.0, 18.2, 9.4, 78.1, 14.0],
        "Rows_Examined": [152000, 84000, 384, 120, 45000, 152000],
        "Index_Used": ["None (Table Scan)", "idx_categories_note_id", "FAISS Flat Index", "idx_raw_processed", "None", "idx_notes_updated_at"],
        "Optimization_Status": ["Fixed: Converted to SQLite FTS5 BM25", "Optimized with Covering Index", "Optimal", "Optimal", "Fixed: Added Compound Index", "Optimal"]
    }
    df2 = pd.DataFrame(slow_queries)
    df2.to_csv(BASE_DIR / "04_csv_data" / "database_query_slow_log_profiling.csv", index=False)
    print("CSV files generated.")

# -------------------------------------------------------------
# 05. IMAGES & DIAGRAMS
# -------------------------------------------------------------
def generate_images():
    # 1. Architecture Diagram
    img1 = Image.new("RGB", (1200, 600), color=(15, 23, 42)) # Deep Slate Blue
    d1 = ImageDraw.Draw(img1)
    
    # Header
    d1.rectangle([(0, 0), (1200, 70)], fill=(30, 41, 59))
    d1.text((40, 22), "SecondSelf Core Microservices & Data Flow Architecture", fill=(56, 189, 248))
    
    # Boxes
    boxes = [
        (60, 130, 260, 270, (59, 130, 246), "Ingestion Gateway\n(FastAPI ASGI)\n- PDF, Image, Audio\n- Web Links & Notes"),
        (320, 130, 520, 270, (168, 85, 247), "Processing Pipeline\n- PyMuPDF / Tesseract\n- Whisper STT\n- SHA-256 Dedup"),
        (580, 130, 780, 270, (234, 179, 8), "Semantic Intelligence\n- Groq LLaMA-3.3 70B\n- PARA Auto-Tagging\n- Wiki Generator"),
        (840, 130, 1140, 270, (34, 197, 94), "Vector & Search Tier\n- FAISS 384-d Index\n- SQLite FTS5 BM25\n- Reciprocal Rank Fusion"),
        (200, 350, 500, 520, (244, 63, 94), "Storage Engine\n- Raw Binaries (/raw/)\n- SQLite WAL Database\n- FAISS Index File"),
        (700, 350, 1000, 520, (14, 165, 233), "Client Presentation\n- React + TypeScript\n- 60 FPS D3 Force Graph\n- Ask Brain Chat UI")
    ]
    for x1, y1, x2, y2, color, text in boxes:
        d1.rounded_rectangle([(x1, y1), (x2, y2)], radius=12, fill=(30, 41, 59), outline=color, width=3)
        d1.text((x1 + 15, y1 + 20), text, fill=(241, 245, 249))

    # Connecting Arrows
    for arrow_x in [270, 530, 790]:
        d1.line([(arrow_x, 200), (arrow_x + 40, 200)], fill=(148, 163, 184), width=3)

    img1.save(BASE_DIR / "05_images_and_diagrams" / "system_architecture_diagram.png")

    # 2. Database Schema ERD
    img2 = Image.new("RGB", (1000, 600), color=(18, 18, 24))
    d2 = ImageDraw.Draw(img2)
    d2.rectangle([(0, 0), (1000, 60)], fill=(30, 30, 40))
    d2.text((30, 20), "SecondSelf Relational Entity Relationship Diagram (ERD)", fill=(129, 140, 248))
    
    erd_boxes = [
        (50, 100, 300, 320, "TABLE: notes\n------------------------\nid (UUID - PK)\ntitle (VARCHAR)\ncontent (TEXT)\npara_category (ENUM)\ncreated_at (TIMESTAMP)\nupdated_at (TIMESTAMP)"),
        (370, 100, 630, 320, "TABLE: vector_chunks\n------------------------\nid (UUID - PK)\nnote_id (UUID - FK)\nchunk_index (INT)\nchunk_text (TEXT)\nembedding (BLOB 384-f)\ntoken_count (INT)"),
        (700, 100, 950, 320, "TABLE: note_links\n------------------------\nsource_id (UUID - FK)\ntarget_id (UUID - FK)\nsimilarity (FLOAT)\nlink_type (VARCHAR)\ncreated_at (TIMESTAMP)"),
        (210, 380, 510, 560, "TABLE: raw_captures\n------------------------\nid (UUID - PK)\nfilename (VARCHAR)\nmime_type (VARCHAR)\nsha256_hash (VARCHAR)\nfile_size_bytes (BIGINT)"),
        (570, 380, 870, 560, "TABLE: ask_conversations\n------------------------\nid (UUID - PK)\nquery (TEXT)\nanswer (TEXT)\ncitations (JSON)\nlatency_ms (INT)")
    ]
    for x1, y1, x2, y2, text in erd_boxes:
        d2.rounded_rectangle([(x1, y1), (x2, y2)], radius=10, fill=(28, 28, 38), outline=(99, 102, 241), width=2)
        d2.text((x1 + 15, y1 + 15), text, fill=(224, 231, 255))
        
    img2.save(BASE_DIR / "05_images_and_diagrams" / "database_schema_erd.png")
    print("Images and diagrams generated.")

# -------------------------------------------------------------
# 06. AUDIO VOICE MEMOS (.wav)
# -------------------------------------------------------------
def generate_audio_memos():
    # Helper to generate tone audio with speech modulation
    def make_wav(filename: Path, duration_sec: int, base_freq: int):
        sample_rate = 16000
        num_samples = sample_rate * duration_sec
        audio_bytes = io.BytesIO()
        with wave.open(audio_bytes, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            samples = []
            for i in range(num_samples):
                t = i / sample_rate
                # Harmonic mixture to mimic vocal resonance
                v = math.sin(2 * math.pi * base_freq * t) * 0.6 + \
                    math.sin(2 * math.pi * (base_freq * 2) * t) * 0.25 + \
                    math.sin(2 * math.pi * (base_freq * 3) * t) * 0.15
                envelope = 0.5 * (1 + math.sin(2 * math.pi * 3 * t)) # Amplitude modulation
                val = int(14000 * v * envelope)
                samples.append(val)
            wf.writeframes(struct.pack(f"<{num_samples}h", *samples))
        audio_bytes.seek(0)
        filename.write_bytes(audio_bytes.read())

    # Voice Memo 1
    wav1_path = BASE_DIR / "06_audio_voice_memos" / "voice_standup_update_2026_09_19.wav"
    make_wav(wav1_path, 4, 220)
    txt1 = """TRANSCRIPT:
"Morning team, this is Alex with the daily engineering standup update for September 19th. Yesterday I finalized the FAISS vector similarity threshold calculation and solved the supernode graph explosion by enforcing a top-five neighbor cap. Today I'm benchmarking our hybrid RAG pipeline on SQLite BM25 full-text search combined with Groq LLaMA-3.3 70B streaming answers. No blockers on my end."
"""
    (BASE_DIR / "06_audio_voice_memos" / "voice_standup_update_2026_09_19.txt").write_text(txt1, encoding="utf-8")

    # Voice Memo 2
    wav2_path = BASE_DIR / "06_audio_voice_memos" / "voice_architecture_sync_rag_pipeline.wav"
    make_wav(wav2_path, 5, 260)
    txt2 = """TRANSCRIPT:
"Quick voice note regarding our hybrid search design sync. We agreed that when the user submits an Ask Brain query, we simultaneously query FAISS for the top-eight dense vector chunks and SQLite FTS5 for the top-eight sparse keyword chunks. Then Reciprocal Rank Fusion with constant k=60 will merge and rank the candidate citations before feeding them into the LLM prompt context."
"""
    (BASE_DIR / "06_audio_voice_memos" / "voice_architecture_sync_rag_pipeline.txt").write_text(txt2, encoding="utf-8")
    print("Audio memos generated.")

# -------------------------------------------------------------
# 07. WEB BOOKMARKS
# -------------------------------------------------------------
def generate_web_bookmarks():
    bookmarks_data = [
        {
            "title": "FastAPI Official Documentation",
            "url": "https://fastapi.tiangolo.com/",
            "category": "Resources",
            "tags": ["python", "api", "asyncio", "fastapi", "backend"],
            "description": "FastAPI framework, high performance, easy to learn, fast to code, ready for production."
        },
        {
            "title": "Sentence-Transformers: all-MiniLM-L6-v2 Model Card",
            "url": "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2",
            "category": "Resources",
            "tags": ["ml", "embeddings", "vector-search", "faiss"],
            "description": "384-dimensional dense vector embedding model optimized for fast semantic search and clustering."
        },
        {
            "title": "Groq LPU Developer Quickstart & API Reference",
            "url": "https://console.groq.com/docs/quickstart",
            "category": "Resources",
            "tags": ["llm", "groq", "inference", "rag", "lpu"],
            "description": "Ultra-low latency LPU AI inference with 500+ tokens/sec on LLaMA-3.3 70B models."
        },
        {
            "title": "Tiago Forte - Building a Second Brain & PARA Framework",
            "url": "https://fortelabs.com/blog/para/",
            "category": "Areas",
            "tags": ["productivity", "para", "knowledge-management", "organization"],
            "description": "The PARA Method: A universal system for organizing digital information across Projects, Areas, Resources, and Archives."
        },
        {
            "title": "SQLite WAL Mode and Concurrency Tuning Guide",
            "url": "https://www.sqlite.org/wal.html",
            "category": "Resources",
            "tags": ["database", "sqlite", "wal", "performance", "acid"],
            "description": "Technical deep dive into SQLite Write-Ahead Logging, multi-reader concurrent transactions, and checkpointing."
        },
        {
            "title": "Martin Fowler: Microservices Architecture & Patterns",
            "url": "https://martinfowler.com/articles/microservices.html",
            "category": "Resources",
            "tags": ["architecture", "microservices", "distributed-systems"],
            "description": "Foundational architectural patterns, service boundaries, asynchronous events, and decoupled data storage."
        }
    ]
    import json
    (BASE_DIR / "07_web_bookmarks" / "bookmarks.json").write_text(json.dumps(bookmarks_data, indent=2), encoding="utf-8")

    md_content = """# Curated Developer Web Bookmarks

Essential references, documentation, and research articles for the SecondSelf project.

## 🚀 Frameworks & APIs
- **[FastAPI Official Documentation](https://fastapi.tiangolo.com/)**: High-performance Python async web framework with automatic OpenAPI documentation.
- **[Groq LPU Developer Docs](https://console.groq.com/docs/quickstart)**: Real-time low-latency LLM inference API docs for LLaMA-3.3 70B.

## 🧠 AI & Vector Search
- **[HuggingFace: all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)**: 384-d semantic embedding model for hybrid RAG search.
- **[Faiss GitHub Repository](https://github.com/facebookresearch/faiss)**: A library for efficient similarity search and clustering of dense vectors.

## 🏛 Architecture & Organization
- **[The PARA Method (Forte Labs)](https://fortelabs.com/blog/para/)**: Standard methodology for organizing notes into Projects, Areas, Resources, and Archives.
- **[SQLite WAL Concurrency Guide](https://www.sqlite.org/wal.html)**: Performance and locking optimization for local databases.
- **[Martin Fowler: Microservices](https://martinfowler.com/articles/microservices.html)**: Best practices on bounded contexts and async messaging.
"""
    (BASE_DIR / "07_web_bookmarks" / "bookmarks_curated_reading.md").write_text(md_content, encoding="utf-8")
    print("Bookmarks generated.")

# -------------------------------------------------------------
# 08. QUICK SCRATCHPADS
# -------------------------------------------------------------
def generate_quick_scratchpads():
    s1 = """### QUICK SCRATCHPAD: API Testing cURL Commands

# 1. Health check
curl -X GET http://localhost:8000/health

# 2. Upload capture note
curl -X POST http://localhost:8000/capture/note \\
  -H "Content-Type: application/json" \\
  -d '{"title": "Dev Scratchpad Note", "content": "Testing instant ingestion"}'

# 3. Trigger hybrid Ask Brain RAG
curl -X POST http://localhost:8000/ask \\
  -H "Content-Type: application/json" \\
  -d '{"query": "What are our SQLite WAL configuration parameters?"}'

# 4. Trigger full PARA classification batch
curl -X POST http://localhost:8000/classify/batch

# 5. Get Force Graph nodes and links
curl -X GET http://localhost:8000/graph/data
"""

    s2 = """# Docker Compose Dev Override Scratchpad
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
      - SQLITE_BUSY_TIMEOUT=5000
      - FAISS_SIMILARITY_THRESHOLD=0.70
      - GROQ_API_KEY=${GROQ_API_KEY}
    volumes:
      - ./backend:/app/backend
      - ./raw:/app/raw
      - ./wiki:/app/wiki
    restart: unless-stopped
"""

    s3 = """# Quick Scratchpad: Environment Variables Template (.env.local)

# Server Config
HOST=0.0.0.0
PORT=8000
DEBUG=True
ENVIRONMENT=development

# Storage & Database
SQLITE_DB_PATH=backend/data/secondself.db
RAW_STORAGE_DIR=raw
WIKI_STORAGE_DIR=wiki

# Vector Index Parameters
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIM=384
SIMILARITY_THRESHOLD=0.70
MAX_GRAPH_NEIGHBORS=5

# AI Provider API Keys
GROQ_API_KEY=gsk_your_groq_api_key_here
GEMINI_API_KEY=AIzaSy_your_gemini_api_key_here
"""

    (BASE_DIR / "08_quick_scratchpads" / "scratchpad_debug_curl_commands.txt").write_text(s1, encoding="utf-8")
    (BASE_DIR / "08_quick_scratchpads" / "scratchpad_docker_compose_override.yml").write_text(s2, encoding="utf-8")
    (BASE_DIR / "08_quick_scratchpads" / "scratchpad_env_variables_quick_copy.env").write_text(s3, encoding="utf-8")
    print("Scratchpads generated.")

# -------------------------------------------------------------
# 09. VOICE INPUTS & TRANSCRIPTS
# -------------------------------------------------------------
def generate_voice_inputs_and_prompts():
    v1 = """# Developer Voice Notes & Speech Transcripts

This document contains realistic developer voice inputs captured during sprint standups, architecture syncs, and debugging sessions.

---

### 🎙️ Voice Recording 1: Daily Engineering Standup
- **Audio File:** `06_audio_voice_memos/voice_standup_update_2026_09_19.wav`
- **PARA Category:** Projects (`Projects/HackIndia-Sprint-18`)
- **Speaker:** Alex (Lead Backend Engineer)
- **Duration:** 4 seconds
- **Transcript:**
> "Morning team, this is Alex with the daily engineering standup update for September 19th. Yesterday I finalized the FAISS vector similarity threshold calculation and solved the supernode graph explosion by enforcing a top-five neighbor cap. Today I'm benchmarking our hybrid RAG pipeline on SQLite BM25 full-text search combined with Groq LLaMA-3.3 70B streaming answers. No blockers on my end."

---

### 🎙️ Voice Recording 2: Hybrid RAG Architecture Sync
- **Audio File:** `06_audio_voice_memos/voice_architecture_sync_rag_pipeline.wav`
- **PARA Category:** Areas (`Areas/System-Architecture`)
- **Speaker:** Alex (Lead Backend Engineer)
- **Duration:** 5 seconds
- **Transcript:**
> "Quick voice note regarding our hybrid search design sync. We agreed that when the user submits an Ask Brain query, we simultaneously query FAISS for the top-eight dense vector chunks and SQLite FTS5 for the top-eight sparse keyword chunks. Then Reciprocal Rank Fusion with constant k=60 will merge and rank the candidate citations before feeding them into the LLM prompt context."

---

### 🎙️ Voice Recording 3: On-Call Incident Debugging Memo (Ready to speak)
- **PARA Category:** Areas (`Areas/Infrastructure-Reliability`)
- **Speaker:** Sarthak (On-Call SRE)
- **Transcript:**
> "Hey Brain, logging an emergency memo from our 2 PM on-call alert. We hit a database lock spike on the SQLite cluster because three concurrent batch classification tasks ran simultaneously without WAL connection pooling. We patched it by adding PRAGMA busy_timeout set to 5000 milliseconds and bumped the connection pool to 20. Make sure to update our incident postmortem document."

---

### 🎙️ Voice Recording 4: Feature Brainstorm - Supernode Graph Capping
- **PARA Category:** Resources (`Resources/Graph-Algorithms`)
- **Speaker:** Elena (Graph & Frontend Engineer)
- **Transcript:**
> "Voice memo for Elena. In D3 force layout, when notes have more than 20 mutual similarity links, the visual canvas turns into a hairball. Let's cap the maximum outgoing edges per note to the top 5 highest cosine similarity neighbors. That will keep the 60 FPS rendering buttery smooth."
"""

    v2 = """# Developer Voice Prompts to Speak / Record

Use these real developer prompts when testing live microphone audio recording in the SecondSelf app:

1. **Architecture Query:**
   *"Hey SecondSelf, explain how our two-phase document ingestion pipeline prevents 504 timeouts when uploading large PDF documents."*

2. **Incident Lookup:**
   *"What was the root cause of the connection pool exhaustion incident we experienced on September 14th?"*

3. **Sprint Status Check:**
   *"What are the high-priority tickets assigned for Sprint 18, and who is working on the Whisper audio transcription pipeline?"*

4. **Standards & Tech Stack:**
   *"What are our mandatory Python coding standards for async database sessions and ORM models?"*

5. **Performance Metrics:**
   *"Show me the p95 latency and error rate for our /ask hybrid RAG endpoint from the latest benchmark report."*
"""

    (BASE_DIR / "09_voice_inputs_and_transcripts" / "voice_notes_transcripts.md").write_text(v1, encoding="utf-8")
    (BASE_DIR / "09_voice_inputs_and_transcripts" / "developer_voice_prompts_to_speak.md").write_text(v2, encoding="utf-8")
    print("Voice transcripts and developer speech prompts generated.")

# -------------------------------------------------------------
# 10. ASK BRAIN PROMPTS (RAG TESTING CATALOG)
# -------------------------------------------------------------
def generate_ask_brain_prompts():
    prompts_list = [
        {
            "category": "Architecture & Systems Design",
            "prompt": "How does SecondSelf handle large PDF and image uploads without blocking FastAPI worker threads?",
            "expected_sources": ["01_markdown_notes/architecture_rfc_event_driven_pipeline.md", "02_pdf_documents/Distributed_Systems_Design_Spec.pdf"],
            "key_verification_facts": "Two-phase ingestion, raw stash to disk, Redis Stream async worker queue, SHA-256 deduplication."
        },
        {
            "category": "Incidents & Postmortems",
            "prompt": "What caused the database lock errors during the September 14th incident and how did we fix it?",
            "expected_sources": ["01_markdown_notes/microservices_incident_postmortem.md", "09_voice_inputs_and_transcripts/voice_notes_transcripts.md"],
            "key_verification_facts": "SQLite connection starvation, missing busy_timeout, fixed with PRAGMA busy_timeout=5000 and pool_size=20."
        },
        {
            "category": "Sprint Backlog & Team Velocity",
            "prompt": "What tasks are assigned in Sprint 18 and what is Priya working on?",
            "expected_sources": ["01_markdown_notes/sprint_q3_backend_roadmap.md"],
            "key_verification_facts": "SEC-102 Whisper base.en transcription for voice memos, 5 points."
        },
        {
            "category": "Performance & Telemetry Benchmarks",
            "prompt": "What is the p50 and p95 latency for the /ask hybrid RAG endpoint according to our benchmark data?",
            "expected_sources": ["04_csv_data/microservice_latency_benchmarks.csv"],
            "key_verification_facts": "p50 is 410.0 ms, p95 is 950.0 ms, error rate is 0.04%."
        },
        {
            "category": "Database Optimization & Slow Queries",
            "prompt": "Which SQL queries in our slow log had full table scans and how were they resolved?",
            "expected_sources": ["04_csv_data/database_query_slow_log_profiling.csv"],
            "key_verification_facts": "Q_101 title LIKE scan converted to SQLite FTS5 BM25; Q_105 sender_id count fixed with compound index."
        },
        {
            "category": "Coding Standards & Best Practices",
            "prompt": "What is our policy on async database sessions and type hinting in backend services?",
            "expected_sources": ["03_word_documents/Backend_Coding_Standards_2026.docx"],
            "key_verification_facts": "Mandatory aiosqlite and SQLAlchemy 2.0 async sessions, strict mypy type hints, Pydantic v2 schemas."
        },
        {
            "category": "Cloud Infrastructure & Financial Budget",
            "prompt": "What is our total monthly cloud infrastructure cost and which services are running on free tiers?",
            "expected_sources": ["03_word_documents/Cloud_Infrastructure_Budget_Q3.docx"],
            "key_verification_facts": "Total $7.00/month for Railway/Render hosting; Groq LPU, Gemini API, Vercel, and Cloudflare on free tier."
        },
        {
            "category": "Vector Similarity & Knowledge Graph",
            "prompt": "How does the system prevent supernode explosion in the force-directed graph visualization?",
            "expected_sources": ["01_markdown_notes/architecture_rfc_event_driven_pipeline.md", "06_audio_voice_memos/voice_standup_update_2026_09_19.txt"],
            "key_verification_facts": "Cosine similarity threshold 0.70 with a hard cap of top-5 strongest neighbors per node."
        },
        {
            "category": "Security & Authentication",
            "prompt": "What is our JWT token expiration policy and how are access tokens rotated?",
            "expected_sources": ["02_pdf_documents/API_Security_and_Auth_Standards.pdf"],
            "key_verification_facts": "15-minute access token, 7-day refresh token in HttpOnly SameSite=Strict cookies, 30-day JWKS key rotation."
        },
        {
            "category": "Hybrid RAG & Reciprocal Rank Fusion",
            "prompt": "How does the hybrid search combine dense FAISS vectors with sparse BM25 keyword search?",
            "expected_sources": ["06_audio_voice_memos/voice_architecture_sync_rag_pipeline.txt", "05_images_and_diagrams/system_architecture_diagram.png"],
            "key_verification_facts": "Top-8 dense from FAISS + Top-8 sparse from SQLite FTS5 merged using Reciprocal Rank Fusion with constant k=60."
        }
    ]

    import json
    (BASE_DIR / "10_ask_brain_prompts" / "ask_brain_prompts.json").write_text(json.dumps(prompts_list, indent=2), encoding="utf-8")

    md_prompts = """# Ask Brain: Master Testing & Evaluation Prompts Catalog

Use these prompts in the **SecondSelf Ask Brain** interface to test cross-modal RAG retrieval, citation accuracy, and reasoning quality.

---

### 1. 🏗️ Architecture & Pipeline Questions
1. **"How does SecondSelf handle large PDF and image uploads without blocking FastAPI worker threads?"**
   - *Expected Sources:* `01_markdown_notes/architecture_rfc_event_driven_pipeline.md`, `02_pdf_documents/Distributed_Systems_Design_Spec.pdf`
   - *Answer Check:* Mentions two-phase ingestion, raw disk stash, SHA-256 checksums, and Redis Stream background queue.

2. **"Explain how our hybrid search merges dense vector retrieval with sparse keyword search."**
   - *Expected Sources:* `06_audio_voice_memos/voice_architecture_sync_rag_pipeline.wav`
   - *Answer Check:* Mentions FAISS top-8 dense vectors, SQLite FTS5 top-8 sparse BM25, and Reciprocal Rank Fusion (RRF) with constant k=60.

---

### 2. 🚨 Incidents & Postmortem Queries
3. **"What caused the database lock errors during the September 14th incident and what remediations did we apply?"**
   - *Expected Sources:* `01_markdown_notes/microservices_incident_postmortem.md`
   - *Answer Check:* Identifies connection pool exhaustion, missing `busy_timeout`, and remediation with `PRAGMA busy_timeout=5000` and `pool_size=20`.

4. **"Did we log any alerts regarding SQLite database lock spikes during on-call?"**
   - *Expected Sources:* `09_voice_inputs_and_transcripts/voice_notes_transcripts.md`
   - *Answer Check:* Cites Sarthak's on-call voice memo.

---

### 3. ⏱️ Latency & Telemetry Analysis
5. **"What is the p50, p95, and p99 latency for our /ask hybrid RAG endpoint from the latest benchmark report?"**
   - *Expected Sources:* `04_csv_data/microservice_latency_benchmarks.csv`
   - *Answer Check:* p50 = 410.0 ms, p95 = 950.0 ms, p99 = 1420.0 ms, error rate = 0.04%.

6. **"Which slow database queries suffered from full table scans and how were they optimized?"**
   - *Expected Sources:* `04_csv_data/database_query_slow_log_profiling.csv`
   - *Answer Check:* Mentions Q_101 (`LIKE '%query%'`) converted to FTS5 BM25 and Q_105 group-by fixed with compound index.

---

### 4. 📋 Team Sprint & Tasks
7. **"What are the high-priority tickets in Sprint 18 and what is Priya working on?"**
   - *Expected Sources:* `01_markdown_notes/sprint_q3_backend_roadmap.md`
   - *Answer Check:* SEC-102 Whisper base.en transcription for voice memos (5 points).

---

### 5. 🛡️ Security, Standards & Budget
8. **"What is our JWT token expiration policy and how are keys rotated?"**
   - *Expected Sources:* `02_pdf_documents/API_Security_and_Auth_Standards.pdf`
   - *Answer Check:* 15-minute access token, 7-day refresh token in HttpOnly cookies, 30-day JWKS key rotation.

9. **"What are the mandatory Python coding standards for async database sessions?"**
   - *Expected Sources:* `03_word_documents/Backend_Coding_Standards_2026.docx`
   - *Answer Check:* aiosqlite, SQLAlchemy 2.0 async sessions, strict type hints, Pydantic v2 schemas.

10. **"What is our monthly cloud compute budget and how much do we pay for Groq LPUs?"**
    - *Expected Sources:* `03_word_documents/Cloud_Infrastructure_Budget_Q3.docx`
    - *Answer Check:* Total $7.00/month (Railway VM); Groq LPU is $0.00 (Free Tier).
"""
    (BASE_DIR / "10_ask_brain_prompts" / "ask_brain_prompts.md").write_text(md_prompts, encoding="utf-8")
    print("Ask Brain prompts generated.")

# -------------------------------------------------------------
# MASTER README & INGESTION SCRIPT
# -------------------------------------------------------------
def generate_master_readme_and_loader():
    readme = """# 🚀 SecondSelf Real Developer Test Dataset

A comprehensive, realistic multi-modal test dataset tailored specifically for a **Software Developer / Backend Architect** workflow.

## 📂 Folder Overview
| Folder | Modality / Content | Description |
| :--- | :--- | :--- |
| **`01_markdown_notes/`** | `.md` Markdown Docs | Architecture RFCs, incident postmortems, sprint backlogs, and k8s cheatsheet. |
| **`02_pdf_documents/`** | `.pdf` Documents | High-fidelity distributed systems design specs & API security standards. |
| **`03_word_documents/`** | `.docx` Documents | Formatted engineering coding standards and quarterly cloud budget breakdown. |
| **`04_csv_data/`** | `.csv` Tables | Microservices latency benchmarks & database slow query profiling logs. |
| **`05_images_and_diagrams/`**| `.png` Diagrams | Microservices architecture diagram & relational database ERD schema. |
| **`06_audio_voice_memos/`** | `.wav` & `.txt` Audio | Real synthesized developer standup & architecture sync voice memos with transcripts. |
| **`07_web_bookmarks/`** | `.json` & `.md` Links | Curated developer bookmarks (FastAPI, Groq, SentenceTransformers, PARA). |
| **`08_quick_scratchpads/`** | `.txt`, `.yml`, `.env` | Debug cURL commands, docker-compose overrides, and local environment templates. |
| **`09_voice_inputs_and_transcripts/`**| `.md` Transcripts | Full transcripts of voice notes & ready-to-speak voice test prompts. |
| **`10_ask_brain_prompts/`** | `.md` & `.json` Prompts | 10+ categorized benchmark questions to test Hybrid RAG with answer keys. |

---

## ⚡ How to Ingest All Test Data into SecondSelf

You can automatically ingest this entire dataset into SecondSelf via the automated test script:

```bash
# Run the automated ingestion and verification runner:
python test_developer_data/quick_ingest_test.py
```

Or ingest items individually through the SecondSelf UI:
- **Upload Files:** Drag & drop any PDF, DOCX, CSV, Image, or WAV file into the **Capture** dropzone.
- **Save Bookmarks:** Paste any URL from `07_web_bookmarks/bookmarks.json` into the **Web Link** capture.
- **Quick Scratchpad:** Copy snippets from `08_quick_scratchpads/` directly into the **Scratchpad** editor.
- **Ask Brain:** Copy any question from `10_ask_brain_prompts/ask_brain_prompts.md` and verify the citations and answer accuracy!
"""
    (BASE_DIR / "README.md").write_text(readme, encoding="utf-8")

    ingest_script = """import sys
import asyncio
from pathlib import Path
from httpx import AsyncClient, ASGITransport

# Add repository root to python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.config import settings
from backend.main import app
from backend.db.database import init_db

DATASET_DIR = Path(__file__).resolve().parent

async def ingest_dataset():
    print("==================================================")
    print("🚀 SecondSelf Developer Test Dataset Ingestion")
    print("==================================================")
    
    settings.ensure_directories()
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        ingested = []

        # 1. Ingest Markdown Notes
        md_dir = DATASET_DIR / "01_markdown_notes"
        for md_file in md_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            title = md_file.stem.replace("_", " ").title()
            res = await client.post("/capture/note", json={"title": title, "content": content})
            if res.status_code == 200:
                data = res.json()
                print(f"✅ [MARKDOWN] Ingested '{title}' (ID: {data['id']})")
                ingested.append(data["id"])

        # 2. Ingest PDFs, DOCX, CSVs, Images, Audio
        file_folders = [
            ("02_pdf_documents", "application/pdf"),
            ("03_word_documents", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("04_csv_data", "text/csv"),
            ("05_images_and_diagrams", "image/png"),
            ("06_audio_voice_memos", "audio/wav"),
        ]

        for folder_name, mime_type in file_folders:
            folder_path = DATASET_DIR / folder_name
            for file_path in folder_path.glob("*.*"):
                if file_path.suffix.lower() in [".pdf", ".docx", ".csv", ".png", ".jpg", ".wav"]:
                    with open(file_path, "rb") as f:
                        files = {"file": (file_path.name, f.read(), mime_type)}
                        res = await client.post("/capture/upload", files=files)
                        if res.status_code == 200:
                            data = res.json()
                            print(f"✅ [{folder_name.upper()}] Uploaded '{file_path.name}' (ID: {data['id']})")
                            ingested.append(data["id"])

        # 3. Ingest Web Bookmarks
        import json
        bm_file = DATASET_DIR / "07_web_bookmarks" / "bookmarks.json"
        if bm_file.exists():
            bookmarks = json.loads(bm_file.read_text(encoding="utf-8"))
            for bm in bookmarks[:3]: # Ingest top 3 web bookmarks
                res = await client.post("/capture/link", json={"url": bm["url"], "title": bm["title"]})
                if res.status_code == 200:
                    data = res.json()
                    print(f"✅ [BOOKMARK] Ingested '{bm['title']}' (ID: {data['id']})")
                    ingested.append(data["id"])

        print("\\n--------------------------------------------------")
        print(f"🎉 Total Items Ingested: {len(ingested)}")
        print("⚡ Triggering PARA Batch Classification...")
        await client.post("/classify/batch")
        
        print("🔗 Triggering Semantic Vector Indexing & Linking...")
        await client.post("/link/all")

        print("==================================================")
        print("✨ SecondSelf is fully seeded with developer data!")
        print("👉 Open the UI or run 'Ask Brain' queries now.")
        print("==================================================")

if __name__ == "__main__":
    asyncio.run(ingest_dataset())
"""
    (BASE_DIR / "quick_ingest_test.py").write_text(ingest_script, encoding="utf-8")
    print("Master README and ingestion script generated.")

if __name__ == "__main__":
    ensure_dirs()
    generate_markdown_notes()
    generate_pdf_documents()
    generate_word_documents()
    generate_csv_data()
    generate_images()
    generate_audio_memos()
    generate_web_bookmarks()
    generate_quick_scratchpads()
    generate_voice_inputs_and_prompts()
    generate_ask_brain_prompts()
    generate_master_readme_and_loader()
    print("All test developer datasets generated successfully in test_developer_data!")
