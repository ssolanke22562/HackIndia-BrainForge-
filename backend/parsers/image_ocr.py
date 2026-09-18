import io
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
from PIL import Image, ImageOps, ImageFilter
import pytesseract
from backend.config import settings

logger = logging.getLogger(__name__)

def preprocess_image(img: Image.Image) -> Image.Image:
    """Standardize orientation, apply dimension guardrails, and enhance contrast."""
    # 1. Standardize EXIF orientation
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    # 2. Dimension guardrail (max 2048px)
    max_dim = max(img.width, img.height)
    if max_dim > 2048:
        scale = 2048.0 / max_dim
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        logger.debug(f"Resized large image to {new_size}")

    # 3. Enhance with OpenCV if available, else PIL
    try:
        import cv2
        import numpy as np
        
        # Convert PIL to cv2 (BGR)
        np_img = np.array(img.convert("RGB"))
        gray = cv2.cvtColor(np_img, cv2.COLOR_RGB2GRAY)
        
        # Bilateral noise filter
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        return Image.fromarray(thresh)
    except Exception:
        # High quality PIL preprocessing fallback
        gray = img.convert("L")
        enhanced = ImageOps.autocontrast(gray, cutoff=2)
        return enhanced

def extract_ocr_with_confidence(img: Image.Image) -> Tuple[str, float]:
    """Execute Tesseract OCR and compute word-level mean confidence."""
    try:
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        text_parts = []
        confidences = []
        
        for i in range(len(data["text"])):
            w = data["text"][i].strip()
            conf = float(data["conf"][i])
            if w:
                text_parts.append(w)
                if conf >= 0:
                    confidences.append(conf)

        extracted_text = " ".join(text_parts).strip()
        mean_conf = (sum(confidences) / len(confidences)) if confidences else 0.0
        return extracted_text, round(mean_conf, 2)
    except Exception as e:
        logger.warning(f"Tesseract OCR image_to_data failed ({e}), attempting simple image_to_string.")
        try:
            simple_text = pytesseract.image_to_string(img).strip()
            return simple_text, 50.0 if simple_text else 0.0
        except Exception as err:
            logger.error(f"Tesseract OCR failed completely: {err}")
            return "", 0.0

def describe_with_vision_llm(file_path: Path) -> str:
    """Fallback to Vision LLM for non-text diagrams, schematics, or photos."""
    # Check Groq Vision or Gemini Flash
    if settings.GROQ_API_KEY:
        try:
            import base64
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)
            
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
                
            mime = "image/png" if file_path.suffix.lower() == ".png" else "image/jpeg"
            response = client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Provide a detailed technical description, OCR text transcription, and structural analysis of any diagrams or visual elements in this image for knowledge retrieval."},
                            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}}
                        ]
                    }
                ],
                max_tokens=600
            )
            content = response.choices[0].message.content
            if content:
                return f"[Visual Content Description & Diagram Analysis]:\n{content.strip()}"
        except Exception as e:
            logger.warning(f"Groq Vision LLM call failed: {e}")

    if settings.GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            with open(file_path, "rb") as f:
                img_bytes = f.read()
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[
                    "Provide a detailed technical description and text transcription of this image/diagram for a second brain knowledge repository.",
                    {"inline_data": {"mime_type": "image/jpeg", "data": img_bytes}}
                ]
            )
            if response.text:
                return f"[Visual Content Description & Diagram Analysis]:\n{response.text.strip()}"
        except Exception as e:
            logger.warning(f"Gemini Vision LLM call failed: {e}")

    return f"[Image: {file_path.name} — Non-text visual diagram or graphic with sparse selectable OCR text]"

def parse_image(file_path: str | Path) -> Dict[str, Any]:
    """
    Optical Character Recognition and visual understanding for screenshots, photos, and diagrams.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    title = path.stem.replace("_", " ").replace("-", " ").title()
    
    with Image.open(path) as raw_img:
        orig_width, orig_height = raw_img.size
        processed_img = preprocess_image(raw_img)

    extracted_text, confidence = extract_ocr_with_confidence(processed_img)

    # If text is sparse or confidence low, trigger Vision description
    if len(extracted_text) < 15 and confidence < 40.0:
        logger.info(f"Image '{path.name}' has low OCR confidence ({confidence}%). Attempting Vision analysis.")
        vision_desc = describe_with_vision_llm(path)
        if extracted_text:
            extracted_text = f"{extracted_text}\n\n{vision_desc}"
        else:
            extracted_text = vision_desc

    metadata = {
        "width": orig_width,
        "height": orig_height,
        "ocr_confidence": confidence,
        "format": "IMAGE"
    }

    return {
        "text": extracted_text,
        "title": title,
        "confidence": confidence / 100.0 if confidence > 0 else 0.5,
        "metadata": metadata
    }
