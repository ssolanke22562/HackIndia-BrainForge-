import os
import io
import wave
import struct
import math
import asyncio
from pathlib import Path
from PIL import Image, ImageDraw
import docx
import pandas as pd
from httpx import AsyncClient, ASGITransport

from backend.config import settings
from backend.main import app
from backend.db.database import init_db

DEMO_KNOWLEDGE_PIECES = [
    {
        "type": "note",
        "title": "SecondSelf Master Product Roadmap",
        "content": """# SecondSelf Master Product Roadmap 2026

## Objective
Build a local-first, multi-modal AI second brain that unifies scattered notes, documents, voice recordings, and bookmarks into a living knowledge graph with hybrid RAG.

## Milestones
- **Q1:** Ingestion Matrix (PDF, DOCX, Image, Audio, CSV, Web, Note) with two-phase raw stashing.
- **Q2:** AI PARA Classification (Projects, Areas, Resources, Archives) via Groq LPUs.
- **Q3:** FAISS dense vector store + SQLite FTS5 BM25 hybrid search via Reciprocal Rank Fusion (RRF).
- **Q4:** Force-directed 60 FPS visual knowledge graph with degree capping."""
    },
    {
        "type": "note",
        "title": "PARA System Implementation Guidelines",
        "content": """# PARA Methodology Implementation

Tiago Forte's PARA framework organizes knowledge by actionability:
1. **Projects:** Series of tasks linked to a specific goal with a deadline (e.g. HackIndia Final Submission).
2. **Areas:** Spheres of activity with a standard to maintain over time (e.g. Health, Finances, System Architecture).
3. **Resources:** Topics or themes of ongoing interest and references (e.g. Python AsyncIO, FAISS Benchmarks, ML Research).
4. **Archives:** Inactive items from the other three categories preserved for historical reference."""
    },
    {
        "type": "note",
        "title": "Vector Embeddings & Cosine Similarity Notes",
        "content": """# Vector Embeddings Architecture

Using sentence-transformers `all-MiniLM-L6-v2` producing 384-dimensional dense vectors.
Similarity metric: Cosine similarity via Inner Product on unit L2-normalized vectors.
Threshold rule: Links between documents are established if Cosine Similarity >= 0.70.
Supernode explosion mitigation: Cap maximum links per note at Top-5 strongest neighbors."""
    },
    {
        "type": "docx",
        "filename": "team_engineering_standards.docx",
        "title": "Engineering Standards & Best Practices",
        "sections": [
            ("Engineering Standards 2026", 1),
            ("Code Quality & Async I/O", 2),
            ("All backend services must use non-blocking async/await with FastAPI and aiosqlite.", 0),
            ("SQLite WAL Configuration", 2),
            ("PRAGMA journal_mode = WAL and busy_timeout = 5000 are strictly required.", 0)
        ],
        "table": [
            ["Standard", "Tool", "Enforcement"],
            ["ORM Schema", "SQLAlchemy 2.0", "Mandatory"],
            ["Type Safety", "Pydantic v2", "Strict"],
            ["Vector Search", "FAISS-CPU", "Normalized L2"]
        ]
    },
    {
        "type": "docx",
        "filename": "quarterly_budget_and_allocations.docx",
        "title": "Quarterly Cloud & Compute Budget",
        "sections": [
            ("Infrastructure Budget Summary", 1),
            ("Resource allocations for AI inference and vector hosting.", 0)
        ],
        "table": [
            ["Item", "Provider", "Estimated Cost"],
            ["Groq LPUs", "Groq Cloud", "$0.00 (Free Tier)"],
            ["Gemini Fallback", "Google AI", "$0.00 (Free Tier)"],
            ["Hosting Server", "Railway/Render", "$5.00/month"]
        ]
    },
    {
        "type": "csv",
        "filename": "model_benchmark_results.csv",
        "data": {
            "Model": ["all-MiniLM-L6-v2", "bge-small-en-v1.5", "text-embedding-3-small"],
            "Dimensions": [384, 384, 1536],
            "Latency_ms": [12.4, 18.2, 85.0],
            "Cost_Per_1M_Tokens": ["$0.00", "$0.00", "$0.02"],
            "Local_Inference": ["Yes", "Yes", "No"]
        }
    },
    {
        "type": "csv",
        "filename": "api_latency_telemetry.csv",
        "data": {
            "Endpoint": ["/capture/upload", "/classify", "/link", "/ask", "/graph"],
            "p50_ms": [45, 180, 25, 420, 15],
            "p95_ms": [110, 350, 60, 780, 35],
            "Success_Rate": ["99.8%", "99.5%", "100%", "99.2%", "100%"]
        }
    },
    {
        "type": "image",
        "filename": "system_architecture_diagram.png",
        "text": "SecondSelf Multi-Modal Architecture: Ingestion -> PARA Classification -> Hybrid RAG -> Force Graph"
    },
    {
        "type": "image",
        "filename": "hybrid_rag_flowchart.png",
        "text": "Hybrid RAG Pipeline: Query -> Dense FAISS (K=8) + Sparse BM25 (K=8) -> RRF Fusion -> Top 5 Cited Chunks"
    },
    {
        "type": "audio",
        "filename": "voice_memo_architecture_sync.wav",
        "duration_sec": 3
    },
    {
        "type": "audio",
        "filename": "standup_notes_voice_memo.wav",
        "duration_sec": 2
    },
    {
        "type": "link",
        "url": "https://fastapi.tiangolo.com",
        "title": "FastAPI Modern High Performance Web Framework"
    }
]

async def seed_knowledge_base():
    """Ingest 10+ real multi-modal knowledge items into SecondSelf raw/ and database."""
    print("Initializing database and directories...")
    settings.ensure_directories()
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        ingested_count = 0

        for item in DEMO_KNOWLEDGE_PIECES:
            item_type = item["type"]
            
            if item_type == "note":
                res = await client.post("/capture/note", json={"content": item["content"], "title": item["title"]})
                data = res.json()
                print(f"[NOTE] Ingested '{item['title']}' -> Note ID: {data['id']} (Status: {data['status']})")
                ingested_count += 1

            elif item_type == "link":
                res = await client.post("/capture/link", json={"url": item["url"], "title": item["title"]})
                data = res.json()
                print(f"[LINK] Ingested '{item['title']}' -> Note ID: {data['id']} (Status: {data['status']})")
                ingested_count += 1

            elif item_type == "docx":
                doc = docx.Document()
                for sec_text, level in item["sections"]:
                    if level > 0:
                        doc.add_heading(sec_text, level=level)
                    else:
                        doc.add_paragraph(sec_text)
                if "table" in item:
                    tbl = doc.add_table(rows=len(item["table"]), cols=len(item["table"][0]))
                    for r_idx, row in enumerate(item["table"]):
                        for c_idx, val in enumerate(row):
                            tbl.cell(r_idx, c_idx).text = val
                
                doc_bytes = io.BytesIO()
                doc.save(doc_bytes)
                doc_bytes.seek(0)
                
                files = {"file": (item["filename"], doc_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
                res = await client.post("/capture/upload", files=files)
                data = res.json()
                print(f"[DOCX] Ingested '{item['filename']}' -> Note ID: {data['id']} (Status: {data['status']})")
                ingested_count += 1

            elif item_type == "csv":
                df = pd.DataFrame(item["data"])
                csv_bytes = io.BytesIO(df.to_csv(index=False).encode("utf-8"))
                files = {"file": (item["filename"], csv_bytes, "text/csv")}
                res = await client.post("/capture/upload", files=files)
                data = res.json()
                print(f"[CSV] Ingested '{item['filename']}' -> Note ID: {data['id']} (Status: {data['status']})")
                ingested_count += 1

            elif item_type == "image":
                img = Image.new("RGB", (600, 200), color=(20, 25, 40))
                draw = ImageDraw.Draw(img)
                draw.text((20, 90), item["text"], fill=(200, 220, 255))
                img_bytes = io.BytesIO()
                img.save(img_bytes, format="PNG")
                img_bytes.seek(0)
                files = {"file": (item["filename"], img_bytes, "image/png")}
                res = await client.post("/capture/upload", files=files)
                data = res.json()
                print(f"[IMAGE] Ingested '{item['filename']}' -> Note ID: {data['id']} (Status: {data['status']})")
                ingested_count += 1

            elif item_type == "audio":
                sample_rate = 16000
                num_samples = sample_rate * item["duration_sec"]
                audio_bytes = io.BytesIO()
                with wave.open(audio_bytes, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    sine_samples = [int(12000 * math.sin(2 * math.pi * 350 * i / sample_rate)) for i in range(num_samples)]
                    wf.writeframes(struct.pack(f"<{num_samples}h", *sine_samples))
                audio_bytes.seek(0)
                files = {"file": (item["filename"], audio_bytes, "audio/wav")}
                res = await client.post("/capture/upload", files=files)
                data = res.json()
                print(f"[AUDIO] Ingested '{item['filename']}' -> Note ID: {data['id']} (Status: {data['status']})")
                ingested_count += 1

        print("\nClassifying all notes via PARA and generating Wiki Vault...")
        await client.post("/classify/batch")
        
        print("Computing FAISS embeddings, chunks, and semantic links...")
        await client.post("/link/all")

        print(f"\nSuccessfully seeded, classified, and linked {ingested_count} multi-modal captures into SecondSelf!")

if __name__ == "__main__":
    asyncio.run(seed_knowledge_base())
