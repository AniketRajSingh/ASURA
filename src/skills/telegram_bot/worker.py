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
from settings import settings as config

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

def _render_pipeline_card(stage: int, detail: str = "", provider: str = "openrouter", elapsed: float = 0.0) -> str:
    """Render a visual CI/CD pipeline stage card for Telegram."""
    stages = [
        ("📥 Ingest", "Session & memory context compiled"),
        ("🧠 Route", f"BrainRouter model selection ({provider})"),
        ("⚡ Stream", detail or "Synthesizing response stream..."),
        ("🚀 Finish", "Response dispatched to Master"),
    ]
    lines = [f"⚡ <b>ASURA Execution Pipeline</b> <code>[{elapsed:.1f}s]</code>\n"]
    for i, (name, desc) in enumerate(stages, 1):
        if i < stage:
            icon = "✅"
            status = "Passed"
        elif i == stage:
            icon = "🔄"
            status = "Running"
        else:
            icon = "⚪"
            status = "Queued"
        lines.append(f"{icon} <b>{name}</b>: <i>{desc}</i> [{status}]")
    return "\n".join(lines)


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
    
    # Render Stage 1: Ingestion
    try:
        await status_msg.edit_text(_render_pipeline_card(1, elapsed=time.perf_counter() - t_start), parse_mode="HTML")
    except Exception:
        pass

    try:
        from core.gateway import handle_message
        from core.brain_router import brain_router
        
        # Render Stage 2: Routing
        active_prov = getattr(config, "LLM_PROVIDER", "openrouter")
        try:
            await status_msg.edit_text(_render_pipeline_card(2, provider=active_prov, elapsed=time.perf_counter() - t_start), parse_mode="HTML")
        except Exception:
            pass

        # Watchdog timeout: if no chunks arrive within 12s, fallback kicks in
        async def _consume_stream():
            nonlocal full_reply, last_up
            stream = await handle_message(user_id, user_msg, channel="telegram", stream=True, agent_name="asura-telegram")
            first_chunk = False
            async for chunk in stream:
                if not first_chunk:
                    first_chunk = True
                    # Render Stage 3: Streaming
                    try:
                        await status_msg.edit_text(_render_pipeline_card(3, detail="First token received. Generating...", provider=active_prov, elapsed=time.perf_counter() - t_start), parse_mode="HTML")
                    except Exception:
                        pass
                if "[METADATA]" in chunk:
                    continue
                full_reply += chunk
                if time.time() - last_up > 2.5:
                    try:
                        await status_msg.edit_text(format_message(full_reply + " █", platform="telegram"), parse_mode="HTML")
                        last_up = time.time()
                    except Exception:
                        pass

        try:
            await asyncio.wait_for(_consume_stream(), timeout=18.0)
        except asyncio.TimeoutError:
            log_app("Pipeline Watchdog: Stream timeout reached (18s). Diverting pipeline to emergency local/Groq fallback...")
            try:
                await status_msg.edit_text(
                    "⚠️ <b>Pipeline Watchdog Alert:</b> Primary model stalled (>18s).\n"
                    "🔄 <i>Auto-diverting workload to high-speed fallback tier...</i>",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            from core.llm import call_llm
            full_reply = await call_llm(user_msg, system_prompt="You are ASURA Sovereign AI. Respond concisely and accurately.")

        # Ensure minimal chunk was generated
        if not full_reply.strip():
            full_reply = "I processed your request, but the stream yielded no direct output. Please retry."

        # Cleanup Temporary Processing Elements
        try:
            await status_msg.delete()
        except Exception:
            pass
        if sticker_msg:
            try:
                await sticker_msg.delete()
            except Exception:
                pass

        # Clean metadata & reasoning tags
        clean_reply = re.sub(r'\[METADATA\].*?\[/METADATA\]', '', full_reply, flags=re.DOTALL)
        clean_reply = re.sub(r'<think>.*?</think>', '', clean_reply, flags=re.DOTALL)
        clean_reply = re.sub(r'</?think>', '', clean_reply).strip()

        # Final Formatting and MCQ Dispatch
        await _dispatch_final_reply(update, context, user_id, clean_reply)
        
        gen_time = time.perf_counter() - t_start
        log_audit("TELEGRAM_QUEUE", f"Processed task for user {user_id} in {gen_time:.2f}s")
        
    except Exception as e:
        log_app(f"Worker Task Processing Error: {e}")
        try:
            # Emergency fail-safe response
            from core.formatter import format_message
            err_notice = f"⚠️ <b>Pipeline Failover:</b> Encountered <code>{e}</code>.\n\nMaster, the system caught this state and remains operational."
            await update.message.reply_text(format_message(err_notice, platform="telegram"), parse_mode="HTML")
        except Exception:
            pass


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
