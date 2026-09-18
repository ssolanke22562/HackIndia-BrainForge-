import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.database import get_db
from backend.db.models import Session as ChatSession, Message, Retrieval, Note
from backend.ask import ask_question_endpoint, AskRequest, AskResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["Chat History & Memory"])

class ContinueThreadRequest(BaseModel):
    question: str

@router.get("", response_model=List[Dict[str, Any]])
async def list_chat_sessions(
    db: AsyncSession = Depends(get_db)
):
    """List all saved chat sessions ordered by last active descending."""
    stmt = select(ChatSession).order_by(ChatSession.updated_at.desc())
    res = await db.execute(stmt)
    sessions = res.scalars().all()

    session_list = []
    for s in sessions:
        # Get message count and last message
        msg_stmt = select(Message).where(Message.session_id == s.id).order_by(Message.created_at.desc())
        msg_res = await db.execute(msg_stmt)
        messages = msg_res.scalars().all()
        
        last_preview = messages[0].content[:80] if messages else "Empty session"
        
        session_list.append({
            "id": s.id,
            "title": s.title,
            "message_count": len(messages),
            "last_message": last_preview,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None
        })

    return session_list

@router.get("/{session_id}", response_model=Dict[str, Any])
async def get_chat_session_thread(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve full conversational thread with cited note snapshots for each assistant message."""
    s_stmt = select(ChatSession).where(ChatSession.id == session_id)
    s_res = await db.execute(s_stmt)
    session_obj = s_res.scalars().first()
    if not session_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Fetch messages in chronological order
    m_stmt = select(Message).where(Message.session_id == session_id).order_by(Message.created_at.asc())
    m_res = await db.execute(m_stmt)
    messages = m_res.scalars().all()

    formatted_messages = []
    for msg in messages:
        citations = []
        if msg.role == "assistant":
            # Fetch retrieval snapshots
            r_stmt = select(Retrieval).where(Retrieval.message_id == msg.id)
            r_res = await db.execute(r_stmt)
            retrievals = r_res.scalars().all()
            for r in retrievals:
                # Fetch note title
                note_title = "Source Note"
                if r.note_id:
                    n_stmt = select(Note.title).where(Note.id == r.note_id)
                    n_res = await db.execute(n_stmt)
                    note_title = n_res.scalar() or "Source Note"
                    
                citations.append({
                    "note_id": r.note_id,
                    "title": note_title,
                    "snippet": r.snippet_text[:200],
                    "score": r.relevance_score
                })

        formatted_messages.append({
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "citations": citations
        })

    return {
        "id": session_obj.id,
        "title": session_obj.title,
        "created_at": session_obj.created_at.isoformat() if session_obj.created_at else None,
        "updated_at": session_obj.updated_at.isoformat() if session_obj.updated_at else None,
        "messages": formatted_messages
    }

@router.post("/{session_id}/continue", response_model=AskResponse)
async def continue_chat_session(
    session_id: str,
    payload: ContinueThreadRequest,
    db: AsyncSession = Depends(get_db)
):
    """Append a follow-up question to an existing session thread and receive a cited response."""
    return await ask_question_endpoint(
        AskRequest(question=payload.question, session_id=session_id),
        db=db
    )

@router.delete("/{session_id}")
async def delete_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a chat session and all its messages/retrievals."""
    stmt = select(ChatSession).where(ChatSession.id == session_id)
    res = await db.execute(stmt)
    session_obj = res.scalars().first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.delete(session_obj)
    await db.commit()
    return {"message": "Session deleted successfully", "id": session_id}
