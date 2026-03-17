# ============================================================
# scripts/set_telegram_commands.py — Command Menu Updater
# ============================================================

import requests
import os
from settings import settings as config

def set_commands(token, commands, bot_name):
    print(f"📡 Updating commands for {bot_name}...")
    url = f"https://api.telegram.org/bot{token}/setMyCommands"
    
    # Format for Telegram API: [{"command": "cmd", "description": "desc"}, ...]
    payload = {"commands": []}
    for line in commands.strip().split('\n'):
        if ' - ' in line:
            cmd, desc = line.split(' - ', 1)
            payload["commands"].append({"command": cmd.strip().lstrip('/'), "description": desc.strip()})
    
    resp = requests.post(url, json=payload)
    if resp.status_code == 200:
        print(f"✅ {bot_name} commands updated successfully.")
    else:
        print(f"❌ Failed to update {bot_name}: {resp.text}")

# ─── CORE BOT COMMANDS ───
CORE_COMMANDS = """
start - High-level navigation menu.
think - Triggers Deep Reasoning (35B model with CoT).
run - Executes Live Shell Commands (Safe commands run instantly).
screenshot - Captures your Desktop State and sends it as a photo.
skills - Interactive Inline Menu. Click a skill to see sub-tools.
system - Detailed Hardware Vitals (CPU, RAM, Disk).
evolve - Triggers an Autonomous Self-Update cycle.
hibernate - Securely shuts down ASURA and releases all OS locks.
todos - View and manage your global task list.
backup - Create or restore a full System Snapshot.
"""

# ─── INSTA BOT COMMANDS ───
INSTA_COMMANDS = """
start - Navigation menu.
topics - Generates AI-Curated Content Ideas.
post - Full posting workflow with Master approval.
"""

if __name__ == "__main__":
    # Update Core Bot
    if config.TELEGRAM_BOT_TOKEN and not config.TELEGRAM_BOT_TOKEN.startswith("YOUR_"):
        set_commands(config.TELEGRAM_BOT_TOKEN, CORE_COMMANDS, "ASURA-Core")
    
    # Update Insta Bot
    if config.INSTAGRAM_BOT_TOKEN and not config.INSTAGRAM_BOT_TOKEN.startswith("YOUR_"):
        set_commands(config.INSTAGRAM_BOT_TOKEN, INSTA_COMMANDS, "ASURA-Insta")
