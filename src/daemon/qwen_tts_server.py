import io
import time
import argparse
import tempfile
import os
import re
import json
import requests
import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="ASURA Qwen3.5:0.8b Voice-To-Voice Endpoint")

_whisper_model = None
_kokoro_pipeline = None
_qwen3_tts = None

def _get_qwen3_tts():
    global _qwen3_tts
    if _qwen3_tts is None:
        try:
            from qwen_tts import QwenTTS
            print("Loading Qwen3-TTS-12Hz-1.7B...")
            _qwen3_tts = QwenTTS.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B")
            if torch.cuda.is_available():
                _qwen3_tts = _qwen3_tts.to("cuda")
        except ImportError:
            print("qwen-tts not found. Qwen3 engine will mock.")
            return None
    return _qwen3_tts

def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            print("Loading Faster-Whisper (STT) on CUDA...")
            _whisper_model = WhisperModel("base", device="cuda", compute_type="float16")
        except ImportError:
            print("faster-whisper not found. /transcribe will mock.")
            return None
    return _whisper_model

def _get_kokoro():
    global _kokoro_pipeline
    if _kokoro_pipeline is None:
        try:
            from kokoro import KPipeline
            print("Loading Kokoro TTS...")
            _kokoro_pipeline = KPipeline(lang_code="a") # or 'e' for English
        except ImportError:
            print("kokoro not found. TTS will mock.")
            return None
    return _kokoro_pipeline

@app.on_event("startup")
async def startup_event():
    print("Pre-warming models...")
    engine = os.getenv("ASURA_TTS_ENGINE", "kokoro").lower()
    ollama_url = os.getenv("ASURA_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    chat_model = os.getenv("ASURA_CHAT_MODEL", "qwen3.5:0.8b")

    _get_whisper()
    
    if engine == "kokoro":
        _get_kokoro()
        p = _get_kokoro()
        if p:
            try:
                print("Pre-warming Kokoro synthesis...")
                list(p("Hello", voice="af_heart"))
                print("Kokoro pre-warmed.")
            except Exception as e:
                print(f"Kokoro pre-warm failed: {e}")
    elif engine == "qwen3":
        _get_qwen3_tts()
        p = _get_qwen3_tts()
        if p:
            try:
                print("Pre-warming Qwen3-TTS synthesis...")
                # Qwen3 usually takes text and optional voice/style
                list(p.synthesis("Hello", stream=True))
                print("Qwen3-TTS pre-warmed.")
            except Exception as e:
                print(f"Qwen3-TTS pre-warm failed: {e}")
    
    # Pre-warm Ollama
    try:
        print(f"Pre-warming Ollama at {ollama_url}...")
        requests.post(f"{ollama_url}/api/generate", 
                      json={"model": chat_model, "prompt": "hi", "stream": False, "options": {"num_predict": 1}},
                      timeout=60)
        print("Ollama pre-warmed.")
    except Exception as e:
        print(f"Ollama pre-warm failed: {e}")

@app.get("/health")
def health_check():
    return {"status": "online"}

def generate_voice_chat_stream(text: str):
    """
    Submits user text to local Ollama.
    Streams TTS chunks dynamically using Kokoro.
    """
    # System prompt to suppress thinking logs and enforce speed
    system_prompt = (
        "You are ASURA. Provide a direct, concise, and conversational response to the user. "
        "Do not use <think> tags. Do not print internal monologues. Do not use asterisks or markdown. "
        "Speak plainly and instantly."
    )
    
    ollama_url = os.getenv("ASURA_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    chat_model = os.getenv("ASURA_CHAT_MODEL", "qwen3.5:0.8b")
    engine = os.getenv("ASURA_TTS_ENGINE", "kokoro").lower()
    
    ollama_payload = {
        "model": chat_model,
        "prompt": text,
        "system": system_prompt,
        "stream": True,
        "options": {"temperature": 0.5, "num_ctx": 2048}
    }
    
    pipeline = None
    if engine == "kokoro":
        pipeline = _get_kokoro()
    
    print(f"--- generate_voice_chat_stream start for: {repr(text)} ---")
    tokens_received = 0
    sentence_buffer = ""
    # Regex to split on sentence ends
    sentence_end_re = re.compile(r'(?<=[.!?\n])\s+')
    
    try:
        print(f"Connecting to Ollama (streaming) at {ollama_url}/api/generate ...")
        # Increase timeout for the initial connection
        r = requests.post(f"{ollama_url}/api/generate", json=ollama_payload, stream=True, timeout=120)
        r.raise_for_status()
        
        for line in r.iter_lines():
            if not line: continue
            try:
                chunk = json.loads(line)
                token = chunk.get("response", "")
                if token:
                    tokens_received += 1
                    print(f"Ollama token: {repr(token)}")
                sentence_buffer += token
                
                # Identify full sentences to send to TTS instantly
                if any(p in token for p in [".", "!", "?", "\n"]):
                    parts = sentence_end_re.split(sentence_buffer)
                    
                    # Speak everything except the last unfinished part
                    for complete_sent in parts[:-1]:
                        s_clean = complete_sent.strip()
                        if len(s_clean) > 1:
                            print(f"Sending to Kokoro: {s_clean}")
                            if engine == "kokoro" and pipeline:
                                try:
                                    for _, _, audio_chunk in pipeline(s_clean, voice="af_heart", speed=1.1):
                                        if hasattr(audio_chunk, "cpu"):
                                            audio_chunk = audio_chunk.cpu().numpy()
                                        audio_int16 = (audio_chunk * 32767).astype(np.int16)
                                        yield audio_int16.tobytes()
                                    print(f"Kokoro Success -> {s_clean}")
                                except Exception as e:
                                    print(f"Kokoro synthesis failed for '{s_clean}': {e}")
                            elif engine == "qwen3":
                                try:
                                    qwen = _get_qwen3_tts()
                                    if qwen:
                                        # Use Qwen3-TTS streaming synthesis
                                        for audio_chunk in qwen.synthesis(s_clean, stream=True):
                                            # Assuming output is float32, convert to int16
                                            audio_int16 = (audio_chunk * 32767).astype(np.int16)
                                            yield audio_int16.tobytes()
                                        print(f"Qwen3 Success -> {s_clean}")
                                    else:
                                        print(f"Qwen3 engine failed to load for '{s_clean}'")
                                except Exception as e:
                                    print(f"Qwen3 synthesis failed: {e}")
                            else:
                                print(f"Engine {engine} or Pipeline missing, mock tone for '{s_clean}'")
                                yield (np.sin(2*np.pi*440*np.linspace(0,0.2,int(24000*0.2))) * 0).astype(np.int16).tobytes()
                    
                    sentence_buffer = parts[-1]
                    
            except json.JSONDecodeError as e:
                print(f"JSON error parsing Ollama output: {e} -> {line}")
                pass
    except Exception as e:
        print(f"Ollama error in streaming generator: {e}")
        # Yield a short burst of silence to satisfy the response
        yield b'\x00' * 1024

    if tokens_received == 0:
        print(f"Warning: Ollama returned 0 tokens for prompt: {text}")
        # Try a simple "Hello" if the primary prompt failed
        if text != "Hello":
            print("Retrying with simple 'Hello' prompt...")
            for chunk in generate_voice_chat_stream("Hello"):
                yield chunk
    sentence_buffer = sentence_buffer.strip()
    if len(sentence_buffer) > 1 and pipeline:
        print(f"Sending remaining buffer to Kokoro: {sentence_buffer}")
        try:
            for _, _, audio_chunk in pipeline(sentence_buffer, voice="af_heart", speed=1.1):
                if hasattr(audio_chunk, "cpu"):
                    audio_chunk = audio_chunk.cpu().numpy()
                audio_int16 = (audio_chunk * 32767).astype(np.int16)
                yield audio_int16.tobytes()
                print("Kokoro Success -> remaining buffer")
        except Exception as e:
            print(f"Kokoro synthesis failed on buffer: {e}")


@app.post("/voice_chat_stream")
async def voice_chat_stream(
    audio: UploadFile = File(...),
):
    """
    1. Transcribes incoming WebM audio via faster-whisper.
    2. Streams LLM response to TTS.
    3. Yields PCM bytes instantly.
    """
    model = _get_whisper()
    audio_bytes = await audio.read()
    
    if model is None:
        user_text = "Hello, this is a mock STT test."
    else:
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            segments, _ = model.transcribe(tmp_path, language="en", vad_filter=True)
            user_text = " ".join(seg.text.strip() for seg in segments)
        finally:
            os.unlink(tmp_path)
            
    print(f"STT result: '{user_text}'")
    if not user_text.strip():
        # Fallback if empty
        user_text = "I heard some sound, but couldn't make out the words. Please speak clearly, Master."

    return StreamingResponse(
        generate_voice_chat_stream(user_text),
        media_type="audio/pcm"
    )

if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()
    
    print(f"🚀 Starting Real-Time Voice-To-Voice Server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)
