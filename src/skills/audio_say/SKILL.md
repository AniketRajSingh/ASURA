---
name: audio_say
description: "Converts text to speech and saves it as an MP3 file using gTTS."
entry_point: audio_say.py
---

# Audio Say Skill

Provides text-to-speech (TTS) capabilities, allowing the system to generate audio files from text input. It primarily uses the `gTTS` (Google Text-to-Speech) library, with a silent fallback if the library is unavailable.

### 🔧 Tools / Functions
- `generate_audio(text, output_path="output.mp3")`: Converts the provided text into an MP3 audio file and returns the absolute path to the generated file.

### 📝 Examples
- "Say 'Hello, how are you?'" -> Generates `output.mp3` with the spoken text.
- "Generate audio for the summary" -> Creates an audio file of the summary text.

### 🛠️ Requirements
- `gtts` library (recommended for actual audio generation)
- Internet connection (required by gTTS for speech synthesis)
