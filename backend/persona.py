import logging
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.database import get_db
from backend.db.models import UserPersona

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/persona", tags=["User Persona & Voice"])

class PersonaDTO(BaseModel):
    id: Optional[str] = None
    name: str = "SecondSelf User"
    role_profession: str = "Knowledge Worker & Researcher"
    communication_tone: str = "Direct, technical, and concise"
    perspective: str = "First-Person (I, my)"
    custom_vocabulary: str = "tradeoffs, architecture, synthesis, high-leverage, action items"
    writing_sample: str = ""
    response_format: str = "TL;DR summary first, followed by clear bullet points and actionable takeaways"
    is_enabled: bool = True

class AnalyzeSampleRequest(BaseModel):
    sample_text: str = Field(..., min_length=10, description="Raw writing sample from user")

class AnalyzeSampleResponse(BaseModel):
    detected_tone: str
    detected_role: str
    suggested_vocabulary: str
    suggested_format: str
    style_summary: str

async def get_or_create_persona(db: AsyncSession) -> UserPersona:
    """Retrieve existing persona or instantiate default row."""
    stmt = select(UserPersona).limit(1)
    res = await db.execute(stmt)
    persona = res.scalars().first()
    
    if not persona:
        persona = UserPersona(
            name="SecondSelf User",
            role_profession="Knowledge Worker & Researcher",
            communication_tone="Direct, technical, and concise",
            perspective="First-Person (I, my)",
            custom_vocabulary="tradeoffs, architecture, synthesis, high-leverage, action items",
            writing_sample="",
            response_format="TL;DR summary first, followed by clear bullet points and actionable takeaways",
            is_enabled=True
        )
        db.add(persona)
        await db.commit()
        await db.refresh(persona)
    return persona

@router.get("", response_model=PersonaDTO)
async def get_persona_endpoint(db: AsyncSession = Depends(get_db)):
    """Fetch current user persona and communication profile."""
    persona = await get_or_create_persona(db)
    return PersonaDTO(
        id=persona.id,
        name=persona.name,
        role_profession=persona.role_profession,
        communication_tone=persona.communication_tone,
        perspective=persona.perspective,
        custom_vocabulary=persona.custom_vocabulary or "",
        writing_sample=persona.writing_sample or "",
        response_format=persona.response_format,
        is_enabled=persona.is_enabled
    )

@router.post("", response_model=PersonaDTO)
async def update_persona_endpoint(payload: PersonaDTO, db: AsyncSession = Depends(get_db)):
    """Save or update user persona and voice settings."""
    persona = await get_or_create_persona(db)
    
    persona.name = payload.name.strip() or "SecondSelf User"
    persona.role_profession = payload.role_profession.strip() or "Knowledge Worker"
    persona.communication_tone = payload.communication_tone.strip() or "Direct & Concise"
    persona.perspective = payload.perspective.strip() or "First-Person (I, my)"
    persona.custom_vocabulary = payload.custom_vocabulary.strip()
    persona.writing_sample = payload.writing_sample.strip()
    persona.response_format = payload.response_format.strip()
    persona.is_enabled = payload.is_enabled
    
    await db.commit()
    await db.refresh(persona)
    
    logger.info(f"Updated UserPersona profile: tone='{persona.communication_tone}', enabled={persona.is_enabled}")
    return PersonaDTO(
        id=persona.id,
        name=persona.name,
        role_profession=persona.role_profession,
        communication_tone=persona.communication_tone,
        perspective=persona.perspective,
        custom_vocabulary=persona.custom_vocabulary,
        writing_sample=persona.writing_sample,
        response_format=persona.response_format,
        is_enabled=persona.is_enabled
    )

@router.post("/analyze", response_model=AnalyzeSampleResponse)
async def analyze_writing_style_endpoint(payload: AnalyzeSampleRequest):
    """
    AI analyzer that examines the user's raw writing sample and extracts
    tone, vocabulary, style traits, and formatting preferences.
    """
    sample = payload.sample_text.strip()
    if not sample:
        raise HTTPException(status_code=400, detail="Sample text cannot be empty.")

    system_prompt = """You are an expert computational linguist and writing style profiler.
Analyze the user's writing sample and return a JSON object with EXACTLY these keys:
{
  "detected_tone": "Concise, technical, witty, or analytical descriptor (e.g. 'Analytical & Pragmatic with high density')",
  "detected_role": "Estimated domain or profession (e.g. 'Software Engineer / Technical Lead')",
  "suggested_vocabulary": "Comma-separated list of signature words, idioms, or technical jargon observed",
  "suggested_format": "Preferred formatting style (e.g. 'Bulleted takeaways with bold keywords')",
  "style_summary": "1-2 sentence summary of their unique voice and communication habits"
}
Respond ONLY with valid JSON.
"""

    # 1. Try Groq
    if settings.GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this writing sample:\n\n{sample}"}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content
            parsed = json.loads(raw)
            return AnalyzeSampleResponse(
                detected_tone=parsed.get("detected_tone", "Direct & Technical"),
                detected_role=parsed.get("detected_role", "Knowledge Worker"),
                suggested_vocabulary=parsed.get("suggested_vocabulary", "key takeaways, trade-offs, architecture"),
                suggested_format=parsed.get("suggested_format", "TL;DR + Bullets"),
                style_summary=parsed.get("style_summary", "Clear, structured, and focused on practical takeaways.")
            )
        except Exception as e:
            logger.warning(f"Groq style analysis failed: {e}")

    # 2. Try Gemini
    if settings.GEMINI_API_KEY:
        try:
            import httpx
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            prompt_text = f"{system_prompt}\n\nWriting sample:\n{sample}"
            payload_data = {"contents": [{"parts": [{"text": prompt_text}]}]}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload_data)
                if resp.status_code == 200:
                    text_resp = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    clean_json = text_resp.strip().removeprefix("```json").removesuffix("```").strip()
                    parsed = json.loads(clean_json)
                    return AnalyzeSampleResponse(
                        detected_tone=parsed.get("detected_tone", "Direct & Technical"),
                        detected_role=parsed.get("detected_role", "Knowledge Worker"),
                        suggested_vocabulary=parsed.get("suggested_vocabulary", "key takeaways, trade-offs"),
                        suggested_format=parsed.get("suggested_format", "TL;DR + Bullets"),
                        style_summary=parsed.get("style_summary", "Structured and goal-oriented writing.")
                    )
        except Exception as e:
            logger.warning(f"Gemini style analysis failed: {e}")

    # Fallback heuristic analysis
    word_count = len(sample.split())
    has_bullets = "•" in sample or "- " in sample
    return AnalyzeSampleResponse(
        detected_tone="Direct, concise, and structured" if has_bullets else "Conversational & Informative",
        detected_role="Technologist / Knowledge Worker",
        suggested_vocabulary="synthesis, tradeoffs, implementation, metrics",
        suggested_format="Bullet points with TL;DR summary" if has_bullets else "Concise paragraphs with bold emphasis",
        style_summary=f"Detected structured communication pattern across {word_count} words."
    )
