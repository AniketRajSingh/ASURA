# ============================================================
# skills/voice_chat/pipeline.py — Voice Conversation Pipeline
#
# Orchestrates a full voice conversation loop:
#   1. Record audio from microphone (or accept audio bytes)
#   2. STT via remote faster-whisper (batch_size=8)
#   3. LLM via gateway (same as text chat)
#   4. TTS via remote Kokoro
#   5. Play audio response
#
# Can be used standalone (CLI) or integrated with the gateway.
# ============================================================

import io
import sys
import time
import threading
import json
import requests
from skills.logger import log_app
from skills.voice_chat.client import (
    transcribe, synthesize, synthesize_stream, detect_speech, check_health,
    VOICE_SERVER_URL
)

# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION = 0.5  # seconds per chunk for VAD


def voice_chat_loop(
    user_id: str = "voice_user",
    ollama_url: str = "http://192.168.3.173:11435",
    voice: str = "af_heart",
    speed: float = 1.0,
):
    """
    Interactive voice chat loop.

    Flow per turn:
      1. Record until silence detected (VAD)
      2. Transcribe audio → text (faster-whisper, batch_size=8)
      3. Send text through gateway → get AI response
      4. Synthesize response → audio (Kokoro)
      5. Play audio

    Args:
        user_id: Session ID for gateway
        ollama_url: Ollama endpoint for LLM
        voice: Kokoro voice ID
        speed: TTS speed multiplier
    """
    try:
        import sounddevice as sd
        import numpy as np
    except ImportError:
        print("ERROR: sounddevice not installed. Run: pip install sounddevice")
        return

    print("\n" + "=" * 50)
    print("  ASURA Voice Chat")
    print("  Voice Server:", VOICE_SERVER_URL)
    print("  Ollama:", ollama_url)
    print("  Voice:", voice, "| Speed:", speed)
    print("=" * 50)

    # Check voice server health
    health = check_health()
    if health.get("status") == "offline":
        print(f"\nVoice server offline at {VOICE_SERVER_URL}")
        print(f"  Error: {health.get('error', 'Unknown')}")
        print(f"\n  Start it on ippc:")
        print(f"    ssh ippc")
        print(f"    cd ~/tf-voice && source .venv/bin/activate")
        print(f"    python voice_server.py")
        return

    print(f"\n  Voice server: ONLINE")
    print(f"  Models: {health.get('models', {})}")
    print(f"\n  Press Ctrl+C to stop.\n")

    # Import gateway for LLM routing
    try:
        from core.gateway import handle_message
    except ImportError:
        handle_message = None

    turn = 0
    while True:
        try:
            turn += 1
            print(f"--- Turn {turn} ---")

            # ── 1. Record audio ──────────────────────────────
            print("  Listening... (speak now, silence to stop)")
            audio_chunks = []
            silence_count = 0
            max_silence = 3  # Stop after 1.5s of silence

            def _record_callback(indata, frames, time_info, status):
                audio_chunks.append(indata.copy())

            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="float32",
                blocksize=int(SAMPLE_RATE * CHUNK_DURATION),
                callback=_record_callback,
            )

            with stream:
                # Wait for speech to start, then record until silence
                recording = True
                speech_started = False

                while recording:
                    time.sleep(CHUNK_DURATION)

                    if len(audio_chunks) == 0:
                        continue

                    # Check last chunk for speech
                    last_chunk = audio_chunks[-1]
                    energy = float(np.abs(last_chunk).mean())

                    if energy > 0.01:  # Speech threshold
                        speech_started = True
                        silence_count = 0
                    elif speech_started:
                        silence_count += 1
                        if silence_count >= max_silence:
                            recording = False

                    # Safety: max 30 seconds
                    total_duration = len(audio_chunks) * CHUNK_DURATION
                    if total_duration > 30:
                        recording = False

            if not audio_chunks:
                print("  No audio captured.")
                continue

            # Combine chunks into WAV bytes
            audio_data = np.concatenate(audio_chunks)
            wav_buf = io.BytesIO()
            import soundfile as sf
            sf.write(wav_buf, audio_data, SAMPLE_RATE, format="WAV")
            audio_bytes = wav_buf.getvalue()

            duration = len(audio_data) / SAMPLE_RATE
            print(f"  Recorded {duration:.1f}s of audio")

            # ── 2. Transcribe ────────────────────────────────
            print("  Transcribing...")
            t0 = time.time()
            result = transcribe(audio_bytes, batch_size=8)
            t1 = time.time()

            user_text = result.get("text", "").strip()
            if not user_text:
                print("  (no speech detected)")
                continue

            print(f"  You: {user_text}  ({t1-t0:.1f}s)")

            # ── 3. LLM Response ──────────────────────────────
            print("  Thinking...")
            t0 = time.time()

            if handle_message:
                ai_text = handle_message(user_id, user_text, channel="voice", stream=False)
            else:
                # Fallback: direct Ollama
                resp = requests.post(
                    f"{ollama_url}/api/generate",
                    json={"model": "gpt-oss:20b", "prompt": user_text, "stream": False},
                    timeout=60,
                )
                ai_text = resp.json().get("response", "")

            t1 = time.time()
            ai_text = ai_text.strip() if ai_text else "Sorry, I couldn't generate a response."
            print(f"  AI: {ai_text[:100]}{'...' if len(ai_text) > 100 else ''}  ({t1-t0:.1f}s)")

            # ── 4. Synthesize & Play (Streaming) ────────────────
            print("  Speaking...")
            t0 = time.time()
            first_chunk = True

            # Use RawOutputStream to instantly stream PCM bytes to the speaker
            stream_out = sd.RawOutputStream(
                samplerate=24000,  # Must match the Qwen3-TTS server sample rate
                channels=1,
                dtype='int16'
            )

            try:
                with stream_out:
                    for chunk in synthesize_stream(ai_text, voice=voice, speed=speed):
                        if first_chunk:
                            print(f"  TTS First Byte Latency: {time.time() - t0:.2f}s")
                            first_chunk = False
                        
                        # Write raw PCM chunk directly to speaker buffer
                        stream_out.write(chunk)
                    
                    if first_chunk:
                        print("  (TTS failed or returned empty stream)")
            except Exception as stream_err:
                print(f"  Playback error: {stream_err}")

            print()

        except KeyboardInterrupt:
            print("\n\n  Voice chat ended.")
            break
        except Exception as e:
            print(f"  Error: {e}")
            continue


def voice_chat_single(audio_bytes: bytes, user_id: str = "voice_user") -> bytes:
    """
    Process a single voice turn (for API/Telegram integration).

    Args:
        audio_bytes: Input audio (WAV)
        user_id: Session ID

    Returns:
        Response audio (WAV bytes)
    """
    from skills.logger import log_app
    log_app(f"voice_chat_single: Received {len(audio_bytes)} bytes of audio.")
    
    # Debug dump to disk
    with open("debug_audio.webm", "wb") as f:
        f.write(audio_bytes)
    
    # New All-In-One Streaming Pipeline (Bypass Mac LLM)
    try:
        from skills.voice_chat.client import voice_chat_direct_stream
        return voice_chat_direct_stream(audio_bytes)
    except Exception as e:
        log_app(f"voice_chat_single mega-endpoint failed: {e}")
        return synthesize(f"Error connecting to Voice Stream: {e}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, "src")

    voice = "af_heart"
    speed = 1.0

    for arg in sys.argv[1:]:
        if arg.startswith("--voice="):
            voice = arg.split("=", 1)[1]
        elif arg.startswith("--speed="):
            speed = float(arg.split("=", 1)[1])

    voice_chat_loop(voice=voice, speed=speed)
