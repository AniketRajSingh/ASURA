# ============================================================
# tests/test_duplex_voice.py — Verification of Real-Time Duplex Voice Engine
# ============================================================

import struct
import pytest
import asyncio
from skills.voice_chat.duplex_stream import AudioVAD, DuplexSession, duplex_engine
from core.consciousness import consciousness


def test_vad_silence_detection():
    vad = AudioVAD(energy_threshold=500.0)
    # 100 samples of zero (silence)
    silence_pcm = struct.pack("<100h", *([0] * 100))
    res = vad.process_chunk(silence_pcm)
    assert res["rms"] == 0.0
    assert res["is_speech"] is False
    assert res["speech_started"] is False


def test_vad_speech_detection():
    vad = AudioVAD(energy_threshold=500.0)
    # 100 samples of loud sound (amplitude 5000)
    loud_pcm = struct.pack("<100h", *([5000] * 100))
    res = vad.process_chunk(loud_pcm)
    assert res["rms"] >= 5000.0
    assert res["is_speech"] is True
    assert res["speech_started"] is True


def test_duplex_session_barge_in():
    session = duplex_engine.get_or_create_session("test_sess_bargein")
    session.is_agent_speaking = True

    # User speaks loudly while agent is speaking
    loud_pcm = struct.pack("<100h", *([4000] * 100))
    ingest_res = session.ingest_audio_chunk(loud_pcm)

    # Must detect barge in and stop agent speaking
    assert ingest_res["barge_in_triggered"] is True
    assert session.is_agent_speaking is False
    assert session._cancel_token.is_set()

    # Verify thought logged in consciousness
    thoughts = consciousness.get_recent_thoughts(limit=5)
    barge_thoughts = [t for t in thoughts if t["thought_type"] == "barge_in"]
    assert len(barge_thoughts) > 0


@pytest.mark.asyncio
async def test_duplex_streaming_generation(monkeypatch):
    session = duplex_engine.get_or_create_session("test_sess_stream")
    tokens = []

    async def _mock_gen():
        for chunk in ["Hello ", "Master, ", "I am ", "ASURA."]:
            yield chunk

    async def _mock_handle_message(*args, **kwargs):
        return _mock_gen()

    monkeypatch.setattr("skills.voice_chat.duplex_stream.handle_message", _mock_handle_message)

    async def _on_token(t):
        tokens.append(t)

    # Run stream with mock input
    reply = await session.generate_response_stream(
        user_text="What is your name?",
        on_token=_on_token,
    )
    assert reply == "Hello Master, I am ASURA."
    assert "".join(tokens) == "Hello Master, I am ASURA."
    assert session.is_agent_speaking is False
