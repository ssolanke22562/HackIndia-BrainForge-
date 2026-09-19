# 🚀 SecondSelf Real Developer Test Dataset

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
