import os
import re
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles

try:
    import json_repair
except ImportError:
    json_repair = None

from backend.config import settings
from backend.db.database import get_db, async_session_maker
from backend.db.models import Note

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/classify", tags=["AI Classification"])

# PARA Schema
class ClassificationResult(BaseModel):
    category: str = Field(..., description="Projects, Areas, Resources, or Archives")
    tags: List[str] = Field(default_factory=list)
    summary: str = Field(..., description="Concise 1-2 sentence summary")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    provider_used: str = Field(default="heuristic")

class ClassifyRequest(BaseModel):
    note_id: str

class ClassifyResponse(BaseModel):
    note_id: str
    category: str
    tags: List[str]
    summary: str
    confidence: float
    wiki_path: Optional[str] = None
    provider_used: str

PARA_PROMPT = """You are an AI knowledge classifier for a Personal Knowledge Management (PKM) system using the PARA Framework:
1. Projects: Short-term efforts with a specific goal and deadline (e.g. hackathon demo, quarterly review, launch checklist, tasks with TODOs).
2. Areas: Long-term ongoing responsibilities or domains of life/work with no end date (e.g. Health & Fitness, Personal Finance, Engineering Standards, Parenting, Team Operations).
3. Resources: Topics or subjects of ongoing interest, reference materials, research papers, cheatsheets, documentation, how-to guides, recipes, articles.
4. Archives: Inactive items from the other 3 categories, past projects completed, deprecated notes, old receipts/logs, historical meeting notes.

Analyze the given title and text content, and output a valid JSON object matching this schema:
{
  "category": "Projects" | "Areas" | "Resources" | "Archives",
  "tags": ["tag1", "tag2", "tag3"],
  "summary": "Concise 1-2 sentence operational summary",
  "confidence": 0.95
}
"""

def sanitize_filename(title: str) -> str:
    """Create a clean, filesystem-safe filename."""
    cleaned = re.sub(r'[\\/*?:"<>|]', '', title).strip()
    safe = re.sub(r'\s+', '_', cleaned)
    safe = re.sub(r'_+', '_', safe)
    return safe[:60] if safe else "Untitled"

def clean_and_parse_json(text: str) -> Dict[str, Any]:
    """Resilient JSON parser using json_repair with fallback."""
    if not text:
        raise ValueError("Empty JSON response")
    
    # Strip markdown code blocks
    cleaned = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE).strip()

    if json_repair:
        try:
            parsed = json_repair.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    try:
        return json.loads(cleaned)
    except Exception as e:
        # Try finding the first {...}
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"Failed to parse LLM JSON: {e}")

def classify_offline_heuristic(title: str, content: str) -> ClassificationResult:
    """
    Tier 3: Fast offline rule-based heuristic and regex classifier.
    """
    text = f"{title}\n{content}".lower()
    
    # Project Indicators
    project_keywords = [
        r"\btodo\b", r"\bdeadline\b", r"\bmilestone\b", r"\baction item\b", r"\bsprint\b",
        r"\bhackathon\b", r"\blaunch\b", r"\bdeliverable\b", r"\broadmap\b", r"\bq[1-4]\b",
        r"\bphase [1-4]\b", r"\bwip\b", r"\bin progress\b", r"\bpriority\b"
    ]
    # Area Indicators
    area_keywords = [
        r"\bhealth\b", r"\bfitness\b", r"\bfinance\b", r"\bbudget\b", r"\broutine\b", r"\bhabit\b",
        r"\bmanagement\b", r"\bstandard\b", r"\bstandards\b", r"\bpolicy\b", r"\bguideline\b",
        r"\bcore values\b", r"\bquarterly\b", r"\brecurring\b", r"\bmonthly\b", r"\bweekly review\b", r"\bteam\b"
    ]
    # Archive Indicators
    archive_keywords = [
        r"\barchive\b", r"\bcompleted\b", r"\bdeprecated\b", r"\blegacy\b", r"\bhistorical\b",
        r"\bold log\b", r"\breceipt\b", r"\binvoice\b", r"\b202[0-3]\b", r"\bretrospective\b",
        r"\bpost-mortem\b", r"\bmeeting notes \(old\)\b"
    ]

    project_score = sum(1 for kw in project_keywords if re.search(kw, text))
    area_score = sum(1 for kw in area_keywords if re.search(kw, text))
    archive_score = sum(1 for kw in archive_keywords if re.search(kw, text))

    # Determine category
    if archive_score > project_score and archive_score > area_score and archive_score > 0:
        category = "Archives"
        confidence = 0.80
    elif project_score > area_score and project_score > 0:
        category = "Projects"
        confidence = 0.85
    elif area_score > 0:
        category = "Areas"
        confidence = 0.80
    else:
        # Default to Resources for general knowledge, reference, and tutorials
        category = "Resources"
        confidence = 0.75

    # Extract tags
    words = re.findall(r'\b[a-zA-Z]{4,15}\b', text)
    from collections import Counter
    stopwords = {"this", "that", "with", "from", "have", "more", "will", "about", "there", "their", "which", "would", "these", "other", "into", "could"}
    filtered_words = [w for w in words if w not in stopwords]
    common = [w for w, _ in Counter(filtered_words).most_common(4)]
    
    # Generate summary
    first_sentence = content.strip().split("\n")[0][:180] if content.strip() else title
    summary = f"Summary of {title}: {first_sentence}" if first_sentence else f"Knowledge capture for {title}."

    return ClassificationResult(
        category=category,
        tags=common,
        summary=summary,
        confidence=confidence,
        provider_used="offline_heuristic"
    )

async def classify_with_groq(title: str, content: str) -> Optional[ClassificationResult]:
    """Tier 1: Groq API classification."""
    if not settings.GROQ_API_KEY:
        return None
    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        
        user_message = f"Title: {title}\nContent snippet:\n{content[:2500]}"
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": PARA_PROMPT},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=300
        )
        raw_text = response.choices[0].message.content
        data = clean_and_parse_json(raw_text)
        
        cat = data.get("category", "Resources").strip().title()
        if cat not in ["Projects", "Areas", "Resources", "Archives"]:
            cat = "Resources"
            
        tags = [t.lower().strip() for t in data.get("tags", []) if isinstance(t, str)]
        summary = data.get("summary", title)
        confidence = float(data.get("confidence", 0.90))

        return ClassificationResult(
            category=cat,
            tags=tags,
            summary=summary,
            confidence=confidence,
            provider_used="groq"
        )
    except Exception as e:
        logger.warning(f"Groq classification failed or timed out: {e}")
        return None

async def classify_with_gemini(title: str, content: str) -> Optional[ClassificationResult]:
    """Tier 2: Gemini API classification."""
    if not settings.GEMINI_API_KEY:
        return None
    try:
        import httpx
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
        user_message = f"{PARA_PROMPT}\n\nTitle: {title}\nContent:\n{content[:2500]}"
        
        payload = {
            "contents": [{"parts": [{"text": user_message}]}],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
        }
        
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = clean_and_parse_json(raw_text)
                
                cat = parsed.get("category", "Resources").strip().title()
                if cat not in ["Projects", "Areas", "Resources", "Archives"]:
                    cat = "Resources"
                    
                tags = [t.lower().strip() for t in parsed.get("tags", []) if isinstance(t, str)]
                summary = parsed.get("summary", title)
                confidence = float(parsed.get("confidence", 0.88))
                
                return ClassificationResult(
                    category=cat,
                    tags=tags,
                    summary=summary,
                    confidence=confidence,
                    provider_used="gemini"
                )
    except Exception as e:
        logger.warning(f"Gemini classification failed: {e}")
        return None

async def run_multi_tier_classification(title: str, content: str) -> ClassificationResult:
    """Execute Tier 1 (Groq) -> Tier 2 (Gemini) -> Tier 3 (Offline Heuristic)."""
    # Tier 1
    res = await classify_with_groq(title, content)
    if res:
        return res
    
    # Tier 2
    res = await classify_with_gemini(title, content)
    if res:
        return res
        
    # Tier 3 (Always succeeds)
    return classify_offline_heuristic(title, content)

async def sync_to_markdown_vault(note: Note, extracted_text: str = "") -> Path:
    """
    Format and synchronize note to living Wiki Markdown Vault with YAML frontmatter.
    Path: wiki/<Category>/<SafeTitle>.md
    """
    category = note.category or "Resources"
    cat_dir = settings.wiki_path / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    
    safe_title = sanitize_filename(note.title)
    wiki_file = cat_dir / f"{safe_title}.md"
    
    tags = []
    try:
        if note.tags_json:
            tags = json.loads(note.tags_json)
    except Exception:
        tags = []
        
    iso_time = note.created_at.isoformat() if note.created_at else datetime.utcnow().isoformat()
    
    frontmatter = [
        "---",
        f"id: \"{note.id}\"",
        f"title: \"{note.title}\"",
        f"category: {category}",
        f"source_type: {note.source_type}",
        f"created_at: \"{iso_time}\"",
        f"tags: {json.dumps(tags)}",
        f"summary: \"{note.summary or ''}\"",
        f"confidence: {note.confidence or 1.0}",
        "links: []",
        "---",
        "",
        f"# {note.title}",
        "",
        f"> **Category:** {category} | **Source:** {note.source_type.upper()}",
        "",
        "## Summary",
        note.summary or "No summary available.",
        "",
        "## Content",
        extracted_text or note.summary or "No extracted content.",
        ""
    ]
    
    content_str = "\n".join(frontmatter)
    async with aiofiles.open(wiki_file, "w", encoding="utf-8") as f:
        await f.write(content_str)
        
    return wiki_file

@router.post("", response_model=ClassifyResponse)
async def classify_note_endpoint(
    payload: ClassifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Classify a note by ID into PARA framework (Projects, Areas, Resources, Archives),
    generate tags & summary, update database record and write to Markdown Wiki Vault.
    """
    stmt = select(Note).where(Note.id == payload.note_id)
    res = await db.execute(stmt)
    note = res.scalars().first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
        
    # Read extracted content from raw or manifest
    content_to_classify = note.summary or note.title
    raw_path = Path(note.raw_path) if note.raw_path else None
    
    if raw_path and raw_path.exists() and raw_path.suffix.lower() in [".txt", ".md", ".json"]:
        try:
            async with aiofiles.open(raw_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = await f.read()
                if raw_text.strip():
                    content_to_classify = raw_text
        except Exception:
            pass

    # Run classification
    classification = await run_multi_tier_classification(note.title, content_to_classify)
    
    # Update note record
    note.category = classification.category
    note.tags_json = json.dumps(classification.tags)
    note.summary = classification.summary
    note.confidence = classification.confidence
    note.status = "classified"
    
    # Sync to Wiki Vault
    wiki_path = await sync_to_markdown_vault(note, content_to_classify)
    note.wiki_path = str(wiki_path)
    
    await db.commit()
    await db.refresh(note)
    
    logger.info(f"Classified Note {note.id} -> {classification.category} via {classification.provider_used}")
    
    return ClassifyResponse(
        note_id=note.id,
        category=classification.category,
        tags=classification.tags,
        summary=classification.summary,
        confidence=classification.confidence,
        wiki_path=str(wiki_path),
        provider_used=classification.provider_used
    )

@router.post("/batch")
async def batch_classify_notes(
    db: AsyncSession = Depends(get_db)
):
    """Classify all unclassified notes in the database."""
    stmt = select(Note).where((Note.category == None) | (Note.category == ""))
    res = await db.execute(stmt)
    notes = res.scalars().all()
    
    results = []
    for note in notes:
        content = note.summary or note.title
        classification = await run_multi_tier_classification(note.title, content)
        note.category = classification.category
        note.tags_json = json.dumps(classification.tags)
        note.summary = classification.summary
        note.confidence = classification.confidence
        note.status = "classified"
        
        wiki_path = await sync_to_markdown_vault(note, content)
        note.wiki_path = str(wiki_path)
        results.append({
            "id": note.id,
            "title": note.title,
            "category": classification.category
        })
        
    await db.commit()
    return {"classified_count": len(results), "notes": results}
