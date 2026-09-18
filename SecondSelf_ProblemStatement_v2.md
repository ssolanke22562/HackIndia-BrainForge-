# Project: SecondSelf — Your Personal AI Second Brain
### (Web App Edition — National Hackathon Build)

## ProblemStatement.md

Every notes app fails the same way: you capture hundreds of notes, bookmarks, PDFs, and ideas — and then you never find them again. Information goes in, but nothing comes back out. Notes sit in folders nobody re-reads. Bookmarks pile up unread. Knowledge doesn't compound.

**Goal:** Build an end-to-end system where you can capture anything (a note, a link, or *any file* — PDF, DOCX, image, audio, spreadsheet), have AI automatically classify and file it, auto-link it to related knowledge, render it as a live interactive graph you can explore, ask it any question in plain English and get an answer synthesized from your own accumulated knowledge, and revisit every past conversation later. Then deploy it as a real, polished web application anyone can open.

Not a notes app. Not a chatbot. A brain that organizes itself, remembers what you asked it, and answers for you.

---

## Final System (what you're building over 4 weeks)

```
Capture any note / link / file (any format)
         ↓
AI classifies & files it (PARA method)
         ↓
AI auto-links it to related knowledge (embeddings)
         ↓
Everything renders as a live, interactive, hoverable graph
         ↓
Ask it anything in plain English → answer pulled from YOUR notes
         ↓
Every Q&A session is saved → revisit past conversations anytime
         ↓
Deployed as a full web app (custom UI, not a Streamlit demo) on a public URL
```

---

## What Changed From the Original Plan

| Area | Before | Now |
|---|---|---|
| **Frontend** | Streamlit app | A properly designed web app — React (Vite) or Next.js frontend + FastAPI backend, with real UI/UX (layout, navigation, theming, responsive design) |
| **File ingestion** | Text/link capture only | Every content type the system is fed gets a dedicated parser — PDF, DOCX, TXT/MD, images (OCR), audio (transcription), spreadsheets/CSV, and raw links |
| **RAG memory** | Stateless — each question answered in isolation | Every question + retrieved context + answer is persisted; a "History" view lets you reopen and re-read any past chat session |

---

## Week-by-Week Problem Statements

Each week is a self-contained problem. Build it, test it on real data (your own notes — not test data), and each week's output becomes the next week's input.

### Week 1 — The Archivist: "Capture Everything, in Any Format, Lose Nothing"

**Problem**
You have no single place to put things, and what you do capture usually isn't just plain text — it's PDFs, screenshots, voice memos, spreadsheets, and links. Build the foundation: one entry point (API + simple upload UI) that captures anything, in whatever format it arrives, into one place.

**Build**
1. Set up the project structure from scratch:
   - `raw/` — where every raw capture lands (original file + extracted text + metadata)
   - `wiki/` — (used later) organized, linked notes
   - `backend/` — FastAPI service exposing capture endpoints
2. Write a capture pipeline that accepts:
   - Plain notes (typed text)
   - Links (auto-fetch + extract page content)
   - PDFs (text extraction)
   - DOCX files (text extraction)
   - Images (OCR to pull out any text, plus a caption/description)
   - Audio files (speech-to-text transcription)
   - Spreadsheets/CSV (structured row/column summary)
3. Every capture — regardless of source format — is normalized into the same internal record:
   - a timestamp
   - a unique ID
   - the source type (note / link / pdf / docx / image / audio / csv)
   - the raw file (stored as-is)
   - the extracted plain-text content (what the AI will actually reason over)
4. Build a minimal upload UI (drag-and-drop file, paste a link, or type a note) that hits the capture API.
5. Test it on 10+ real pieces of your own scattered information, across at least 3 different formats.

**Deliverable ("Ship the Capture Pipeline")**
- A working capture API + upload UI — one flow saves anything (note, link, or any supported file type) to `raw/` with timestamp + unique ID + extracted text.
- Your `raw/` folder populated with 10+ real captured items spanning multiple formats (not test data).
- 🏅 Badge: **The Archivist**

**Acceptance Criteria**
- [ ] `raw/`, `wiki/`, and `backend/` structure exists
- [ ] Capture works for a note, a link, AND at least 3 file types (e.g. PDF, image, audio)
- [ ] Every capture is normalized to timestamp + unique ID + source type + extracted text
- [ ] 10+ real items captured across multiple formats
- [ ] A basic upload UI exists (not just curl/Postman)

---

### Week 2 — The Librarian: "Teach AI to Organize For You"

**Problem**
A pile of raw captures — of mixed formats — is still a mess. Manual tagging never happens. Make the AI do the filing, regardless of whether the source was a PDF, a voice note, or a link, and make it notice when two notes are about the same thing and link them automatically.

**Build**

**2.1 — Auto-Classify (The Sorting Hat)**
- Write a function that sends any raw capture's *extracted text* (whatever the original format was) to a free LLM (Groq / Llama 3) and gets back:
  - a category (using the PARA framework: Projects, Areas, Resources, Archives)
  - tags
  - a one-line summary
- Run it across last week's real captures — including the PDFs, images, and audio — and watch them organize themselves the same way regardless of source format.

**2.2 — Auto-Link Related Notes (Connect the Dots)**
- Compute embeddings for each note's extracted text (sentence-transformers, local + free).
- Compare each new capture against existing notes in `wiki/`.
- When content is related (similarity above a threshold), auto-insert a link between them.
- No manual tagging — the system notices relationships on its own, across formats (e.g. a PDF and a voice memo about the same topic get linked).

**Deliverable ("Ship the Self-Organizing Wiki")**
- A pipeline that auto-classifies raw captures (any format) with PARA and auto-links related notes.
- Run on 15+ real items → an organized `wiki/` folder with linked notes.
- 🏅 Badge: **The Librarian**

**Acceptance Criteria**
- [ ] Any raw capture, of any supported format → category + tags + summary automatically
- [ ] PARA categorization working
- [ ] Embeddings computed per note
- [ ] Related notes auto-linked across formats (no manual tagging)
- [ ] Runs on 15+ real items → organized `wiki/`

---

### Week 3 — The Cartographer: "Visualize the Brain"

**Problem**
Your knowledge is now organized and linked — but you can't see it. Turn the wiki into something you can actually look at, explore, and watch think, inside the real web app (not a script or a demo page).

**Build**

**3.1 — Graph Data Model (Give It a Shape)**
- Write a script/endpoint that reads every note and its links.
- Build a nodes-and-edges representation in memory:
  - every note → a node (with its source type — note/pdf/image/audio/csv — shown visually, e.g. different icons/colors per type)
  - every relationship/link → an edge
- Export/serve it as clean JSON via the FastAPI backend.

**3.2 — Interactive Graph (The Brain Comes Alive)**
- Use a JS graph library (vis-network or Cytoscape.js) inside the React/Next.js frontend to render:
  - notes as nodes (that pulse / are visually alive, styled per source type)
  - links as edges
  - hover popups that reveal each note's content, source format, and a thumbnail/preview where relevant (e.g. the original image or a snippet of the PDF)
  - drag-to-explore and zoom
  - a proper layout inside the app's navigation (not a standalone page)
- A force-directed graph of your own knowledge, fully integrated into the app's UI.

**Deliverable ("Ship the Living Brain")**
- Your wiki converted to a graph and rendered as an interactive visual brain (hover, drag, zoom) inside the real web app, built from your real notes across all captured formats.
- 🏅 Badge: **The Cartographer**

**Acceptance Criteria**
- [ ] Backend endpoint builds nodes + edges from notes and serves clean JSON
- [ ] Interactive force-directed graph renders from that JSON, inside the app's UI
- [ ] Hover reveals note content and source format
- [ ] Drag + zoom work
- [ ] Built from your real notes across multiple formats, not dummy data

---

### Week 4 — The Oracle: "Ask It Anything, Remember Every Conversation, Ship It Public"

**Problem**
A visual brain is beautiful, but the real payoff is answers — and being able to come back to them. Wire up natural-language search over everything you know, save every conversation so nothing is lost, and package the whole thing into one deployable, well-designed product.

**Build**

**4.1 — Ask Your Brain (Natural Language Search / RAG)**
- Build a single `ask()` function/endpoint that combines:
  - the embeddings (find relevant notes to a question, across all formats)
  - the wiki (the source content)
  - an LLM (synthesize an answer from retrieved notes, citing which notes it used)
- This is retrieval-augmented Q&A over your own knowledge.
- Test against real questions about your own captured notes, including questions that require pulling from a PDF, an image, and an audio transcript together.

**4.2 — Chat History Storage (Remember Every Session)**
- Persist every Q&A interaction to a database (SQLite is fine for a hackathon):
  - session ID, timestamp, the question asked, the notes retrieved (with IDs), and the final answer
- Group interactions into "conversations"/sessions so a user can:
  - see a list of past chat sessions
  - reopen one and read the full back-and-forth
  - continue an old session with a new follow-up question (using the saved context)
- Expose this via a `/history` endpoint and a **History** page in the web app's navigation, alongside the graph and the search bar.

**4.3 — UI, Deployment, Public URL (Give It a Real Face)**
- Assemble everything into one polished web app (React/Next.js frontend + FastAPI backend), with:
  - a proper navigation shell (Capture / Graph / Ask / History)
  - the interactive brain graph
  - the ask-anything search/chat interface
  - the chat history browser
  - responsive, clean, intentional visual design — not default component styling
- Deploy frontend + backend to a free platform (e.g. Vercel/Netlify for frontend, Render/Railway/HF Spaces for backend), or as a single containerized deployment.
- Get a public URL anyone can open.

**Deliverable ("Ship SecondSelf" — the final product)**
Deploy the complete system — capture (any format) → auto-classify → auto-link → live interactive graph → ask-anything search → persisted chat history — all wired into one designed web app with a public URL.
- 🏅 Badge: **The Oracle**

**Acceptance Criteria**
- [ ] `ask()` returns answers synthesized from your own notes (retrieval + LLM), across formats
- [ ] Every Q&A session is saved and retrievable later via a History view
- [ ] One web app contains the graph, the search/chat interface, and the history browser
- [ ] Deployed live with a public URL
- [ ] Full pipeline works end to end in the deployed app: capture (any format) → classify → link → graph → ask → history

---

## Final Deliverables (whole project)
- [ ] Public GitHub repo with a clean README + setup instructions
- [ ] Live deployed URL — interactive graph + ask-your-brain chat + chat history, all working
- [ ] End-to-end flow verified: capture (any format) → classify → link → graph → ask → save to history
- [ ] All 4 weekly milestones complete (Capture Pipeline, Self-Organizing Wiki, Living Brain, SecondSelf Web App deployment)
- [ ] Clean, intentional UI — not a default Streamlit look

---

## Suggested Repo Structure

```
secondself/
├── backend/
│   ├── main.py              # FastAPI app entrypoint
│   ├── capture.py           # Week 1: multi-format capture + text extraction
│   ├── parsers/             # Week 1: per-format extractors
│   │   ├── pdf_parser.py
│   │   ├── docx_parser.py
│   │   ├── image_ocr.py
│   │   ├── audio_transcribe.py
│   │   └── csv_parser.py
│   ├── classify.py          # Week 2: PARA classification via LLM
│   ├── link.py               # Week 2: embeddings + auto-linking
│   ├── build_graph.py       # Week 3: nodes/edges → graph JSON
│   ├── ask.py                # Week 4: retrieval + LLM answer (RAG)
│   ├── history.py            # Week 4: chat session persistence (SQLite)
│   └── db/
│       └── secondself.db
├── frontend/                 # React (Vite) or Next.js app
│   ├── src/
│   │   ├── pages/            # Capture, Graph, Ask, History views
│   │   ├── components/       # Graph renderer, chat UI, upload widget
│   │   └── styles/
│   └── package.json
├── raw/                       # Week 1: raw captures (original file + metadata)
├── wiki/                      # Week 2: classified + auto-linked notes
├── graph.json                 # Week 3: exported graph data
├── requirements.txt
└── README.md
```

---

## Suggested Build Order in Cursor

1. Scaffold repo structure (`backend/`, `frontend/`) + `requirements.txt` + frontend `package.json`
2. `backend/capture.py` + `parsers/` → test capture on real items across multiple formats (Week 1)
3. `backend/classify.py` → PARA categories/tags/summary (Week 2.1)
4. `backend/link.py` → embeddings + similarity auto-linking (Week 2.2)
5. `backend/build_graph.py` → JSON nodes/edges (Week 3.1)
6. `frontend/` graph view with vis-network/Cytoscape, wired to the backend (Week 3.2)
7. `backend/ask.py` → retrieval-augmented Q&A (Week 4.1)
8. `backend/history.py` + SQLite → persist and serve chat sessions (Week 4.2)
9. `frontend/` — build out Capture / Graph / Ask / History pages with real design (Week 4.3)
10. Deploy frontend + backend → public URL
11. Write README, push to GitHub

---

## AI Tools
- https://cursor.com/download
- https://antigravity.google/product/antigravity-ide
- https://qoder.com/
- https://devin.ai/download/
- VS Code + Claude

---

## Context Docs
- `problemStatement.md` → the problem being solved (this file)
- `architecture.md` → HOW the project will be built (backend + frontend + data flow)
- `implementation-plan.md` → phase-wise implementation plan
  - Phase 0 → setup
  - Phase 1–5 → implement project code
  - Phase 6–7 → local testing
  - Phase 8–9 → deploy the project + final round of testing
- `edge-case.md` → corner scenarios and edge cases (e.g. corrupted file upload, OCR failure, empty audio, huge PDF, duplicate captures)

---

## Prompts
1. Generate a detailed architecture for making this project using `@PROBLEM_STATEMENT.md`
2. Save the architecture into `architecture.md`
3. Generate a phase-wise `Implementation-plan.md` using `@architecture.md` and `@PROBLEM_STATEMENT.md`
4. Generate an `edge-case.md` for storing all corner scenarios and edge cases using `@docs/architecture.md` and `@docs/Implementation-plan.md`
5. Implement Phase 0 as per `@docs/Implementation-plan.md`
