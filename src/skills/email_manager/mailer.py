# ============================================================
# skills/email_manager/mailer.py — Email Integration (IMAP/SMTP)
# ============================================================

import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from settings import settings as config
from skills.logger import log_audit, log_app


def send_email(to: str, subject: str, body: str, html: bool = False) -> bool:
    """Send an email via SMTP."""
    if not config.EMAIL_ADDRESS or not config.EMAIL_PASSWORD:
        log_audit("EMAIL", "Email not configured")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = config.EMAIL_ADDRESS
        msg["To"] = to
        msg["Subject"] = subject

        content_type = "html" if html else "plain"
        msg.attach(MIMEText(body, content_type))

        with smtplib.SMTP(config.EMAIL_SMTP_SERVER, config.EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
            server.send_message(msg)

        log_audit("EMAIL", f"Sent to {to}: {subject}")
        return True

    except Exception as e:
        log_audit("EMAIL_ERROR", f"Send failed: {e}")
        return False


def check_inbox(folder: str = "INBOX", limit: int = 5) -> list[dict]:
    """Check inbox for recent emails."""
    if not config.EMAIL_ADDRESS or not config.EMAIL_IMAP_SERVER:
        return [{"error": "Email not configured"}]

    try:
        mail = imaplib.IMAP4_SSL(config.EMAIL_IMAP_SERVER)
        mail.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
        mail.select(folder)

        _, data = mail.search(None, "ALL")
        ids = data[0].split()[-limit:]  # Last N emails

        emails = []
        for eid in reversed(ids):
            _, msg_data = mail.fetch(eid, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

            emails.append({
                "from": msg.get("From", ""),
                "subject": msg.get("Subject", ""),
                "date": msg.get("Date", ""),
                "body": body[:500],
            })

        mail.logout()
        log_audit("EMAIL", f"Checked inbox: {len(emails)} emails")
        return emails

    except Exception as e:
        log_audit("EMAIL_ERROR", f"Inbox check failed: {e}")
        return [{"error": str(e)}]


def format_inbox_summary(emails: list[dict]) -> str:
    if not emails:
        return "📭 No emails."
    if "error" in emails[0]:
        return f"⚠️ {emails[0]['error']}"

    lines = [f"📬 *Inbox ({len(emails)} recent)*\n"]
    for e in emails:
        lines.append(f"📧 *{e['subject'][:50]}*\n   From: {e['from'][:30]}\n   {e['date'][:20]}")
    return "\n".join(lines)
