# SecondSelf - Your Personal AI Second Brain

**National Hackathon PRD v3: Multi-Modal RAG + Knowledge Graph + Persistent Memory**[cite: 4]

---

## 1. One-line thesis
SecondSelf turns scattered notes, files, links, images, and voice memos into a self-organizing, queryable, visual second brain that answers questions from your own knowledge and remembers every conversation.[cite: 4]

---

## 2. Problem
Every notes app fails the same way: capture is easy, retrieval is broken[cite: 4]. You save PDFs, screenshots, voice memos, spreadsheets, and links — then never find them again[cite: 4]. Information goes in, but knowledge never compounds[cite: 4].

---

## 3. Insight
The bottleneck is not capture[cite: 4]. It is normalization + semantic linking + memory[cite: 4]. If every capture becomes the same internal record, AI can classify it, embed it, link it, graph it, and answer from it across formats[cite: 4].

---

## 4. Solution
A full-stack web app with six core capabilities:[cite: 4]
1. **Capture anything** — note, link, PDF, DOCX, TXT/MD, image, audio, CSV/XLSX.[cite: 4]
2. **Normalize every capture** — original file + extracted text + metadata + timestamp + unique ID.[cite: 4]
3. **Auto-classify** — PARA category, tags, one-line summary, confidence.[cite: 4]
4. **Auto-link** — embeddings + cosine similarity → related notes linked across formats.[cite: 4]
5. **Visualize** — live interactive force-directed graph with node types, hover previews, drag, zoom.[cite: 4]
6. **Ask + remember** — RAG-based Q&A with citations; every session persisted and reopenable.[cite: 4]

---

## 5. Why this is technically hard
* **Multi-modal ingestion:** PDF text, DOCX, OCR, ASR, CSV summarization, link extraction.[cite: 4]
* **Cross-format semantic linking:** a PDF, an image, and an audio transcript must land in the same embedding space.[cite: 4]
* **Long-document retrieval:** chunking, overlap, parent-document retrieval, citation mapping.[cite: 4]
* **RAG faithfulness:** answers must cite retrieved notes, not hallucinate.[cite: 4]
* **Persistent conversational memory:** sessions, retrieved context, follow-up context.[cite: 4]
* **Graph UX:** real-time rendering from backend JSON with meaningful node/edge semantics.[cite: 4]

---

## 6. System architecture

```text
Frontend: React/Next.js + vis-network/Cytoscape.js
Capture | Graph | Ask | History
       ↓ REST/JSON
Backend: FastAPI
/capture /classify /link /graph /ask /history
       ↓
Ingestion Layer
parsers/: pdf, docx, image_ocr, audio_transcribe, csv, link
       ↓
Storage Layer
raw/            -> original file + extracted text + metadata
wiki/           -> classified + linked notes
SQLite          -> notes, links, embeddings metadata, chat sessions
Vector Index    -> FAISS/Chroma + SQLite FTS5 for hybrid search
       ↓
AI Layer
LLM:            -> Groq/Llama 3 + fallback Gemini/OpenAI
Embeddings:     -> sentence-transformers (all-MiniLM-L6-v2 or bge-small)
OCR:            -> Tesseract/PaddleOCR
ASR:            -> faster-whisper/Whisper.cpp
```[cite: 4]

---

## 7. AI/ML pipeline details

### 7.1 Capture + extraction
* **PDF:** PyMuPDF; fallback OCR for scanned PDFs.[cite: 4]
* **DOCX:** python-docx.[cite: 4]
* **Image:** OCR + optional vision caption/description.[cite: 4]
* **Audio:** faster-whisper transcription.[cite: 4]
* **CSV/XLSX:** pandas/openpyxl → schema + row/column summary.[cite: 4]
* **Link:** trafilatura/BeautifulSoup → main content + title.[cite: 4]
* **Every item normalized to:**[cite: 4]

```json
{
  "id": "uuid",
  "timestamp": "ISO",
  "source_type": "pdf|docx|image|audio|csv|link|note",
  "raw_path": "raw/...",
  "extracted_text": "...",
  "metadata": {}
}
```[cite: 4]

### 7.2 Classification
Send extracted text to LLM with strict JSON schema:[cite: 4]
```json
{
  "category": "Projects | Areas | Resources | Archives",
  "tags": ["..."],
  "summary": "one line",
  "confidence": 0.0
}
```[cite: 4]
*Fallback: keyword/regex classifier if LLM fails.*[cite: 4]

### 7.3 Embeddings + auto-linking
* Chunk long text: 500-800 tokens, 15% overlap.[cite: 4]
* Embed chunks with sentence-transformers.[cite: 4]
* Store in FAISS/Chroma.[cite: 4]
* Link new note to existing notes if cosine similarity > threshold.[cite: 4]
* Avoid hub explosion: cap top-k links per note, dedupe edges.[cite: 4]

### 7.4 RAG Q&A
* Hybrid retrieval: BM25/FTS5 + vector search.[cite: 4]
* Optional reranker: cross-encoder or LLM rerank.[cite: 4]
* LLM prompt: "Answer only from these notes. Cite note IDs."[cite: 4]
* Return: answer + cited notes + retrieved context.[cite: 4]

### 7.5 Chat history
* **SQLite tables:**[cite: 4]
  * `sessions (id, title, created_at, updated_at)`[cite: 4]
  * `messages (id, session_id, role, content, created_at)`[cite: 4]
  * `retrievals (id, message_id, note_id, chunk_id, score)`[cite: 4]
* **Endpoints:**[cite: 4]
  * `POST /ask`[cite: 4]
  * `GET /history`[cite: 4]
  * `GET /history/{session_id}`[cite: 4]
  * `POST /history/{session_id}/continue`[cite: 4]

---

## 8. Feature breakdown

| Feature | Must-have | Technical proof |
| :--- | :--- | :--- |
| **Capture** | Note, link, PDF, image, audio, CSV | Multi-format parsers |
| **Normalize** | Timestamp, UUID, source type, raw file, text | Unified schema |
| **Classify** | PARA + tags + summary | Structured LLM output |
| **Link** | Auto-link related notes | Embeddings + similarity |
| **Graph** | Interactive force graph | vis-network/Cytoscape |
| **Ask** | RAG with citations | Hybrid retrieval + LLM |
| **History** | Save/reopen/continue chats | SQLite session memory |
| **Deploy** | Public URL | Vercel/Netlify + Render/Railway |[cite: 4]

---

## 9. Week-by-week milestones

* **Week 1: The Archivist**[cite: 4]
  * Ship multi-format capture API + upload UI.[cite: 4]
  * *Acceptance:* 10+ real items, 3+ formats, normalized schema.[cite: 4]
* **Week 2: The Librarian**[cite: 4]
  * Ship PARA classification + embeddings + auto-linking.[cite: 4]
  * *Acceptance:* 15+ real items in `wiki/`, cross-format links.[cite: 4]
* **Week 3: The Cartographer**[cite: 4]
  * Ship graph JSON endpoint + interactive graph in app.[cite: 4]
  * *Acceptance:* hover, drag, zoom, source-type styling.[cite: 4]
* **Week 4: The Oracle**[cite: 4]
  * Ship RAG `ask()`, chat history, polished UI, deployment.[cite: 4]
  * *Acceptance:* public URL, cross-modal Q&A, saved sessions.[cite: 4]

---

## 10. Evaluation plan
Judges love measurable AI. Add this:[cite: 4]
* **Extraction accuracy:** 10 files, manual check of extracted text.[cite: 4]
* **Classification:** 30 notes, precision/recall/F1 for PARA.[cite: 4]
* **Retrieval:** 20 Q/A pairs, Recall@5 and MRR.[cite: 4]
* **Answer faithfulness:** LLM-as-judge or manual 1-5 score.[cite: 4]
* **Citation accuracy:** % answers citing correct notes.[cite: 4]
* **Latency:** p95 `/ask` under 8s.[cite: 4]
* **Cost:** under $0.01/query using free tiers.[cite: 4]
* **Graph:** 100+ nodes load under 2s.[cite: 4]

---

## 11. 3-minute demo script
1. **0:00-0:30:** "I have 200 scattered notes. Watch."[cite: 4]
2. **0:30-1:00:** Drag PDF, upload voice memo, paste link. They auto-appear.[cite: 4]
3. **1:00-1:30:** Show graph: nodes colored by type, hover reveals content.[cite: 4]
4. **1:30-2:15:** Ask: "What did I decide about X across my PDF and voice memo?" Answer cites both.[cite: 4]
5. **2:15-2:45:** Open History, reopen past session, continue follow-up.[cite: 4]
6. **2:45-3:00:** Show public URL. "This is SecondSelf."[cite: 4]

---

## 12. Deployment
* **Frontend:** Vercel/Netlify.[cite: 4]
* **Backend:** Render/Railway/HF Spaces.[cite: 4]
* Or single Docker container.[cite: 4]
* Environment variables for API keys.[cite: 4]
* Health endpoint `/health`.[cite: 4]

---

## 13. Risks & mitigations

| Risk | Mitigation |
| :--- | :--- |
| **LLM rate limit** | Model-agnostic fallback |
| **OCR failure** | Manual text fallback + confidence flag |
| **Huge PDF** | Chunking + async processing |
| **Empty audio** | Detect silence, mark failed |
| **Duplicate captures** | Hash raw file + text similarity |
| **Graph too dense** | Top-k links + threshold tuning |
| **Sensitive data** | Local-first, no training, redact logs |[cite: 4]

---

## 14. Final deliverables
* Public GitHub repo with README + setup.[cite: 4]
* Live public URL.[cite: 4]
* End-to-end flow: capture → classify → link → graph → ask → history.[cite: 4]
* All 4 badges: Archivist, Librarian, Cartographer, Oracle.[cite: 4]
* Clean, intentional UI — not default Streamlit.[cite: 4]

---

## 15. Judge-facing one-liner
> "SecondSelf is a multi-modal personal RAG system that ingests any file type, auto-organizes it with LLMs, links it with embeddings, renders it as a live knowledge graph, and answers questions with citations while remembering every conversation."[cite: 4]