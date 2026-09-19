import pytest
from backend.ask import build_rag_system_prompt, generate_grounded_answer
from backend.db.models import UserPersona
from backend.persona import AnalyzeSampleRequest, analyze_writing_style_endpoint

def test_build_rag_system_prompt_disabled():
    persona = UserPersona(is_enabled=False)
    prompt = build_rag_system_prompt(persona)
    assert "You are SecondSelf, an intelligent Second Brain assistant." in prompt
    assert "User Identity:" not in prompt

def test_build_rag_system_prompt_enabled():
    persona = UserPersona(
        name="Dr. Jane Doe",
        role_profession="Biotech Founder & Geneticist",
        communication_tone="Rigorous, hypothesis-driven, and concise",
        perspective="First-Person (I, my)",
        custom_vocabulary="CRISPR, assay, titration, p-value",
        response_format="Executive bullet points with key metrics",
        writing_sample="We observed a 3x yield improvement in the batch tests.",
        is_enabled=True
    )
    prompt = build_rag_system_prompt(persona)
    assert "Dr. Jane Doe" in prompt
    assert "Biotech Founder & Geneticist" in prompt
    assert "Rigorous, hypothesis-driven" in prompt
    assert "CRISPR, assay, titration" in prompt
    assert "First-Person" in prompt
    assert "Behavioral Guidelines" in prompt

@pytest.mark.asyncio
async def test_grounded_answer_with_persona():
    persona = UserPersona(
        name="Alex",
        role_profession="Chief Architect",
        communication_tone="Direct and actionable",
        is_enabled=True
    )
    context = [
        {
            "chunk_id": "c1",
            "note_id": "note-999",
            "title": "Database Scalability RFC",
            "category": "Projects",
            "source_type": "docx",
            "content": "We are migrating to partitioned SQLite tables for sub-millisecond query latencies.",
            "relevance_score": 0.95
        }
    ]
    ans, provider = await generate_grounded_answer("How are we scaling the database?", context, persona=persona)
    assert "[Note: note-999]" in ans
    assert "Alex" in ans or "Database Scalability RFC" in ans or "SQLite" in ans

@pytest.mark.asyncio
async def test_persona_style_analyzer():
    sample = "In our latest sprint, we reduced API latency by 45% using Redis caching and connection pooling. The primary trade-off was increased cache invalidation complexity."
    res = await analyze_writing_style_endpoint(AnalyzeSampleRequest(sample_text=sample))
    assert res.detected_tone != ""
    assert res.suggested_vocabulary != ""
    assert res.style_summary != ""
