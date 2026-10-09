# Installation & Setup

ASURA is an autonomous, sovereign AI infrastructure. The following instructions configure the system on local hardware.

## System Prerequisites
- **Python 3.10+** (Python 3.12 recommended)
- **uv** (recommended package and virtual environment manager)
- **Telegram Bot Token**: Generated via [@BotFather](https://t.me/BotFather)
- **Ollama**: Local model execution daemon (optional if using OpenRouter or Groq cloud providers)

## Repository Setup

```bash
git clone <repository-url>
cd ASURA

# Automated environment setup
python run.py setup

# Alternative manual virtual environment configuration
uv venv
uv pip install -e .
```

## Configuration

Credentials and environment variables are loaded from `.env` (or managed in `src/settings.py`):

1. `TELEGRAM_BOT_TOKEN`: Telegram bot API token.
2. `TELEGRAM_ADMIN_CHAT_ID`: Primary administrator chat ID.
3. `ASURA_LLM_PROVIDER`: Provider routing (`openrouter`, `groq`, or `ollama`).
4. `OPENROUTER_API_KEY`: API token for OpenRouter model access.
5. `GROQ_API_KEY`: API token for Groq cloud inference.
6. `OLLAMA_BASE_URL`: Local daemon URL (default: `http://localhost:11434`).

## Local Model Deployment (Ollama Tier)

For offline execution:

```bash
ollama pull qwen2.5:7b
ollama pull llama3.2-vision
```

## Execution

```bash
python run.py              # Launch system with live file watcher
python run.py start        # Background daemon mode with auto-restart
python run.py start --no-watch  # Start without file watcher
python src/main.py         # Direct orchestrator launch
```

Upon initial execution, the first user issuing `/start` on Telegram claims permanent administrative ownership via Role-Based Access Control (RBAC).

## Shutdown

```bash
python stop.py             # Graceful shutdown (terminates watcher, core, and OS locks)
python stop.py --force     # Force termination
```

## Role-Based Access Control
ASURA enforces multi-tier access control:
- **Owner**: Unrestricted system actuation, shell execution, and self-evolution.
- **Admin**: Command execution without self-evolution permissions.
- **User**: Conversational capabilities and non-destructive skills.
- **Viewer**: Read-only observability and status queries.
