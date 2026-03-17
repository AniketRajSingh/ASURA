# ============================================================
# skills/notification_router/router.py — Notification Routing
# Route different notification types to different channels
# ============================================================
from settings import settings as config
from skills.logger import log_audit

_routes = {
    "critical":  ["telegram", "email"],
    "evolution": ["telegram"],
    "webhook":   ["telegram", "dashboard"],
    "system":    ["telegram"],
    "reminder":  ["telegram"],
    "default":   ["telegram"],
}

async def route_notification(message: str, category: str = "default", **kwargs):
    channels = _routes.get(category, _routes["default"])
    log_audit("NOTIFY", f"[{category}] → {channels}")
    for ch in channels:
        try:
            if ch == "telegram":
                from skills.telegram_bot.bot import _notify_master
                await _notify_master(message)
            elif ch == "email" and config.EMAIL_ADDRESS:
                from skills.email_manager import send_email
                send_email(config.EMAIL_ADDRESS, f"ASURA Alert: {category}", message)
        except Exception as e:
            log_audit("NOTIFY_ERROR", f"{ch}: {e}")

def set_route(category: str, channels: list[str]):
    _routes[category] = channels
    log_audit("NOTIFY", f"Route set: {category} → {channels}")

def get_routes() -> dict: return dict(_routes)
def format_routes() -> str:
    lines = ["📡 *Notification Routes*\n"]
    for cat, chs in _routes.items():
        lines.append(f"  • {cat}: {', '.join(chs)}")
    return "\n".join(lines)
