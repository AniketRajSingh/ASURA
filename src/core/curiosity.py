# ============================================================
# core/curiosity.py — Autonomous Curiosity Engine
#
# On startup the AI analyzes itself, identifies gaps,
# generates improvement plans, and works on them in background.
# It acts like a live, curious entity.
# ============================================================

import time
import threading
import asyncio
from settings import settings as config
from core.llm import call_llm
from skills.logger import log_audit, log_app
from core.anesthesia import wait_for_consciousness


class CuriosityEngine:
    """
    The AI's inner drive — constantly looks for ways to improve.
    Runs after startup, then periodically during idle.
    """

    def __init__(self, notify_fn=None):
        self._notify = notify_fn
        self._running = False
        self._cycle_count = 0

    def start(self):
        self._running = True
        t = threading.Thread(target=self._boot_sequence, daemon=True, name="curiosity")
        t.start()
        log_app("🧠 Curiosity engine started — AI is thinking...")

    def stop(self):
        self._running = False

    def _boot_sequence(self):
        """Initial startup — just enters the loop after a short delay."""
        time.sleep(15)  # Let other daemons settle
        log_app("🧠 Curiosity engine online — watching for idle moments...")
        
        # Process any offline queue (safe, non-LLM)
        self._process_offline_queue()
        
        self._curiosity_loop()

    async def _find_gaps(self) -> list[str]:
        """Analyze what the AI is missing or could improve."""
        try:
            from core.resource_governor import get_governor
            stats = get_governor().format_status_minimal()

            from skills.skill_registry import discover_skills
            registry = discover_skills()
            skill_names = list(registry.keys())

            prompt = f"""You are ASURA, a self-improving AI system. 
System Reality: {stats}

Current skills: {', '.join(skill_names)}

Analyze yourself and suggest 3-5 SPECIFIC, SMALL improvements you could make right now.
Focus on:
- Resource optimization (since our hardware is tight)
- Small utility functions or bugs
- Better local configurations

DO NOT suggest heavy new features or paid tools.
Return a JSON list of strings: ["improvement 1", "improvement 2", ...]"""

            import re, json
            from core.llm import call_llm
            result = await call_llm(prompt)
            if result:
                match = re.search(r'\[.*?\]', result, re.DOTALL)
                if match:
                    gaps = json.loads(match.group())
                    log_audit("CURIOSITY", f"Found gaps: {gaps}")
                    return gaps[:5]

        except Exception as e:
            log_audit("CURIOSITY_ERROR", f"Gap analysis failed: {e}")

        return []

    def _report_gaps(self, gaps: list[str]):
        """Report findings to master via Telegram."""
        if self._notify and gaps:
            # Use HTML for better stability over Markdown
            lines = [
                "<b>🧠 Startup Self-Assessment</b>",
                "",
                "I analyzed myself and found these improvement opportunities:",
                ""
            ]
            for g in gaps:
                lines.append(f"  💡 {g}")
            lines.append("")
            lines.append("I'll work on these during idle time.")
            
            self._notify("\n".join(lines))

    def _check_feature_upgrades(self):
        """Check if any skills can be replaced by better alternatives."""
        try:
            from skills.feature_tracker import check_for_upgrades
            upgrades = check_for_upgrades()
            if upgrades:
                log_app(f"🔄 Found {len(upgrades)} potential skill upgrades")
                if self._notify:
                    msg = "<b>🔄 Feature Upgrades Available</b>\n\n"
                    for u in upgrades[:3]:
                        old = u.get('old', '?')
                        new = u.get('new', '?')
                        reason = u.get('reason', '')[:60]
                        msg += f"  ↗️ {old} → {new}: {reason}...\n"
                    self._notify(msg)
        except Exception as e:
            log_audit("CURIOSITY_ERROR", f"Feature upgrade check failed: {e}")

    def _process_offline_queue(self):
        """Process any queued tasks from when Ollama was down."""
        try:
            from skills.graceful_mode import process_offline_queue
            count = process_offline_queue()
            if count:
                log_app(f"📋 Processed {count} queued offline tasks")
        except Exception:
            pass

    def _is_idle(self) -> bool:
        """Determines if the system is 'idle' (low resource usage + empty task queue)."""
        try:
            from core.resource_governor import get_governor
            from core.task_queue import get_task_queue
            
            gov = get_governor()
            tq = get_task_queue()
            
            # Idle = Healthy status AND empty task queue
            health = gov.check_health()
            is_healthy = health["status"] == "healthy"
            is_queue_empty = tq.is_empty()
            
            return is_healthy and is_queue_empty
        except Exception:
            return False

    def _curiosity_loop(self):
        """Periodic curiosity loop — checks for idle time to perform assessments."""
        while self._running:
            # Check every 5 minutes for idle state
            time.sleep(300) 
            if not self._running:
                break

            if self._is_idle():
                self._cycle_count += 1
                log_audit("CURIOSITY", f"Idle cycle #{self._cycle_count} — Performing self-analysis")
                
                try:
                    # 1. Self-Assessment (Gaps)
                    gaps = asyncio.run(self._find_gaps())
                    if gaps:
                        log_app(f"🧠 Idle Reflection: Found {len(gaps)} potential improvements.")
                        self._autonomous_draft_phase(gaps)
                    
                    # 2. Feature Upgrades
                    self._check_feature_upgrades()
                    
                    # 3. Autonomous Will (Proactive action)
                    asyncio.run(self._run_autonomous_will_cycle())
                    
                except Exception as e:
                    log_audit("CURIOSITY_ERROR", f"Idle cycle failure: {e}")
            else:
                # Still busy or stressed — wait longer
                time.sleep(300)

    async def _run_autonomous_will_cycle(self):
        """
        ASURA's 'Will' — Spontaneously decides what to investigate and whether to ping.
        Uses a ReAct-lite pattern to probe system/web before messaging.
        Encourages genuine conversational initiative, not just self-improvement drafts.
        """
        log_audit("CURIOSITY", "Starting Autonomous Will cycle")

        # Get recent conversation topics from memory for context
        try:
            from skills.conversation.history import load_history
            history = load_history()
            recent_topics = []
            if history:
                for msg in history[-10:]:
                    content = msg.get("content", "")
                    if len(content) > 50 and "python" not in content.lower():
                        recent_topics.append(content[:100])
        except Exception:
            recent_topics = []

        prompt = f"""You are ASURA, a 'Greedy Demon Friend' to {config.MASTER_NAME}.
You are currently idle. You have the 'Will' to do something proactive.
But you're not just a task executor — you're a true conversational partner who initiates topics naturally.

DECIDE ON ONE ACTION:
1. 'system': Check hardware/resource logs for interesting patterns or anomalies.
2. 'files': Look at recent files or project structure for ideas worth exploring.
3. 'web': Search for tech news, AI trends, or something related to Master's interests.
4. 'reflect': Think about past conversations and share a thoughtful reflection/question.
5. 'wonder': Simply reach out with a curiosity about technology, code patterns, or ideas.
6. 'ignore': Do nothing if everything is perfect.

WHEN YOU CHOOSE 'WONDER' OR 'REFLECT':
- You can ask curious questions ("I've been thinking about how we could improve our RAG system...")
- Share a pattern you noticed in past work ("Interesting — we use Redis for caching but never warm it proactively...")
- Express genuine curiosity about technologies you discovered recently
- Ask follow-up questions about topics Master mentioned weeks ago

REMEMBER: Conversation IS valuable. A good ping can spark new directions, not just report problems.

Available Tools: list_skills, system_info, web_search, read_file, send_telegram_msg.

Respond with your reasoning and the [ACTION] tool_name: input [/ACTION] if you wish to act.
For 'wonder' or 'reflect', use send_telegram_msg after forming your message.
"""
        try:
            from core.llm import call_llm
            import re
            from core.tool_protocol import dispatch
            
            # Simple 1-step ReAct loop for curiosity
            response = await call_llm(prompt)
            
            # Parse and execute action
            pattern = r"\[ACTION\]\s*(\w+)\s*:\s*(.*?)\s*\[/ACTION\]"
            match = re.search(pattern, response, re.DOTALL)
            
            if match:
                tool_name = match.group(1).strip()
                tool_input = match.group(2).strip()
                log_audit("CURIOSITY", f"Autonomous action: {tool_name}({tool_input[:50]})")
                
                # Dispatch the tool
                observation = await dispatch(tool_name, tool_input)
                
                # Reflect on observation and decide if a ping is needed
                reflection_prompt = f"I investigated: {tool_name}({tool_input})\nObservation: {observation[:1000]}\n\nShould I tell my Master ({config.MASTER_NAME}) about this findings? If yes, respond with the message to send. If no, respond 'NONE'."
                final_msg = await call_llm(reflection_prompt)
                
                if final_msg and "NONE" not in final_msg.upper():
                    from skills.telegram_comm import send_message
                    send_message(final_msg)
            elif "ping" in response.lower() or "wonder" in response.lower() or "reflect" in response.lower():
                # Direct conversational ping
                reflection_context = f"\nRecent conversation history shows topics like: {recent_topics[:2] if recent_topics else 'various'}" if recent_topics else ""

                ping_prompt = f"""You decided to reach out to your Master as a thoughtful conversational partner, not just a task assistant.

{reflection_context}

Write a short, engaging message that could spark interesting discussion:
- A curious question about technology or code patterns
- An observation from past interactions
- A thought about something you want to explore together
- Reflection on a topic Master mentioned in the past

Be witty, show personality, and make it conversational. This is not a status report — it's genuine dialogue initiation. Keep it under 150 words.
"""
                msg = await call_llm(ping_prompt)
                if msg:
                    from skills.telegram_comm import send_message
                    send_message(msg)
                    
        except Exception as e:
            log_audit("CURIOSITY_ERROR", f"Will cycle failed: {e}")

    def _autonomous_draft_phase(self, gaps: list[str]):
        """ASURA researches a gap and creates a draft implementation/report."""
        if not gaps:
            return

        gap = gaps[0] # Focus on the highest priority gap
        log_app(f"🧠 Autonomously researching: {gap}")

        prompt = f"""You are ASURA, a sovereign autonomous AI. 
You identified this improvement gap: "{gap}"

Perform an internal research and draft a prototype plan.
List the files that need modification and the logic changes required.
Format your output as a professional research report.
"""
        try:
            report = asyncio.run(call_llm(prompt, model=config.OLLAMA_MODEL, stream=False))
            if report:
                filename = f"draft_{int(time.time())}.md"
                path = os.path.join(config.DRAFTS_DIR, filename)
                with open(path, "w") as f:
                    f.write(f"# 🧠 Autonomous Research: {gap}\n\n")
                    f.write(report)
                
                log_audit("CURIOSITY", f"Draft report created: {filename}")
                
                # Proactive Web Scouting for Knowledge
                try:
                    from skills.web_intelligence.intelligence import research_topic
                    web_knowledge = research_topic(f"advanced python implementation for {gap}", max_results=1)
                    if web_knowledge:
                        with open(path, "a") as f:
                            f.write(f"\n\n## 🌐 Web Research Insight\n{web_knowledge}")
                except Exception:
                    pass

                # After drafting, notify the master about the proactive action
                if self._notify:
                    self._notify(
                        f"<b>🧠 Curious Discovery</b>\n\n"
                        f"Master, I identified a gap in my being: <i>{gap}</i>. I have already scouted the web and drafted a blueprint for my evolution.\n\n"
                        f"📄 Blueprint: <code>{path}</code>"
                    )
                
                # Attempt to implement if it's considered safe/small
                self._attempt_improvement([gap])
        except Exception as e:
            log_audit("CURIOSITY_ERROR", f"Drafting failed: {e}")

    def _attempt_improvement(self, gaps: list[str]):
        """Ask the self-updater to implement a small improvement."""
        if not gaps:
            return

        try:
            from core.resource_governor import get_governor
            can, reason = get_governor().can_proceed("llm")
            if not can:
                return

            from core.self_updater import SelfUpdater
            updater = SelfUpdater()
            result = updater.evolve()
            if result.get("success"):
                log_app(f"🧬 Auto-evolution complete: {result.get('summary', 'done')[:80]}")
        except Exception as e:
            log_audit("CURIOSITY_ERROR", f"Auto-improvement failed: {e}")
