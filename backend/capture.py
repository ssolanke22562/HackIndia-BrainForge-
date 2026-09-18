import os
import json
import uuid
import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import aiofiles
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.database import get_db, async_session_maker
from backend.db.models import Note
from backend.parsers import detect_source_type, parse_item, CaptureItem
from backend.parsers.pdf_parser import EncryptedFileError
from backend.parsers.docx_parser import CorruptedDocxError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/capture", tags=["Capture & Ingestion"])

# Request & Response Schemas
class LinkCaptureRequest(BaseModel):
    url: str
    title: Optional[str] = None

class NoteCaptureRequest(BaseModel):
    content: str
    title: Optional[str] = None

class CaptureResponse(BaseModel):
    id: str
    status: str  # "captured", "DUPLICATE_IDENTIFIED", "parse_failed"
    source_type: str
    title: str
    sha256_hash: Optional[str] = None
    extracted_snippet: str
    message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

def compute_sha256(content: bytes) -> str:
    """Compute SHA-256 fingerprint for duplicate detection."""
    return hashlib.sha256(content).hexdigest()

async def find_duplicate_note(db: AsyncSession, sha256_hash: str) -> Optional[Note]:
    """Check database for existing note with identical SHA-256 hash."""
    stmt = select(Note).where(Note.sha256_hash == sha256_hash)
    result = await db.execute(stmt)
    return result.scalars().first()

@router.post("/upload", response_model=CaptureResponse)
async def capture_file_upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest multi-modal file (PDF, DOCX, Image, Audio, CSV/XLSX) with two-phase raw stashing
    and SHA-256 deduplication.
    """
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )

    file_name = file.filename or "uploaded_file"
    ext = Path(file_name).suffix.lower()
    source_type = detect_source_type(file_name)

    if source_type == "unknown":
        # Stash in quarantine
        quarantine_id = str(uuid.uuid4())
        quarantine_file = settings.raw_path / "quarantine" / f"{quarantine_id}{ext}"
        async with aiofiles.open(quarantine_file, "wb") as f:
            await f.write(raw_bytes)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file format '{ext}'. File quarantined. Supported formats: PDF, DOCX, PNG/JPG, MP3/WAV, CSV/XLSX, TXT/MD."
        )

    # 1. Deduplication via SHA-256
    sha256_hash = compute_sha256(raw_bytes)
    existing_note = await find_duplicate_note(db, sha256_hash)
    if existing_note:
        logger.info(f"Duplicate file identified for hash {sha256_hash}: Note {existing_note.id}")
        return CaptureResponse(
            id=existing_note.id,
            status="DUPLICATE_IDENTIFIED",
            source_type=existing_note.source_type,
            title=existing_note.title,
            sha256_hash=sha256_hash,
            extracted_snippet=(existing_note.summary or existing_note.title or "")[:200],
            message=f"File already exists in second brain as '{existing_note.title}'",
            metadata={"existing_note_id": existing_note.id}
        )

    # 2. Two-Phase Raw Storage
    note_id = str(uuid.uuid4())
    raw_file_path = settings.raw_path / f"{note_id}{ext}"
    manifest_file_path = settings.raw_path / f"{note_id}.json"

    try:
        async with aiofiles.open(raw_file_path, "wb") as f:
            await f.write(raw_bytes)

        manifest_data = {
            "id": note_id,
            "original_filename": file_name,
            "source_type": source_type,
            "sha256_hash": sha256_hash,
            "size_bytes": len(raw_bytes),
            "created_at": settings.APP_NAME
        }
        async with aiofiles.open(manifest_file_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(manifest_data, indent=2))
    except Exception as e:
        logger.error(f"Failed to persist raw file for note {note_id}: {e}")
        # Clean up partial raw file
        if raw_file_path.exists():
            raw_file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Raw storage write failure: {e}"
        )

    # 3. Parser Matrix Execution
    try:
        capture_item = await parse_item(
            item_id=note_id,
            source_type=source_type,
            file_path=raw_file_path,
            custom_title=Path(file_name).stem.replace("_", " ").replace("-", " ").title()
        )
    except EncryptedFileError as e:
        raw_file_path.unlink(missing_ok=True)
        manifest_file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except CorruptedDocxError as e:
        logger.error(f"Docx error: {e}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        logger.error(f"Extraction failed for {file_name}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Parsing error: {e}")

    # 4. Insert Note into SQLite & FTS5
    new_note = Note(
        id=note_id,
        source_type=source_type,
        raw_path=str(raw_file_path),
        title=capture_item.title,
        sha256_hash=sha256_hash,
        summary=capture_item.extracted_text[:300].replace("\n", " "),
        status="captured",
        tags_json="[]"
    )
    db.add(new_note)
    await db.commit()
    await db.refresh(new_note)

    # Insert into FTS5 for instant search
    try:
        await db.execute(
            text(
                "INSERT INTO notes_fts (note_id, title, summary, extracted_text) "
                "VALUES (:id, :title, :summary, :text)"
            ),
            {
                "id": note_id,
                "title": capture_item.title,
                "summary": new_note.summary,
                "text": capture_item.extracted_text
            }
        )
        await db.commit()
    except Exception as fts_err:
        logger.warning(f"Failed to index note {note_id} into FTS5: {fts_err}")

    logger.info(f"Successfully ingested {source_type} Note '{capture_item.title}' (ID: {note_id})")

    return CaptureResponse(
        id=note_id,
        status="captured",
        source_type=source_type,
        title=capture_item.title,
        sha256_hash=sha256_hash,
        extracted_snippet=capture_item.extracted_text[:250],
        message="Successfully ingested into second brain raw store",
        metadata=capture_item.metadata
    )

@router.post("/link", response_model=CaptureResponse)
async def capture_link(
    payload: LinkCaptureRequest,
    db: AsyncSession = Depends(get_db)
):
    """Ingest web URL or bookmark, extracting readability markdown with 8s timeout."""
    url = payload.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty.")

    sha256_hash = compute_sha256(url.encode("utf-8"))
    existing_note = await find_duplicate_note(db, sha256_hash)
    if existing_note:
        return CaptureResponse(
            id=existing_note.id,
            status="DUPLICATE_IDENTIFIED",
            source_type="link",
            title=existing_note.title,
            sha256_hash=sha256_hash,
            extracted_snippet=(existing_note.summary or "")[:200],
            message="URL bookmark already exists in second brain"
        )

    note_id = str(uuid.uuid4())
    try:
        capture_item = await parse_item(
            item_id=note_id,
            source_type="link",
            raw_text_content=url,
            custom_title=payload.title
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Web content extraction failed: {e}")

    # Write raw json manifest
    manifest_path = settings.raw_path / f"{note_id}.json"
    manifest_data = {
        "id": note_id,
        "url": url,
        "source_type": "link",
        "sha256_hash": sha256_hash,
        "title": capture_item.title
    }
    async with aiofiles.open(manifest_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(manifest_data, indent=2))

    new_note = Note(
        id=note_id,
        source_type="link",
        raw_path=str(manifest_path),
        title=capture_item.title,
        sha256_hash=sha256_hash,
        summary=capture_item.extracted_text[:300].replace("\n", " "),
        status="captured",
        tags_json="[]"
    )
    db.add(new_note)
    await db.commit()

    # Index into FTS5
    await db.execute(
        text("INSERT INTO notes_fts (note_id, title, summary, extracted_text) VALUES (:id, :title, :summary, :text)"),
        {"id": note_id, "title": capture_item.title, "summary": new_note.summary, "text": capture_item.extracted_text}
    )
    await db.commit()

    return CaptureResponse(
        id=note_id,
        status="captured",
        source_type="link",
        title=capture_item.title,
        sha256_hash=sha256_hash,
        extracted_snippet=capture_item.extracted_text[:250],
        message="Web article ingested successfully",
        metadata=capture_item.metadata
    )

@router.post("/note", response_model=CaptureResponse)
async def capture_quick_note(
    payload: NoteCaptureRequest,
    db: AsyncSession = Depends(get_db)
):
    """Ingest typed raw text note or scratchpad memo."""
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Note content cannot be empty.")

    sha256_hash = compute_sha256(content.encode("utf-8"))
    existing_note = await find_duplicate_note(db, sha256_hash)
    if existing_note:
        return CaptureResponse(
            id=existing_note.id,
            status="DUPLICATE_IDENTIFIED",
            source_type="note",
            title=existing_note.title,
            sha256_hash=sha256_hash,
            extracted_snippet=(existing_note.summary or "")[:200],
            message="Identical note already exists in second brain"
        )

    note_id = str(uuid.uuid4())
    capture_item = await parse_item(
        item_id=note_id,
        source_type="note",
        raw_text_content=content,
        custom_title=payload.title
    )

    # Persist raw text file & manifest
    raw_file = settings.raw_path / f"{note_id}.md"
    async with aiofiles.open(raw_file, "w", encoding="utf-8") as f:
        await f.write(content)

    new_note = Note(
        id=note_id,
        source_type="note",
        raw_path=str(raw_file),
        title=capture_item.title,
        sha256_hash=sha256_hash,
        summary=content[:300].replace("\n", " "),
        status="captured",
        tags_json="[]"
    )
    db.add(new_note)
    await db.commit()

    # Index into FTS5
    await db.execute(
        text("INSERT INTO notes_fts (note_id, title, summary, extracted_text) VALUES (:id, :title, :summary, :text)"),
        {"id": note_id, "title": capture_item.title, "summary": new_note.summary, "text": content}
    )
    await db.commit()

    return CaptureResponse(
        id=note_id,
        status="captured",
        source_type="note",
        title=capture_item.title,
        sha256_hash=sha256_hash,
        extracted_snippet=content[:250],
        message="Quick note captured successfully",
        metadata=capture_item.metadata
    )

@router.get("", response_model=List[Dict[str, Any]])
async def list_recent_captures(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """List most recently captured notes across all modalities."""
    stmt = select(Note).order_by(Note.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    notes = res.scalars().all()
    
    return [
        {
            "id": n.id,
            "title": n.title,
            "source_type": n.source_type,
            "category": n.category,
            "summary": n.summary,
            "status": n.status,
            "created_at": n.created_at.isoformat() if n.created_at else None
        }
        for n in notes
    ]

@router.get("/{note_id}")
async def get_capture_details(
    note_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve detailed capture record and raw manifest information."""
    stmt = select(Note).where(Note.id == note_id)
    res = await db.execute(stmt)
    note = res.scalars().first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    manifest = {}
    manifest_file = settings.raw_path / f"{note_id}.json"
    if manifest_file.exists():
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            pass

    return {
        "id": note.id,
        "title": note.title,
        "source_type": note.source_type,
        "category": note.category,
        "summary": note.summary,
        "raw_path": note.raw_path,
        "sha256_hash": note.sha256_hash,
        "status": note.status,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "manifest": manifest
    }
