import pytest
from backend.ask import compute_rrf, generate_grounded_answer

def test_compute_rrf_scoring():
    dense_results = [("chunk-1", 0.92), ("chunk-2", 0.85), ("chunk-3", 0.77)]
    sparse_results = [("chunk-2", 1.5), ("chunk-4", 1.2), ("chunk-1", 0.9)]
    
    rrf = compute_rrf(dense_results, sparse_results, k_constant=60)
    assert len(rrf) == 4
    
    # Chunk-2 and Chunk-1 appear in both lists so they should rank highest
    top_ids = [cid for cid, _ in rrf[:2]]
    assert "chunk-1" in top_ids
    assert "chunk-2" in top_ids

@pytest.mark.asyncio
async def test_knowledge_void_guardrail():
    empty_context = []
    ans, provider = await generate_grounded_answer("What is the speed of light in vacuum?", empty_context)
    assert "couldn't find any information" in ans.lower()
    assert provider == "knowledge_void"

@pytest.mark.asyncio
async def test_grounded_answer_synthesis_local():
    context = [
        {
            "chunk_id": "c1",
            "note_id": "note-123",
            "title": "Quantum Computing Roadmap",
            "category": "Projects",
            "source_type": "pdf",
            "content": "Phase 2 will integrate superconducting qubits with error mitigation algorithms.",
            "relevance_score": 0.88
        }
    ]
    ans, provider = await generate_grounded_answer("What is planned for Phase 2?", context)
    assert "[Note: note-123]" in ans
    assert "Quantum Computing Roadmap" in ans or "superconducting" in ans
