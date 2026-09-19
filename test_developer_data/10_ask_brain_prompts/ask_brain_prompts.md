# Ask Brain: Master Testing & Evaluation Prompts Catalog

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
