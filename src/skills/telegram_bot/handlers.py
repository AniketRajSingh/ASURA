#!/usr/bin/env python3
"""
Telegram Bot handlers for the Self‑Updating AI system owned by Aniket Raj Singh.
"""

import html as html_mod
import os
import asyncio
from typing import List
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes, ConversationHandler

from skills.logger import log_audit, log_app
from core.sovereignty import get_authority
from core.formatter import format_message

# Conversation states
TOPIC_SELECTION: int = 1
SUGGEST_TOPIC: int = 2
PREVIEW: int = 3
CAPTION: int = 4

__all__ = [
    "TOPIC_SELECTION",
    "SUGGEST_TOPIC",
    "PREVIEW",
    "CAPTION",
    "cmd_start",
    "cmd_topics",
    "topic_callback",
    "suggest_topic_input",
    "preview_callback",
    "caption_input",
    "cancel",
    "cmd_hibernate",
    "cmd_screenshot",
    "chat_handler",
    "voice_handler",
    "photo_handler",
    "show_task_manager",
]

# ===========================================================================
# Security Decorator: Sovereign Master Only
# ===========================================================================
def master_only(func):
    """Decorator to restrict access to the sovereign Master only."""
    from functools import wraps
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        from settings import settings as cfg
        user_id = update.effective_user.id
        if cfg.PUBLIC_ACCESS_ALLOWED:
            return await func(update, context, *args, **kwargs)
        if user_id != cfg.TELEGRAM_ADMIN_CHAT_ID:
            log_audit("SECURITY_ALERT", f"Unauthorized access attempt by {user_id}")
            await update.message.reply_text(
                format_message("⛔ <b>Access Denied.</b> Only my Master has sovereignty over my systems.", platform="telegram"),
                parse_mode="HTML",
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

@master_only
async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice notes: Transcribe -> Reasoning -> Speak back."""
    from settings import settings as cfg
    log_audit("TELEGRAM", "Processing voice note...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
    voice_file = await update.message.voice.get_file()
    ogg_path = os.path.join(cfg.DATA_DIR, f"voice_{update.message.message_id}.ogg")
    await voice_file.download_to_drive(ogg_path)
    try:
        from skills.voice.interface import transcribe_audio
        text = transcribe_audio(ogg_path)
        if not text or "failed" in text.lower():
            await update.message.reply_text("🎙️ I heard you, but my voice engine is currently offline.")
            return
        from core.gateway import handle_message
        reply = await handle_message(str(update.effective_user.id), text, channel="telegram", agent_name="asura-telegram")
        await update.message.reply_text(format_message(reply, platform="telegram"), parse_mode="HTML")
    finally:
        if os.path.exists(ogg_path): os.remove(ogg_path)

@master_only
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photos for visual analysis and UI debugging."""
    from settings import settings as cfg
    log_audit("TELEGRAM", "Processing incoming photo...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    path = os.path.join(cfg.DATA_DIR, f"photo_{update.message.message_id}.jpg")
    await photo_file.download_to_drive(path)
    caption = update.message.caption or "Analyze this image."
    try:
        from skills.visual.vision import analyze_image, debug_ui_screenshot
        if any(w in caption.lower() for w in ["debug", "fix", "issue", "broken"]):
            analysis = await debug_ui_screenshot(path, bug_description=caption)
        else:
            analysis = await analyze_image(path, question=caption, heavy=True)
        await update.message.reply_text(format_message(analysis, platform="telegram"), parse_mode="HTML")
    finally:
        if os.path.exists(path): os.remove(path)

# ===========================================================================
# Helper: Send topics as inline buttons
# ===========================================================================
async def send_topic_buttons(update_or_context, topics: List[str], chat_id: int | None = None) -> None:
    keyboard = [[InlineKeyboardButton(f"📌 {topic}", callback_data=f"topic_{i}")] for i, topic in enumerate(topics)]
    keyboard.append([InlineKeyboardButton("🔄 Generate New", callback_data="generate_new"),
                     InlineKeyboardButton("💡 Suggest Me", callback_data="suggest_me")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🤖 *Here are today's AI & Tech topic suggestions:*\n\nPick one, generate new options, or suggest your own!"
    if hasattr(update_or_context, "bot"):
        await update_or_context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update_or_context.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

@master_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from settings import settings as cfg
    from telegram import WebAppInfo
    import socket
    
    # ─── Smart URL Detection ────────────
    # 1. Use manual override if set in .env
    # 2. Use local network IP (so it works on phone via Wi-Fi)
    # 3. Fallback to localhost
    webapp_url = cfg.TELEGRAM_WEBAPP_URL
    
    if not webapp_url:
        try:
            # Get local IP address
            s = socket.socket(socket.getaddrinfo('8.8.8.8', 80)[0][0], socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            webapp_url = f"http://{local_ip}:{cfg.DASHBOARD_PORT}"
        except:
            webapp_url = f"http://localhost:{cfg.DASHBOARD_PORT}"

    # ─── Deep Linking Logic ────────────
    args = context.args
    if args:
        param = args[0]
        if param == "sys_check":
            await update.message.reply_text("🔍 <b>Deep Link:</b> Initiating System Health Audit...")
            from core.startup_checks import run_startup_checks
            res = await run_startup_checks()
            await update.message.reply_text(res, parse_mode="HTML")
            return
        elif param == "screenshot":
            await cmd_screenshot(update, context)
            return

    # ─── Standard Menu ────────────
    from telegram import ReplyKeyboardMarkup
    
    # Persistent Bottom Keyboard
    reply_kb = ReplyKeyboardMarkup([
        ["🖥️ Dashboard", "🧩 Skills"],
        ["🚦 Health", "📸 Screenshot"],
        ["🔍 Think", "📋 Task Manager"],
        ["🛠️ Control Panel"]
    ], resize_keyboard=True)

    # Inline Action Buttons
    if webapp_url.startswith("https://"):
        launch_btn = InlineKeyboardButton("🖥️ Launch Command Center", web_app=WebAppInfo(url=webapp_url))
    else:
        launch_btn = InlineKeyboardButton("🖥️ Launch Command Center", url=webapp_url)

    keyboard = [
        [launch_btn],
        [InlineKeyboardButton("🧩 Skills Registry", callback_data="back_to_skills"),
         InlineKeyboardButton("🚦 System Vitals", callback_data="choice_check_health")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"🤖 <b>ASURA — Sovereign AI</b>\n"
        f"Master: <code>{cfg.MASTER_NAME}</code>\n\n"
        f"I am your recursive intelligence hub. Use the button below to launch the "
        f"interactive <b>Command Center</b> Mini-App, or use the menu buttons below."
    )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")
    # Also send the persistent keyboard
    await update.message.reply_text("<i>Persistent menu activated.</i>", reply_markup=reply_kb, parse_mode="HTML")

async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle '@bot search' in any chat. Search FAISS memory and KG."""
    query = update.inline_query.query
    if not query:
        return

    from core.memory_manager import memory_manager
    from telegram import InlineQueryResultArticle, InputTextMessageContent
    import uuid

    # Search Memory
    results = await memory_manager.recall(query, limit=5)
    
    articles = []
    # Split results into chunks for the inline cards
    for i, part in enumerate(results.split("•")):
        if not part.strip() or "===" in part: continue
        
        articles.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=f"Neural Match {i+1}",
                description=part.strip()[:100],
                input_message_content=InputTextMessageContent(f"<b>ASURA Neural Recall:</b>\n\n{part.strip()}", parse_mode="HTML")
            )
        )

    await update.inline_query.answer(articles, cache_time=60)

@master_only
async def cmd_topics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from skills.ai_content.generator import generate_topics
    await update.message.reply_text("⏳ Generating topic suggestions...")
    try:
        topics = await generate_topics()
        context.user_data["topics"] = topics
        await send_topic_buttons(update, topics)
        return TOPIC_SELECTION
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")
        return ConversationHandler.END

async def topic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    from skills.ai_content.generator import generate_topics, generate_caption
    from skills.instagram_poster.renderer import render_post
    if data == "generate_new":
        topics = await generate_topics()
        context.user_data["topics"] = topics
        await send_topic_buttons(update, topics, chat_id=query.message.chat_id)
        return TOPIC_SELECTION
    if data == "suggest_me":
        await query.edit_message_text("💡 *Send me your topic idea:*", parse_mode="Markdown")
        return SUGGEST_TOPIC
    if data.startswith("topic_"):
        idx = int(data.split("_")[1]); selected = context.user_data["topics"][idx]
        context.user_data["selected_topic"] = selected
        image_path = render_post(selected); context.user_data["image_path"] = image_path
        caption = await generate_caption(selected); context.user_data["default_caption"] = caption
        with open(image_path, "rb") as img:
            await query.message.reply_photo(photo=img, caption=f"📸 Preview: {selected}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Post Now", callback_data="post_now"), InlineKeyboardButton("❌ Cancel", callback_data="cancel_post")]]), parse_mode="Markdown")
        return PREVIEW
    return TOPIC_SELECTION

async def suggest_topic_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from skills.instagram_poster.renderer import render_post
    from skills.ai_content.generator import generate_caption
    topic = update.message.text.strip(); context.user_data["selected_topic"] = topic
    image_path = render_post(topic); context.user_data["image_path"] = image_path
    caption = await generate_caption(topic); context.user_data["default_caption"] = caption
    with open(image_path, "rb") as img:
        await update.message.reply_photo(photo=img, caption=f"📸 Preview: {topic}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Post Now", callback_data="post_now"), InlineKeyboardButton("❌ Cancel", callback_data="cancel_post")]]), parse_mode="Markdown")
    return PREVIEW

async def preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query; await query.answer()
    if query.data == "cancel_post": await query.edit_message_caption(caption="❌ Post cancelled."); return ConversationHandler.END
    if query.data == "post_now":
        caption = context.user_data.get("default_caption", "")
        await query.message.reply_text(f"✏️ *Accept caption?*\n\n{caption}\n\nType custom or 'use_default'.", parse_mode="Markdown")
        return CAPTION
    return PREVIEW

async def caption_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from skills.instagram_poster.poster import upload_image, post_to_instagram
    user_text = update.message.text.strip()
    caption = context.user_data["default_caption"] if user_text.lower() == "use_default" else user_text
    image_path = context.user_data["image_path"]
    try:
        url = upload_image(image_path)
        post_id = await post_to_instagram(url, caption, context.bot, update.effective_chat.id)
        await update.message.reply_text(f"🎉 Published! ID: `{post_id}`", parse_mode="Markdown")
    except Exception as e: await update.message.reply_text(f"❌ Failed: {e}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("👋 Cancelled."); return ConversationHandler.END

@master_only
async def cmd_hibernate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("💤 *Initiating Hibernation...*", parse_mode="Markdown")
    get_authority().hibernate(); return ConversationHandler.END

@master_only
async def cmd_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("📸 Taking screenshot...")
    try:
        from core.tool_protocol import dispatch
        path = await dispatch("screenshot", None)
        if path:
            with open(path, "rb") as f: await update.message.reply_photo(photo=f)
            os.remove(path)
    except Exception as e: await update.message.reply_text(f"❌ Failed: {e}")

@master_only
async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id); user_msg = update.message.text
    if not user_msg: return

    # ─── Persistent Menu Mapping ────────────
    from skills.telegram_bot.bot import cmd_skills, cmd_think
    if user_msg == "🖥️ Dashboard":
        return await cmd_start(update, context)
    elif user_msg == "🧩 Skills":
        return await cmd_skills(update, context)
    elif user_msg == "🚦 Health":
        from core.startup_checks import run_startup_checks
        from skills.hardware_monitor.monitor import get_resource_summary
        
        status_msg = await update.message.reply_text("🚦 <b>ASURA Pulse: Monitoring active...</b>", parse_mode="HTML")
        
        async def _refresh_vitals():
            for i in range(12): # Refresh 12 times (60 seconds)
                try:
                    integrity_res, hardware_stats = await asyncio.gather(
                        run_startup_checks(silent=True),
                        asyncio.to_thread(get_resource_summary)
                    )
                    full_report = (
                        f"📊 <b>ASURA System Vitals (Live)</b>\n"
                        f"<i>Updated: {datetime.now().strftime('%H:%M:%S')}</i>\n\n"
                        f"{hardware_stats}\n\n"
                        f"🛠️ <b>Integrity Check:</b>\n{integrity_res}"
                    )
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("📋 Task Manager", callback_data="choice_task_manager")],
                        [InlineKeyboardButton("🧹 Deep Cleanup", callback_data="deep_cleanup")],
                        [InlineKeyboardButton("🛑 Stop Live", callback_data="choice_stop_live")]
                    ])
                    try: await status_msg.edit_text(full_report, reply_markup=kb, parse_mode="HTML")
                    except: break
                    await asyncio.sleep(5)
                except: break
            try: await status_msg.edit_text(status_msg.text.replace("(Live)", "(Final)"), parse_mode="HTML")
            except: pass

        asyncio.create_task(_refresh_vitals())
        return
    elif user_msg == "📸 Screenshot":
        return await cmd_screenshot(update, context)
    elif user_msg == "🔍 Think":
        from telegram import ForceReply
        return await update.message.reply_text(
            "🧠 <b>Deep Reasoning Mode</b>\nWhat should I reason about?", 
            reply_markup=ForceReply(selective=True),
            parse_mode="HTML"
        )
    elif user_msg == "📋 Task Manager":
        return await show_task_manager(update, context)

    elif user_msg == "🛠️ Control Panel":
        from settings import settings as cfg
        debug_status = "✅ ON" if getattr(cfg, "DEBUG_MODE", False) else "❌ OFF"
        public_status = "✅ ON" if getattr(cfg, "PUBLIC_ACCESS_ALLOWED", False) else "❌ OFF"
        
        kb = [
            [InlineKeyboardButton(f"🪲 Debug Mode: {debug_status}", callback_data="toggle_debug")],
            [InlineKeyboardButton(f"🌍 Public Access: {public_status}", callback_data="toggle_public")],
            [InlineKeyboardButton("📜 System Logs", callback_data="view_logs")],
            [InlineKeyboardButton("🧠 Memory Pulse", callback_data="memory_pulse")],
            [InlineKeyboardButton("🌐 Cluster Topology", callback_data="cluster_topology")],
            [InlineKeyboardButton("🤖 Evolution Log", callback_data="evolution_log")],
            [InlineKeyboardButton("🚀 Trigger Evolution", callback_data="trigger_evolution")],
            [InlineKeyboardButton("🧹 Deep Cleanup", callback_data="deep_cleanup")],
            [InlineKeyboardButton("🔄 System Restart", callback_data="system_restart")],
            [InlineKeyboardButton("🛠️ Capability Probe", callback_data="capability_probe")]
        ]
        return await update.message.reply_text(
            "🛠️ <b>ASURA Sovereign Control Panel</b>\nManage core system state and evolution cycles.",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML"
        )

    # Handle replies to the "Think" prompt
    if update.message.reply_to_message and "What should I reason about?" in update.message.reply_to_message.text:
        from skills.telegram_bot.bot import cmd_think
        context.args = [user_msg]
        return await cmd_think(update, context)

    # ─── New: Edit/Question Recommendation Loop ───────────
    if update.message.reply_to_message and "Edit Recommendation" in update.message.reply_to_message.text:
        rec_id = context.user_data.get("editing_rec_id")
        if rec_id:
            from core.recommendation import recommendation_store
            from core.llm import call_llm
            status = await update.message.reply_text("🔄 <i>Updating recommendation...</i>", parse_mode="HTML")
            
            # Logic: Use LLM to update the recommendation based on user feedback
            items = recommendation_store.get_pending()
            rec = next((i for i in items if i.id == rec_id), None)
            
            prompt = f"Original Recommendation: {rec.content if rec else 'N/A'}\nUser Feedback/Question: {user_msg}\n\nUpdate the recommendation or answer the question concisely. Maintain a proactive, actionable tone."
            updated_content = await call_llm(prompt)
            updated_content = updated_content.replace("<br>", "\n").replace("<br/>", "\n").replace("</br>", "")
            import re
            
            # Simple Markdown to HTML Conversion for Telegram
            updated_content = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', updated_content)
            updated_content = re.sub(r'__(.+?)__', r'<b>\1</b>', updated_content)
            updated_content = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', updated_content)
            updated_content = re.sub(r'```(.*?)```', r'<pre>\1</pre>', updated_content, flags=re.DOTALL)
            
            # Smart Table Wrapping
            table_pattern = r'(\n(?:\|.*?\|)+\n(?:\|[- :|]+\|)+\n(?:\|.*?\|(?: *\n|$))+)'
            def wrap_table(match): return f"\n<pre>{match.group(1).strip()}</pre>\n"
            updated_content = re.sub(table_pattern, wrap_table, "\n" + updated_content)
            
            # Clean unsupported HTML
            updated_content = re.sub(r'<(?!/?(b|i|u|s|a|code|pre)\b)[^>]+>', '', updated_content)
            
            recommendation_store.update_content(rec_id, updated_content)
            
            await status.delete()
            kb = [
                [InlineKeyboardButton("📥 Add to Queue", callback_data=f"choice_rec_add_{rec_id}")],
                [InlineKeyboardButton("✏️ Further Edit / Question", callback_data=f"choice_rec_edit_{rec_id}")],
                [InlineKeyboardButton("❌ Dismiss", callback_data=f"choice_rec_del_{rec_id}")]
            ]
            return await update.message.reply_text(
                f"🎯 <b>Updated Recommendation</b>\n\n{updated_content}",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="HTML"
            )

    # ─── New: Anti-Bloat Consolidation ───────────────────
    context.user_data["msg_count"] = context.user_data.get("msg_count", 0) + 1
    if context.user_data["msg_count"] >= 10:
        context.user_data["msg_count"] = 0
        from core.gateway import get_or_create_session
        session = get_or_create_session(user_id, "telegram")
        # Trigger async consolidation (simplified)
        log_app("Anti-Bloat: Consolidating history...")
        from skills.conversation.history import consolidate_history
        await asyncio.to_thread(consolidate_history, user_id)

    # ─── Multi-Device Routing Logic ───────────
    from settings import settings as cfg
    from core.federation import federation
    
    target_peer = None
    clean_msg = user_msg
    
    # Detect prefix: [DeviceName] command
    import re
    match = re.match(r'^\[(.*?)\]\s*(.*)', user_msg)
    if match:
        target_name = match.group(1).strip()
        clean_msg = match.group(2).strip()
        
        # If target is NOT this instance, find the peer URL
        if target_name.lower() != cfg.INSTANCE_NAME.lower():
            for peer_url in cfg.ASURA_PEERS:
                # We'll ping to verify name (simplified for now)
                target_peer = peer_url
                break
    
    if target_peer:
        status_msg = await update.message.reply_text(f"📡 <i>Routing to {target_name}...</i>", parse_mode="HTML")
        reply = await federation.remote_handoff(clean_msg, target_peer)
        await status_msg.edit_text(format_message(reply or "❌ Peer unreachable.", platform="telegram"), parse_mode="HTML")
        return
    # ──────────────────────────────────────────

    # ─── Precision Telemetry & Profiling ────────────
    import time
    t_start = time.perf_counter()

    # ─── Visual Thinking Indicator (Sticker) ────────
    # Using local premium thinking sticker
    sticker_path = os.path.join(cfg.BASE_DIR, "assets", "thinking.png")
    sticker_msg = None
    if os.path.exists(sticker_path):
        try:
            with open(sticker_path, "rb") as f:
                sticker_msg = await update.message.reply_sticker(sticker=f)
        except Exception as e:
            log_app(f"Sticker Error: {e}")
    
    t_sticker = time.perf_counter()
    status_msg = await update.message.reply_text("🧠 <i>ASURA is processing...</i>", parse_mode="HTML")
    t_status = time.perf_counter()
    
    try:
        from skills.telegram_bot.bot import get_llm_queue
        
        # Create Task Payload for the Sovereign Worker
        task = {
            "user_id": user_id,
            "user_msg": user_msg,
            "status_msg": status_msg,
            "sticker_msg": sticker_msg,
            "update": update,
            "context": context
        }
        
        # Enqueue the workload instantly to free the polling connection
        await get_llm_queue().put(task)
        log_audit("TELEGRAM", f"Message payload from {user_id} dispatched to Sovereign Worker Queue")
    except Exception as e:
        log_app(f"Chat Handler Error: {e}")
        try:
            await update.message.reply_text(f"❌ <b>Error:</b> {e}", parse_mode="HTML")
        except: pass

async def show_task_manager(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the Task Manager queue."""
    from core.recommendation import recommendation_store
    approved = recommendation_store.get_approved()
    
    # Handle both Message and CallbackQuery
    send_fn = update.message.reply_text if update.message else update.callback_query.message.reply_text
    
    if not approved:
        kb = [[InlineKeyboardButton("🧠 Manage Recommendations", callback_data="choice_expand_recs")]]
        await send_fn(
            "📋 <b>Task Manager</b>\nYour queue is currently empty. Would you like to review pending recommendations?", 
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML"
        )
        return
    
    msg = "📋 <b>Active Sovereign Queue</b>\nThese tasks execute autonomously when resources allow.\n\n"
    kb = []
    for i, task in enumerate(approved):
        msg += f"{i+1}. <b>{task.content}</b>\n"
        kb.append([
            InlineKeyboardButton(f"✅ Done #{i+1}", callback_data=f"choice_task_done_{task.id}"),
            InlineKeyboardButton(f"🗑️ Delete #{i+1}", callback_data=f"choice_task_del_{task.id}")
        ])
    await send_fn(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def checklist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interactive checklist toggles."""
    query = update.callback_query
    await query.answer()
    
    # Toggle logic
    keyboard = query.message.reply_markup.inline_keyboard
    for row in keyboard:
        for button in row:
            if button.callback_data == query.data:
                if "☐" in button.text:
                    button.text = button.text.replace("☐", "☑")
                else:
                    button.text = button.text.replace("☑", "☐")
                    
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
