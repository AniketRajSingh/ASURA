# ============================================================
# core/context_manager.py — Context Window Management
#
# Claude Code-style context compaction: auto-summarizes old
# messages instead of hard-truncating. Preserves task continuity.
# ============================================================

import asyncio
from settings import settings as config
from core.llm import call_llm
from skills.logger import log_audit

# Max messages before compaction triggers
COMPACT_THRESHOLD = 12
# Max tokens before compaction triggers (estimated)
TOKEN_LIMIT = 4096
# Keep the most recent N messages intact
KEEP_RECENT = 6


async def compact_history(history: list[dict]) -> list[dict]:
    """
    Compact conversation history to prevent context overflow.

    Instead of hard-truncating to the last 10 messages (losing all
    earlier context), this summarizes old messages into a single
    context block and keeps recent messages intact.

    Args:
        history: Full conversation history

    Returns:
        Compacted history: [summary_msg, ...recent_messages]
    """
    current_tokens = estimate_tokens(history)
    
    if len(history) <= COMPACT_THRESHOLD and current_tokens <= TOKEN_LIMIT:
        return history

    # Split: old messages to summarize, recent to keep
    old_messages = history[:-KEEP_RECENT]
    recent_messages = history[-KEEP_RECENT:]

    # Build summary of old messages
    summary = await _summarize_messages(old_messages)

    log_audit("CONTEXT", f"Compacted {len(old_messages)} messages into summary ({len(summary)} chars, ~{current_tokens} tokens handled)")

    # Return: summary + recent messages
    compacted = [
        {"role": "user", "content": f"[EARLIER CONTEXT SUMMARY]\n{summary}\n[/EARLIER CONTEXT SUMMARY]"}
    ] + recent_messages

    return compacted


async def _summarize_messages(messages: list[dict]) -> str:
    """Summarize a list of messages using the LLM (acting as a compression agent)."""
    # Build detailed conversation text for the agent to analyze
    conv_text = ""
    for m in messages:
        role = m.get("role", "?").upper()
        content = m.get("content", "")
        # Include tool names if present in content (ReAct style)
        conv_text += f"[{role}]: {content[:500]}\n"

    prompt = (
        "ACT AS THE ASURA CONTEXT COMPRESSION AGENT.\n"
        "Your goal is to distill the following conversation history into a high-density 'Context Injection' block.\n"
        "DO NOT just summarize. You MUST preserve:\n"
        "1. DEFINED GOALS: What is the user ultimately trying to achieve?\n"
        "2. TECHNICAL STATE: Active file paths, specific code changes discussed, or git diff summaries.\n"
        "3. PENDING TASKS: What was the very next step intended before this compression?\n"
        "4. KEY PREFERENCES: Any style, structural, or logic rules the user established.\n\n"
        "FORMAT: Use concise bullet points. Max 1000 characters.\n\n"
        f"--- CONVERSATION TO COMPRESS ---\n{conv_text[:6000]}"
    )

    try:
        # Use summary model (standardized)
        # Force a short timeout so chat doesn't hang; fall back to text summary quickly
        res = await call_llm(prompt, model=getattr(config, "OLLAMA_MODEL_SUMMARY", config.OLLAMA_MODEL_FAST), stream=False, timeout=15)
        if not res or len(res.strip()) < 10:
            log_audit("CONTEXT", "LLM summary too short, using fallback")
            return _fallback_summary(messages)
        return res[:1500]
    except Exception as e:
        # Fallback: create a simple text summary without LLM
        log_audit("CONTEXT", f"LLM summary failed ({e.__class__.__name__}), using text fallback")
        return _fallback_summary(messages)


def _fallback_summary(messages: list[dict]) -> str:
    """Create a basic summary without LLM (fallback)."""
    user_msgs = [m["content"][:100] for m in messages if m.get("role") == "user"]
    tool_actions = []
    for m in messages:
        content = m.get("content", "")
        if "[OBSERVATION from" in content:
            # Extract tool name
            start = content.find("from ") + 5
            end = content.find("]", start)
            if start > 4 and end > start:
                tool_actions.append(content[start:end])

    lines = ["Earlier conversation summary:"]
    if user_msgs:
        lines.append(f"• User requests: {'; '.join(user_msgs[:5])}")
    if tool_actions:
        lines.append(f"• Tools used: {', '.join(set(tool_actions))}")
    lines.append(f"• Total messages: {len(messages)}")
    return "\n".join(lines)


def estimate_tokens(messages: list[dict]) -> int:
    """Rough token estimate (4 chars ≈ 1 token)."""
    total_chars = sum(len(m.get("content", "")) for m in messages)
    return total_chars // 4
