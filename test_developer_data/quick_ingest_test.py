import sys
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
    print(">> SecondSelf Developer Test Dataset Ingestion")
    print("==================================================")

    async with AsyncClient(base_url="http://127.0.0.1:8000", timeout=60.0) as client:
        ingested = []

        # 1. Ingest Markdown Notes
        md_dir = DATASET_DIR / "01_markdown_notes"
        for md_file in md_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            title = md_file.stem.replace("_", " ").title()
            res = await client.post("/capture/note", json={"title": title, "content": content})
            if res.status_code == 200:
                data = res.json()
                print(f"[+] [MARKDOWN] Ingested '{title}' (ID: {data['id']})")
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
                            print(f"[+] [{folder_name.upper()}] Uploaded '{file_path.name}' (ID: {data['id']})")
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
                    print(f"[+] [BOOKMARK] Ingested '{bm['title']}' (ID: {data['id']})")
                    ingested.append(data["id"])

        print("\n--------------------------------------------------")
        print(f"Total Items Ingested: {len(ingested)}")
        print(">> Triggering PARA Batch Classification...")
        await client.post("/classify/batch")
        
        print(">> Triggering Semantic Vector Indexing & Linking...")
        await client.post("/link/all")

        print("==================================================")
        print("SecondSelf is fully seeded with developer data!")
        print("==================================================")

if __name__ == "__main__":
    asyncio.run(ingest_dataset())
