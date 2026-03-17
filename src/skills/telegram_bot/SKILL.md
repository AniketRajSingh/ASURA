---
name: telegram_bot
description: "Provides a Telegram Bot interface for system interaction, Instagram posting workflows, and conversational chat."
entry_point: bot.py
---

# Telegram Bot

A comprehensive Telegram interface for managing the ASURA system. It supports command-based interaction, role-based access control, automated Instagram posting workflows, and proactive notifications.

### 🔧 Tools / Functions
- `start_bot()`: Initializes and starts the Telegram bot polling service.
- `notify_master(message)`: Sends a thread-safe notification message to the configured admin chat.
- `send_file_to_master(file_path, caption="")`: Uploads and sends a file (image, document, etc.) to the admin chat.

### 📝 Examples
- "Start the bot" -> [Bot starts polling]
- `notify_master("System update complete!")` -> [Message sent to admin]

### 🛠️ Requirements
- `python-telegram-bot` library
- `TELEGRAM_BOT_TOKEN` in `.env`
- `TELEGRAM_ADMIN_CHAT_ID` in `.env`
