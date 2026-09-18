import os
import json
import pytest
from pathlib import Path
from backend.config import settings
from backend.classify import (
    classify_offline_heuristic,
    clean_and_parse_json,
    sanitize_filename,
    sync_to_markdown_vault
)
from backend.db.models import Note

def test_sanitize_filename():
    assert sanitize_filename("Project / Plan: 2026?") == "Project_Plan_2026"
    assert sanitize_filename("") == "Untitled"

def test_json_clean_and_parse():
    raw_markdown = """```json
    {
        "category": "Projects",
        "tags": ["hackathon", "ai"],
        "summary": "Hackathon project planning.",
        "confidence": 0.95
    }
    ```"""
    parsed = clean_and_parse_json(raw_markdown)
    assert parsed["category"] == "Projects"
    assert "hackathon" in parsed["tags"]

def test_offline_heuristic_classification_projects():
    title = "Q4 Hackathon Launch Deliverables"
    content = "TODO: Complete Phase 1 and Phase 2 before the deadline tomorrow."
    result = classify_offline_heuristic(title, content)
    assert result.category == "Projects"
    assert result.confidence >= 0.70

def test_offline_heuristic_classification_areas():
    title = "Personal Fitness Routine & Health Standards"
    content = "Maintain weekly review, daily habit tracking, and monthly gym budget."
    result = classify_offline_heuristic(title, content)
    assert result.category == "Areas"

def test_offline_heuristic_classification_archives():
    title = "Old Receipts and Historical Meeting Notes 2021"
    content = "Deprecated legacy archive from 2021 completed project."
    result = classify_offline_heuristic(title, content)
    assert result.category == "Archives"

def test_offline_heuristic_classification_resources():
    title = "Python AsyncIO Tutorial and Cheatsheet"
    content = "Reference guide on event loops, tasks, coroutines, and future patterns."
    result = classify_offline_heuristic(title, content)
    assert result.category == "Resources"

@pytest.mark.asyncio
async def test_sync_to_markdown_vault(tmp_path):
    note = Note(
        id="test-note-uuid",
        title="Test Wiki Synchronization",
        source_type="pdf",
        category="Projects",
        summary="A test note for markdown wiki export.",
        tags_json='["test", "wiki"]',
        confidence=0.92
    )
    wiki_file = await sync_to_markdown_vault(note, "Extracted full text body goes here.")
    assert wiki_file.exists()
    
    with open(wiki_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "category: Projects" in content
        assert "id: \"test-note-uuid\"" in content
        assert "Extracted full text body goes here." in content
