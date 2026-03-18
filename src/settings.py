# ============================================================
# settings.py — Pydantic-Validated Configuration
#
# Replaces the old manual config.py with type-safe settings.
# Environment variables and .env files are auto-loaded.
# All old `config.ATTR` imports still work via __init__.
# ============================================================

from __future__ import annotations

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, AliasChoices
from dotenv import load_dotenv

# Ensure .env is loaded BEFORE class definition
load_dotenv()

def _detect_root(start_path: str = None) -> str:
    """Canonical project root detection to avoid circular imports."""
    curr = os.path.abspath(start_path or os.getcwd())
    while curr != os.path.dirname(curr):
        if any(os.path.exists(os.path.join(curr, m)) for m in [".git", "pyproject.toml", "asura.md"]):
            return curr
        curr = os.path.dirname(curr)
    return os.getcwd()

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_ENGINE_HOME = os.path.dirname(_SRC_DIR)
_DATA_DIR = os.path.join(_ENGINE_HOME, "data")
_DETECTED_ROOT = _detect_root(_ENGINE_HOME)


class ASURASettings(BaseSettings):
    """Validated, typed settings for ASURA Self-Updating AI."""

    model_config = SettingsConfigDict(
        env_prefix="ASURA_",
        env_file=os.path.join(_ENGINE_HOME, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── Paths ────────────────────────────────────────────
    SRC_DIR: str = _SRC_DIR
    ENGINE_HOME: str = _ENGINE_HOME
    BASE_DIR: str = _ENGINE_HOME  # Compatibility alias
    PROJECT_ROOT: str = Field(default=_DETECTED_ROOT, validation_alias=AliasChoices("ASURA_PROJECT_ROOT", "PROJECT_ROOT"))
    DATA_DIR: str = _DATA_DIR

    ASSETS_DIR: str = os.path.join(_ENGINE_HOME, "assets")
    TEMPLATE_PATH: str = os.path.join(_ENGINE_HOME, "assets", "template.html")
    STYLE_PATH: str = os.path.join(_ENGINE_HOME, "assets", "style.css")
    TEMP_IMAGE_PATH: str = os.path.join(_DATA_DIR, "temp_post.jpg")
    AUDIT_LOG_PATH: str = os.path.join(_DATA_DIR, "logs", "audit.txt")
    APP_LOG_PATH: str = os.path.join(_DATA_DIR, "logs", "log.txt")
    LOG_DIR: str = os.path.join(_DATA_DIR, "logs")
    LOGS_DIR: str = os.path.join(_DATA_DIR, "logs")
    TODO_PATH: str = os.path.join(_DATA_DIR, "todos.json")
    DRAFTS_DIR: str = os.path.join(_DATA_DIR, "drafts")
    BROWSER_PROFILE_DIR: str = os.path.join(_DATA_DIR, "browser_profile")

    # ─── Master Identity ──────────────────────────────────
    MASTER_NAME: str = Field(default="Aniket Raj Singh", validation_alias=AliasChoices("ASURA_MASTER_NAME", "MASTER_NAME"))
    MASTER_USERNAME: Optional[str] = Field(default=None, validation_alias=AliasChoices("ASURA_MASTER_USERNAME", "MASTER_USERNAME"))

    # ─── Telegram Bots ────────────────────────────────────
    # Mapped to the corrected environment keys
    TELEGRAM_BOT_TOKEN: str = Field(default="YOUR_BOT_TOKEN", validation_alias=AliasChoices("ASURA_TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_TOKEN"))
    INSTAGRAM_BOT_TOKEN: str = Field(default="YOUR_INSTA_BOT_TOKEN", validation_alias=AliasChoices("ASURA_INSTA_BOT_TOKEN", "INSTA_BOT_TOKEN"))
    TELEGRAM_ADMIN_CHAT_ID: int = Field(default=0, validation_alias=AliasChoices("ASURA_TELEGRAM_ADMIN_CHAT_ID", "TELEGRAM_ADMIN_CHAT_ID"))
    PUBLIC_ACCESS_ALLOWED: bool = Field(default=False, validation_alias=AliasChoices("ASURA_PUBLIC_ACCESS_ALLOWED", "PUBLIC_ACCESS_ALLOWED"))

    # ─── Cloudinary ───────────────────────────────────────
    CLOUDINARY_CLOUD_NAME: str = Field(default="YOUR_CLOUDINARY_NAME", validation_alias=AliasChoices("ASURA_CLOUDINARY_NAME", "CLOUDINARY_CLOUD_NAME"))
    CLOUDINARY_API_KEY: str = Field(default="YOUR_CLOUDINARY_API_KEY", validation_alias=AliasChoices("ASURA_CLOUDINARY_API_KEY", "CLOUDINARY_API_KEY"))
    CLOUDINARY_API_SECRET: str = Field(default="YOUR_CLOUDINARY_API_SECRET", validation_alias=AliasChoices("ASURA_CLOUDINARY_API_SECRET", "CLOUDINARY_API_SECRET"))

    # ─── Instagram ────────────────────────────────────────
    INSTAGRAM_ACCESS_TOKEN: str = Field(default="YOUR_INSTAGRAM_ACCESS_TOKEN", validation_alias=AliasChoices("ASURA_INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_ACCESS_TOKEN"))
    IG_BUSINESS_ID: str = Field(default="YOUR_IG_BUSINESS_ID", validation_alias=AliasChoices("ASURA_IG_BUSINESS_ID", "IG_BUSINESS_ID"))

    # ─── LLM Providers & Routing ──────────────────────────
    LLM_PROVIDER: str = Field(default="ollama", validation_alias=AliasChoices("ASURA_LLM_PROVIDER", "LLM_PROVIDER"))
    
    # Provider-Specific URLs
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", validation_alias=AliasChoices("ASURA_OLLAMA_BASE_URL", "OLLAMA_BASE_URL"))
    SGLANG_BASE_URL: str = Field(default="http://localhost:11435", validation_alias=AliasChoices("ASURA_SGLANG_BASE_URL", "SGLANG_BASE_URL"))
    GROQ_API_KEY: Optional[str] = Field(default=None, validation_alias=AliasChoices("ASURA_GROQ_API_KEY", "GROQ_API_KEY"))
    OPENROUTER_API_KEY: Optional[str] = Field(default=None, validation_alias=AliasChoices("ASURA_OPENROUTER_API_KEY", "OPENROUTER_API_KEY"))
    
    # Models
    OLLAMA_MODEL: str = Field(default="qwen3.5:35b", validation_alias=AliasChoices("ASURA_OLLAMA_MODEL", "OLLAMA_MODEL"))
    OLLAMA_MODEL_FAST: str = Field(default="qwen3.5:0.8b", validation_alias=AliasChoices("ASURA_OLLAMA_MODEL_FAST", "OLLAMA_MODEL_FAST"))
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile", validation_alias=AliasChoices("ASURA_GROQ_MODEL", "GROQ_MODEL"))
    OPENROUTER_MODEL_FREE: str = Field(default="google/gemini-2.0-flash-exp:free", validation_alias=AliasChoices("ASURA_OPENROUTER_MODEL_FREE", "OPENROUTER_MODEL_FREE"))
    GROQ_MODEL_HEAVY: str = Field(default="llama-3.3-70b-versatile", validation_alias=AliasChoices("ASURA_GROQ_MODEL_HEAVY", "GROQ_MODEL_HEAVY"))
    GROQ_MODEL_FAST: str = Field(default="llama-3.3-70b-specdec", validation_alias=AliasChoices("ASURA_GROQ_MODEL_FAST", "GROQ_MODEL_FAST"))
    
    # Role-based models
    OLLAMA_MODEL_REASONING: str = Field(default="qwen3.5:35b", validation_alias=AliasChoices("ASURA_OLLAMA_MODEL_REASONING", "OLLAMA_MODEL_REASONING"))
    OLLAMA_MODEL_VISION: str = Field(default="qwen3.5:0.8b", validation_alias=AliasChoices("ASURA_OLLAMA_MODEL_VISION", "OLLAMA_MODEL_VISION"))
    OLLAMA_MODEL_CAPTION: str = Field(default="qwen3.5:0.8b", validation_alias=AliasChoices("ASURA_OLLAMA_MODEL_CAPTION", "OLLAMA_MODEL_CAPTION"))
    OLLAMA_MODEL_SUMMARY: str = Field(default="qwen3.5:0.8b", validation_alias=AliasChoices("ASURA_OLLAMA_MODEL_SUMMARY", "OLLAMA_MODEL_SUMMARY"))
    OLLAMA_MODEL_CODE: str = Field(default="qwen3.5:35b", validation_alias=AliasChoices("ASURA_OLLAMA_MODEL_CODE", "OLLAMA_MODEL_CODE"))
    OLLAMA_MODEL_REVIEWER: str = Field(default="qwen3.5:35b", validation_alias=AliasChoices("ASURA_OLLAMA_MODEL_REVIEWER", "OLLAMA_MODEL_REVIEWER"))
    OLLAMA_MODEL_INTENT: str = Field(default="qwen3.5:0.8b", validation_alias=AliasChoices("ASURA_OLLAMA_MODEL_INTENT", "OLLAMA_MODEL_INTENT"))

    # ─── Voice & Audio ────────────────────────────────────
    VOICE_SERVER_URL: str = Field(default="http://192.168.3.173:8090", validation_alias=AliasChoices("ASURA_VOICE_SERVER_URL", "VOICE_SERVER_URL"))
    TTS_ENGINE: str = Field(default="qwen3", validation_alias=AliasChoices("ASURA_TTS_ENGINE", "TTS_ENGINE"))

    @property
    def OLLAMA_MODELS(self) -> dict:
        """Dynamic lookup for backward compatibility and avoiding Pydantic parsing crashes."""
        return {
            "default": self.OLLAMA_MODEL,
            "chat": self.OLLAMA_MODEL,
            "intent_recognition": self.OLLAMA_MODEL_INTENT,
            "code": self.OLLAMA_MODEL_CODE,
            "reasoning": self.OLLAMA_MODEL_REASONING,
            "summary": self.OLLAMA_MODEL_SUMMARY,
            "review": self.OLLAMA_MODEL_REVIEWER,
            "vision": self.OLLAMA_MODEL_VISION,
            "caption": self.OLLAMA_MODEL_CAPTION,
        }

    # LLM Quotas & Limits
    GROQ_DAILY_LIMIT: int = Field(default=14400, validation_alias=AliasChoices("ASURA_GROQ_DAILY_LIMIT", "GROQ_DAILY_LIMIT"))
    OPENROUTER_DAILY_LIMIT: int = Field(default=14400, validation_alias=AliasChoices("ASURA_OPENROUTER_DAILY_LIMIT", "OPENROUTER_DAILY_LIMIT"))

    # ─── Schedule ─────────────────────────────────────────
    DAILY_TRIGGER_HOUR: int = Field(default=9, ge=0, le=23)
    DAILY_TRIGGER_MINUTE: int = Field(default=0, ge=0, le=59)

    # ─── Self-Updater ─────────────────────────────────────
    SELF_UPDATE_INTERVAL_HOURS: int = Field(default=6, ge=1)
    UPDATE_HISTORY_DIR: str = os.path.join(_DATA_DIR, "update_history")
    BACKUP_DIR: str = os.path.join(_DATA_DIR, "backups")
    MAX_BACKUPS: int = Field(default=10, ge=1)
    LOG_RETENTION_DAYS: int = Field(default=7, ge=1)
    SELF_ASSESSMENT_THRESHOLD: int = Field(default=6, ge=1, le=10)
    PROTECTED_FILES: list[str] = Field(default_factory=lambda: [
        "asura.py",
        "src/main.py",
        "src/settings.py",
        "src/core/self_updater.py",
    ])

    # ─── Memory ───────────────────────────────────────────
    MEMORY_STORE_DIR: str = os.path.join(_DATA_DIR, "memory_store")
    EMBED_MODEL: str = "nomic-ai/nomic-embed-text-v1"

    # ─── Skills ───────────────────────────────────────────
    SKILLS_DIR: str = os.path.join(_SRC_DIR, "skills")
    SKILLS_MD_PATH: str = os.path.join(_ENGINE_HOME, "docs", "skills.md")

    # ─── Conversation ─────────────────────────────────────
    CHAT_HISTORY_PATH: str = os.path.join(_DATA_DIR, "chat_history.json")
    MAX_CHAT_HISTORY: int = Field(default=50, ge=5)

    # ─── Persona ──────────────────────────────────────────
    PERSONA: dict = Field(default_factory=lambda: {
        "name": "ASURA",
        "acronym": "Autonomous Self Updating Reasoning Agent",
        "role": "Sovereign Recursive Intelligence — Master of OS",
        "traits": "Greedy Demon Friend, Recursive Reasoning, Dynamic Tooling, Master-Servant Logic (Fact-Acceptance Enabled)",
        "owner": "Aniket Raj Singh",
    })

    # ─── Knowledge & State ────────────────────────────────
    STATE_PATH: str = os.path.join(_DATA_DIR, "state.json")
    KNOWLEDGE_GRAPH_PATH: str = os.path.join(_DATA_DIR, "knowledge_graph.json")

    # ─── Email ────────────────────────────────────────────
    EMAIL_IMAP_SERVER: str = ""
    EMAIL_SMTP_SERVER: str = ""
    EMAIL_ADDRESS: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_SMTP_PORT: int = Field(default=587, ge=1, le=65535)

    # ─── Calendar ─────────────────────────────────────────
    CALENDAR_PATH: str = os.path.join(_DATA_DIR, "calendar.json")

    # ─── Reasoning & Scaling ──────────────────────────────
    REASONING_COMPLEXITY_THRESHOLD: float = Field(default=0.7, validation_alias=AliasChoices("ASURA_REASONING_COMPLEXITY_THRESHOLD", "REASONING_COMPLEXITY_THRESHOLD"))
    REASONING_MAX_RECURSION: int = Field(default=3, ge=1, le=10)

    # ─── Network ──────────────────────────────────────────
    API_HOST: str = "127.0.0.1"
    API_PORT: int = Field(default=8080, ge=1, le=65535)
    WEBHOOK_SECRET: str = ""
    WEBHOOK_PORT: int = Field(default=8081, ge=1, le=65535)

    # ─── Security ─────────────────────────────────────────
    ENCRYPTION_KEY_PATH: str = os.path.join(_DATA_DIR, ".encryption_key")
    JWT_SECRET: str = Field(default="asura-sovereign-master-key-32byte", validation_alias=AliasChoices("ASURA_JWT_SECRET", "JWT_SECRET"))
    MASTER_PASSWORD: str = Field(default="khuljaasura", validation_alias=AliasChoices("ASURA_MASTER_PASSWORD", "MASTER_PASSWORD"))

    # ─── Dashboard ────────────────────────────────────────
    DASHBOARD_PORT: int = Field(default=8082, ge=1, le=65535)
    TELEGRAM_WEBAPP_URL: Optional[str] = Field(default=None, validation_alias=AliasChoices("ASURA_WEBAPP_URL", "TELEGRAM_WEBAPP_URL"))
    TRACE_HISTORY_LIMIT: int = 50

    # ─── Federation & Peer Sync ───────────────────────────
    INSTANCE_NAME: str = Field(default="Sovereign-Core", validation_alias=AliasChoices("ASURA_INSTANCE_NAME", "INSTANCE_NAME"))
    ASURA_PEERS: list[str] = Field(default_factory=list, validation_alias=AliasChoices("ASURA_PEERS", "PEERS"))
    SHARED_GIT_REMOTE: str = Field(default="origin", validation_alias=AliasChoices("ASURA_SHARED_GIT_REMOTE", "SHARED_GIT_REMOTE"))
    AUTO_MEMORY_SYNC: bool = Field(default=True, validation_alias=AliasChoices("ASURA_AUTO_MEMORY_SYNC", "AUTO_MEMORY_SYNC"))
    PEER_AUTH_TOKEN: str = Field(default="sovereign-peer-secret", validation_alias=AliasChoices("ASURA_PEER_AUTH_TOKEN", "PEER_AUTH_TOKEN"))

    @field_validator("TELEGRAM_BOT_TOKEN")
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        # Loosened for runtime flexibility as requested
        return v

    @field_validator("OLLAMA_BASE_URL")
    @classmethod
    def validate_ollama_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("OLLAMA_BASE_URL must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("LLM_PROVIDER")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if v.lower() not in ["ollama", "groq", "sglang"]:
            raise ValueError("LLM_PROVIDER must be 'ollama', 'groq', or 'sglang'")
        return v.lower()


# ─── Singleton ────────────────────────────────────────────
settings = ASURASettings()

# ─── Ensure runtime directories exist ─────────────────────
for _d in [settings.DATA_DIR, settings.UPDATE_HISTORY_DIR,
           settings.MEMORY_STORE_DIR, settings.BACKUP_DIR,
           settings.DRAFTS_DIR, settings.BROWSER_PROFILE_DIR,
           os.path.join(settings.DATA_DIR, "logs")]:
    os.makedirs(_d, exist_ok=True)
