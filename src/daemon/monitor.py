"""
Telegram Monitor for ASURA Daemon
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# Add project root to path
ROOT = Path(__file__).parent.parent.parent.absolute()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from telegram import Update
from telegram.ext import Application, CommandHandler as TelegramCommandHandler, MessageHandler, filters, ContextTypes
from daemon.command_handler import CommandHandler
from daemon.config import TELEGRAM_TOKEN, ADMIN_CHAT_ID, ASURA_STOP_SCRIPT, ASURA_RUN_SCRIPT
from daemon.logger import logger

class DaemonMonitor:
    def __init__(self):
        self.handler = CommandHandler(ASURA_STOP_SCRIPT, ASURA_RUN_SCRIPT)

    async def start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🤖 ASURA Daemon v4.1 Active.\nCommands: /restart, /status, /stop")

    async def process_msg(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text: return
        
        chat_id = str(update.effective_chat.id)
        if ADMIN_CHAT_ID and chat_id != ADMIN_CHAT_ID:
            logger.warning(f"Unauthorized access attempt: {chat_id}")
            return

        text = update.message.text
        
        # 1. Handle Daemon Commands
        if text.startswith('/'):
            response = self.handler.handle_command(text)
            if response:
                await update.message.reply_text(response)
                return

        # 2. Proxy to ASURA Core
        import httpx
        try:
            # We use the local API port (default 8080)
            # This allows the daemon to pass the message to the main AI
            api_url = "http://localhost:8080/api/chat"
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info(f"Forwarding message to ASURA Core: {text[:50]}...")
                
                # Check if system is up first (simple status check)
                try:
                    resp = await client.post(api_url, json={"message": text, "user_id": chat_id})
                    if resp.status_code == 200:
                        data = resp.json()
                        reply = data.get("response", "✅ Received.")
                        await update.message.reply_text(reply)
                    else:
                        await update.message.reply_text("🕒 ASURA is currently busy or booting up. Please wait a moment.")
                except httpx.ConnectError:
                    await update.message.reply_text("💤 ASURA Core is currently offline or restarting. Please standby.")
        except Exception as e:
            logger.error(f"Proxy error: {e}")
            await update.message.reply_text(f"⚠️ Gateway Error: {str(e)}")

    def run(self):
        if not TELEGRAM_TOKEN:
            logger.error("No TELEGRAM_BOT_TOKEN found in environment.")
            return

        logger.info("📡 Starting ASURA Daemon Monitor...")
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        app.add_handler(TelegramCommandHandler("start", self.start_cmd))
        app.add_handler(TelegramCommandHandler("restart", self.process_msg))
        app.add_handler(TelegramCommandHandler("status", self.process_msg))
        app.add_handler(TelegramCommandHandler("stop", self.process_msg))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.process_msg))
        
        # Start background health monitoring
        import threading
        threading.Thread(target=self._health_check_loop, daemon=True, name="daemon-health-check").start()
        
        app.run_polling()

    def _health_check_loop(self):
        """Background loop to ensure ASURA Core is alive."""
        import time, httpx
        logger.info("🛡️ Daemon Health Monitoring active.")
        fail_count = 0
        while True:
            try:
                # Check health endpoint
                resp = httpx.get("http://localhost:8080/health", timeout=5)
                if resp.status_code == 200:
                    fail_count = 0
                else:
                    fail_count += 1
            except Exception:
                fail_count += 1
            
            if fail_count >= 3:
                logger.warning(f"🚨 ASURA Core unresponsive ({fail_count} checks). Triggering auto-restart...")
                self.handler.restart_asura()
                fail_count = 0
                time.sleep(60) # Wait longer after restart
            
            time.sleep(30)

if __name__ == "__main__":
    monitor = DaemonMonitor()
    monitor.run()
