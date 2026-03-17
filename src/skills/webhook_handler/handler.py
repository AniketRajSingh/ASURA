# ============================================================
# skills/webhook_handler/handler.py — Incoming Webhook Handler
# Accept webhooks (GitHub, payments, etc.) and trigger skills
# ============================================================

import os
import json
import hmac
import hashlib
import threading
from datetime import datetime
from settings import settings as config
from skills.logger import log_audit, log_app

_webhook_log = []


def verify_signature(payload: bytes, signature: str, secret: str = None) -> bool:
    """Verify webhook signature (GitHub-style HMAC-SHA256)."""
    if not secret:
        secret = config.WEBHOOK_SECRET
    if not secret:
        return True  # No secret configured, accept all

    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


def process_webhook(event_type: str, payload: dict) -> str:
    """Process an incoming webhook event and trigger appropriate actions."""
    log_audit("WEBHOOK", f"Event: {event_type} | Keys: {list(payload.keys())[:5]}")

    _webhook_log.append({
        "event": event_type,
        "timestamp": datetime.now().isoformat(),
        "payload_keys": list(payload.keys()),
    })

    # GitHub push event
    if event_type == "push":
        repo = payload.get("repository", {}).get("name", "unknown")
        ref = payload.get("ref", "")
        commits = len(payload.get("commits", []))
        return f"📦 GitHub push: {repo} ({ref}) — {commits} commits"

    # GitHub issue/PR
    if event_type in ("issues", "pull_request"):
        action = payload.get("action", "")
        title = payload.get(event_type.rstrip("s"), {}).get("title", "")
        return f"🔔 GitHub {event_type}: [{action}] {title}"

    # Generic event
    return f"📨 Webhook received: {event_type}"


def get_webhook_log(limit: int = 10) -> list[dict]:
    return _webhook_log[-limit:]


def create_webhook_server():
    """Create a minimal Flask-like webhook receiver."""
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class WebhookHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            signature = self.headers.get("X-Hub-Signature-256", "")
            if not verify_signature(body, signature):
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Invalid signature")
                return

            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = {"raw": body.decode("utf-8", errors="ignore")}

            event_type = self.headers.get("X-GitHub-Event", "generic")
            result = process_webhook(event_type, payload)

            # Notify master
            _notify_webhook(result)

            self.send_response(200)
            self.end_headers()
            self.wfile.write(result.encode())

        def log_message(self, format, *args):
            pass  # Suppress default logging

    return HTTPServer(("0.0.0.0", config.WEBHOOK_PORT), WebhookHandler)


def _notify_webhook(message: str):
    """Send webhook notification to master via Telegram."""
    try:
        from skills.telegram_bot.bot import _notify_master
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(_notify_master(message))
            else:
                loop.run_until_complete(_notify_master(message))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(_notify_master(message))
    except Exception as e:
        log_app(f"Webhook notification failed: {e}")


def start_webhook_server():
    """Start the webhook server in a background thread."""
    def run():
        server = create_webhook_server()
        log_app(f"Webhook server on port {config.WEBHOOK_PORT}")
        server.serve_forever()

    t = threading.Thread(target=run, daemon=True, name="webhook-server")
    t.start()
    log_audit("WEBHOOK", f"Server started on port {config.WEBHOOK_PORT}")
