"""
Asynchronous Worker Daemon
Decouples Telegram Polling from heavy LLM execution. 
Pulls user queries from an asyncio Queue, processes the stream, and intelligently 
throttles chunked updates back to the Telegram UI to avoid API limits.
"""

import asyncio
import time
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from skills.logger import log_app, log_audit
from core.formatter import format_message

async def stream_worker_daemon(app):
    """Infinite loop daemon that processes tasks from the LLM Queue."""
    from skills.telegram_bot.bot import get_llm_queue
    queue = get_llm_queue()
    log_app("🚀 ASURA Async Queue Worker started. Awaiting LLM tasks...")
    
    while True:
        try:
            task = await queue.get()
            await _process_llm_task(task)
            queue.task_done()
        except asyncio.CancelledError:
            log_app("Async Queue Worker terminated.")
            break
        except Exception as e:
            log_app(f"Worker Global Error: {e}")
            await asyncio.sleep(2) # Prevent rapid crashes

async def _process_llm_task(task: dict):
    user_id = task["user_id"]
    user_msg = task["user_msg"]
    status_msg = task["status_msg"]
    sticker_msg = task.get("sticker_msg")
    update = task["update"]
    context = task["context"]

    t_start = time.perf_counter()
    full_reply = ""
    last_up = time.time()
    
    try:
        from core.gateway import handle_message
        
        # This async generator connects to Ollama heavily
        stream = await handle_message(user_id, user_msg, channel="telegram", stream=True, agent_name="asura-telegram")
        
        first_chunk_received = False
        
        async for chunk in stream:
            if not first_chunk_received:
                first_chunk_received = True

            if "[METADATA]" in chunk: continue
            full_reply += chunk
            
            # Intelligent Throttling (3.0 seconds) to avoid Telegram HTTP 429 Flood Control
            if time.time() - last_up > 3.0:
                try:
                    await status_msg.edit_text(format_message(full_reply + " █", platform="telegram"), parse_mode="HTML")
                    last_up = time.time()
                except Exception as e:
                    if "Message is not modified" not in str(e):
                        pass # Ignore minor edit_text sync errors

        # Ensure minimal chunk was generated
        if not full_reply.strip():
            full_reply = "I completed the thought process, but the stream yielded no direct response."

        # Cleanup Temporary Processing Elements
        try: await status_msg.delete()
        except: pass
        if sticker_msg:
            try: await sticker_msg.delete()
            except: pass

        # Final Formatting and MCQ Dispatch
        await _dispatch_final_reply(update, context, user_id, full_reply.strip())
        
        gen_time = time.perf_counter() - t_start
        log_audit("TELEGRAM_QUEUE", f"Processed task for user {user_id} in {gen_time:.2f}s")
        
    except Exception as e:
        log_app(f"Worker Task Processing Error: {e}")
        try: await update.message.reply_text(f"❌ <b>Sovereign Queue Error:</b> {e}", parse_mode="HTML")
        except: pass


async def _dispatch_final_reply(update, context, user_id, full_reply: str):
    """Extracts interactive elements and uses send_smart_reply for chunked formatting."""
    from skills.telegram_bot.bot import get_or_create_session, send_smart_reply
    session = get_or_create_session(user_id, "telegram")
    choices = session.metadata.pop("pending_choices", None)
    markup = None
    
    # 1. Handle MCQ Buttons
    if choices:
        kb = [[InlineKeyboardButton(c, callback_data=f"choice_{i+j}") for j, c in enumerate(choices[i:i+2])] for i in range(0, len(choices), 2)]
        markup = InlineKeyboardMarkup(kb)
        context.user_data["pending_mcq"] = {"choices": choices}
        session.save()
        
    # 2. Handle Checklist (MSQ) Buttons
    check_items = re.findall(r'[☐☑]\s*(.*)', full_reply)
    if check_items and not markup: # Don't mix MCQ and MSQ
        kb = [[InlineKeyboardButton(f"☐ {item}", callback_data=f"toggle_check_{i}")] for i, item in enumerate(check_items)]
        markup = InlineKeyboardMarkup(kb)
        full_reply = re.sub(r'[☐☑]\s*.*', '', full_reply).strip()
        full_reply += "\n\n📋 <b>Interactive Checklist:</b>"
        
    if full_reply:
        await send_smart_reply(update, full_reply, parse_mode="HTML", reply_markup=markup)
