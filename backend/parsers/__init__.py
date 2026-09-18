import datetime
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.parsers.pdf_parser import parse_pdf, EncryptedFileError
from backend.parsers.docx_parser import parse_docx, CorruptedDocxError
from backend.parsers.image_ocr import parse_image
from backend.parsers.audio_transcribe import parse_audio
from backend.parsers.csv_parser import parse_csv
from backend.parsers.link_extractor import parse_url

logger = logging.getLogger(__name__)

class CaptureItem(BaseModel):
    """Normalized schema for all multi-modal ingested items."""
    id: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    source_type: str  # pdf, docx, image, audio, csv, link, note
    raw_path: Optional[str] = None
    extracted_text: str
    title: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

def detect_source_type(file_name_or_url: str) -> str:
    """Detect modality source type from file extension or URL scheme."""
    lower = file_name_or_url.lower().strip()
    if lower.startswith("http://") or lower.startswith("https://"):
        return "link"

    ext = Path(lower).suffix
    if ext == ".pdf":
        return "pdf"
    elif ext in [".docx", ".doc"]:
        return "docx"
    elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"]:
        return "image"
    elif ext in [".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac"]:
        return "audio"
    elif ext in [".csv", ".xlsx", ".xls", ".tsv"]:
        return "csv"
    elif ext in [".txt", ".md", ".json", ".markdown"]:
        return "note"
    else:
        return "unknown"

async def parse_item(
    item_id: str,
    source_type: str,
    file_path: Optional[str | Path] = None,
    raw_text_content: Optional[str] = None,
    custom_title: Optional[str] = None
) -> CaptureItem:
    """
    Unified entry point for parsing any multi-modal capture into the CaptureItem schema.
    """
    extracted_text = ""
    title = custom_title or "Untitled Capture"
    metadata: Dict[str, Any] = {}
    path_str = str(file_path) if file_path else None

    if source_type == "note":
        extracted_text = (raw_text_content or "").strip()
        if not custom_title:
            # Extract first non-empty line as title
            lines = [line.strip("# ").strip() for line in extracted_text.splitlines() if line.strip()]
            title = lines[0][:80] if lines else "Typed Note"
        metadata = {"format": "NOTE", "char_count": len(extracted_text)}

    elif source_type == "link":
        target_url = str(file_path) if file_path else (raw_text_content or "").strip()
        parsed = await parse_url(target_url)
        extracted_text = parsed["text"]
        title = custom_title or parsed["title"]
        metadata = parsed["metadata"]

    elif source_type == "pdf" and file_path:
        parsed = parse_pdf(file_path)
        extracted_text = parsed["text"]
        title = custom_title or parsed["title"]
        metadata = parsed["metadata"]

    elif source_type == "docx" and file_path:
        parsed = parse_docx(file_path)
        extracted_text = parsed["text"]
        title = custom_title or parsed["title"]
        metadata = parsed["metadata"]

    elif source_type == "image" and file_path:
        parsed = parse_image(file_path)
        extracted_text = parsed["text"]
        title = custom_title or parsed["title"]
        metadata = parsed["metadata"]

    elif source_type == "audio" and file_path:
        parsed = parse_audio(file_path)
        extracted_text = parsed["text"]
        title = custom_title or parsed["title"]
        metadata = parsed["metadata"]

    elif source_type == "csv" and file_path:
        parsed = parse_csv(file_path)
        extracted_text = parsed["text"]
        title = custom_title or parsed["title"]
        metadata = parsed["metadata"]

    else:
        raise ValueError(f"Unsupported or invalid source type: '{source_type}' with path '{file_path}'")

    return CaptureItem(
        id=item_id,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_type=source_type,
        raw_path=path_str,
        extracted_text=extracted_text,
        title=title,
        metadata=metadata
    )
