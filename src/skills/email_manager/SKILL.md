---
name: email_manager
description: "Email integration skill. Send emails via SMTP, check inboxes via IMAP, and format summaries for notifications."
entry_point: mailer.py
---

# Email Manager

Provides full email lifecycle management via standard SMTP and IMAP protocols. It allows ASURA to send reports and alerts to the master, monitor inboxes for incoming commands, and format email summaries for quick review.

### 🔧 Tools / Functions
- `send_email(to, subject, body, html)`: Send an email using SMTP (supports plain text and HTML content).
- `check_inbox(folder, limit)`: Connect to an IMAP server and retrieve the most recent emails from a specified folder.
- `format_inbox_summary(emails)`: Generate a human-readable Markdown summary of recent inbox activity.

### 📝 Examples
- "Email the audit log to master@example.com" -> Sends a plain-text email with the recent log content.
- "Check my inbox for updates" -> Displays a list of recent email subjects and senders.

### 🛠️ Requirements
- `smtplib`, `imaplib`
- Valid SMTP/IMAP credentials configured in `config.py` (EMAIL_ADDRESS, EMAIL_PASSWORD, etc.)
