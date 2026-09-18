import io
import math
import logging
import wave
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
from backend.config import settings

logger = logging.getLogger(__name__)

def calculate_audio_rms(file_path: Path) -> Tuple[float, float]:
    """
    Calculate duration and Root Mean Square (RMS) energy level of an audio file:
    RMS = sqrt(1/N * sum(x_i^2))
    """
    try:
        # Check standard WAV first
        if file_path.suffix.lower() == ".wav":
            with wave.open(str(file_path), "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                duration = n_frames / float(framerate) if framerate > 0 else 0.0
                
                raw_bytes = wf.readframes(n_frames)
                if sampwidth == 2:
                    dtype = np.int16
                elif sampwidth == 4:
                    dtype = np.int32
                else:
                    dtype = np.uint8

                data = np.frombuffer(raw_bytes, dtype=dtype).astype(np.float32)
                if len(data) == 0:
                    return 0.0, 0.0
                
                # Normalize to [-1.0, 1.0]
                max_val = np.iinfo(dtype).max if dtype != np.uint8 else 255.0
                data = data / max_val
                rms = float(np.sqrt(np.mean(data ** 2)))
                return rms, duration
    except Exception as e:
        logger.debug(f"Direct WAV RMS check skipped ({e}), proceeding with fallback calculation.")

    # Generic file size / non-zero byte approximation
    file_size = file_path.stat().st_size
    if file_size < 1024:
        return 0.001, 0.0
    return 0.05, 10.0  # Assumed non-empty

def transcribe_audio_whisper(file_path: Path) -> Tuple[str, str]:
    """Transcribe audio with faster-whisper or Groq Audio API."""
    # 1. Try Groq Whisper API if key available (extremely fast sub-second)
    if settings.GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)
            with open(file_path, "rb") as f:
                transcription = client.audio.transcriptions.create(
                    file=(file_path.name, f.read()),
                    model="whisper-large-v3",
                    response_format="json",
                    temperature=0.0
                )
            return transcription.text.strip(), "en"
        except Exception as e:
            logger.warning(f"Groq Whisper transcription API failed: {e}")

    # 2. Try local faster-whisper
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base.en", compute_type="int8", device="cpu")
        segments, info = model.transcribe(str(file_path), beam_size=5, vad_filter=True)
        text_parts = [segment.text.strip() for segment in segments]
        return " ".join(text_parts).strip(), info.language
    except ImportError:
        logger.debug("faster-whisper not installed locally.")
    except Exception as e:
        logger.error(f"Local Whisper transcription error: {e}")

    return f"[Voice Memo / Audio Recording: {file_path.name}]", "en"

def parse_audio(file_path: str | Path) -> Dict[str, Any]:
    """
    Speech-to-text conversion for voice memos, recorded meetings, and audio notes.
    Includes RMS energy silence detection.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    title = path.stem.replace("_", " ").replace("-", " ").title()
    rms, duration = calculate_audio_rms(path)
    
    # Empty audio / silence check
    if rms < 0.005 and duration > 0.5:
        logger.info(f"Audio file '{path.name}' flagged as silent (RMS: {rms:.6f}).")
        return {
            "text": f"[Silent Audio Note: {path.name} (RMS energy {rms:.4f} below threshold)]",
            "title": title,
            "duration_seconds": duration,
            "is_empty": True,
            "metadata": {
                "rms_energy": rms,
                "duration_seconds": duration,
                "status": "empty_audio",
                "format": "AUDIO"
            }
        }

    transcribed_text, lang = transcribe_audio_whisper(path)
    if not transcribed_text:
        transcribed_text = f"[Audio Memo: {path.name} (No detectable speech)]"

    return {
        "text": transcribed_text,
        "title": title,
        "duration_seconds": duration,
        "language": lang,
        "is_empty": False,
        "metadata": {
            "rms_energy": rms,
            "duration_seconds": duration,
            "language": lang,
            "format": "AUDIO"
        }
    }
