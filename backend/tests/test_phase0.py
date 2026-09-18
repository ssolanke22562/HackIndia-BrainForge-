import pytest
import numpy as np
from sqlalchemy import text
from httpx import AsyncClient, ASGITransport

from backend.config import settings
from backend.db.database import init_db, close_db, engine, async_session_maker
from backend.db.models import Note, Chunk, Link, Session, Message, Retrieval
from backend.db.vector_store import VectorStore
from backend.main import app

@pytest.mark.asyncio
async def test_config_and_directories():
    """Verify settings loading and directory creation."""
    assert settings.APP_NAME == "SecondSelf"
    assert settings.EMBEDDING_DIMENSION == 384
    assert settings.COSINE_SIMILARITY_THRESHOLD == 0.70
    assert settings.MAX_LINK_DEGREE == 5
    
    # Verify directories exist
    assert settings.raw_path.exists()
    assert (settings.raw_path / "quarantine").exists()
    assert settings.wiki_path.exists()
    for cat in ["Projects", "Areas", "Resources", "Archives"]:
        assert (settings.wiki_path / cat).exists()
    assert settings.db_path.exists()
    assert settings.vector_path.exists()

@pytest.mark.asyncio
async def test_database_initialization_and_wal():
    """Verify database initialization, WAL journal mode, and table creation."""
    await init_db()
    
    async with engine.connect() as conn:
        res = await conn.execute(text("PRAGMA journal_mode;"))
        mode = res.scalar()
        assert mode.lower() == "wal", f"Expected WAL mode, got {mode}"
        
        # Test FTS5 insertion and query
        await conn.execute(
            text(
                "INSERT INTO notes_fts (note_id, title, summary, extracted_text) "
                "VALUES ('test-1', 'AI Roadmap', 'Executive planning', 'Multi-modal ingestion architecture with FAISS');"
            )
        )
        fts_res = await conn.execute(
            text("SELECT note_id, rank FROM notes_fts WHERE notes_fts MATCH 'FAISS' ORDER BY rank;")
        )
        row = fts_res.fetchone()
        assert row is not None
        assert row[0] == "test-1"

@pytest.mark.asyncio
async def test_vector_store():
    """Verify FAISS vector store operations, cosine similarity, and serialization."""
    test_store = VectorStore(dimension=384, storage_dir=settings.vector_path)
    test_store.reset()
    
    # Create synthetic test vectors
    vec1 = np.random.randn(1, 384).astype(np.float32)
    vec2 = np.random.randn(1, 384).astype(np.float32)
    
    test_store.add_vectors(vec1, ["chunk-uuid-1"])
    test_store.add_vectors(vec2, ["chunk-uuid-2"])
    
    assert test_store.count() == 2
    
    # Query with vec1 - top result must be chunk-uuid-1 with similarity ~ 1.0
    results = test_store.search(vec1, top_k=2)
    assert len(results) == 2
    top_id, top_score = results[0]
    assert top_id == "chunk-uuid-1"
    assert top_score >= 0.99
    
    # Test persistence and re-loading
    test_store.save()
    reloaded_store = VectorStore(dimension=384, storage_dir=settings.vector_path)
    assert reloaded_store.count() == 2
    assert reloaded_store.chunk_id_map == ["chunk-uuid-1", "chunk-uuid-2"]

@pytest.mark.asyncio
async def test_fastapi_health_endpoint():
    """Verify FastAPI application boots and health probe returns expected metadata."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app_name"] == "SecondSelf"
        assert data["database"] == "connected"
        assert "vector_store" in data
        assert "stats" in data
