"""Audio Generator Skill

Provides simple utilities to create audio files.

Functions exposed:
    generate_tone
    speak_text
    generate_audio
"""

from .audio_generator import generate_tone, speak_text, generate_audio

__all__ = ["generate_tone", "speak_text", "generate_audio"]
