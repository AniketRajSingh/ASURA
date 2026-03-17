---
name: voice
description: "Voice interface for high-quality speech-to-text (Whisper) and cross-platform text-to-speech conversion."
entry_point: interface.py
---

# Voice Skill

Provides multimodal capabilities for processing audio inputs and generating spoken responses. Supports macOS, Windows, and Linux.

### 🔧 Tools / Functions
- `transcribe_audio(audio_path: str) -> str`: Convert audio files to text using Whisper (local or via Ollama).
- `text_to_speech(text: str, output_path: str = None) -> str`: Convert text to audio using the best available system engine (say, PowerShell, espeak).

### 📝 Examples
- "Transcribe this voice note" -> Processes audio file and returns text.
- "Say 'System online'" -> Generates and plays/saves an audio file of the speech.

### 🛠️ Requirements
- `ffmpeg` for audio format conversion.
- `whisper` model (local or Ollama).
- `espeak` or `pico2wave` (Linux only).
