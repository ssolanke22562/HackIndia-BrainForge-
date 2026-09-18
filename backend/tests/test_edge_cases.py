import io
import pytest
from pathlib import Path
from backend.parsers.pdf_parser import parse_pdf, EncryptedFileError
from backend.parsers.docx_parser import parse_docx, CorruptedDocxError
from backend.parsers.audio_transcribe import calculate_audio_rms, parse_audio
from backend.parsers.csv_parser import parse_csv
from backend.parsers import detect_source_type
from backend.link import recursive_text_split
from backend.ask import generate_grounded_answer

def test_edge_case_corrupted_pdf(tmp_path):
    """Edge Case 1 & 2: Corrupted PDF detection."""
    fake_pdf = tmp_path / "corrupted.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 mock corrupted non-valid pdf payload")
    with pytest.raises(Exception):
        parse_pdf(fake_pdf)

def test_edge_case_corrupted_docx(tmp_path):
    """Edge Case 3: Malformed DOCX archive handling."""
    corrupted_docx = tmp_path / "bad.docx"
    corrupted_docx.write_bytes(b"Not a real zip or docx content")
    with pytest.raises(CorruptedDocxError):
        parse_docx(corrupted_docx)

def test_edge_case_silent_audio(tmp_path):
    """Edge Case 4: RMS Energy silence check on silent wave data."""
    import wave
    silent_wav = tmp_path / "silent.wav"
    with wave.open(str(silent_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00" * 32000) # 1 sec silence
    rms, duration = calculate_audio_rms(silent_wav)
    assert rms < 0.005

def test_edge_case_complex_csv(tmp_path):
    """Edge Case 5: Ingest multi-column spreadsheet with special characters."""
    csv_file = tmp_path / "budget.csv"
    csv_file.write_text("Project,Budget ($),Status,Lead Engineer\nAlpha,150000,Active,Alice\nBeta,250000,Planning,Bob\n", encoding="utf-8")
    data = parse_csv(csv_file)
    assert "Alpha" in data["text"]
    assert "150000" in data["text"]
    assert data["metadata"]["column_count"] == 4
    assert data["metadata"]["row_count"] == 2
    assert data["title"] == "Budget"

def test_edge_case_unsupported_format_detection():
    """Edge Case 6: Unknown extensions quarantined."""
    assert detect_source_type("virus.exe") == "unknown"
    assert detect_source_type("binary.bin") == "unknown"
    assert detect_source_type("archive.rar") == "unknown"

@pytest.mark.asyncio
async def test_edge_case_out_of_domain_query():
    """Edge Case 9: Knowledge void guardrail against hallucinations."""
    ans, provider = await generate_grounded_answer("Who won the 1982 football championship in Brazil?", [])
    assert "couldn't find any information" in ans.lower()
    assert provider == "knowledge_void"

def test_edge_case_empty_and_huge_text_splitting():
    """Edge Case 10: Recursive splitter handles empty and large text cleanly."""
    assert recursive_text_split("") == []
    huge_text = "Word " * 5000
    chunks = recursive_text_split(huge_text, chunk_size=500, chunk_overlap=50)
    assert len(chunks) > 10
    for c in chunks:
        assert len(c) <= 600
