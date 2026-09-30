# ============================================================
# daemon/telegram_daemon.py — Persistent Interaction Layer
# ============================================================

import os
import sys
import asyncio
import signal

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from settings import settings as config
from skills.logger import log_app, log_audit

PID_FILE = os.path.join(config.DATA_DIR, "telegram_bot.pid")

def check_singleton():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            import psutil
            if psutil.pid_exists(old_pid):
                print(f"⚠️ Telegram Bot already running (PID: {old_pid}). Exiting.")
                sys.exit(0)
        except: pass
    
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

def cleanup_pid(signum=None, frame=None):
    if os.path.exists(PID_FILE):
        try: os.remove(PID_FILE)
        except: pass
    sys.exit(0)

async def main():
    check_singleton()
    signal.signal(signal.SIGINT, cleanup_pid)
    signal.signal(signal.SIGTERM, cleanup_pid)
    
    # ─── Specialized Interaction Boot ───────────
    # We do NOT call async_main() here. We only start the bot.
    os.environ["ASURA_MANAGED_BOT"] = "true"
    os.environ["ASURA_TELEGRAM_ACTIVE"] = "true"
    
    from skills.telegram_bot.bot import create_core_bot, create_insta_bot
    log_app("🚀 Starting Persistent Telegram Interaction Layer (Bot Only)...")
    
    core_app = create_core_bot()
    insta_app = create_insta_bot()
    
    await core_app.initialize()
    await core_app.start()
    await insta_app.initialize()
    await insta_app.start()
    
    log_app("🤖 Dual Bots Polling: ACTIVE (Daemon Mode)")
    
    try:
        # Start both updaters
        await core_app.updater.start_polling()
        await insta_app.updater.start_polling()
        
        # Block here until interrupted
        stop_event = asyncio.Event()
        
        # Setup signals for internal cleanup if needed
        def stop_polling(*args):
            stop_event.set()
        
        log_app("🚀 Bots are persistent. Listening for updates...")
        await stop_event.wait()
        
    except Exception as e:
        log_audit("BOT_DAEMON_FATAL", f"Daemon failed: {e}")
        log_app(f"❌ Critical Bot Error: {e}. Cooling down...")
        await asyncio.sleep(15)
        raise e
    finally:
        await core_app.updater.stop()
        await insta_app.updater.stop()
        await core_app.stop()
        await insta_app.stop()
        await core_app.shutdown()
        await insta_app.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        cleanup_pid()
    except Exception as e:
        log_audit("DAEMON_CRASH", str(e))
        cleanup_pid()
