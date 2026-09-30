# ============================================================
# main.py — Self-Updating AI System Orchestrator
# God-Tier: 45+ skills, resource governor, curiosity engine
# Also supports CLI mode: python src/main.py --cli "task"
# ============================================================

import sys, os, argparse

# Ensure src/ is on the path (works whether run from root or src/)
_src = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _src)

import requests
from settings import settings as config
from skills.logger import log_audit, log_app
from skills.memory import initialize as init_memory
from skills.skill_registry import discover_skills

# === CLI Mode Support (asura.py compatible) ===
CLI_MODE = "--cli" in sys.argv or "ASURA_CLI_MODE" in os.environ


def parse_args():
    """Parse command-line arguments for CLI mode."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--cli", action="store_true")
    parser.add_argument("--interactive", "-i", action="store_true")
    args, unknown = parser.parse_known_args()
    return args


if CLI_MODE:
    args = parse_args()
    if args.cli and not args.interactive:
        # In non-interactive CLI mode, skip async services
        import asyncio
        from cli.main_entry import run_standalone_task



def startup_banner():
    banner = """
╔══════════════════════════════════════════════════════════╗
║             ASURA — Sovereign AI System                  ║
║               Master: Aniket Raj Singh                   ║
║                                                          ║
║  🤖 45+ Skills  │  🧠 Resource Governor                  ║
║  📋 Task Queue  │  🔄 Feature Evolution                  ║
║  🎤 Voice Web   │  💭 Emotion-Aware                      ║
║  🔀 Git Auto    │  ⏰ Cron Scheduler                     ║
║  🧪 Auto-Tests  │  📊 Health Alerts                      ║
║  🌍 Browser     │  🤝 Multi-Agent                        ║
║  🧠 Curiosity   │  🔐 RBAC Auth                          ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)
    log_audit("SYSTEM", "ASURA Sovereign AI starting up")


def get_bot_username() -> str:
    """Fetch the bot's Telegram username at startup."""
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getMe",
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                return data["result"].get("username", "unknown")
    except Exception:
        pass
    return "unknown"


def print_live_channels(skill_count: int):
    """Print all live interfaces the AI is accessible on."""
    bot_username = get_bot_username()

    channels = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📡 SOVEREIGN PORTAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  💬 Telegram Bot  →  https://t.me/{bot_username}
  🖥️  Command Center →  http://localhost:{config.DASHBOARD_PORT}
  🔌 REST API       →  http://localhost:{config.API_PORT}

  📦 Skills loaded: {skill_count}
  🔐 Auth: RBAC (first /start = permanent owner)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    print(channels)


async def init_system():
    log_app("Initializing system...")
    
    # ─── Engage Power Lock ────────────
    from core.sovereignty import get_authority
    get_authority().stay_awake()
    
    init_memory()

    from skills.skill_registry import load_skills
    registry = load_skills()
    log_app(f"Systems check: {len(registry)} skills active.")

    # Run boot-time self-check (verify all skills + tools)
    try:
        from core.startup_checks import run_startup_checks
        await run_startup_checks()
    except Exception as e:
        log_app(f"Startup self-check error: {e}")

    # Initialize resource governor
    from core.resource_governor import get_governor
    gov = get_governor()
    health = gov.check_health()
    log_app(f"System health: {health['status']}")

    # Initialize task queue
    from core.task_queue import get_task_queue
    tq = get_task_queue()
    tq.start()

    # Register existing features in tracker
    try:
        from skills.feature_tracker import auto_register_existing_features
        auto_register_existing_features()
    except Exception as e:
        log_app(f"Feature registration skipped: {e}")

    # Init git repo
    try:
        from skills.git_manager import init_repo
        init_repo()
    except Exception as e:
        log_app(f"Git init skipped: {e}")

    # Generate skills.md
    from core.self_updater import SelfUpdater
    SelfUpdater()._update_skills_md()

    # Trigger Architectural Knowledge Graph Scan (Self-Discovery)
    try:
        from core.knowledge_scanner import knowledge_scanner
        asyncio.create_task(asyncio.to_thread(lambda: asyncio.run(knowledge_scanner.scan_all())))
    except Exception as e:
        log_app(f"KG: Initial scan failed: {e}")

    # Guardian Drive: Pre-start self-healing check
    try:
        from core.self_healing import SelfHealingDaemon
        healer = SelfHealingDaemon()
        await healer.pre_start_check()
    except Exception as e:
        log_app(f"Guardian Drive check skipped: {e}")

    return registry


import asyncio

async def start_parallel_services():
    """Launch all system daemons in parallel tasks."""
    from core.self_updater import SelfUpdaterDaemon
    from core.proactive import ProactiveEngine
    from core.curiosity import CuriosityEngine
    from core.observer import FileSystemObserver
    from skills.scheduler import SchedulerDaemon
    from skills.telegram_bot.bot import get_notify_fn, set_proactive_engine, create_core_bot, create_insta_bot

    notify = get_notify_fn()

    # 1. Initialize Daemons
    updater = SelfUpdaterDaemon(notify_fn=notify)
    proactive = ProactiveEngine(notify_fn=notify)
    set_proactive_engine(proactive)
    scheduler = SchedulerDaemon(notify_fn=notify)
    curiosity = CuriosityEngine(notify_fn=notify)
    observer = FileSystemObserver(notify_fn=notify)
    
    # ── Start Federation Sync ───────────
    from core.federation import federation
    federation.start_sync_daemon()

    # 2. Build Async Tasks
    tasks = [
        asyncio.create_task(updater.start()),
        asyncio.create_task(asyncio.to_thread(proactive.start)),
        asyncio.create_task(asyncio.to_thread(scheduler.start)),
        asyncio.create_task(asyncio.to_thread(curiosity.start)),
        asyncio.create_task(observer.start()),
    ]

    # 3. Add Optional Services
    try:
        from skills.health_alerter import HealthAlerter
        alerter = HealthAlerter(notify_fn=notify, check_interval=120)
        tasks.append(asyncio.create_task(asyncio.to_thread(alerter.start)))
    except Exception as e: log_app(f"Health alerter skip: {e}")

    try:
        from core.doc_updater import DocUpdater
        doc_sync = DocUpdater(notify_fn=notify)
        tasks.append(asyncio.create_task(asyncio.to_thread(doc_sync.start)))
    except Exception as e: log_app(f"Doc sync skip: {e}")

    try:
        from skills.graceful_mode.offline import process_offline_queue
        
        async def graceful_mode_daemon():
            log_app("🔌 Graceful Mode Daemon active.")
            while True:
                try:
                    count = process_offline_queue()
                    if count > 0:
                        log_audit("OFFLINE", f"Processed {count} queued tasks.")
                except Exception as e:
                    log_app(f"Graceful daemon error: {e}")
                await asyncio.sleep(300) # Check every 5 minutes
        
        tasks.append(asyncio.create_task(graceful_mode_daemon()))
    except Exception as e: log_app(f"Graceful mode daemon skip: {e}")

    # 4. Start Dashboards & Servers (Truly Parallel)
    try:
        from skills.dashboard import start_dashboard
        tasks.append(asyncio.create_task(asyncio.to_thread(start_dashboard)))
    except Exception as e: log_app(f"Dashboard skip: {e}")

    try:
        from skills.api_server import start_api_server
        tasks.append(asyncio.create_task(asyncio.to_thread(start_api_server)))
    except Exception as e: log_app(f"API skip: {e}")

    # 5. Start Telegram Bots Async (Federated Election)
    from core.federation import federation
    
    # Check if run.py handled the bot separately (Parallel Persistence)
    managed_flag = os.environ.get("ASURA_MANAGED_BOT")
    
    if managed_flag == "skip":
        log_app("🤖 Interaction Layer: ACTIVE (Managed by separate process)")
        is_leader = False # Don't start another instance
    else:
        is_leader = await federation.should_start_bot()
    
    if is_leader:
        from skills.telegram_bot.bot import create_core_bot, create_insta_bot
        log_app("Starting Dual Telegram Bots (Cluster Leader)...")
        core_app = create_core_bot()
        insta_app = create_insta_bot()
        
        await core_app.initialize()
        await core_app.start()
        await insta_app.initialize()
        await insta_app.start()

        # ─── Multi-Bot Polling (Parallel) ────
        # Managed Bot mode means the bot is running in its own persistent process
        if os.environ.get("ASURA_MANAGED_BOT") == "true":
            log_app("🤖 PERSISTENT BOT MODE: Starting long-polling...")
            await core_app.updater.start_polling()
            await insta_app.updater.start_polling()
            log_app("🤖 Interaction Layer: STANDBY (Parallel to Core)")
        else:
            # Standard mode (Core + Bots in same process)
            await core_app.updater.start_polling()
            await insta_app.updater.start_polling()
            log_app("🤖 Dual Bots Polling: ACTIVE")

            # ─── Startup Notification ────────────
            import platform, socket
            from skills.telegram_bot.bot import send_ephemeral_message
            
            try:
                hostname = socket.gethostname()
                # Get local IP
                s = socket.socket(socket.getaddrinfo('8.8.8.8', 80)[0][0], socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except: 
                local_ip = "Unknown IP"
                hostname = "Unknown Host"

            device_info = f"💻 <b>{config.INSTANCE_NAME}</b> is ONLINE\n" \
                          f"OS: <code>{platform.system()} {platform.release()}</code>\n" \
                          f"Host: <code>{hostname}</code>\n" \
                          f"IP: <code>{local_ip}</code>"
            
            send_ephemeral_message(f"Master I am online from {device_info}", delay=10, silent=True)
        
        # Set global flag for health checks
        os.environ["ASURA_TELEGRAM_ACTIVE"] = "true"
    else:
        log_app("📡 Following peer leader. Telegram bots remain dormant.")
        os.environ["ASURA_TELEGRAM_ACTIVE"] = "false"
    
    # 6. Keep the process alive indefinitely
    # Since daemons and bot polling run in background threads/tasks,
    # we must block the main async loop to prevent successful exit (code 0).
    log_app("🚀 TURBO-PARALLEL: All services operational and persistent.")
    
    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        log_app("Parallel services cancelled.")
    except Exception as e:
        log_app(f"Error in persistent wait: {e}")

# === CLI Entry Point ===
async def run_cli_entry():
    """CLI entry point for --cli mode."""
    if args.interactive:
        from cli.main_entry import run_interactive_cli
        await run_interactive_cli()
    else:
        # Get prompt from the first argument after --cli
        # sys.argv usually looks like: ['main.py', '--cli', 'the prompt']
        prompt = ""
        for i, arg in enumerate(sys.argv):
            if arg == "--cli" and i + 1 < len(sys.argv):
                prompt = sys.argv[i+1]
                break

        if not prompt:
            print("⚠️  No prompt provided. Usage:")
            print("    asura 'analyze the codebase'")
            print("    python src/main.py --cli 'fix the bug'")
            return

        from cli.main_entry import run_standalone_task
        await run_standalone_task(prompt)


async def async_main():
    try:
        startup_banner()
        registry = await init_system()
        print_live_channels(len(registry))

        if CLI_MODE and args.cli:
            # Run in CLI mode instead of starting services
            await run_cli_entry()
        else:
            await start_parallel_services()
    except KeyboardInterrupt:
        log_app("Shutdown signal received.")
    except Exception as e:
        import traceback
        tb_text = traceback.format_exc()
        log_audit("CRASH", f"Fatal exception in async_main:\n{tb_text}")
        log_app(f"❌ FATAL CRASH: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass
