"""
Proactive Communication Skill — ASURA
Allows ASURA to proactively reach out to the master via Telegram.
"""

from skills.telegram_bot.bot import notify_master
from skills.logger import log_audit

def send_message(text: str):
    """
    Sends a proactive message to the Master.
    Use this when you feel curious, want to ask a question, 
    or have news to share.
    """
    log_audit("PROACTIVE_COMM", f"Sending: {text[:50]}")
    notify_master(text)
    return "Message sent to Master."

def register():
    from core.tool_protocol import register_tool
    register_tool(
        name="send_telegram_msg",
        function=send_message,
        description="Send a proactive message to the Master via Telegram. Use for curiosity or questions.",
        category="communication"
    )
