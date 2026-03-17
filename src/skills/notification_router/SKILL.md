---
name: notification_router
description: "Intelligent notification routing system for dispatching alerts across Telegram, email, and dashboard."
entry_point: router.py
---

# Notification Router

Routes system alerts, reminders, and notifications to the correct channel based on their importance and category.

### 🔧 Tools / Functions
- `route_notification(message, category)`: Dispatches a message to Telegram, Email, or other configured sinks.
- `set_route(category, channels)`: Dynamically update where certain categories of alerts are sent.
- `format_routes()`: Show the current routing table.

### 📝 Examples
- "Notify me on Telegram if the build fails" -> Routes critical notifications to the bot.

### 🛠️ Requirements
- `telegram_bot` and/or `email_manager` skills enabled.
