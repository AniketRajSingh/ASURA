#!/usr/bin/env python3
"""
stop.py — Universal Sovereign Kill Switch (Cross-Platform)

Usage:
    python stop.py          # Graceful shutdown
    python stop.py --force  # Force kill (SIGKILL)
"""

import os
import sys
import signal
import psutil
import platform

def kill_processes(force: bool = False, scope: str = "all"):
    print(f"🛑 Initiating Sovereign Kill Switch [Scope: {scope}]...")
    current_pid = os.getpid()

    # Kill order matters
    phases = []
    
    if scope in ["all", "core"]:
        phases.extend([
            ("Watcher", ["run.py", "uv"]),
            ("Core", ["main.py", "src/main.py", "src.main", "ASURA/src/main"]),
            ("Telegram", ["telegram_daemon.py", "bot.py"]),
            ("Dashboard", ["app.py", "dashboard/app.py"]),
        ])
        
    if scope in ["all", "daemon"]:
        phases.append(("Gateway", ["monitor.py", "command_handler.py"]))

    if scope == "all":
        phases.extend([
            ("AI Engines", ["qwen_tts_server.py", "ollama"]),
            ("Power Locks", ["caffeinate", "systemd-inhibit"]),
        ])

    total_killed = 0

    for phase_name, targets in phases:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['pid'] == current_pid:
                    continue

                cmdline = " ".join(proc.info['cmdline'] or [])
                name = proc.info['name'] or ""

                # Broader matching
                is_target = any(t in cmdline or t in name for t in targets)

                if is_target:
                    print(f"  ⚡ [{phase_name}] Terminating PID {proc.info['pid']} ({name})")
                    try:
                        proc.terminate()
                        # Short wait before force kill
                        _, alive = psutil.wait_procs([proc], timeout=1)
                        if alive:
                            print(f"  🚨 PID {proc.info['pid']} resilient. SIGKILL sent.")
                            proc.kill()
                    except:
                        try: proc.kill()
                        except: pass
                    total_killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

    # Clean up flags
    for flag in ["data/hibernate.flag"]:
        if os.path.exists(flag):
            os.remove(flag)
            print(f"  🧹 Cleaned up: {flag}")

    # Release Windows power lock if applicable
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            print("  🔓 Windows power lock released")
        except Exception:
            pass

    print(f"\n✅ Sovereign Shutdown Complete. {total_killed} processes terminated.")


if __name__ == "__main__":
    force = "--force" in sys.argv
    scope = "all"
    if "--core" in sys.argv:
        scope = "core"
    elif "--daemon" in sys.argv:
        scope = "daemon"
        
    kill_processes(force=force, scope=scope)

