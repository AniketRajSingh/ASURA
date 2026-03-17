# ⚙️ Installation & Setup

TF is a high-performance, autonomous AI system. Follow these steps to get it running on your local machine.

## 📋 Prerequisites
- **Python 3.10+** (3.12 recommended)
- **Ollama**: To run the local LLMs that power TF.
- **Telegram Bot Token**: Create one via [@BotFather](https://t.me/BotFather).
- **Cloudinary Account**: For image hosting (optional but recommended).

## 🚀 Step 1: Clone & Optimized Setup
TF is cross-platform (Mac, Windows, Linux). We recommend using **uv** for the fastest setup.

```bash
git clone <your-repo-url>
cd TF

# Optimized Cross-Platform Setup (Automatic)
python run.py setup

# Manual Setup (if desired)
uv venv
uv pip install -e .
python scripts/setup_env.py
python scripts/setup_qwen_tts.py
```
> **Note**: `psutil` is required for core resource governance and safety fail-safes.

## 🔑 Step 2: Configuration
Open `src/config.py` and set your credentials:
1. `TELEGRAM_BOT_TOKEN`: Your bot's API key.
2. `OLLAMA_BASE_URL`: Usually `http://localhost:11434`.
3. `CLOUDINARY_*`: Your Cloudinary credentials.

## 🏠 Step 3: Ollama Models
TF requires models that support tool-use and reasoning. We recommend:
```bash
ollama run gpt-oss:20b
# Optional: vision support
ollama pull llama3.2-vision
```

## ▶️ Step 4: Launch
```bash
python run.py              # Auto-setup + start with file watcher
python run.py start        # Start with auto-restart on code changes
python run.py start --no-watch  # Start without file watcher
```
Upon the first run, the first user to type `/start` to the bot on Telegram will be registered as the permanent **Owner**.

## ⏹️ Step 5: Stopping
```bash
python stop.py             # Graceful shutdown (kills watcher + core + OS locks)
python stop.py --force     # Force kill if graceful fails
```
You can also send `/hibernate` via Telegram.

## 🛡️ Security Note
TF uses **RBAC (Role Based Access Control)**. 
- **Owner**: Full system access.
- **Admin**: Command access, no self-evolution.
- **User**: Chat and basic skills only.
- **Viewer**: Read-only access to stats.
