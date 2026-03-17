---
name: audio_generator
description: "Generates pure audio tones and converts text to speech using the gTTS library."
entry_point: audio_generator.py
---

# Audio Generator

Creates simple audio files, including pure frequency tones for alerts and speech from text for audible responses.

### 🔧 Tools / Functions
- `generate_tone(freq: float, duration: float, filename: str)`: Create a WAV file with a pure sine wave tone.
- `generate_audio(text: str, output_path: str, driver: str = "gtts")`: High-level text-to-speech generation.
- `speak_text(text: str, filename: str)`: Directly use gTTS to create an MP3 speech file.

### 📝 Examples
- "Generate a beep sound" -> Creates a short high-frequency WAV file.
- "Create an audio version of this summary" -> Generates an MP3 file of the provided text.

### 🛠️ Requirements
- `gtts` (Google Text-to-Speech) library.
