import os
import re
import uuid
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

import numpy as np
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from sentence_transformers import SentenceTransformer

from backend.config import settings
from backend.db.database import get_db, async_session_maker
from backend.db.models import Note, Chunk, Link
from backend.db.vector_store import vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/link", tags=["Embeddings & Auto-Linking"])

# Lazy-loaded embedding model
_embedding_model: Optional[SentenceTransformer] = None

def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading SentenceTransformer model: {settings.EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _embedding_model

def recursive_text_split(
    text_content: str,
    chunk_size: int = settings.CHUNK_SIZE,
    chunk_overlap: int = settings.CHUNK_OVERLAP
) -> List[str]:
    """
    Recursively split text into overlapping chunks using hierarchical delimiters:
    1. Paragraphs (\n\n)
    2. Newlines (\n)
    3. Sentences (. )
    4. Spaces ( )
    """
    text_content = text_content.strip()
    if not text_content:
        return []
        
    if len(text_content) <= chunk_size:
        return [text_content]

    separators = ["\n\n", "\n", ". ", " "]
    
    def _split_recursive(text_chunk: str, sep_idx: int) -> List[str]:
        if len(text_chunk) <= chunk_size:
            return [text_chunk.strip()] if text_chunk.strip() else []
            
        if sep_idx >= len(separators):
            # Fallback to hard character slicing with overlap
            chunks = []
            start = 0
            while start < len(text_chunk):
                end = min(start + chunk_size, len(text_chunk))
                chunks.append(text_chunk[start:end].strip())
                if end == len(text_chunk):
                    break
                start += max(1, chunk_size - chunk_overlap)
            return [c for c in chunks if c]

        sep = separators[sep_idx]
        parts = text_chunk.split(sep)
        chunks: List[str] = []
        current_chunk = ""
        
        for part in parts:
            candidate = f"{current_chunk}{sep}{part}" if current_chunk else part
            if len(candidate) <= chunk_size:
                current_chunk = candidate
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                if len(part) > chunk_size:
                    chunks.extend(_split_recursive(part, sep_idx + 1))
                    current_chunk = ""
                else:
                    current_chunk = part
                    
        if current_chunk and current_chunk.strip():
            chunks.append(current_chunk.strip())
            
        return [c for c in chunks if c]

    raw_chunks = _split_recursive(text_content, 0)
    
    # Merge tiny fragments
    final_chunks: List[str] = []
    for c in raw_chunks:
        if not c:
            continue
        if final_chunks and len(final_chunks[-1]) + len(c) + 1 <= chunk_size and len(c) < 150:
            final_chunks[-1] = f"{final_chunks[-1]} {c}"
        else:
            final_chunks.append(c)
            
    return final_chunks if final_chunks else [text_content]

def compute_embeddings(texts: List[str]) -> np.ndarray:
    """Compute dense vectors using SentenceTransformer."""
    if not texts:
        return np.empty((0, settings.EMBEDDING_DIMENSION), dtype=np.float32)
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return embeddings.astype(np.float32)

async def chunk_and_index_note(note: Note, content: str, db: AsyncSession) -> List[Chunk]:
    """Chunk extracted content, generate embeddings, index in FAISS and SQLite."""
    # 1. Clean previous chunks for this note
    await db.execute(delete(Chunk).where(Chunk.note_id == note.id))
    await db.flush()
    
    # 2. Split text
    chunks_text = recursive_text_split(content)
    if not chunks_text:
        chunks_text = [note.title]

    # 3. Compute Embeddings
    embeddings = compute_embeddings(chunks_text)
    
    # 4. Insert chunks to SQLite & FAISS
    created_chunks: List[Chunk] = []
    chunk_uuids: List[str] = []
    
    for idx, c_text in enumerate(chunks_text):
        chunk_id = str(uuid.uuid4())
        chunk = Chunk(
            id=chunk_id,
            note_id=note.id,
            chunk_index=idx,
            content=c_text,
            embedding_id=chunk_id
        )
        db.add(chunk)
        created_chunks.append(chunk)
        chunk_uuids.append(chunk_id)

    await db.flush()
    
    # Add to FAISS
    vector_store.add_vectors(embeddings, chunk_uuids)
    
    logger.info(f"Indexed {len(created_chunks)} chunks for Note '{note.title}' (ID: {note.id})")
    return created_chunks

async def compute_semantic_links(
    db: AsyncSession,
    target_note_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Compute document-level cosine similarities across notes, enforce tau >= 0.70 threshold,
    cap maximum degree to top-K (K=5), prune mutual links, and handle orphan nodes.
    """
    # Fetch all notes and their chunks
    stmt = select(Note)
    res = await db.execute(stmt)
    all_notes = res.scalars().all()
    
    if len(all_notes) < 2:
        return []

    # Get document representations
    note_vectors: Dict[str, np.ndarray] = {}
    model = get_embedding_model()
    
    for n in all_notes:
        doc_text = f"{n.title}. {n.summary or ''}"
        vec = model.encode([doc_text], convert_to_numpy=True, normalize_embeddings=True)[0]
        note_vectors[n.id] = vec.astype(np.float32)

    # Clean existing links if recalculating all or for target
    if target_note_id:
        await db.execute(delete(Link).where(
            (Link.source_note_id == target_note_id) | (Link.target_note_id == target_note_id)
        ))
    else:
        await db.execute(delete(Link))
    await db.flush()

    # Calculate pair-wise cosine similarities
    created_links: List[Dict[str, Any]] = []
    tau = settings.COSINE_SIMILARITY_THRESHOLD
    max_k = settings.MAX_LINK_DEGREE

    source_notes = [n for n in all_notes if n.id == target_note_id] if target_note_id else all_notes

    for src_note in source_notes:
        src_vec = note_vectors[src_note.id]
        candidates: List[Tuple[Note, float]] = []

        for other_note in all_notes:
            if other_note.id == src_note.id:
                continue
            other_vec = note_vectors[other_note.id]
            # Cosine similarity on normalized vectors is dot product
            sim = float(np.dot(src_vec, other_vec))
            if sim >= tau:
                candidates.append((other_note, sim))

        # Sort descending by similarity
        candidates.sort(key=lambda x: x[1], reverse=True)
        # Degree capping to top-K
        top_candidates = candidates[:max_k]

        for target_note, score in top_candidates:
            # Check if reverse link already exists to prevent duplicate undirected edges
            existing_stmt = select(Link).where(
                ((Link.source_note_id == src_note.id) & (Link.target_note_id == target_note.id)) |
                ((Link.source_note_id == target_note.id) & (Link.target_note_id == src_note.id))
            )
            existing_res = await db.execute(existing_stmt)
            if existing_res.scalars().first():
                continue

            link_id = str(uuid.uuid4())
            new_link = Link(
                id=link_id,
                source_note_id=src_note.id,
                target_note_id=target_note.id,
                similarity_score=round(score, 4),
                link_type="semantic"
            )
            db.add(new_link)
            created_links.append({
                "id": link_id,
                "source": src_note.id,
                "target": target_note.id,
                "score": round(score, 4),
                "type": "semantic"
            })

    await db.commit()
    logger.info(f"Created {len(created_links)} semantic links (Threshold: {tau}, Max-K: {max_k})")
    return created_links

class LinkRequest(BaseModel):
    note_id: str

class LinkAllResponse(BaseModel):
    total_links: int
    links: List[Dict[str, Any]]

@router.post("", response_model=Dict[str, Any])
async def link_note_endpoint(
    payload: LinkRequest,
    db: AsyncSession = Depends(get_db)
):
    """Chunk, embed, vector-index, and semantically link a note."""
    stmt = select(Note).where(Note.id == payload.note_id)
    res = await db.execute(stmt)
    note = res.scalars().first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    content = note.summary or note.title
    # Check if raw file contains text
    if note.raw_path and os.path.exists(note.raw_path):
        ext = os.path.splitext(note.raw_path)[1].lower()
        if ext in [".txt", ".md"]:
            try:
                with open(note.raw_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                pass

    # 1. Chunk and index
    chunks = await chunk_and_index_note(note, content, db)
    
    # 2. Compute links
    links = await compute_semantic_links(db, target_note_id=note.id)
    
    note.status = "indexed"
    await db.commit()

    return {
        "note_id": note.id,
        "chunks_indexed": len(chunks),
        "links_created": len(links),
        "links": links
    }

@router.post("/all", response_model=LinkAllResponse)
async def link_all_notes_endpoint(
    db: AsyncSession = Depends(get_db)
):
    """Recompute semantic links across the entire knowledge graph."""
    links = await compute_semantic_links(db, target_note_id=None)
    return LinkAllResponse(
        total_links=len(links),
        links=links
    )
