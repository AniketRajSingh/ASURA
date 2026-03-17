# ============================================================
# skills/voice/interface.py — Qwen-Optimized Voice Interface
# Routing through scripts/qwen_tts_server for high-speed V2V.
# Includes automatic format normalization (OGG -> WAV).
# ============================================================

import os
import requests
import subprocess
from settings import settings as config
from skills.logger import log_audit, log_app

# Default to your specialized Qwen server port
VOICE_SERVER_URL = getattr(config, "VOICE_SERVER_URL", "http://127.0.0.1:8090")

def _ensure_wav(audio_path: str) -> str:
    """Ensure audio is in a format compatible with Whisper (WAV/WebM)."""
    if audio_path.endswith((".wav", ".webm")):
        return audio_path
    
    # Target path
    wav_path = audio_path.rsplit(".", 1)[0] + "_normalized.wav"
    try:
        log_app(f"VOICE: Normalizing {os.path.basename(audio_path)} to WAV...")
        subprocess.run(
            ["ffmpeg", "-y", "-i", audio_path, "-ar", "16000", "-ac", "1", wav_path],
            capture_output=True, check=True
        )
        return wav_path
    except Exception as e:
        log_app(f"VOICE: Normalization failed: {e}")
        return audio_path

def voice_to_voice(audio_path: str, output_path: str = "response.pcm") -> str:
    """
    Perform high-speed Voice-to-Voice (Audio In -> LLM -> Audio Out).
    """
    if not os.path.isfile(audio_path):
        return f"Error: Audio file not found at {audio_path}"

    # Normalize format (handle Telegram .ogg)
    norm_path = _ensure_wav(audio_path)
    
    log_app(f"VOICE: Starting V2V loop for {os.path.basename(norm_path)}")
    try:
        with open(norm_path, "rb") as f:
            files = {"audio": (os.path.basename(norm_path), f, "audio/wav")}
            resp = requests.post(f"{VOICE_SERVER_URL}/voice_chat_stream", files=files, stream=True, timeout=120)
            
        if resp.status_code == 200:
            with open(output_path, "wb") as out:
                for chunk in resp.iter_content(chunk_size=4096):
                    out.write(chunk)
            log_audit("VOICE", f"V2V Success: Generated {output_path}")
            return output_path
    except Exception as e:
        log_app(f"VOICE: V2V request failed: {e}")
    finally:
        if norm_path != audio_path and os.path.exists(norm_path):
            os.remove(norm_path)

    return ""

def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio using the Qwen server."""
    if not os.path.isfile(audio_path):
        return "Error: File not found."

    norm_path = _ensure_wav(audio_path)
    try:
        with open(norm_path, "rb") as f:
            files = {"audio": (os.path.basename(norm_path), f, "audio/wav")}
            resp = requests.post(f"{VOICE_SERVER_URL}/transcribe", files=files, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("text", "")
    except Exception as e:
        log_app(f"VOICE: Transcription failed: {e}")
    finally:
        if norm_path != audio_path and os.path.exists(norm_path):
            os.remove(norm_path)
            
    return "STT Failed. Check qwen_tts_server."

def text_to_speech(text: str, output_path: str = None) -> str:
    """Generate audio from text using Qwen TTS engine."""
    if not output_path:
        output_path = os.path.join(config.DATA_DIR, "voice_out.wav")

    try:
        resp = requests.post(
            f"{VOICE_SERVER_URL}/synthesize",
            data={"text": text, "voice": "qwen3", "speed": 1.0},
            timeout=30
        )
        if resp.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return output_path
    except Exception: pass
    return ""
