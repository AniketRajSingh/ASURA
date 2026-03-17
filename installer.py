#!/usr/bin/env python3
"""
ASURA — Global Command Installer
Registers the 'asura' command to work from any directory.
Works on macOS, Windows, and Linux.
"""

import os
import sys
import platform
import subprocess
from pathlib import Path

def get_project_root():
    return Path(__file__).parent.absolute()

def install_unix():
    """Installation logic for macOS and Linux."""
    root = get_project_root()
    source_script = root / "asura.py"
    target_link = Path("/usr/local/bin/asura")

    # 1. Ensure asura.py is executable
    os.chmod(source_script, 0o755)

    print(f"🔗 Registering Unix symlink: {target_link} -> {source_script}")

    # 2. Check if already exists
    if target_link.exists():
        if target_link.is_symlink() and os.readlink(target_link) == str(source_script):
            print("✅ ASURA is already correctly linked.")
            return True
        else:
            print("⚠️  Found existing file at /usr/local/bin/asura. Overwriting...")
    
    try:
        # Needs sudo for /usr/local/bin
        cmd = ["sudo", "ln", "-sf", str(source_script), str(target_link)]
        subprocess.run(cmd, check=True)
        print("🚀 ASURA is now global! Try typing 'asura' in a new terminal.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create symlink (Sudo required?): {e}")
        return False

def install_windows():
    """Installation logic for Windows."""
    root = get_project_root()
    source_script = root / "asura.py"
    bat_file = root / "asura.bat"

    # 1. Create a .bat shim in the project root
    bat_content = f'@echo off\npython "{source_script}" %*'
    with open(bat_file, "w") as f:
        f.write(bat_content)
    
    print(f"📝 Created Windows shim: {bat_file}")

    # 2. Add project root to User PATH
    current_path = os.environ.get("PATH", "")
    if str(root) in current_path:
        print("✅ Project directory is already in PATH.")
        return True

    print(f"🛣️  Adding {root} to Windows PATH...")
    try:
        # Use setx to permanently update path
        new_path = f"{current_path};{root}"
        subprocess.run(['setx', 'PATH', new_path], check=True, capture_output=True)
        print("🚀 ASURA is now global! RESTART your terminal/CMD to apply changes.")
        return True
    except Exception as e:
        print(f"❌ Failed to update Windows PATH: {e}")
        return False

def main():
    system = platform.system()
    print(f"🛠️  Installing ASURA Global CLI for {system}...")

    success = False
    if system in ("Darwin", "Linux"):
        success = install_unix()
    elif system == "Windows":
        success = install_windows()
    else:
        print(f"❌ Unsupported OS: {system}")
        sys.exit(1)

    if success:
        print("\n✨ Installation successful.")
    else:
        print("\n⚠️  Installation encountered issues.")

if __name__ == "__main__":
    main()
