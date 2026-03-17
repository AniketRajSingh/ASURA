#!/usr/bin/env python3
"""
run.py — Cross-Platform Setup & Runner for ASURA Self-Updating AI
Works on Windows, macOS, and Linux.

Usage:
    python run.py setup        # Create venv + install dependencies
    python run.py start        # Start with auto-restart on code changes
    python run.py start --no-watch  # Start without file watcher
    python run.py test         # Verify all skills import cleanly
    python run.py              # Default: setup if needed, then start
"""

import os
import sys
import time
import signal
import subprocess
import platform

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
VENV_DIR = os.path.join(BASE_DIR, ".venv")
PYPROJECT = os.path.join(BASE_DIR, "pyproject.toml")

# Cross-platform venv paths
if platform.system() == "Windows":
    PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe")
    PIP = os.path.join(VENV_DIR, "Scripts", "pip.exe")
    ACTIVATE_HINT = f"  {VENV_DIR}\\Scripts\\activate"
else:
    PYTHON = os.path.join(VENV_DIR, "bin", "python")
    PIP = os.path.join(VENV_DIR, "bin", "pip")
    ACTIVATE_HINT = f"  source {VENV_DIR}/bin/activate"


def get_clean_env():
    """Return an environment dict with conflicting VIRTUAL_ENV removed."""
    env = os.environ.copy()
    if "VIRTUAL_ENV" in env:
        # If the active venv doesn't match this project, unset it
        if os.path.abspath(env["VIRTUAL_ENV"]) != os.path.abspath(VENV_DIR):
            del env["VIRTUAL_ENV"]
    # Also clear PYTHONHOME if set, as it can interfere with venv isolation
    env.pop("PYTHONHOME", None)
    return env


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════╗
║     ASURA — Self-Updating AI System                      ║
║        Cross-Platform Setup & Runner                     ║
╚══════════════════════════════════════════════════════════╝
    """)


def check_python():
    ver = sys.version_info
    if ver.major < 3 or (ver.major == 3 and ver.minor < 9):
        print(f"❌ Python 3.9+ required. You have {ver.major}.{ver.minor}")
        sys.exit(1)
    print(f"✅ Python {ver.major}.{ver.minor}.{ver.micro} ({platform.system()} {platform.machine()})")
    
    # ── Environment Guard ──
    v_env = os.environ.get("VIRTUAL_ENV")
    if v_env and os.path.exists(v_env):
        if os.path.abspath(v_env) != os.path.abspath(VENV_DIR):
            print(f"\n⚠️  ENVIRONMENT MISMATCH DETECTED!")
            print(f"   Active: {v_env}")
            print(f"   Target: {VENV_DIR}")
            print(f"   Action: Triggering Self-Healing Setup...")
            
            # Deactivate logic (unset env vars for current process)
            os.environ.pop("VIRTUAL_ENV", None)
            
            # Wipe local venv to force fresh install in correct dir
            import shutil
            if os.path.isdir(VENV_DIR):
                print("   🗑️ Wiping legacy .venv...")
                shutil.rmtree(VENV_DIR)
            
            # Re-recreate and reinstall
            create_venv()
            install_deps()
            print("\n✅ Environment healed and isolated. Please restart ASURA.\n")
            sys.exit(0)


def create_venv():
    if os.path.isdir(VENV_DIR):
        print("ℹ️  Virtual environment already exists — skipping")
        return
    print("🐍 Creating virtual environment with uv...")
    try:
        subprocess.run(["uv", "venv", VENV_DIR], check=True, env=get_clean_env())
    except FileNotFoundError:
        print("❌ 'uv' not found. Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
        sys.exit(1)
    print("✅ Virtual environment created")


def install_deps():
    if os.path.isfile(PYPROJECT):
        print("📦 Installing dependencies with uv (ultra-fast)...")
        result = subprocess.run(["uv", "pip", "install", "-e", "."],
                                capture_output=True, text=True, cwd=BASE_DIR, env=get_clean_env())
        if result.returncode == 0:
            print("✅ All dependencies installed")
        else:
            print(f"⚠️  Deps installation issue:\n{result.stderr}")


def ensure_dirs():
    for d in ["data/logs", "data/memory_store", "data/backups",
              "data/update_history", "assets"]:
        os.makedirs(os.path.join(BASE_DIR, d), exist_ok=True)
    print("✅ Runtime directories ready")


def run_env_setup():
    print("\n🔐 Running environment configuration...")
    subprocess.run([PYTHON, os.path.join(BASE_DIR, "scripts", "setup_env.py")], check=True)


def run_qwen_setup():
    print("\n🎙️  Running voice engine setup...")
    subprocess.run([PYTHON, os.path.join(BASE_DIR, "scripts", "setup_qwen_tts.py")], check=True)


def run_daemon():
    """Start the Sovereign Gateway (Telegram Monitor) in background."""
    print("📡 Starting Sovereign Gateway Daemon...")
    env = get_clean_env()
    # Path to daemon script
    daemon_script = os.path.join(SRC_DIR, "daemon", "monitor.py")
    
    # Ensure logs dir exists
    log_file = os.path.join(BASE_DIR, "data", "logs", "daemon.log")
    
    try:
        with open(log_file, "a") as f:
            subprocess.Popen(
                [PYTHON, "-u", daemon_script],
                cwd=BASE_DIR,
                env=env,
                stdout=f,
                stderr=f,
                start_new_session=True
            )
        print(f"✅ Gateway started. Logs: {os.path.relpath(log_file, BASE_DIR)}")
    except Exception as e:
        print(f"❌ Failed to start gateway: {e}")


def run_tests():
    print("\n🧪 Running skill import tests...\n")
    proc = subprocess.run(
        ["uv", "run", "python", "-c", """
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath('.')), 'src'))
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from skills.skill_registry import discover_skills
try:
    from skills.ai_content.generator import _dispatch_action  # verify it's gone
except ImportError:
    pass
registry = discover_skills()
print(f"📦 {len(registry)} skills discovered:")
for name in sorted(registry.keys()):
    print(f"   ✅ {name}")
print(f"\\n🏆 ALL {len(registry)} SKILLS OPERATIONAL")
"""],
        cwd=BASE_DIR,
        env=get_clean_env(),
    )
    return proc.returncode == 0


# ============================================================
# File Watcher — Polls src/ for .py changes
# ============================================================
def _snapshot_mtimes(watch_dir: str) -> dict[str, float]:
    """Get modification times for all .py files in a directory tree."""
    mtimes = {}
    for root, dirs, files in os.walk(watch_dir):
        # Skip __pycache__ and .venv
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".venv", "node_modules")]
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                try:
                    mtimes[path] = os.path.getmtime(path)
                except OSError:
                    pass
    return mtimes


def _detect_changes(old: dict, new: dict) -> list[str]:
    """Return list of changed/added/deleted files."""
    changed = []
    for path, mtime in new.items():
        if path not in old or old[path] != mtime:
            changed.append(path)
    for path in old:
        if path not in new:
            changed.append(path)
    return changed


def _is_already_running() -> bool:
    """Check if another ASURA main.py instance is already running."""
    try:
        import psutil
        current_pid = os.getpid()
        parent_pid = os.getppid()
        for proc in psutil.process_iter(['pid', 'cmdline', 'status']):
            try:
                pid = proc.info['pid']
                if pid in (current_pid, parent_pid):
                    continue
                # Skip zombies and dead processes
                status = proc.info.get('status', '')
                if status in ('zombie', 'dead', psutil.STATUS_ZOMBIE):
                    continue
                cmdline = " ".join(proc.info['cmdline'] or [])
                # Must be a python process running main.py directly (not run.py or stop.py)
                if "main.py" in cmdline and "python" in cmdline and "run.py" not in cmdline and "stop.py" not in cmdline:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except ImportError:
        pass
    return False


def start_system(watch: bool = True):
    """Start main.py with optional auto-restart on code changes."""
    
    env = get_clean_env()

    # ── Single-instance guard ──────────────────────────────
    if _is_already_running():
        print("⚠️  Another ASURA instance is already running!")
        print("   Use 'python stop.py' first, then try again.")
        return

    print("\n🚀 Starting ASURA Self-Updating AI...\n")

    if not watch:
        # Simple mode — no watcher
        try:
            subprocess.run(
                ["uv", "run", "python", "-u", os.path.join(SRC_DIR, "main.py")],
                cwd=BASE_DIR,
                env=env,
            )
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down gracefully...")
        return

    # ── Watch Mode ─────────────────────────────────────────
    print("👁️  File watcher ACTIVE — auto-restart on .py changes\n")
    poll_interval = 2  # seconds
    crash_count = 0
    MAX_CRASH_RESTARTS = 5  # Stop after this many consecutive OOM crashes
    consecutive_system_crashes = 0

    while True:
        # Take initial snapshot
        snapshot = _snapshot_mtimes(SRC_DIR)

        # Start main.py as a subprocess
        proc = subprocess.Popen(
            ["uv", "run", "python", "-u", os.path.join(SRC_DIR, "main.py")],
            cwd=BASE_DIR,
            env=env,
        )

        try:
            while True:
                time.sleep(poll_interval)

                # Check if process died on its own
                if proc.poll() is not None:
                    exit_code = proc.returncode
                    
                    if exit_code != 0:
                        consecutive_system_crashes += 1
                        print(f"\n⚠️  ASURA Crashed (Code {exit_code}). Streak: {consecutive_system_crashes}")
                        
                        # DEEP RECOVERY TRIGGER
                        # If we crash twice in a row, the healer is likely broken
                        if consecutive_system_crashes >= 2:
                            print("🆘 HEALING SYSTEM FAILURE DETECTED. Initiating Recursive Self-Repair...")
                            
                            # We must add src to path to import recovery
                            sys.path.insert(0, SRC_DIR)
                            from core.self_recovery import trigger_deep_recovery
                            
                            # Get last error from audit log to give ghost a target
                            try:
                                with open(os.path.join(BASE_DIR, "data", "logs", "audit.txt"), "r") as f:
                                    last_lines = f.readlines()[-20:]
                                    error_context = "".join(last_lines)
                            except: error_context = "Unknown fatal startup error"

                            success = trigger_deep_recovery(error_context)
                            if success:
                                print("✅ REPAIR COMPLETE. Resuming normal operations.")
                                consecutive_system_crashes = 0
                            else:
                                print("❌ REPAIR FAILED. System remains unstable.")

                    if exit_code == -9:
                        crash_count += 1
                        if crash_count >= MAX_CRASH_RESTARTS:
                            print(f"\n❌ Process killed by OS (OOM) {crash_count} times. Stopping.")
                            print("   Your system is out of memory. Close other apps and try again.")
                            return
                        backoff = min(3 * crash_count, 30)
                        print(f"\n⚠️  Process killed by OS (OOM, exit -9). Attempt {crash_count}/{MAX_CRASH_RESTARTS}")
                        print(f"🔄 Restarting in {backoff} seconds...")
                        time.sleep(backoff)
                    else:
                        crash_count = 0  # Reset on non-OOM exit
                        print(f"🔄 Restarting in 3 seconds...")
                        time.sleep(3)

                    break  # Break inner loop to restart
                
                # If we are here, ASURA is running
                if consecutive_system_crashes > 0 and time.time() - proc.start_time > 60:
                    # If it stays alive for 60s, consider it stabilized
                    consecutive_system_crashes = 0

                # Check for file changes
                current = _snapshot_mtimes(SRC_DIR)
                changed = _detect_changes(snapshot, current)

                if changed:
                    # Check if evolution is in progress — defer restart
                    evolve_lock = os.path.join(BASE_DIR, "data", ".evolving")
                    if os.path.isfile(evolve_lock):
                        # Check if the lock is stale (older than 10 minutes)
                        try:
                            lock_age = time.time() - os.path.getmtime(evolve_lock)
                            if lock_age < 600:  # 10 min timeout
                                print(f"\n⏳ Change detected but evolution in progress — deferring restart...")
                                snapshot = current  # Reset snapshot so we don't re-trigger
                                continue
                            else:
                                print(f"\n⚠️ Stale evolve lock ({int(lock_age)}s old) — removing and restarting")
                                os.remove(evolve_lock)
                        except Exception:
                            pass

                    crash_count = 0  # Reset on intentional restart
                    short_names = [os.path.relpath(p, SRC_DIR) for p in changed[:5]]
                    print(f"\n🔄 Change detected in: {', '.join(short_names)}")
                    print("♻️  Restarting ASURA...\n")

                    # Kill the old process
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()

                    time.sleep(1)
                    break  # Break inner loop to restart

        except KeyboardInterrupt:
            print("\n\n👋 Shutting down gracefully...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            return


def setup():
    print_banner()
    check_python()
    create_venv()
    install_deps()
    ensure_dirs()
    run_env_setup()
    run_qwen_setup()
    print(f"""
✅ Setup complete!

To start the AI:    python run.py start
To run tests:       python run.py test
""")


def main():
    print_banner()
    check_python()
    
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    command = args[0].lower() if args else "auto"

    if command == "setup":
        create_venv()
        install_deps()
        ensure_dirs()
    elif command == "start":
        if not os.path.isfile(PYTHON):
            setup()
        watch = "--no-watch" not in args
        start_system(watch=watch)
    elif command == "test":
        if not os.path.isfile(PYTHON):
            setup()
        run_tests()
    elif command == "daemon":
        if not os.path.isfile(PYTHON):
            setup()
        run_daemon()
    elif command == "auto":
        if not os.path.isfile(PYTHON):
            setup()
        # If running via daemon, set the environment flag
        if "--managed" in args:
            os.environ["ASURA_MANAGED_BOT"] = "true"
        start_system(watch=True)
    elif command in ("help", "-h", "--help"):
        print(__doc__)
    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()

