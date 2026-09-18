import logging
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image

logger = logging.getLogger(__name__)

class EncryptedFileError(Exception):
    """Raised when a PDF file is password-protected and cannot be decrypted."""
    pass

def parse_pdf(file_path: str | Path) -> Dict[str, Any]:
    """
    High-fidelity layout-aware text extraction from PDF documents.
    Automatically triggers Tesseract OCR fallback for scanned or rasterized pages.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    extracted_blocks = []
    total_text_length = 0
    page_count = 0
    metadata = {}
    title = path.stem.replace("_", " ").replace("-", " ").title()

    # Try PyMuPDF (fitz)
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(path))
        page_count = len(doc)
        
        # 1. Check for encryption
        if doc.is_encrypted:
            # Try decrypting with empty password
            if not doc.authenticate(""):
                raise EncryptedFileError(f"PDF '{path.name}' is password-protected. Please decrypt it before uploading.")

        # Extract document metadata
        doc_meta = doc.metadata or {}
        if doc_meta.get("title"):
            title = doc_meta["title"].strip()
        metadata = {
            "author": doc_meta.get("author", ""),
            "creator": doc_meta.get("creator", ""),
            "producer": doc_meta.get("producer", ""),
            "page_count": page_count,
            "format": "PDF"
        }

        # 2. Iterate pages and extract layout-aware blocks
        for page_idx in range(page_count):
            page = doc[page_idx]
            # blocks: (x0, y0, x1, y1, text, block_no, block_type)
            blocks = page.get_text("blocks")
            # Sort blocks top-to-bottom, left-to-right
            sorted_blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
            
            page_text_parts = []
            for b in sorted_blocks:
                if len(b) >= 5 and b[4]:
                    text = b[4].strip()
                    if text:
                        page_text_parts.append(text)
            
            page_text = "\n\n".join(page_text_parts)
            if page_text:
                extracted_blocks.append(f"--- Page {page_idx + 1} ---\n{page_text}")
                total_text_length += len(page_text)

        # 3. Scanned PDF fallback if sparse selectable text
        if total_text_length < 50 and page_count > 0:
            logger.warning(f"Sparse text detected in '{path.name}' ({total_text_length} chars). Triggering Tesseract OCR fallback.")
            ocr_text_parts = []
            try:
                import pytesseract
                for page_idx in range(min(page_count, 20)):  # Guardrail max 20 pages OCR
                    page = doc[page_idx]
                    pix = page.get_pixmap(dpi=200)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ocr_page_text = pytesseract.image_to_string(img).strip()
                    if ocr_page_text:
                        ocr_text_parts.append(f"--- Page {page_idx + 1} (OCR) ---\n{ocr_page_text}")
                
                if ocr_text_parts:
                    extracted_blocks = ocr_text_parts
                    metadata["ocr_applied"] = True
            except Exception as ocr_err:
                logger.error(f"Tesseract OCR fallback failed for '{path.name}': {ocr_err}")

        doc.close()

    except ImportError:
        # Fallback to pypdf / pdfplumber if fitz is not installed
        logger.warning("PyMuPDF (fitz) not available, using pypdf fallback.")
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            page_count = len(reader.pages)
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception:
                    raise EncryptedFileError(f"PDF '{path.name}' is encrypted.")

            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    extracted_blocks.append(f"--- Page {idx + 1} ---\n{text.strip()}")
            metadata["page_count"] = page_count
        except Exception as e:
            logger.error(f"Fallback PDF extraction failed: {e}")
            raise

    full_text = "\n\n".join(extracted_blocks).strip()
    if not full_text:
        full_text = f"[PDF Document: {path.name} with {page_count} pages. No selectable or OCR text could be extracted.]"

    return {
        "text": full_text,
        "title": title,
        "page_count": page_count,
        "metadata": metadata
    }
