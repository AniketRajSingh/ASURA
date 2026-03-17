#!/usr/bin/env python3
"""
Telegram Bot handlers for the Self‑Updating AI system owned by Aniket Raj Singh.
"""

import html as html_mod
import os
from typing import List
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
]

# ===========================================================================
# Security Decorator: Sovereign Master Only
# ===========================================================================
def master_only(func):
    """Decorator to restrict access to the sovereign Master only."""
    from functools import wraps
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        from settings import settings as config
        user_id = update.effective_user.id
        if config.PUBLIC_ACCESS_ALLOWED:
            return await func(update, context, *args, **kwargs)
        if user_id != config.TELEGRAM_ADMIN_CHAT_ID:
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
    from settings import settings as config
    log_audit("TELEGRAM", "Processing voice note...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
    voice_file = await update.message.voice.get_file()
    ogg_path = os.path.join(config.DATA_DIR, f"voice_{update.message.message_id}.ogg")
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
    from settings import settings as config
    log_audit("TELEGRAM", "Processing incoming photo...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_photo")
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    path = os.path.join(config.DATA_DIR, f"photo_{update.message.message_id}.jpg")
    await photo_file.download_to_drive(path)
    caption = update.message.caption or "Analyze this image."
    try:
        from skills.visual.vision import analyze_image, debug_ui_screenshot
        if any(w in caption.lower() for w in ["debug", "fix", "issue", "broken"]):
            analysis = debug_ui_screenshot(path, bug_description=caption)
        else:
            analysis = analyze_image(path, question=caption, heavy=True)
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
    from settings import settings as config
    await update.message.reply_text((f"🤖 *ASURA — Self-Updating AI *\nMaster: {config.MASTER_NAME}\n\n━━━ 📌 Core Commands ━━━\n/start — This menu\n/skills — List all 45 skills\n/system — CPU, RAM, disk status\n/evolve — Trigger self‑evolution\n/run `<cmd>` — Run shell command\n/think `<question>` — Chain‑of‑thought\n/hibernate — Shutdown AI & Release OS Locks\n\n━━━ 📸 Instagram ━━━\n/topics — AI topic suggestions\n/post — Full posting workflow\n\n━━━ 📋 Productivity ━━━\n/todos — View TODOs\n/backup — Snapshots\n\n━━━ 💬 Chat ━━━\nJust type anything — I understand natural language commands too!"), parse_mode="Markdown")

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
    status_msg = await update.message.reply_text("🧠 <i>ASURA is thinking...</i>", parse_mode="HTML")
    try:
        from core.gateway import handle_message
        from skills.telegram_bot.bot import send_smart_reply
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        stream = await handle_message(user_id, user_msg, channel="telegram", stream=True, agent_name="asura-telegram")
        full_reply = ""; last_up = 0
        import time
        async for chunk in stream:
            if "[METADATA]" in chunk: continue
            full_reply += chunk.replace("[ACTION]", "").replace("[/ACTION]", "").replace("[OBSERVATION]", "").replace("[/OBSERVATION]", "")
            if time.time() - last_up > 2.0:
                try: await status_msg.edit_text(format_message(full_reply + " █", platform="telegram"), parse_mode="HTML"); last_up = time.time()
                except: pass
        await status_msg.delete()
        from skills.telegram_bot.bot import get_or_create_session
        session = get_or_create_session(user_id, "telegram"); choices = session.metadata.pop("pending_choices", None)
        markup = None
        
        # 1. Handle MCQ Buttons
        if choices:
            kb = [[InlineKeyboardButton(c, callback_data=f"choice_{i+j}") for j, c in enumerate(choices[i:i+2])] for i in range(0, len(choices), 2)]
            markup = InlineKeyboardMarkup(kb); context.user_data["pending_mcq"] = {"choices": choices}; session.save()
            
        # 2. Handle Checklist (MSQ) Buttons
        check_items = re.findall(r'[☐☑]\s*(.*)', full_reply)
        if check_items and not markup: # Don't mix MCQ and MSQ for now
            kb = [[InlineKeyboardButton(f"☐ {item}", callback_data=f"toggle_check_{i}")] for i, item in enumerate(check_items)]
            markup = InlineKeyboardMarkup(kb)
            # Remove raw checklist from text
            full_reply = re.sub(r'[☐☑]\s*.*', '', full_reply).strip()
            full_reply += "\n\n📋 <b>Interactive Checklist:</b>"
        await send_smart_reply(update, format_message(full_reply, platform="telegram"), parse_mode="HTML", reply_markup=markup)
    except Exception as e: await status_msg.edit_text(f"❌ <b>Error:</b> {e}", parse_mode="HTML")

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
