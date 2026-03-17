---
name: calendar_manager
description: "Calendar and reminder management system for scheduling events and setting notifications."
entry_point: calendar.py
---

# Calendar Manager

Manage your schedule and set reminders. Integrates with the system's background scheduler to trigger notifications when events are due.

### 🔧 Tools / Functions
- `add_event(title, when, description, remind_minutes)`: Add a new event with an optional reminder.
- `remove_event(event_id)`: Remove an existing event.
- `get_upcoming(hours)`: Retrieve events occurring within the specified window.
- `format_calendar_summary()`: Get a human-readable list of upcoming events.

### 📝 Examples
- "Schedule a meeting for tomorrow at 2 PM" -> Event added with a default 30-minute reminder.
- "What's on my calendar?" -> Shows upcoming events for the next 48 hours.

### 🛠️ Requirements
- `CALENDAR_PATH` in `config.py` (defaults to `calendar.json`).
