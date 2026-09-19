import os
import re
import uuid
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

import numpy as np
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.database import get_db, async_session_maker
from backend.db.models import Note, Chunk, Session as ChatSession, Message, Retrieval, UserPersona
from backend.db.vector_store import vector_store
from backend.link import get_embedding_model

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ask", tags=["Hybrid RAG & Q&A"])

# Request & Response Schemas
class AskRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=10)

class CitationItem(BaseModel):
    note_id: str
    title: str
    category: str
    source_type: str
    snippet: str
    relevance_score: float

class AskResponse(BaseModel):
    answer: str
    session_id: str
    citations: List[CitationItem]
    knowledge_void: bool = False
    provider_used: str = "offline_synthesis"
    persona_applied: bool = False

def build_rag_system_prompt(persona: Optional[UserPersona] = None) -> str:
    """Dynamically construct RAG system prompt with user behavioral and voice profile."""
    base_rules = (
        "Answer accurately and truthfully based EXCLUSIVELY on the provided user knowledge context.\n"
        "For every factual claim or insight, you MUST cite the source note using this format: [Note: <note_id>].\n"
        "If the provided context does not contain enough information to answer the question, state clearly: "
        '"I couldn\'t find any information about this in your captured notes." Do NOT fabricate any facts or citations.'
    )

    if not persona or not persona.is_enabled:
        return f"You are SecondSelf, an intelligent Second Brain assistant.\n{base_rules}"

    sample_snippet = f'\n- Writing Style Benchmark: "{persona.writing_sample[:300]}"' if persona.writing_sample else ""
    return f"""You are SecondSelf — the user's personal AI replica and intellectual alter ego.
You must synthesize the answer in the USER'S DISTINCTIVE VOICE, TONE, and BEHAVIORAL PROFILE:
- User Identity: {persona.name} ({persona.role_profession})
- Communication Tone: {persona.communication_tone}
- Perspective: {persona.perspective}
- Preferred Vocabulary / Jargon: {persona.custom_vocabulary or 'Natural and domain-relevant'}
- Formatting Preference: {persona.response_format or 'Clear and structured'}{sample_snippet}

Behavioral Guidelines:
1. Speak as the user explaining their own knowledge, notes, and thoughts in their natural style.
2. Mirror the user's tone, vocabulary habits, and formatting preferences.
3. Strict Grounding: All factual details MUST originate solely from the provided user context.
4. Always append the required note citation [Note: <note_id>] after each grounded point.

{base_rules}
"""

def compute_rrf(
    dense_results: List[Tuple[str, float]], 
    sparse_results: List[Tuple[str, float]], 
    k_constant: int = 60
) -> List[Tuple[str, float]]:
    """
    Reciprocal Rank Fusion (RRF):
    RRF(d) = sum_{m in {dense, sparse}} 1 / (k_constant + rank_m(d))
    """
    scores: Dict[str, float] = {}
    
    # Dense rank scoring
    for rank, (chunk_id, sim) in enumerate(dense_results):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k_constant + rank + 1))
        
    # Sparse rank scoring
    for rank, (chunk_id, bm25_score) in enumerate(sparse_results):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k_constant + rank + 1))
        
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_items

async def hybrid_retrieve(
    query: str,
    top_k: int = 5,
    db: AsyncSession = None
) -> Tuple[List[Dict[str, Any]], float]:
    """
    Perform Dense FAISS search + Sparse SQLite FTS5 search and merge via RRF.
    Returns (retrieved_chunks, max_dense_similarity).
    """
    # 1. Dense Search via FAISS
    model = get_embedding_model()
    query_vector = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
    
    dense_hits = vector_store.search(query_vector, top_k=8)
    max_dense_sim = dense_hits[0][1] if dense_hits else 0.0

    # 2. Sparse Search via SQLite FTS5
    sparse_chunk_ids: List[Tuple[str, float]] = []
    clean_query = re.sub(r'[^a-zA-Z0-9\s]', ' ', query).strip()
    
    if clean_query and db:
        try:
            # Query FTS5 virtual table
            fts_stmt = text(
                "SELECT note_id, rank FROM notes_fts WHERE notes_fts MATCH :q ORDER BY rank LIMIT 8"
            )
            fts_res = await db.execute(fts_stmt, {"q": clean_query})
            note_matches = fts_res.fetchall()
            
            for rank_idx, (note_id, bm25_rank) in enumerate(note_matches):
                # Retrieve the first chunk of this note
                chunk_stmt = select(Chunk).where(Chunk.note_id == note_id).limit(1)
                c_res = await db.execute(chunk_stmt)
                chunk = c_res.scalars().first()
                if chunk:
                    sparse_chunk_ids.append((chunk.id, float(bm25_rank or rank_idx)))
        except Exception as e:
            logger.debug(f"FTS5 query failed or empty: {e}")

    # 3. Merge rankings via RRF
    rrf_ranked = compute_rrf(dense_hits, sparse_chunk_ids, k_constant=60)
    top_rrf_ids = [cid for cid, _ in rrf_ranked[:top_k]]

    if not top_rrf_ids:
        return [], max_dense_sim

    # 4. Fetch chunk & note details
    retrieved_items: List[Dict[str, Any]] = []
    if db:
        chunk_stmt = select(Chunk, Note).join(Note, Chunk.note_id == Note.id).where(Chunk.id.in_(top_rrf_ids))
        res = await db.execute(chunk_stmt)
        rows = res.all()
        
        # Preserve RRF ordering
        chunk_map = {c.id: (c, n) for c, n in rows}
        for cid in top_rrf_ids:
            if cid in chunk_map:
                chunk_obj, note_obj = chunk_map[cid]
                # Find dense sim score if present
                sim = next((s for cid_hit, s in dense_hits if cid_hit == cid), 0.50)
                retrieved_items.append({
                    "chunk_id": chunk_obj.id,
                    "note_id": note_obj.id,
                    "title": note_obj.title,
                    "category": note_obj.category or "Resources",
                    "source_type": note_obj.source_type,
                    "content": chunk_obj.content,
                    "relevance_score": round(float(sim), 3)
                })

    return retrieved_items, max_dense_sim

async def generate_grounded_answer(
    question: str,
    context_items: List[Dict[str, Any]],
    conversation_history: List[Dict[str, str]] = None,
    persona: Optional[UserPersona] = None
) -> Tuple[str, str]:
    """Generate grounded answer using Groq -> Gemini -> Fallback synthesis with Persona Voice."""
    if not context_items:
        return "I couldn't find any information about this in your captured notes.", "knowledge_void"

    context_str = "\n\n".join([
        f"<user_knowledge_context id=\"{item['note_id']}\" title=\"{item['title']}\">\n{item['content']}\n</user_knowledge_context>"
        for item in context_items
    ])

    user_prompt = (
        f"Context from second brain:\n{context_str}\n\n"
        f"User Question: {question}\n\n"
        "Please provide a clear, accurate, synthesized answer with [Note: <id>] citations after each claim."
    )

    system_prompt = build_rag_system_prompt(persona)

    # 1. Try Groq
    if settings.GROQ_API_KEY:
        try:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=settings.GROQ_API_KEY)
            
            messages = [{"role": "system", "content": system_prompt}]
            if conversation_history:
                messages.extend(conversation_history[-4:])
            messages.append({"role": "user", "content": user_prompt})

            response = await client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.3 if (persona and persona.is_enabled) else 0.2,
                max_tokens=750
            )
            return response.choices[0].message.content, "groq"
        except Exception as e:
            logger.warning(f"Groq RAG synthesis failed: {e}")

    # 2. Try Gemini
    if settings.GEMINI_API_KEY:
        try:
            import httpx
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            prompt_text = f"{system_prompt}\n\n{user_prompt}"
            payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    ans = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return ans, "gemini"
        except Exception as e:
            logger.warning(f"Gemini RAG synthesis failed: {e}")

    # 3. Tier 3: Local Extractive Synthesis
    bullet_points = []
    for item in context_items:
        clean_snippet = item["content"].strip().replace("\n", " ")[:200]
        bullet_points.append(f"• Based on **{item['title']}** ({item['category']}): \"{clean_snippet}...\" [Note: {item['note_id']}]")

    prefix = f"SecondSelf ({persona.name if persona else 'Personalized Voice'}):" if (persona and persona.is_enabled) else "SecondSelf Knowledge Synthesis:"
    fallback_answer = (
        f"{prefix}\n\nHere is what I found in your knowledge base regarding \"{question}\":\n\n" +
        "\n".join(bullet_points)
    )
    return fallback_answer, "local_extractive"

@router.post("", response_model=AskResponse)
async def ask_question_endpoint(
    payload: AskRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Conversational RAG Q&A with hybrid dense+sparse retrieval, RRF ranking,
    knowledge void detection, persona behavioral synthesis, and grounded citations.
    """
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # 1. Retrieve or Create Session
    session_id = payload.session_id
    chat_session = None
    if session_id:
        s_stmt = select(ChatSession).where(ChatSession.id == session_id)
        s_res = await db.execute(s_stmt)
        chat_session = s_res.scalars().first()

    if not chat_session:
        session_id = str(uuid.uuid4())
        chat_session = ChatSession(
            id=session_id,
            title=question[:40] + ("..." if len(question) > 40 else "")
        )
        db.add(chat_session)
        await db.flush()

    # 2. Record User Message
    user_msg_id = str(uuid.uuid4())
    user_msg = Message(
        id=user_msg_id,
        session_id=session_id,
        role="user",
        content=question
    )
    db.add(user_msg)
    await db.flush()

    # 3. Fetch User Persona
    p_stmt = select(UserPersona).limit(1)
    p_res = await db.execute(p_stmt)
    user_persona = p_res.scalars().first()

    # 4. Hybrid Retrieval
    retrieved_items, max_dense_sim = await hybrid_retrieve(question, top_k=payload.top_k, db=db)

    # 5. Knowledge Void Guardrail check
    if not retrieved_items or (max_dense_sim < 0.35 and len(retrieved_items) == 0):
        answer_text = "I couldn't find any information about this in your captured notes."
        provider = "knowledge_void"
        citations_response = []
        is_void = True
        persona_applied = False
    else:
        is_void = False
        # Fetch conversation history for context window
        history_stmt = select(Message).where(Message.session_id == session_id).order_by(Message.created_at.desc()).limit(6)
        h_res = await db.execute(history_stmt)
        past_msgs = list(reversed(h_res.scalars().all()))
        history_formatted = [{"role": m.role, "content": m.content} for m in past_msgs if m.id != user_msg_id]

        # Generate grounded answer in persona voice
        answer_text, provider = await generate_grounded_answer(
            question, 
            retrieved_items, 
            history_formatted, 
            persona=user_persona
        )
        persona_applied = bool(user_persona and user_persona.is_enabled)

        # Format citations
        citations_response = [
            CitationItem(
                note_id=item["note_id"],
                title=item["title"],
                category=item["category"],
                source_type=item["source_type"],
                snippet=item["content"][:200],
                relevance_score=item["relevance_score"]
            )
            for item in retrieved_items
        ]

    # 5. Record Assistant Message & Retrievals
    asst_msg_id = str(uuid.uuid4())
    asst_msg = Message(
        id=asst_msg_id,
        session_id=session_id,
        role="assistant",
        content=answer_text
    )
    db.add(asst_msg)
    await db.flush()

    # Snapshot cited retrievals
    for item in retrieved_items:
        retrieval_entry = Retrieval(
            id=str(uuid.uuid4()),
            message_id=asst_msg_id,
            note_id=item["note_id"],
            chunk_id=item["chunk_id"],
            snippet_text=item["content"],
            relevance_score=item["relevance_score"]
        )
        db.add(retrieval_entry)

    # Update session timestamp
    chat_session.updated_at = datetime.utcnow()
    await db.commit()

    return AskResponse(
        answer=answer_text,
        session_id=session_id,
        citations=citations_response,
        knowledge_void=is_void,
        provider_used=provider,
        persona_applied=persona_applied
    )
