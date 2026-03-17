# skills/telegram_bot — Telegram bot interface skill
from .bot import start_bot, notify_master, send_file_to_master

def send_telegram_message(args):
    """
    Sends a message to the master via Telegram.
    Expects args to be a string or a dict with a 'text' key.
    """
    text = args.get("text", "") if isinstance(args, dict) else str(args)
    if not text:
        return "Error: No text provided."
    
    notify_master(text)
    return f"Message sent to Master via Telegram."

def register():
    """Register the Telegram communication tool."""
    from core.tool_protocol import register_tool
    register_tool(
        name="send_telegram_message",
        function=send_telegram_message,
        description="Send a message, report, or interactive menu [Choice 1] | [Choice 2] to the Master's Telegram.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The message text to send."}
            },
            "required": ["text"]
        },
        category="communication"
    )
