from __future__ import annotations

"""Audio generator skill.

This skill exposes two helper functions:

* :func:`generate_tone` – generate a mono WAV file containing a pure sine
  wave.  Parameters:

  - ``freq`` – frequency in Hz.
  - ``duration`` – duration in seconds.
  - ``filename`` – output file path.

* :func:`speak_text` – generate speech audio using the `gtts` library.
  Parameters:

  - ``text`` – the string to speak.
  - ``filename`` – output file path.

Both functions return the path of the created file.
"""

import math
import os
import wave
from pathlib import Path

try:
    # ``gtts`` is optional; we import lazily to keep the skill lightweight.
    from gtts import gTTS
except Exception:  # pragma: no cover - dependency optional
    gTTS = None

__all__ = ["generate_tone", "speak_text", "generate_audio"]


def generate_tone(freq: float, duration: float, filename: str | os.PathLike, sample_rate: int = 44100, amplitude: float = 0.5) -> str:
    """Generate a mono WAV file with a sine wave.

    Parameters
    ----------
    freq: float
        Frequency of the tone in Hertz.
    duration: float
        Length of the tone in seconds.
    filename: str | PathLike
        Destination path for the .wav file.
    sample_rate: int, optional
        Sampling rate, default 44100 Hz.
    amplitude: float, optional
        Peak amplitude (0.0 to 1.0).  Default 0.5.

    Returns
    -------
    str
        Absolute path of the created file.
    """
    num_samples = int(sample_rate * duration)
    # Prepare audio samples
    samples = [
        int(amplitude * 32767 * math.sin(2 * math.pi * freq * t / sample_rate))
        for t in range(num_samples)
    ]

    # Ensure output directory exists
    Path(filename).parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(filename), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16‑bit audio
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples))

    return str(Path(filename).resolve())


def generate_audio(text: str, output_path: str | os.PathLike, lang: str = "en", driver: str = "gtts") -> str:
    """Generate audio from text.

    Parameters
    ----------
    text: str
        Text to convert.
    output_path: str | PathLike
        Destination file path (mp3 or wav).
    lang: str
        Language code.
    driver: str
        TTS backend: "gtts" or "pyttsx3".

    Returns
    -------
    str
        Absolute path to the generated file.
    """
    if driver == "gtts":
        return speak_text(text, output_path, lang)
    else:
        raise RuntimeError("Only gtts driver is implemented in this version.")

def speak_text(text: str, filename: str | os.PathLike, lang: str = "en", tld: str = "com") -> str:
    """Generate speech audio from text using gTTS.

    Parameters
    ----------
    text: str
        The text to convert to speech.
    filename: str | PathLike
        Destination path for the MP3 file.
    lang: str, optional
        Language code (default ``"en"``).
    tld: str, optional
        Top‑level domain to influence accent (default ``"com"``).

    Returns
    -------
    str
        Absolute path of the created file.

    Raises
    ------
    RuntimeError
        If gTTS is not installed.
    """
    if gTTS is None:
        raise RuntimeError("gtts library is required for speak_text(). Install with 'pip install gtts'.")

    tts = gTTS(text=text, lang=lang, tld=tld)
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    tts.save(str(filename))
    return str(Path(filename).resolve())


# End of audio_generator.py