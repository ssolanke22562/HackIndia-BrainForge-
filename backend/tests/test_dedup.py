import io
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, func

from backend.main import app
from backend.db.database import init_db, async_session_maker
from backend.db.models import Note

@pytest.mark.asyncio
async def test_deduplication_for_notes():
    """Verify that uploading the identical typed note triggers SHA-256 duplicate detection."""
    await init_db()
    transport = ASGITransport(app=app)
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_id = str(uuid.uuid4())
        payload = {
            "content": f"Unique Memo {unique_id}: Evaluating Reciprocal Rank Fusion parameters for SecondSelf RAG.",
            "title": f"RRF Tuning Experiment {unique_id}"
        }
        
        # 1. First capture
        res1 = await client.post("/capture/note", json=payload)
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["status"] == "captured"
        note_id1 = data1["id"]
        sha1 = data1["sha256_hash"]
        
        # 2. Duplicate capture
        res2 = await client.post("/capture/note", json=payload)
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["status"] == "DUPLICATE_IDENTIFIED"
        assert data2["id"] == note_id1
        assert data2["sha256_hash"] == sha1

@pytest.mark.asyncio
async def test_deduplication_for_file_uploads():
    """Verify that uploading an identical binary file twice skips re-processing."""
    await init_db()
    transport = ASGITransport(app=app)
    
    unique_marker = str(uuid.uuid4())
    file_bytes = f"Col1,Col2,Col3\n1,2,{unique_marker}\n4,5,6\n7,8,9\n".encode("utf-8")
    
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. First file upload
        files = {"file": ("data_matrix.csv", io.BytesIO(file_bytes), "text/csv")}
        res1 = await client.post("/capture/upload", files=files)
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["status"] == "captured"
        first_note_id = data1["id"]
        sha1 = data1["sha256_hash"]
        
        # 2. Second upload with same bytes
        files_dup = {"file": ("data_matrix_renamed.csv", io.BytesIO(file_bytes), "text/csv")}
        res2 = await client.post("/capture/upload", files=files_dup)
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["status"] == "DUPLICATE_IDENTIFIED"
        assert data2["id"] == first_note_id
        assert data2["sha256_hash"] == sha1
        
        # Verify in DB that only 1 record exists with this hash
        async with async_session_maker() as session:
            stmt = select(func.count(Note.id)).where(Note.sha256_hash == sha1)
            count = (await session.execute(stmt)).scalar()
            assert count == 1
