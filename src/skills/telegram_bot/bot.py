"""
Telegram Bot Hub for ASURA Sovereign AI
Supports Dual-Bot Infrastructure:
1. Core Bot (System Control, Research, Evolution)
2. Insta Bot (Content Generation, Draft Approvals)
"""

import os
import asyncio
import logging
from datetime import time, timezone, timedelta, datetime
from functools import wraps
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from settings import settings as config
logging.getLogger("httpx").setLevel(logging.WARNING)

from skills.logger import log_audit, log_app
from skills.todo_manager import format_todos_summary, add_todo
from skills.hardware_monitor import get_resource_summary
from skills.backup_manager import create_snapshot, list_snapshots, restore_snapshot
from skills.skill_registry import discover_skills, list_skills
from skills.telegram_bot.handlers import (
    TOPIC_SELECTION, SUGGEST_TOPIC, PREVIEW, CAPTION,
    cmd_start, cmd_topics,
    topic_callback, suggest_topic_input,
    preview_callback, caption_input,
    cancel, chat_handler, send_topic_buttons, cmd_hibernate,
    cmd_screenshot, voice_handler, photo_handler, checklist_callback
)
from skills.ai_content.generator import generate_topics


# ==============================================================
# Smart Reply — Handles splitting and formatting
# ==============================================================
async def send_smart_reply(update: Update, text: str, **kwargs):
    if not text: return
    MAX_LEN = 4000
    if len(text) <= MAX_LEN:
        await safe_reply(update.message, text, **kwargs)
        return
    parts = []
    while text:
        if len(text) <= MAX_LEN:
            parts.append(text)
            break
        split_at = text.rfind("\n", 0, MAX_LEN)
        if split_at == -1: split_at = text.rfind(" ", 0, MAX_LEN)
        if split_at == -1: split_at = MAX_LEN
        parts.append(text[:split_at])
        text = text[split_at:].lstrip()
    for i, part in enumerate(parts):
        await safe_reply(update.message, f"[{i+1}/{len(parts)}]\n{part}", **kwargs)

async def safe_reply(message, text: str, **kwargs):
    for attempt in range(2):
        try:
            await message.reply_text(text, parse_mode="HTML" if "HTML" in str(kwargs.get("parse_mode", "")) else "Markdown", **kwargs)
            return
        except Exception:
            try:
                await message.reply_text(text, **kwargs)
                return
            except: pass


# ─── Global refs ──────────────────────────────────────────────
_core_app: Application = None
_insta_app: Application = None
_proactive_engine = None


def set_proactive_engine(engine):
    global _proactive_engine
    _proactive_engine = engine


# ==============================================================
# RBAC Authentication Decorator
# ==============================================================
def requires_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            from core.rbac import has_permission, get_owner_id, register_owner, get_role
            chat_id = update.effective_chat.id
            if get_owner_id() is None:
                register_owner(chat_id, update.effective_user.full_name)
            if not has_permission(chat_id, permission):
                await update.message.reply_text(f"🔒 Access denied. Role required: `{permission}`.")
                return
            if _proactive_engine:
                _proactive_engine.mark_interaction()
            return await func(update, context)
        return wrapper
    return decorator


def owner_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from core.rbac import is_owner, get_owner_id, register_owner
        chat_id = update.effective_chat.id
        if get_owner_id() is None:
            register_owner(chat_id, update.effective_user.full_name)
        if not is_owner(chat_id):
            await update.message.reply_text("🔒 Owner only.")
            return
        return await func(update, context)
    return wrapper


# ==============================================================
# Notification Logic (Dual-Bot Aware)
# ==============================================================
def notify_master(message: str, is_insta: bool = False):
    """Sync notification wrapper with absolute fallback."""
    global _core_app, _insta_app
    if not config.TELEGRAM_ADMIN_CHAT_ID: return

    target_app = _insta_app if is_insta else _core_app
    token = config.INSTAGRAM_BOT_TOKEN if is_insta else config.TELEGRAM_BOT_TOKEN

    try:
        loop = getattr(target_app, "main_loop", None) if target_app else None
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(
                target_app.bot.send_message(chat_id=config.TELEGRAM_ADMIN_CHAT_ID, text=message, parse_mode="HTML"), 
                loop
            )
        else:
            import requests
            if not token or token.startswith("YOUR_"): return
            session = requests.Session(); session.trust_env = False
            session.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                         json={"chat_id": config.TELEGRAM_ADMIN_CHAT_ID, "text": message, "parse_mode": "HTML"}, 
                         timeout=15)
    except Exception as e:
        log_app(f"Notification failed: {e}")


def send_file_to_master(file_path: str, caption: str = "", is_insta: bool = False) -> bool:
    global _core_app, _insta_app
    if not os.path.exists(file_path): return False
    target_app = _insta_app if is_insta else _core_app
    token = config.INSTAGRAM_BOT_TOKEN if is_insta else config.TELEGRAM_BOT_TOKEN
        
    try:
        loop = getattr(target_app, "main_loop", None) if target_app else None
        if loop and loop.is_running():
            from telegram import InputFile
            async def _send():
                with open(file_path, "rb") as f:
                    await target_app.bot.send_document(
                        chat_id=config.TELEGRAM_ADMIN_CHAT_ID,
                        document=InputFile(f, filename=os.path.basename(file_path)),
                        caption=caption
                    )
            asyncio.run_coroutine_threadsafe(_send(), loop)
            return True
        else:
            import requests
            if not token or token.startswith("YOUR_"): return False
            session = requests.Session(); session.trust_env = False
            with open(file_path, "rb") as f:
                resp = session.post(f"https://api.telegram.org/bot{token}/sendDocument", 
                                    data={"chat_id": config.TELEGRAM_ADMIN_CHAT_ID, "caption": caption}, 
                                    files={"document": f}, timeout=60)
            return resp.status_code == 200
    except Exception: return False


# ─── Bot Handlers ───

async def choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    data = query.data
    if not data.startswith("choice_"): return
    idx = int(data.split("_")[1]); pending = context.user_data.pop("pending_mcq", None)
    if not pending: return
    choice_text = pending["choices"][idx]
    await query.edit_message_text(f"🎯 **Selection:** {choice_text}")
    from core.gateway import handle_message
    reply = await handle_message(str(update.effective_user.id), f"I choose: {choice_text}", channel="telegram")
    await update.message.reply_text(reply, parse_mode="Markdown")

async def cmd_skills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    registry = discover_skills()
    kb = [[InlineKeyboardButton(s, callback_data=f"skill_info_{s}")] for s in sorted(registry.keys())]
    await update.message.reply_text("🧩 <b>ASURA Capability Registry</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def cmd_think(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = " ".join(context.args)
    if not q: return
    await update.message.reply_text("🧠 *Thinking...*")
    from core.reasoning import think
    res = await asyncio.get_event_loop().run_in_executor(None, think, q)
    await update.message.reply_text(f"💡 {res.get('conclusion')}")

async def skill_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    name = query.data.replace("skill_info_", "")
    registry = discover_skills(); skill = registry.get(name)
    if skill:
        await query.edit_message_text(f"<b>Skill: {name}</b>\n{skill.get('description')}", parse_mode="HTML")

async def back_to_skills_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    await cmd_skills(update, context)


# ─── Bot Lifecycle ───

def create_core_bot():
    """Build the main ASURA bot for system control and research."""
    async def post_init(app: Application):
        app.main_loop = asyncio.get_running_loop()
    
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("skills", cmd_skills))
    app.add_handler(CommandHandler("run", cmd_run))
    app.add_handler(CommandHandler("think", cmd_think))
    app.add_handler(CommandHandler("screenshot", cmd_screenshot))
    
    app.add_handler(CallbackQueryHandler(skill_info_callback, pattern="^skill_info_"))
    app.add_handler(CallbackQueryHandler(back_to_skills_callback, pattern="^back_to_skills$"))
    app.add_handler(CallbackQueryHandler(choice_callback, pattern="^choice_"))
    app.add_handler(CallbackQueryHandler(checklist_callback, pattern="^toggle_check_"))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, requires_permission("chat")(chat_handler)))
    app.add_handler(MessageHandler(filters.VOICE, requires_permission("chat")(voice_handler)))
    app.add_handler(MessageHandler(filters.PHOTO, requires_permission("visual")(photo_handler)))
    
    global _core_app
    _core_app = app
    return app

def create_insta_bot():
    """Build the specialized Instagram Content bot."""
    async def post_init(app: Application):
        app.main_loop = asyncio.get_running_loop()

    app = Application.builder().token(config.INSTAGRAM_BOT_TOKEN).post_init(post_init).build()
    
    # Instagram-specific handlers (topics and posting)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("topics", cmd_topics))
    
    from skills.telegram_bot.handlers import (
        TOPIC_SELECTION, SUGGEST_TOPIC, PREVIEW, CAPTION,
        topic_callback, suggest_topic_input, preview_callback, caption_input, cancel
    )
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("post", cmd_topics)],
        states={
            TOPIC_SELECTION: [CallbackQueryHandler(topic_callback)],
            SUGGEST_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, suggest_topic_input)],
            PREVIEW: [CallbackQueryHandler(preview_callback)],
            CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, caption_input)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)
    
    global _insta_app
    _insta_app = app
    return app

def get_notify_fn(): return notify_master

def start_bot():
    """Legacy entry point, triggers core bot only."""
    app = create_core_bot()
    app.run_polling()
