import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, func

from backend.config import settings
from backend.db.database import init_db, close_db, async_session_maker
from backend.db.models import Note, Link
from backend.db.vector_store import vector_store
from backend.capture import router as capture_router
from backend.classify import router as classify_router
from backend.link import router as link_router
from backend.build_graph import router as graph_router
from backend.ask import router as ask_router
from backend.history import router as history_router
from backend.persona import router as persona_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("secondself")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for handling startup and shutdown events."""
    logger.info("Starting SecondSelf API Engine...")
    settings.ensure_directories()
    
    # 1. Initialize SQLite database & FTS5
    await init_db()
    
    # 2. Vector Store status check
    logger.info(f"Vector Store initialized. Total indexed vectors: {vector_store.count()}")
    
    # 3. Check if DB is empty and auto-seed initial knowledge base
    async with async_session_maker() as session:
        try:
            count_res = await session.execute(select(func.count(Note.id)))
            current_count = count_res.scalar() or 0
            if current_count == 0:
                logger.info("Empty database detected. Auto-seeding knowledge base in background...")
                import asyncio
                from backend.seed_demo_data import seed_knowledge_base
                asyncio.create_task(seed_knowledge_base())
        except Exception as seed_check_err:
            logger.warning(f"Startup seed check warning: {seed_check_err}")

    yield
    
    # Shutdown
    logger.info("Shutting down SecondSelf API Engine...")
    vector_store.save()
    await close_db()
    logger.info("Shutdown complete.")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="SecondSelf: Multi-Modal AI Second Brain & Knowledge Graph Platform",
    lifespan=lifespan
)

# CORS Middleware: Universal cross-origin support for all deployment domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# Mount Routers
app.include_router(capture_router)
app.include_router(classify_router)
app.include_router(link_router)
app.include_router(graph_router)
app.include_router(ask_router)
app.include_router(history_router)
app.include_router(persona_router)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "An internal server error occurred",
            "detail": str(exc) if settings.DEBUG else None
        }
    )

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint returning system status and component metrics."""
    notes_count = 0
    links_count = 0
    
    try:
        async with async_session_maker() as session:
            note_res = await session.execute(select(func.count(Note.id)))
            notes_count = note_res.scalar() or 0
            link_res = await session.execute(select(func.count(Link.id)))
            links_count = link_res.scalar() or 0
    except Exception as e:
        logger.warning(f"Could not retrieve DB counts for health probe: {e}")

    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "connected",
        "vector_store": {
            "ready": True,
            "vectors_indexed": vector_store.count(),
            "dimension": vector_store.dimension
        },
        "stats": {
            "notes_count": notes_count,
            "links_count": links_count
        }
    }

@app.post("/seed", tags=["System"])
async def trigger_seed():
    """Trigger on-demand knowledge base seeding."""
    import asyncio
    from backend.seed_demo_data import seed_knowledge_base
    asyncio.create_task(seed_knowledge_base())
    return {
        "status": "success",
        "message": "Seeding task started in background."
    }

# Mount Static Files for Production Bundle if available
dist_dir = settings.BASE_DIR / "frontend" / "dist"
if dist_dir.exists():
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

    @app.get("/{full_path:path}", tags=["Frontend"])
    async def serve_frontend(full_path: str):
        file_path = dist_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_dir / "index.html")
else:
    @app.get("/", tags=["System"])
    async def root():
        return {
            "message": "SecondSelf API is running. Access OpenAPI docs at /docs",
            "status": "online",
            "version": settings.APP_VERSION
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
