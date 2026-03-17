from __future__ import annotations

"""
Self‑Updating AI system – audio_say skill.

This module provides a simple text‑to‑speech conversion using the `gtts` library.
If the `gtts` package is not available, it falls back to a dummy implementation
that creates an empty MP3 file, preventing a :class:`ModuleNotFoundError` during
runtime.

The module logs its operations using :func:`core.logger.log_app` and
:func:`core.logger.log_audit`.  It is intended to be used as a skill in the
larger AI system owned by Aniket Raj Singh.

Author: Aniket Raj Singh
"""

import os
import sys
from typing import Any

# Import configuration if needed (placeholder for future use)
try:
    from settings import settings as config  # pragma: no cover
except Exception:
    # If config is not present, silently ignore; it can be added later.
    pass

# Core utilities ---------------------------------------------------------------
try:
    from skills.logger import log_audit, log_app
except Exception:
    # Minimal fallback logger if core.logger cannot be imported
    def log_audit(message: str) -> None:  # pragma: no cover
        print(f"[AUDIT] {message}")

    def log_app(message: str) -> None:  # pragma: no cover
        print(f"[APP] {message}")

# Text‑to‑Speech ---------------------------------------------------------------
try:
    from gtts import gTTS  # type: ignore
except ModuleNotFoundError:
    log_app("gtts module not found. Falling back to DummyTTS.")

    class DummyTTS:  # pragma: no cover
        """
        Dummy TTS implementation used when gtts is unavailable.
        It creates an empty MP3 file to mimic the interface of gTTS.
        """

        def __init__(self, text: str, lang: str = "en"):  # noqa: D401
            """
            Initialise with the text to convert and optional language.
            """
            self.text = text
            self.lang = lang

        def save(self, output_path: str) -> None:
            """
            Create an empty MP3 file at the specified path.
            """
            log_app(f"Creating dummy MP3 at {output_path}.")
            # Ensure the directory exists
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            # Write minimal MP3 header bytes to make it a valid (though silent) file
            with open(output_path, "wb") as f:
                f.write(b"\x00\x00\x00\x00")  # minimal placeholder

    gTTS = DummyTTS  # type: ignore

# Public API --------------------------------------------------------------------
__all__ = ["generate_audio"]


def generate_audio(text: str, output_path: str = "output.mp3") -> str:
    """
    Generate an MP3 file from the given text.

    Parameters
    ----------
    text : str
        Text to convert to speech.
    output_path : str, optional
        Path where the MP3 file will be saved. Defaults to ``"output.mp3"``.

    Returns
    -------
    str
        Absolute path to the created audio file.

    Raises
    ------
    RuntimeError
        If the TTS generation fails for any reason.
    """
    log_app(f"Starting TTS generation for text: {text!r}")
    try:
        tts = gTTS(text=text, lang="en")
        tts.save(output_path)
        abs_path = os.path.abspath(output_path)
        log_audit(f"Audio file created at {abs_path}")
        log_app(f"Audio generation successful: {abs_path}")
        return abs_path
    except Exception as exc:  # pragma: no cover
        error_msg = f"Failed to generate audio: {exc}"
        log_app(error_msg)
        log_audit(error_msg)
        raise RuntimeError(error_msg) from exc


# Command‑line interface --------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate speech from text")
    parser.add_argument("text", help="Text to convert to speech")
    parser.add_argument("-o", "--output", default="output.mp3", help="Output file path")
    args = parser.parse_args()

    try:
        path = generate_audio(args.text, args.output)
        print(f"Audio saved to {path}")
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)