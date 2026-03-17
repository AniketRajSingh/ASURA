"""
Natural Language Command Parser Skill.

Translates human-intent messages (e.g., 'check my emails') into specific 
internal skill function calls using regex pattern matching and argument extraction.

Architecture:
- _INTENT_MAP: Global registry of regex patterns to (skill, function, metadata) tuples.
- parse_intent: Primary entry point for intent detection.
- extract_args: Utility to strip boilerplate and isolate command arguments.
"""

import re
from skills.logger import log_audit

# Intent → skill mapping
_INTENT_MAP = {
    r"(check|read|get).*(email|mail|inbox)": ("email_manager", "check_inbox", {}),
    r"(send|write).*(email|mail)": ("email_manager", "send_email", {"needs_args": True}),
    r"(show|list|get).*(todo|task)": ("todo_manager", "format_todos", {}),
    r"(add|create).*(todo|task)": ("todo_manager", "add_todo", {"needs_args": True}),
    r"(show|get|check).*(system|status|resource|cpu|memory)": ("hardware_monitor", "get_resource_summary", {}),
    r"(show|list).*(skill)": ("skill_registry", "discover_skills", {}),
    r"(backup|snapshot)": ("backup_manager", "create_snapshot", {}),
    r"(show|get|check).*(calendar|event|schedule)": ("calendar_manager", "format_calendar_summary", {}),
    r"(add|create).*(event|reminder)": ("calendar_manager", "add_event", {"needs_args": True}),
    r"(show|get).*(git|commit|branch)": ("git_manager", "format_git_summary", {}),
    r"(commit|save).*(change|code)": ("git_manager", "auto_commit", {}),
    r"(summar|tldr)": ("doc_summarizer", "summarize_text", {"needs_args": True}),
    r"(review|check).*(code|file)": ("code_review", "review_file", {"needs_args": True}),
    r"(search|look|find).*(web|internet|online)": ("web_intelligence", "web_search", {"needs_args": True}),
    r"(browse|open).*(url|website|page)": ("browser", "browse_url", {"needs_args": True}),
    r"(encrypt)": ("encryption", "encrypt_file", {"needs_args": True}),
    r"(decrypt)": ("encryption", "decrypt_file", {"needs_args": True}),
    r"(show|get).*(goal|dream)": ("dream_machine", "format_goals", {}),
    r"(show|get).*(queue|background)": ("task_queue", "get_status", {}),
    r"(show|get).*(graph|knowledge)": ("knowledge_graph", "get_graph_stats", {}),
    r"(evolve|update|upgrade).*(self|system|ai)": ("self_updater", "evolve", {}),
    r"(how.*(feel|doing|you))|(bored|lonely)": ("chat", "proactive", {}),
}


def parse_intent(message: str) -> dict:
    """Parse a natural language message into an intent + skill."""
    msg_lower = message.lower().strip()

    for pattern, (skill, func, meta) in _INTENT_MAP.items():
        if re.search(pattern, msg_lower):
            log_audit("NL_PARSE", f"Intent: {skill}.{func} from '{msg_lower[:40]}'")
            return {
                "matched": True,
                "skill": skill,
                "function": func,
                "needs_args": meta.get("needs_args", False),
                "raw_message": message,
            }

    return {"matched": False, "raw_message": message}


def extract_args(message: str, intent: dict) -> str:
    """Extract arguments from the message after intent matching."""
    # Remove common intent words to get the argument
    noise = ["please", "can you", "could you", "show me", "get me", "check",
             "the", "my", "a", "an", "for", "about"]
    words = message.lower().split()
    args = [w for w in words if w not in noise and len(w) > 2]
    return " ".join(args[-3:])  # Last 3 significant words as args
