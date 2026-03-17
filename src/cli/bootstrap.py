import os
import sys
import subprocess
import platform
from pathlib import Path

def setup_venv(base_dir: Path, venv_dir: Path):
    """Create virtual environment with uv (ultra-fast)."""
    print("🐍 Creating virtual environment with uv...")
    try:
        subprocess.run(["uv", "venv", str(venv_dir)], check=True, capture_output=True)
        print("✅ Virtual environment created")
        return True
    except FileNotFoundError:
        print("❌ 'uv' not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create venv: {e.stderr.decode()}")
        return False

def install_deps(base_dir: Path):
    """Install project dependencies using uv pip install."""
    print("📦 Installing dependencies with uv...")
    try:
        result = subprocess.run(
            ["uv", "pip", "install", "-e", "."],
            cwd=base_dir,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ All dependencies installed")
            return True
        else:
            print(f"⚠️  Dependency issue: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Install failed: {e}")
        return False

def get_clean_env():
    """Return environment without conflicting VIRTUAL_ENV."""
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.pop("PYTHONHOME", None)
    return env

def is_venv_ready(venv_dir: Path):
    """Check if virtual environment is set up."""
    if platform.system() == "Windows":
        return (venv_dir / "Scripts" / "python.exe").is_file()
    return (venv_dir / "bin" / "python").is_file()
