"""
Telegram Bot Hub for ASURA Sovereign AI
Supports Dual-Bot Infrastructure:
1. Core Bot (System Control, Research, Evolution)
2. Insta Bot (Content Generation, Draft Approvals)
"""

import os
import asyncio
import logging
import re
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
    InlineQueryHandler,
    ContextTypes,
    filters,
)

from settings import settings as cfg
logging.getLogger("httpx").setLevel(logging.WARNING)

from skills.logger import log_audit, log_app

# ─── Global refs (Must be at top to avoid circular initialization errors) ────
_core_app: Application = None
_insta_app: Application = None
_proactive_engine = None
_pending_approvals: dict[int, dict] = {}

_llm_task_queue = None

def get_llm_queue():
    global _llm_task_queue
    if _llm_task_queue is None:
        _llm_task_queue = asyncio.Queue()
    return _llm_task_queue

def set_proactive_engine(engine):
    global _proactive_engine
    _proactive_engine = engine

# ==============================================================
# Smart Reply — Handles splitting and formatting
# ==============================================================
async def send_smart_reply(update: Update, text: str, **kwargs):
    """
    Intelligently splits responses and handles message formatting via core.formatter.
    """
    if not text: return
    
    reply_markup = kwargs.get("reply_markup")
    kwargs["reply_markup"] = None 

    # 1. Split and Format
    pattern = r'(```.*?```|\[ACTION\].*?\[/ACTION\]|\[OBSERVATION\].*?\[/OBSERVATION\])'
    parts = re.split(pattern, text, flags=re.DOTALL)
    clean_parts = [p.strip() for p in parts if p.strip()]
    
    from core.formatter import format_message
    for i, part in enumerate(clean_parts):
        is_last = (i == len(clean_parts) - 1)
        current_kwargs = kwargs.copy()
        if is_last: current_kwargs["reply_markup"] = reply_markup
        
        formatted_part = format_message(part, platform="telegram")
        if not formatted_part.strip(): continue
        await safe_reply(update.effective_message, formatted_part, **current_kwargs)

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

# ==============================================================
# RBAC Authentication Decorator
# ==============================================================
def requires_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            from core.rbac import has_permission, get_owner_id, register_owner, get_role
            chat_id = update.effective_chat.id
            
            # Master Bypass: If configured ID matches, always allow
            if chat_id == cfg.TELEGRAM_ADMIN_CHAT_ID:
                if _proactive_engine: _proactive_engine.mark_interaction()
                return await func(update, context)

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
        
        # Master Bypass
        if chat_id == cfg.TELEGRAM_ADMIN_CHAT_ID:
            return await func(update, context)

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
_last_proactive_msg_id = None

def notify_master(message: str, is_insta: bool = False, type: str = "generic", shred: bool = False):
    """Sync notification wrapper with absolute fallback, interactive types, and shredding."""
    global _core_app, _insta_app, _last_proactive_msg_id
    from settings import settings as cfg
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    if not cfg.TELEGRAM_ADMIN_CHAT_ID: return

    markup = None
    if type == "proactive_summary":
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Expand Recommendations", callback_data="choice_expand_recs")]])

    # 1. Try via Active App Loop
    target_app = _insta_app if is_insta else _core_app
    try:
        loop = getattr(target_app, "main_loop", None) if target_app else None
        if loop and loop.is_running():
            async def _send_and_shred():
                global _last_proactive_msg_id
                # Shred previous if requested
                if shred and _last_proactive_msg_id:
                    try: await target_app.bot.delete_message(chat_id=cfg.TELEGRAM_ADMIN_CHAT_ID, message_id=_last_proactive_msg_id)
                    except: pass
                
                # Send new
                new_msg = await target_app.bot.send_message(
                    chat_id=cfg.TELEGRAM_ADMIN_CHAT_ID, 
                    text=message, 
                    parse_mode="HTML",
                    reply_markup=markup
                )
                if shred: _last_proactive_msg_id = new_msg.message_id

            asyncio.run_coroutine_threadsafe(_send_and_shred(), loop)
            return
    except: pass

    # 2. FALLBACK: Pure requests
    import requests
    token = cfg.INSTAGRAM_BOT_TOKEN if is_insta else cfg.TELEGRAM_BOT_TOKEN
    bot_name = "Insta-Bot" if is_insta else "Core-Bot"

    if not token or token.startswith("YOUR_"):
        log_app(f"Notification skipped: {bot_name} token is placeholder.")
        return
    
    try:
        session = requests.Session(); session.trust_env = False
        
        # Shred previous if requested
        if shred and _last_proactive_msg_id:
            try: session.post(f"https://api.telegram.org/bot{token}/deleteMessage", 
                             json={"chat_id": cfg.TELEGRAM_ADMIN_CHAT_ID, "message_id": _last_proactive_msg_id}, timeout=3)
            except: pass

        payload = {"chat_id": cfg.TELEGRAM_ADMIN_CHAT_ID, "text": message, "parse_mode": "HTML"}
        if markup:
            # InlineKeyboardMarkup to dict
            kb = [[{"text": b.text, "callback_data": b.callback_data} for b in row] for row in markup.inline_keyboard]
            payload["reply_markup"] = {"inline_keyboard": kb}

        resp = session.post(f"https://api.telegram.org/bot{token}/sendMessage", json=payload, timeout=15)
        if resp.status_code == 200:
            if shred: _last_proactive_msg_id = resp.json().get("result", {}).get("message_id")
            log_app(f"Delivered to {bot_name} via fallback.")
        else:
            log_app(f"Failed to deliver to {bot_name}: {resp.text}")
    except Exception as e:
        log_app(f"Notification failed for {bot_name}: {e}")

def send_file_to_master(file_path: str, caption: str = "", is_insta: bool = False) -> bool:
    global _core_app, _insta_app
    if not os.path.exists(file_path): return False
    target_app = _insta_app if is_insta else _core_app
    token = cfg.INSTAGRAM_BOT_TOKEN if is_insta else cfg.TELEGRAM_BOT_TOKEN
        
    try:
        loop = getattr(target_app, "main_loop", None) if target_app else None
        if loop and loop.is_running():
            from telegram import InputFile
            async def _send():
                with open(file_path, "rb") as f:
                    await target_app.bot.send_document(
                        chat_id=cfg.TELEGRAM_ADMIN_CHAT_ID,
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
                                    data={"chat_id": cfg.TELEGRAM_ADMIN_CHAT_ID, "caption": caption}, 
                                    files={"document": f}, timeout=60)
            return resp.status_code == 200
    except Exception: return False

async def _delete_after_delay(chat_id: int, message_id: int, delay: int):
    """Wait and then delete a specific message."""
    await asyncio.sleep(delay)
    global _core_app
    try:
        await _core_app.bot.delete_message(chat_id=chat_id, message_id=message_id)
        log_audit("TELEGRAM", f"Self-destructed message {message_id} after {delay}s")
    except Exception: pass

def send_ephemeral_message(text: str, delay: int = 60, silent: bool = False):
    """Send a message that self-destructs after 'delay' seconds."""
    global _core_app
    if not cfg.TELEGRAM_ADMIN_CHAT_ID: return

    try:
        loop = getattr(_core_app, "main_loop", None) if _core_app else None
        if loop and loop.is_running():
            async def _send_and_shred():
                display_text = text if silent else f"🕒 <b>EPHEMERAL (Destructs in {delay}s):</b>\n\n{text}"
                msg = await _core_app.bot.send_message(
                    chat_id=cfg.TELEGRAM_ADMIN_CHAT_ID, 
                    text=display_text, 
                    parse_mode="HTML"
                )
                asyncio.create_task(_delete_after_delay(cfg.TELEGRAM_ADMIN_CHAT_ID, msg.message_id, delay))
            
            asyncio.run_coroutine_threadsafe(_send_and_shred(), loop)
            return True
    except Exception as e:
        log_app(f"Ephemeral send failed: {e}")
    return False

def send_poll_to_master(question: str, options: list[str], is_anonymous: bool = False, allows_multiple_answers: bool = False) -> bool:
    global _core_app
    if not cfg.TELEGRAM_ADMIN_CHAT_ID: return False

    try:
        loop = getattr(_core_app, "main_loop", None) if _core_app else None
        if loop and loop.is_running():
            async def _send():
                await _core_app.bot.send_poll(
                    chat_id=cfg.TELEGRAM_ADMIN_CHAT_ID,
                    question=question,
                    options=options,
                    is_anonymous=is_anonymous,
                    allows_multiple_answers=allows_multiple_answers
                )
            asyncio.run_coroutine_threadsafe(_send(), loop)
            return True
        else:
            import requests
            token = cfg.TELEGRAM_BOT_TOKEN
            if not token or token.startswith("YOUR_"): return False
            url = f"https://api.telegram.org/bot{token}/sendPoll"
            resp = requests.post(url, json={
                "chat_id": cfg.TELEGRAM_ADMIN_CHAT_ID,
                "question": question,
                "options": options,
                "is_anonymous": is_anonymous,
                "allows_multiple_answers": allows_multiple_answers
            }, timeout=15)
            return resp.status_code == 200
    except Exception: return False

# ─── Delayed Handler Imports ───
from skills.telegram_bot.handlers import (
    TOPIC_SELECTION, SUGGEST_TOPIC, PREVIEW, CAPTION,
    cmd_start, cmd_topics,
    topic_callback, suggest_topic_input,
    preview_callback, caption_input,
    cancel, chat_handler, send_topic_buttons, cmd_hibernate,
    cmd_screenshot, voice_handler, photo_handler, checklist_callback,
    inline_query_handler
)
from skills.ai_content.generator import generate_topics

# ─── Commands ───

@owner_only
async def cmd_allow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from core.rbac import add_user
    args = context.args or []
    if len(args) < 1: return
    uid = int(args[0]); role = args[1] if len(args) > 1 else "user"
    if add_user(uid, f"User-{uid}", role):
        await update.message.reply_text(f"✅ Added {uid} as {role}")

@owner_only
async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from core.rbac import format_users
    await update.message.reply_text(format_users())

async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd = " ".join(context.args)
    if not cmd: return
    from skills.shell_executor import execute
    result = await execute(cmd)
    output = result.get("stdout", "") or result.get("stderr", "") or "(no output)"
    await update.message.reply_text(f"```\n{output[:3000]}\n```", parse_mode="Markdown")

async def cmd_think(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trigger deep reasoning mode."""
    if context.args:
        q = " ".join(context.args)
    else:
        # If called from chat_handler mapping or with no args
        q = update.effective_message.text
        if q == "🔍 Think": q = "Hello ASURA, let's think."

    status = await update.effective_message.reply_text("🌀 **Initiating Deep Reasoning...**", parse_mode="Markdown")
    try:
        from core.reasoning import think
        from core.formatter import format_message
        res_dict = await think(q)
        conclusion = res_dict.get("conclusion", "Reasoning complete.")
        await status.edit_text(format_message(conclusion, platform="telegram"), parse_mode="HTML")
    except Exception as e:
        await status.edit_text(f"❌ Reasoning failed: {e}")

async def skill_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    from skills.skill_registry import load_skills
    name = query.data.replace("skill_info_", "")
    registry = load_skills(); skill = registry.get(name)
    if skill:
        await query.edit_message_text(f"<b>Skill: {name}</b>\n{skill.get('description')}", parse_mode="HTML")

async def back_to_skills_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    await cmd_skills(update, context)

async def choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    from skills.logger import log_audit
    log_audit("TELEGRAM_CALLBACK", f"User {update.effective_user.id} clicked: {data}")
    if not any(data.startswith(prefix) for prefix in ["choice_", "task_", "health_", "toggle_", "cleanup_", "view_", "memory_", "cluster_", "evolution_", "trigger_", "deep_", "system_", "capability_", "node_", "skill_", "probe_", "logs_", "choice_table_click_"]): return
    
    # ─── Specialized Direct Actions ────────────
    if data == "choice_check_health":
        from settings import settings as cfg
        await query.answer("🚦 Node selection requested.")
        kb = [[InlineKeyboardButton(f"📍 Local: {cfg.INSTANCE_NAME}", callback_data="health_node_local")]]
        for i, peer in enumerate(cfg.ASURA_PEERS):
            kb.append([InlineKeyboardButton(f"📡 Peer: {peer.replace('http://','').split(':')[0]}", callback_data=f"health_node_{i}")])
        await query.edit_message_text("🚦 <b>Select node for ASURA Pulse:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    elif data.startswith("health_node_"):
        node_id = data.replace("health_node_", "")
        if node_id == "local":
            from core.startup_checks import run_startup_checks
            from skills.hardware_monitor.monitor import get_resource_summary
            status_msg = await query.message.reply_text("🚦 <b>ASURA Pulse: Monitoring Local...</b>", parse_mode="HTML")
            async def _refresh_vitals():
                for i in range(12):
                    if context.user_data.get(f"stop_live_{status_msg.message_id}"):
                        break
                    try:
                        integrity_res, hardware_stats = await asyncio.gather(run_startup_checks(silent=True), asyncio.to_thread(get_resource_summary))
                        full_report = f"📊 <b>ASURA System Vitals (Live)</b>\n<i>Updated: {datetime.now().strftime('%H:%M:%S')}</i>\n\n{hardware_stats}\n\n🛠️ <b>Integrity:</b>\n{integrity_res}"
                        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                        kb = InlineKeyboardMarkup([
                            [InlineKeyboardButton("📋 Task Manager", callback_data="choice_task_manager")],
                            [InlineKeyboardButton("🛑 Stop Live", callback_data="choice_stop_live")]
                        ])
                        try: await status_msg.edit_text(full_report, reply_markup=kb, parse_mode="HTML")
                        except: break
                        await asyncio.sleep(5)
                    except: break
            asyncio.create_task(_refresh_vitals()); return
        else:
            idx = int(node_id); target = cfg.ASURA_PEERS[idx]
            await query.answer(f"📡 Querying Remote Health...")
            from core.federation import federation
            res = await federation.remote_handoff("/health", target)
            await query.edit_message_text(f"📡 <b>Remote Vitals:</b>\n\n{res}", parse_mode="Markdown")
        return
    
    elif data == "toggle_debug":
        from settings import settings as cfg
        cfg.DEBUG_MODE = not getattr(cfg, "DEBUG_MODE", False)
        status = "✅ ON" if cfg.DEBUG_MODE else "❌ OFF"
        await query.answer(f"Debug Mode: {status}")
        # Refresh the keyboard by re-triggering the Control Panel view
        from skills.telegram_bot.handlers import chat_handler
        update.message.text = "🛠️ Control Panel"
        return await chat_handler(update, context)

    elif data == "toggle_public":
        from settings import settings as cfg
        cfg.PUBLIC_ACCESS_ALLOWED = not getattr(cfg, "PUBLIC_ACCESS_ALLOWED", False)
        status = "✅ ON" if cfg.PUBLIC_ACCESS_ALLOWED else "❌ OFF"
        await query.answer(f"Public Access: {status}")
        from skills.telegram_bot.handlers import chat_handler
        update.message.text = "🛠️ Control Panel"
        return await chat_handler(update, context)

    elif data == "trigger_evolution":
        await query.answer("🚀 Initiating Evolution Cycle...")
        from core.self_updater import updater
        import threading
        threading.Thread(target=updater.run_cycle, daemon=True).start()
        await query.edit_message_text("🚀 <b>Evolution Cycle Triggered.</b>\nASURA is now self-improving...", parse_mode="HTML")
        return

    elif data == "deep_cleanup":
        from settings import settings as cfg
        await query.answer("🧹 Node selection requested.")
        kb = [[InlineKeyboardButton(f"📍 Local: {cfg.INSTANCE_NAME}", callback_data="cleanup_node_local")]]
        for i, peer in enumerate(cfg.ASURA_PEERS):
            kb.append([InlineKeyboardButton(f"📡 Peer: {peer.replace('http://','').split(':')[0]}", callback_data=f"cleanup_node_{i}")])
        await query.edit_message_text("🧹 <b>Select node for Deep Cleanup:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    elif data.startswith("cleanup_node_"):
        node_id = data.replace("cleanup_node_", "")
        if node_id == "local":
            from settings import settings as cfg
            from core.declarative_agent_loader import get_agent_loader
            try:
                for log in [cfg.APP_LOG_PATH, cfg.AUDIT_LOG_PATH]:
                    if os.path.exists(log):
                        with open(log, "w") as f: f.write("")
                loader = get_agent_loader(); loader._learned_cache = {}; loader._save_cache()
                await query.edit_message_text("✅ <b>Local Cleanup Successful.</b>", parse_mode="HTML")
            except: await query.edit_message_text("❌ Cleanup failed."); return
        else:
            idx = int(node_id); target = cfg.ASURA_PEERS[idx]
            from core.federation import federation
            res = await federation.remote_handoff("/cleanup", target)
            await query.edit_message_text(f"📡 <b>Remote Cleanup:</b>\n{res}", parse_mode="HTML")
        return

    elif data == "system_restart":
        from settings import settings as cfg
        await query.answer("🔄 Node selection requested.")
        
        # Build node selection keyboard
        kb = [
            [InlineKeyboardButton(f"📍 Local: {cfg.INSTANCE_NAME}", callback_data="choice_restart_node_local")]
        ]
        
        # Add peer nodes
        for i, peer in enumerate(cfg.ASURA_PEERS):
            peer_name = peer.replace("http://", "").replace(":8080", "")
            kb.append([InlineKeyboardButton(f"📡 Peer: {peer_name}", callback_data=f"choice_restart_node_{i}")])
            
        await query.edit_message_text(
            "🔄 <b>Cluster Restart Protocol</b>\nWhich node would you like to warm-restart?",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML"
        )
        return

    elif data.startswith("choice_restart_node_"):
        from settings import settings as cfg
        from core.federation import federation
        node_id = data.replace("choice_restart_node_", "")
        
        if node_id == "local":
            await query.answer("🔄 Restarting Local Node...")
            await query.edit_message_text(f"🔄 <b>Restarting {cfg.INSTANCE_NAME}...</b>\nConnection will drop briefly.", parse_mode="HTML")
            import sys
            await asyncio.sleep(2)
            os.execv(sys.executable, ['python'] + sys.argv)
        else:
            idx = int(node_id)
            target_peer = cfg.ASURA_PEERS[idx]
            peer_display = target_peer.replace("http://", "").replace(":8080", "")
            await query.answer(f"📡 Restarting {peer_display}...")
            await query.edit_message_text(f"📡 <b>Triggering Remote Restart...</b>\nTarget: <code>{peer_display}</code>", parse_mode="HTML")
            
            # Send the /restart command to the peer via federation
            try:
                reply = await federation.remote_handoff("/restart", target_peer)
                await query.edit_message_text(f"✅ <b>Remote Signal Sent</b>\n{reply}", parse_mode="HTML")
            except Exception as e:
                await query.edit_message_text(f"❌ <b>Remote Restart Failed</b>\n{e}", parse_mode="HTML")
        return

    elif data == "capability_probe":
        from settings import settings as cfg
        await query.answer("🛠️ Node selection requested.")
        kb = [[InlineKeyboardButton(f"📍 Local: {cfg.INSTANCE_NAME}", callback_data="probe_node_local")]]
        for i, peer in enumerate(cfg.ASURA_PEERS):
            kb.append([InlineKeyboardButton(f"📡 Peer: {peer.replace('http://','').split(':')[0]}", callback_data=f"probe_node_{i}")])
        await query.edit_message_text("🛠️ <b>Select node for Capability Probe:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    elif data.startswith("probe_node_"):
        node_id = data.replace("probe_node_", "")
        if node_id == "local":
            from core.startup_checks import verify_dispatcher_tools
            status_msg = await query.message.reply_text("🛠️ <b>ASURA Probe: Testing Local...</b>", parse_mode="HTML")
            try:
                results = await verify_dispatcher_tools(); passed = results.get("passed", [])
                await status_msg.edit_text(f"🛠️ <b>Local Probe</b>\n✅ Operational: {', '.join(passed)}", parse_mode="HTML")
            except: await status_msg.edit_text("❌ Probe failed."); return
        else:
            idx = int(node_id); target = cfg.ASURA_PEERS[idx]
            from core.federation import federation
            res = await federation.remote_handoff("/probe", target)
            await query.edit_message_text(f"📡 <b>Remote Probe:</b>\n{res}", parse_mode="HTML")
        return

    elif data == "view_logs":
        from settings import settings as cfg
        await query.answer("📜 Node selection requested.")
        kb = [[InlineKeyboardButton(f"📍 Local: {cfg.INSTANCE_NAME}", callback_data="logs_node_local")]]
        for i, peer in enumerate(cfg.ASURA_PEERS):
            kb.append([InlineKeyboardButton(f"📡 Peer: {peer.replace('http://','').split(':')[0]}", callback_data=f"logs_node_{i}")])
        await query.edit_message_text("📜 <b>Select node to view logs:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    elif data.startswith("logs_node_"):
        node_id = data.replace("logs_node_", "")
        if node_id == "local":
            from settings import settings as cfg
            try:
                with open(cfg.APP_LOG_PATH, "r") as f:
                    last_logs = "".join(f.readlines()[-15:])
                await query.edit_message_text(f"📜 <b>Local Logs</b>\n<pre>{last_logs}</pre>", parse_mode="HTML")
            except: await query.edit_message_text("❌ Failed to read logs."); return
        else:
            idx = int(node_id); target = cfg.ASURA_PEERS[idx]
            from core.federation import federation
            res = await federation.remote_handoff("/logs", target)
            await query.edit_message_text(f"📡 <b>Remote Logs:</b>\n<pre>{res}</pre>", parse_mode="HTML")
        return

    elif data == "cluster_topology":
        from core.federation import federation
        from settings import settings as cfg
        await query.answer("🌐 Querying Cluster...")
        status_msg = await query.message.reply_text("🌐 <b>ASURA Cluster: Pinging peers...</b>", parse_mode="HTML")
        try:
            peers = await federation.ping_peers()
            
            lines = [f"🌐 <b>ASURA Federated Cluster</b>\n"]
            lines.append(f"📍 <b>Local:</b> <code>{cfg.INSTANCE_NAME}</code> (ONLINE)")
            
            if not peers:
                lines.append("\n<i>No sibling peers configured.</i>")
            else:
                for p in peers:
                    status_icon = "🟢" if p["status"] == "online" else "🔴"
                    url = p["url"].replace("http://", "").replace(":8080", "")
                    lines.append(f"{status_icon} <b>Peer:</b> <code>{url}</code> ({p['status'].upper()})")
            
            await status_msg.edit_text("\n".join(lines), parse_mode="HTML")
        except Exception as e:
            await status_msg.edit_text(f"❌ Cluster probe failed: {e}")
        return

    elif data == "evolution_log":
        from settings import settings as cfg
        await query.answer("🤖 Reading Evolution Bridge...")
        try:
            log_path = os.path.join(cfg.BASE_DIR, "chat_gemini_claude.md")
            if os.path.exists(log_path):
                with open(log_path, "r") as f:
                    content = f.read()
                # Simple cleanup for Telegram display
                content = content.replace("# ", "⭐️ ").replace("## ", "\n🔹 ").replace("### ", "\n🔸 ")
                await query.edit_message_text(f"🤖 <b>ASURA Evolution Log</b>\n\n{content[:3500]}", parse_mode="HTML")
            else:
                await query.edit_message_text("🤖 <b>No Evolution Log currently recorded.</b>", parse_mode="HTML")
        except Exception as e:
            await query.edit_message_text(f"❌ Failed to read evolution log: {e}")
        return

    elif data == "memory_pulse":
        from core.memory_manager import memory_manager
        from skills.memory.store import get_memory_store, get_freshness_score
        try:
            vault_data = await memory_manager._load_vault()
            vault_count = len(vault_data.get("permanent_facts", []))
            store_count = len(get_memory_store())
            freshness = get_freshness_score()
            
            report = (
                f"🧠 <b>ASURA Memory Pulse</b>\n"
                f"<i>State of global consciousness</i>\n\n"
                f"💎 <b>Sovereign Vault:</b> {vault_count} permanent facts\n"
                f"🌐 <b>Episodic RAG:</b> {store_count} processed documents\n"
                f"🔥 <b>Intelligence Freshness:</b> {freshness:.1f}%\n\n"
                f"✨ <i>All memory layers are synchronized and operational.</i>"
            )
            await query.edit_message_text(report, parse_mode="HTML")
        except Exception as e:
            await query.edit_message_text(f"❌ Memory Pulse failed: {e}")
        return

    elif data == "choice_expand_recs":
        from core.recommendation import recommendation_store
        pending = recommendation_store.get_pending()
        if not pending:
            await query.edit_message_text("✅ All recommendations processed.")
            return
        
        # Telegram limit is 100 buttons; we'll show top 15 for usability
        display_limit = 15
        top_pending = pending[:display_limit]
        
        kb = []
        for r in top_pending:
            kb.append([InlineKeyboardButton(f"💡 {r.content[:40]}...", callback_data=f"choice_rec_action_{r.id}")])
        
        if len(pending) > 5:
            kb.append([InlineKeyboardButton("🧹 Dismiss All Pending", callback_data="choice_clear_recs")])
        kb.append([InlineKeyboardButton("⬅️ Back to Hub", callback_data="choice_system_back")])
        
        msg = f"🧠 <b>ASURA Recommendations ({len(pending)} pending)</b>\n"
        if len(pending) > display_limit:
            msg += f"<i>Showing top {display_limit}. Use Dashboard for full list.</i>\n\n"
        msg += "Select one to take action:"
        
        await query.edit_message_text(
            msg,
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML"
        )
        return

    elif data.startswith("choice_rec_action_"):
        rec_id = data.replace("choice_rec_action_", "")
        from core.recommendation import recommendation_store
        items = recommendation_store.get_pending()
        rec = next((i for i in items if i.id == rec_id), None)
        if not rec: await query.answer("Expired."); return

        kb = [
            [InlineKeyboardButton("📥 Add to Queue", callback_data=f"choice_rec_add_{rec_id}")],
            [InlineKeyboardButton("✏️ Suggest Edit / Question", callback_data=f"choice_rec_edit_{rec_id}")],
            [InlineKeyboardButton("❌ Dismiss", callback_data=f"choice_rec_del_{rec_id}")],
            [InlineKeyboardButton("⬅️ Back to List", callback_data="choice_expand_recs")]
        ]
        await query.edit_message_text(
            f"🎯 <b>Recommendation Action</b>\n\n{rec.content}",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML"
        )
        return

    elif data.startswith("choice_rec_add_"):
        rec_id = data.replace("choice_rec_add_", "")
        from core.recommendation import recommendation_store
        recommendation_store.update_status(rec_id, "approved")
        kb = [[InlineKeyboardButton("⬅️ Back to List", callback_data="choice_expand_recs")]]
        await query.edit_message_text("✅ <b>Task Added to Queue</b>\nI'll execute this autonomously when resources allow.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    elif data.startswith("choice_rec_del_"):
        rec_id = data.replace("choice_rec_del_", "")
        from core.recommendation import recommendation_store
        recommendation_store.update_status(rec_id, "dismissed")
        kb = [[InlineKeyboardButton("⬅️ Back to List", callback_data="choice_expand_recs")]]
        await query.edit_message_text("🗑️ <b>Recommendation Dismissed.</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    elif data.startswith("choice_rec_edit_"):
        rec_id = data.replace("choice_rec_edit_", "")
        from telegram import ForceReply
        context.user_data["editing_rec_id"] = rec_id
        await query.message.reply_text(
            f"✏️ <b>Edit Recommendation</b>\nWhat should I change or what is your question about this task?",
            reply_markup=ForceReply(selective=True),
            parse_mode="HTML"
        )
        return

    elif data.startswith("choice_task_done_"):
        tid = data.replace("choice_task_done_", "")
        from core.recommendation import recommendation_store
        recommendation_store.update_status(tid, "done")
        await query.edit_message_text("✅ <b>Task marked as complete.</b>", parse_mode="HTML")
        return

    elif data.startswith("choice_task_del_"):
        tid = data.replace("choice_task_del_", "")
        from core.recommendation import recommendation_store
        recommendation_store.remove(tid)
        await query.edit_message_text("🗑️ <b>Task removed from queue.</b>", parse_mode="HTML")
        return

    elif data == "choice_task_manager":
        from skills.telegram_bot.handlers import show_task_manager
        return await show_task_manager(update, context)

    elif data == "choice_clear_recs":
        from core.recommendation import recommendation_store
        recommendation_store.clear_all(status="pending")
        await query.edit_message_text("🧹 <b>Sovereign Cleanup:</b> All pending recommendations have been dismissed.", parse_mode="HTML")
        return

    elif data == "choice_stop_live":
        await query.answer("🛑 Live monitoring stopped.")
        context.user_data[f"stop_live_{query.message.message_id}"] = True
        try: await query.edit_message_text(query.message.text.replace(" (Live)", " (Stopped)"), reply_markup=None)
        except: pass
        return

    # ─── MCQ Button Processing ────────────
    parts = data.split("_")
    if len(parts) < 2 or not parts[1].isdigit(): return
    
    idx = int(parts[1]); pending = context.user_data.pop("pending_mcq", None)
    if not pending: return
    choice_text = pending["choices"][idx]
    await query.edit_message_text(f"🎯 **Selection:** {choice_text}")
    from core.gateway import handle_message
    reply = await handle_message(str(update.effective_user.id), f"I choose: {choice_text}", channel="telegram")
    await update.effective_message.reply_text(reply, parse_mode="Markdown")

async def cmd_skills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from skills.skill_registry import load_skills
    registry = load_skills()
    kb = [[InlineKeyboardButton(s, callback_data=f"skill_info_{s}")] for s in sorted(registry.keys())]
    await update.effective_message.reply_text("🧩 <b>ASURA Capability Registry</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# ─── Bot Lifecycle ───

def create_core_bot():
    """Build the main ASURA bot for system control and research."""
    async def post_init(app: Application):
        app.main_loop = asyncio.get_running_loop()
        
        # Initialize central LLM Queue
        get_llm_queue()
        
        # Start Async Stream Daemon
        from skills.telegram_bot.worker import stream_worker_daemon
        app.create_task(stream_worker_daemon(app))
        
        # Register commands for the "Menu" button
        from telegram import BotCommand
        await app.bot.set_my_commands([
            BotCommand("start", "Launch Hub & Dashboard"),
            BotCommand("skills", "View Capabilities"),
            BotCommand("think", "Deep Reasoning Mode"),
            BotCommand("screenshot", "Capture Screen"),
            BotCommand("run", "Execute Command"),
        ])
    
    app = Application.builder().token(cfg.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("skills", cmd_skills))
    app.add_handler(CommandHandler("run", cmd_run))
    app.add_handler(CommandHandler("think", cmd_think))
    app.add_handler(CommandHandler("screenshot", cmd_screenshot))
    
    app.add_handler(CallbackQueryHandler(skill_info_callback, pattern="^skill_info_"))
    app.add_handler(CallbackQueryHandler(back_to_skills_callback, pattern="^back_to_skills$"))
    app.add_handler(CallbackQueryHandler(choice_callback, pattern="^(choice_|task_|health_|toggle_|cleanup_|view_|memory_|cluster_|evolution_|trigger_|deep_|system_|capability_|node_|skill_|probe_|logs_|choice_table_click_)"))
    app.add_handler(CallbackQueryHandler(checklist_callback, pattern="^toggle_check_"))
    
    app.add_handler(InlineQueryHandler(inline_query_handler))

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
        from telegram import BotCommand
        await app.bot.set_my_commands([
            BotCommand("start", "Launch Insta Dashboard"),
            BotCommand("post", "Create New Content"),
            BotCommand("topics", "View Trending Topics"),
            BotCommand("cancel", "Abort Operation"),
        ])

    app = Application.builder().token(cfg.INSTAGRAM_BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("topics", cmd_topics))
    
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
    
    # Also allow general chat on the Insta bot
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, requires_permission("chat")(chat_handler)))
    
    global _insta_app
    _insta_app = app
    return app

def get_notify_fn(): return notify_master
def get_or_create_session(uid, ch):
    from core.gateway import get_or_create_session as _gs
    return _gs(uid, ch)

def start_bot():
    """Legacy entry point, triggers core bot only."""
    app = create_core_bot()
    app.run_polling()
