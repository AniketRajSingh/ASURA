# ============================================================
# skills/voice_chat/client.py — Voice API Client
#
# Connects to the remote voice server (192.168.3.173:8090)
# for STT (faster-whisper) and TTS (Kokoro) operations.
# ============================================================

import io
import requests
from settings import settings
from skills.logger import log_app


# Unified Voice Server URL from settings
VOICE_SERVER_URL = settings.VOICE_SERVER_URL


def transcribe(audio_bytes: bytes, language: str = "en", batch_size: int = 8) -> dict:
    """
    Send audio to the remote faster-whisper server for transcription.

    Args:
        audio_bytes: Raw WAV/MP3/WebM/OGG audio data
        language: Language code (default: "en")
        batch_size: Whisper batch size (default: 8)

    Returns:
        {"text": "...", "language": "en", "duration_seconds": 0.5}
    """
    try:
        # Determine format from magic bytes
        filename = "audio.wav"
        mime = "audio/wav"
        if audio_bytes.startswith(b"\x1a\x45\xdf\xa3"):
            filename = "audio.webm"
            mime = "audio/webm"
        elif audio_bytes.startswith(b"OggS"):
            filename = "audio.ogg"
            mime = "audio/ogg"
        elif audio_bytes.startswith(b"ID3") or audio_bytes.startswith(b"\xff\xfb"):
            filename = "audio.mp3"
            mime = "audio/mpeg"

        resp = requests.post(
            f"{VOICE_SERVER_URL}/transcribe",
            files={"audio": (filename, io.BytesIO(audio_bytes), mime)},
            data={"language": language, "batch_size": batch_size},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        log_app(f"Voice server unreachable at {VOICE_SERVER_URL}")
        return {"text": "", "error": f"Voice server offline at {VOICE_SERVER_URL}"}
    except Exception as e:
        return {"text": "", "error": str(e)}


def synthesize(text: str, voice: str = "default", speed: float = 1.0) -> bytes:
    """
    Send text to the remote TTS server for synthesis.
    Wraps the raw PCM stream into a valid WAV format for browser playback.

    Args:
        text: Text to speak
        voice: Voice ID
        speed: Speech speed multiplier

    Returns:
        WAV audio bytes
    """
    try:
        raw_pcm = b""
        for chunk in synthesize_stream(text, voice, speed):
            if isinstance(chunk, bytes):
                raw_pcm += chunk
                
        if not raw_pcm:
            return b""
            
        import wave
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, 'wb') as wav_file:
            wav_file.setnchannels(1)            # Mono
            wav_file.setsampwidth(2)            # 16-bit (2 bytes)
            wav_file.setframerate(24000)        # 24kHz Qwen TTS sample rate
            wav_file.writeframes(raw_pcm)
            
        return wav_buf.getvalue()
    except Exception as e:
        log_app(f"TTS error: {e}")
        return b""


def synthesize_stream(text: str, voice: str = "default", speed: float = 1.0):
    """
    Generator that yields streaming WAV audio bytes as they 
    arrive from the dedicated Qwen3-TTS server.
    """
    try:
        with requests.post(
            f"{VOICE_SERVER_URL}/synthesize_stream",
            json={"text": text, "voice": voice, "speed": speed},
            stream=True,
            timeout=30
        ) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk
    except Exception as e:
        log_app(f"TTS streaming error: {e}")
        return b""

def voice_chat_direct_stream(audio_bytes: bytes) -> bytes:
    """
    Sends the raw microphone WebM payload to the remote IPPC 
    all-in-one endpoint, which:
    1. Transcribes it
    2. Runs it through Ollama qwen:0.5b locally
    3. Synthesizes it via Kokoro
    4. Streams back raw 16-bit PCM Audio
    """
    try:
        # Determine format from magic bytes
        filename = "audio.wav"
        mime = "audio/wav"
        if audio_bytes.startswith(b"\x1a\x45\xdf\xa3"):
            filename = "audio.webm"
            mime = "audio/webm"
        elif audio_bytes.startswith(b"OggS"):
            filename = "audio.ogg"
            mime = "audio/ogg"

        raw_pcm = b""
        with requests.post(
            f"{VOICE_SERVER_URL}/voice_chat_stream",
            files={"audio": (filename, io.BytesIO(audio_bytes), mime)},
            stream=True,
            timeout=120
        ) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    raw_pcm += chunk
                    
        import wave
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, 'wb') as wav_file:
            wav_file.setnchannels(1)            # Mono
            wav_file.setsampwidth(2)            # 16-bit (2 bytes)
            wav_file.setframerate(24000)        # 24kHz Kokoro sample rate
            wav_file.writeframes(raw_pcm)
            
        return wav_buf.getvalue()
    except Exception as e:
        log_app(f"Direct Voice Stream error: {e}")
        return b""


def detect_speech(audio_bytes: bytes) -> dict:
    """
    Send audio to the remote Silero VAD for voice activity detection.

    Returns:
        {"has_speech": True/False, "segments": [...]}
    """
    try:
        resp = requests.post(
            f"{VOICE_SERVER_URL}/vad",
            files={"audio": ("audio.wav", io.BytesIO(audio_bytes), "audio/wav")},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"has_speech": False, "error": str(e)}


def check_health() -> dict:
    """Check if the voice server is reachable and models are loaded."""
    try:
        resp = requests.get(f"{VOICE_SERVER_URL}/health", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"status": "offline", "error": str(e)}
