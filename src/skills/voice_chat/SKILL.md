---
name: voice_chat
description: "Real-time voice interaction layer for hands-free command and response."
entry_point: pipeline.py
---

# Voice Chat

Enables real-time, hands-free voice interaction with ASURA. It handles the full pipeline from audio recording and speech-to-text (STT) to LLM processing and text-to-speech (TTS) synthesis.

### 🔧 Tools / Functions
- `voice_chat_loop()`: Interactive voice chat loop with VAD (Voice Activity Detection), STT, LLM, and streaming TTS.
- `voice_chat_single(audio_bytes)`: Process a single voice turn for external integrations (e.g., Telegram).

### 📝 Examples
- "Start voice chat" -> Activates the microphone and waits for speech.
- "Process this audio message" -> Returns the synthesized AI response as audio bytes.

### 🛠️ Requirements
- `sounddevice`, `numpy`, `soundfile`
- Remote voice server running `faster-whisper` and `Kokoro` (configured via `VOICE_SERVER_URL`)
