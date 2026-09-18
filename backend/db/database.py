import logging
from typing import AsyncGenerator
import aiosqlite
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from backend.config import settings
from backend.db.models import Base

logger = logging.getLogger(__name__)

# Create asynchronous SQLAlchemy engine
engine: AsyncEngine = create_async_engine(
    settings.sqlite_url,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
)

# SQLite Connection PRAGMA hook for WAL and concurrency optimization
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA busy_timeout = 5000;")
    cursor.execute("PRAGMA synchronous = NORMAL;")
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.close()

# Asynchronous session maker
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing an async database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db() -> None:
    """Initialize database tables, PRAGMAs, and FTS5 virtual tables."""
    settings.ensure_directories()
    
    # 1. Create standard SQLAlchemy tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # 2. Create SQLite FTS5 virtual table for BM25 lexical search
        await conn.execute(
            text(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                    note_id UNINDEXED,
                    title,
                    summary,
                    extracted_text,
                    tokenize = 'porter unicode61'
                );
                """
            )
        )
        
        # 3. Verify and log WAL mode status
        result = await conn.execute(text("PRAGMA journal_mode;"))
        mode = result.scalar()
        logger.info(f"SQLite initialized at {settings.db_file_path}. Journal mode: {mode}")

async def close_db() -> None:
    """Safely dispose engine on application shutdown."""
    await engine.dispose()
    logger.info("Database engine connections closed.")
