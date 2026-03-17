#!/usr/bin/env python3
"""
ASURA — Unified Command-Line Interface (Universal)
Works on macOS, Windows, and Linux.
"""

import os
import sys
import argparse
import html
import asyncio
import subprocess
from pathlib import Path

# ─── Setup Pathing (Cross-platform & Symlink Aware) ───
# Use Path(__file__).resolve() to follow symlinks to the actual project folder
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
VENV_DIR = BASE_DIR / ".venv"

# Force current working directory to the project root for UV operations
os.chdir(str(BASE_DIR))

# Inject paths early
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(SRC_DIR))

def is_venv_ready():
    """Check if the virtual environment exists and is healthy."""
    if os.name == "nt":
        return (VENV_DIR / "Scripts" / "python.exe").exists()
    return (VENV_DIR / "bin" / "python").exists()

def reexecute_in_venv():
    """Ensure we are running inside the project virtual environment."""
    if os.environ.get("VIRTUAL_ENV") == str(VENV_DIR):
        return

    # Path to python in venv
    if os.name == "nt":  # Windows
        python_exe = VENV_DIR / "Scripts" / "python.exe"
    else:  # Unix
        python_exe = VENV_DIR / "bin" / "python"

    if python_exe.exists():
        # Re-execute with the venv python
        os.environ["VIRTUAL_ENV"] = str(VENV_DIR)
        env = os.environ.copy()
        # Keep PYTHONPATH for src access
        env["PYTHONPATH"] = f"{BASE_DIR}:{SRC_DIR}:{env.get('PYTHONPATH', '')}"
        
        try:
            # sys.argv[0] is the script path
            os.execve(str(python_exe), [str(python_exe)] + sys.argv, env)
        except Exception as e:
            print(f"⚠️ Re-execution failed: {e}. Attempting to continue...")

def _send_notification(title: str, body: str, icon: str = "📢"):
    """Helper to send telegram notification safely."""
    try:
        from skills.telegram_bot.bot import notify_master
        msg = f"{icon} <b>{title}</b>\n\n{body}"
        notify_master(msg)
        return True
    except Exception:
        return False

def main():
    # Detect project root
    os.environ["ASURA_PROJECT_ROOT"] = str(BASE_DIR)

    parser = argparse.ArgumentParser(description="ASURA — Unified Universal CLI")
    parser.add_argument("-c", "--command", metavar="COMMAND", help="Execute single task")
    parser.add_argument("-p", "--plan", metavar="PROMPT", help="Planning/design mode")
    parser.add_argument("-i", "--interactive", action="store_true", help="Start interactive REPL")
    parser.add_argument("-a", "--agent", metavar="AGENT", default="auto", help="Specify AI agent")
    parser.add_argument("--setup", action="store_true", help="Force setup of environment")
    parser.add_argument("--notify", metavar="MSG", help="Send a Telegram notification")
    parser.add_argument("--file", metavar="FILE", help="Send file content as Telegram notification")

    args = parser.parse_args()

    # Step 1: Bootstrap check (Internalized logic to avoid NameErrors)
    if not is_venv_ready():
        print("🌱 ASURA: Initializing Environment (UV Sync)...")
        try:
            # We use 'uv' directly as it's our project standard
            subprocess.run(["uv", "sync", "--all-extras"], cwd=BASE_DIR, check=True)
        except Exception as e:
            print(f"❌ Failed to initialize venv: {e}")
            sys.exit(1)

    # Step 2: Ensure VENV execution
    reexecute_in_venv()

    # Step 3: Runtime Execute
    try:
        from rich.console import Console
        console = Console()
        from cli.main_entry import run_standalone_task, run_interactive_cli
    except ImportError as e:
        print(f"❌ Critical modules missing: {e}. Try running with --setup.")
        sys.exit(1)

    if args.command:
        asyncio.run(run_standalone_task(args.command, mode="task", agent=args.agent))
    elif args.plan:
        asyncio.run(run_standalone_task(args.plan, mode="plan", agent=args.agent))
    elif args.notify:
        if _send_notification("CLI Notification", html.escape(args.notify)):
            console.print(f"[bold green]✅ Notification sent.[/bold green]")
    elif args.file:
        file_path = Path(args.file)
        if file_path.exists():
            body = f"<b>File:</b> <code>{file_path.name}</code>\n\n<pre>{html.escape(file_path.read_text())}</pre>"
            _send_notification("File Transfer", body, "📄")
    else:
        # Default: Interactive Mode
        asyncio.run(run_interactive_cli(selected_agent=args.agent))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 ASURA Shutdown.")
