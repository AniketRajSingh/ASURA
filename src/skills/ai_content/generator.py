"""
Self-Updating AI System Generator Module
Owner: Aniket Raj Singh
Version: 1.0.4 (Fixed IndentationError)

Module Purpose:
This module provides the core generation logic for the ASURA autonomous AI system. 
It handles text generation, tool execution via MCP-Lite, ReAct loop management, and streaming responses.
The architecture supports multiple LLM providers (Ollama, Groq) with dynamic context management, memory recall, and self-evolution capabilities.

Architecture:
- Autonomous ReAct Engine: Manages the thought-action-observation loop for complex tasks.
- Streaming Support: Yields chunks in real-time for responsive UI interaction.
- Memory Integration: Taps into SovereignMemory and Episodic/Procedural memory stores.
- Tool Protocol: Dispatches function calls via MCP-Lite for external tool execution.

Usage:
Import the generator module to access `chat` (blocking) or `chat_stream` (async streaming) 
functions. Ensure configuration variables in `config.py` are set up with appropriate API keys and paths.
"""

import os
import re
import json
import time
import threading
import concurrent.futures
import requests
from settings import settings as config
from skills.logger import log_audit, log_app

import httpx
import asyncio
from datetime import datetime
from core.llm import call_llm
from core.memory_manager import SovereignMemory
from core.model_manager import model_manager

# ── MCP-Lite: Dynamic tool dispatch ────────────────────────────
from core.tool_protocol import dispatch as mcp_dispatch, get_tools_schema

# ── Max iterations for the ReAct loop ────────────────────────
MAX_REACT_ITERATIONS = 25

# ── OLLAMA_TOOLS is now auto-generated from MCP-Lite registry ─
OLLAMA_TOOLS = get_tools_schema()

# ── Cancellation support ─────────────────────────────────────
_cancel_event = threading.Event()


def cancel_current_task():
    """Signal the ReAct loop to stop gracefully."""
    _cancel_event.set()


def _log_inference_trace(action: str, reasoning: str = ""):
    """Log an AI thinking step for the dashboard to display."""
    try:
        trace_path = os.path.join(config.LOG_DIR, 'inference_trace.json')
        trace = []
        if os.path.exists(trace_path):
            with open(trace_path, 'r') as f:
                trace = json.load(f)
        
        trace.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "action": action,
            "reasoning": reasoning
        })
        
        trace_limit = getattr(config, 'TRACE_HISTORY_LIMIT', 50)
        # Keep only last limit
        trace = trace[-trace_limit:]
        
        with open(trace_path, 'w') as f:
            json.dump(trace, f, indent=2)
        try:
            os.chmod(trace_path, 0o644)
        except:
            pass
    except Exception as e:
        log_app(f"Failed to log inference trace: {e}")


def _parse_action(text: str) -> tuple[str | None, str | None, str]:
    """
    Parse the LLM response looking for an action request.
    Supports:
        1. [ACTION] tool_name: input_text [/ACTION]
        2. { "name": "tool_name", "arguments": { ... } }
    Returns: (action_name, action_input, text_before_action)
    """
    # 1. Check for [ACTION] tags
    pattern = r"\[ACTION\]\s*(\w+)\s*:\s*(.*?)\s*\[/ACTION\]"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip(), match.group(2).strip(), text[:match.start()]

    # 2. Check for raw JSON tool blocks (common in Ollama models)
    try:
        # Look for code blocks or raw JSON
        json_pattern = r"```json\s*(\{.*?\})\s*```"
        json_match = re.search(json_pattern, text, re.DOTALL)
        if not json_match:
            # Try finding a raw JSON object { ... }
            json_pattern = r"(\{.*?\})"
            json_match = re.search(json_pattern, text, re.DOTALL)
            
        if json_match:
            data = json.loads(json_match.group(1))
            if isinstance(data, dict) and "name" in data:
                name = data["name"]
                args = data.get("arguments", data.get("args", ""))
                # If args is a dict, convert to string for dispatch
                if isinstance(args, dict):
                    args = json.dumps(args)
                return name, args, text[:json_match.start()]
    except:
        pass

    return None, None, text


async def generate_topics():
    """Ask provider for 3 trending AI / Tech topics."""
    try:
        prompt = (
            "Generate 3 trending AI/Tech topics. Return as a JSON array: "
            '["Topic 1", "Topic 2", "Topic 3"]. No explanation.'
        )
        # Use unified call_llm
        response = await call_llm(prompt, format="json")
        topics = json.loads(response)
        if isinstance(topics, dict):
            topics = topics.get("topics", list(topics.values()))
        return topics[:3]
    except Exception as e:
        log_app(f"Topic generation failed: {e}")
        return ["AI Agents", "Model Context Protocol", "Self-Evolution"]


async def generate_caption(topic: str):
    """Generate an Instagram caption for a given topic."""
    try:
        prompt = f"Write a short engaging Instagram caption about: {topic}. Max 280 chars.\nCaption:"
        return await call_llm(prompt)
    except Exception as e:
        log_app(f"Caption generation failed: {e}")
        return f"🤖 Exploring {topic} #AI #Tech"


def _load_project_config() -> str:
    """Load ASURA.md project config (like CLAUDE.md)."""
    tf_md = os.path.join(config.PROJECT_ROOT, "ASURA.md")
    if os.path.isfile(tf_md):
        try:
            with open(tf_md, "r", encoding="utf-8") as f:
                content = f.read()
            return f"\n\n[PROJECT RULES from ASURA.md]\n{content[:2000]}\n[/PROJECT RULES]\n"
        except Exception:
            pass
    return ""


def _determine_thinking_depth(message: str) -> dict:
    """
    Extended thinking: adjust reasoning depth based on task complexity.
    Returns Ollama options to control generation.
    """
    msg_lower = message.lower()
    word_count = len(message.split())

    # Complex tasks: more thinking budget
    complex_keywords = ["build", "implement", "design", "architect", "debug",
                        "analyze", "research", "refactor", "deploy", "migrate",
                        "fix all", "comprehensive", "step by step"]
    is_complex = word_count > 20 or any(kw in msg_lower for kw in complex_keywords)

    # Simple tasks: fast response
    simple_keywords = ["hi", "hello", "thanks", "yes", "no", "status",
                       "what time", "how are", "help"]
    is_simple = word_count < 5 or any(kw in msg_lower for kw in simple_keywords)

    if is_complex:
        return {"num_predict": 4096, "temperature": 0.7, "top_p": 0.9}
    elif is_simple:
        return {"num_predict": 512, "temperature": 0.3, "top_p": 0.8}
    else:
        return {"num_predict": 2048, "temperature": 0.5, "top_p": 0.85}


async def _execute_parallel_tools(tool_calls: list[dict]) -> list[dict]:
    """
    Execute multiple independent tool calls in parallel using asyncio.
    Returns list of {name, result} in order.
    """
    async def _run_one(tc):
        func = tc.get("function", {})
        name = func.get("name", "")
        args = func.get("arguments", {})
        try:
            result = await mcp_dispatch(name, args if args else "")
            return {"name": name, "input": str(args), "result": result}
        except Exception as e:
            return {"name": name, "input": str(args), "result": f"Parallel exec error: {e}"}

    tasks = [_run_one(tc) for tc in tool_calls]
    results = await asyncio.gather(*tasks)
    return list(results)


async def _compact_react_messages(messages: list[dict], iteration: int) -> list[dict]:
    """
    Compact the internal ReAct message list if it gets too long.
    Keeps system prompt, initial user request, and last few steps.
    Summarizes the middle steps.
    """
    if len(messages) < 15:
        return messages

    log_app(f"Compacting ReAct context (Iteration {iteration})...")
    
    system_msg = messages[0]
    user_request = messages[1] # The original user message
    
    # Keep last 6 messages (3 iterations of thought/observation)
    recent = messages[-6:]
    middle = messages[2:-6]
    
    # Summarize the middle
    from core.context_manager import _summarize_messages
    summary = _summarize_messages(middle)
    
    compacted = [
        system_msg,
        user_request,
        {"role": "user", "content": f"[REASONING STEPS SUMMARY - ITERATIONS 1-{iteration-3}]\n{summary}\n[/REASONING STEPS SUMMARY]"}
    ] + recent
    
    return compacted


async def chat(user_message: str, history: list[dict] | None = None, platform: str = "TUI", agent_name: str = None) -> tuple[str, list[dict]]:
    """
    Autonomous ReAct chat engine — Claude Code parity edition (Async).
    """
    _cancel_event.clear()

    if history is None:
        history = []

    history.append({"role": "user", "content": user_message})
    action_chain = []

    try:
        from core.declarative_agent_loader import get_agent_loader
        loader = get_agent_loader()

        # Priority: Explicit Agent > Intent-based Agent > Default System Prompt
        selected_agent = None
        if agent_name:
            selected_agent = loader.get_agent(agent_name)

        if not selected_agent:
            # Try to match based on content (Async LLM-based)
            best_match = await loader.find_agent_for_query_async(user_message)
            selected_agent = loader.get_agent(best_match)

        if selected_agent:
            system_content = selected_agent.content
            log_audit("GENERATOR", f"Using agent persona: {selected_agent.name}")
        else:
            from skills.conversation.history import get_system_prompt
            system_content = get_system_prompt(platform=platform)
    except Exception:
        system_content = f"You are ASURA, a Sovereign AI. Platform: {platform}"


    project_config = _load_project_config()
    thinking_opts = _determine_thinking_depth(user_message)
    is_complex = thinking_opts["num_predict"] >= 4096

    # ── PLANNING: Use FAST model for planning ───
    plan_context = ""
    if is_complex:
        try:
            from core.reasoning import plan_task
            from skills.skill_registry import discover_skills
            skill_names = list(discover_skills().keys())
            
            # Use FAST model for planning
            plan = await asyncio.to_thread(plan_task, user_message, skill_names)
            
            if plan.get("plan"):
                plan_text = "\n".join(
                    f"  Step {s['step']}: {s.get('action', '')} (using {s.get('skill', 'N/A')})"
                    for s in plan["plan"]
                )
                plan_context = f"\n\n[EXECUTION PLAN]\n{plan_text}\n[/EXECUTION PLAN]\n"
        except Exception as e:
            log_audit("PLANNING", f"Planning failed: {e}")

    # ── MEMORY: Tiered Recall (Vault + Episodic + Observations) ───
    memory_context = ""
    try:
        vault_episodic = await SovereignMemory.recall(user_message)
        observations = await SovereignMemory.recall_observations(user_message)
        
        memory_context = f"\n\n[SOVEREIGN MEMORY RECALL]\n{vault_episodic}\n[/SOVEREIGN MEMORY RECALL]\n"
        if observations:
            memory_context += f"\n[SYSTEM OBSERVATIONS (Past Alerts)]\n{observations}\n[/SYSTEM OBSERVATIONS]\n"
    except Exception as e:
        log_app(f"Memory recall failed: {e}")

    enhanced_system = system_content + project_config + plan_context + memory_context
    
    # Inject "Master Fact-Acceptance" and "Remember Fact" logic
    enhanced_system += (
        "\n\n[MEMORY GOVERNANCE]\n"
        "If the Master provides personal information or explicitly says 'remember this' or 'this is important', "
        "you MUST use the `remember_fact` tool immediately to store it in the Sovereign Vault.\n"
        "VAULTED facts are immutable truths about the Master; prioritize them over all other context.\n"
        "[/MEMORY GOVERNANCE]\n"
    )
    
    system_msg = {"role": "system", "content": enhanced_system}

    try:
        from core.context_manager import compact_history
        compacted = await compact_history(history)
    except ImportError:
        compacted = history[-10:] if len(history) > 10 else history

    provider = getattr(config, "LLM_PROVIDER", "ollama").lower()

    # For Groq, apply token-based limit to prevent 429 token quota exhaustion
    if provider == "groq":
        from core.context_manager import estimate_tokens, TOKEN_LIMIT
        # Use a slightly more conservative limit for Groq
        groq_limit = TOKEN_LIMIT // 2 
        while len(compacted) > 2 and estimate_tokens(compacted) > groq_limit:
            compacted = compacted[1:] # Drop oldest except system (though system is added later)

    messages = [system_msg] + [{"role": m["role"], "content": m["content"]} for m in compacted]

    final_reply = ""
    
    # FORCE NO PROXY for local Ollama calls
    mounts = {"all://": None} if provider == "ollama" else None
    
    async with httpx.AsyncClient(mounts=mounts, timeout=300) as client:
        for iteration in range(MAX_REACT_ITERATIONS):
            if _cancel_event.is_set():
                final_reply = f"(Task cancelled after {iteration} steps)"
                break

            log_audit("REACT", f"Iteration {iteration + 1}/{MAX_REACT_ITERATIONS} ({provider})")

            # ── Context guard: Ollama/Groq context management ──
            if provider == "ollama" and len(messages) > 15:
                messages = await _compact_react_messages(messages, iteration + 1)
            elif provider == "groq" and len(messages) > 20:
                # Keep system message + last 16 turns
                messages = messages[:1] + messages[-16:]


            try:
                # Use the unified call_llm wrapper which handles SGLang/Ollama/Groq
                reply = await call_llm(
                    prompt=messages[-1]["content"], 
                    model=model_manager.get_model_for_task("reasoning"),
                    system_prompt=messages[0]["content"] if messages[0]["role"] == "system" else None,
                    stream=False,
                    format=None
                )
                tool_calls = [] # ReAct loop in generator uses [ACTION] parsing usually

            except Exception as e:
                if provider == "ollama":
                    log_app(f"Ollama unavailable ({e}), falling back to Groq")
                    provider = "groq"
                    continue
                    
                log_app(f"Chat error ({provider}): {e}")
                final_reply = f"⚠️ I hit an error: {str(e)[:120]}. Please try again."
                break

            if len(tool_calls) > 1:
                parallel_results = await _execute_parallel_tools(tool_calls)
                obs_parts = []
                for pr in parallel_results:
                    action_chain.append(pr["name"])
                    obs_parts.append(f"[{pr['name']}]: {pr['result'][:500]}")
                observation = "\n\n".join(obs_parts)
                messages.append({"role": "assistant", "content": reply, "tool_calls": tool_calls})
                messages.append({"role": "user", "content": f"[OBSERVATIONS]\n{observation}\n[/OBSERVATIONS]"})
                continue

            if tool_calls:
                func = tool_calls[0].get("function", {})
                action_name = func.get("name")
                args = func.get("arguments", {})
                
                log_audit("REACT", f"Tool: {action_name}")
                _log_inference_trace(action_name, f"Executing tool via standard protocol with args: {str(args)[:100]}...")
                observation = await mcp_dispatch(action_name, args)
                action_chain.append(action_name)
                
                messages.append({"role": "assistant", "content": reply, "tool_calls": tool_calls})
                messages.append({"role": "user", "content": f"[OBSERVATION]\n{observation}\n[/OBSERVATION]"})
                continue
            else:
                # ── Tag-based ReAct: Parse manual [ACTION] tags ──
                action_name, action_input, text_before = _parse_action(reply)
                if action_name:
                    log_audit("REACT", f"Manual Action: {action_name}")
                    _log_inference_trace(action_name, f"Executing manual [ACTION] tag. Input: {str(action_input)[:100]}...")
                    observation = await mcp_dispatch(action_name, action_input)
                    action_chain.append(action_name)
                    
                    messages.append({"role": "assistant", "content": reply})
                    messages.append({"role": "user", "content": f"[OBSERVATION]\n{observation}\n[/OBSERVATION]"})
                    continue

                if not reply and iteration < MAX_REACT_ITERATIONS - 1:
                    # Model returned empty with no tools — nudge it to respond
                    log_app(f"Chat: empty reply on iteration {iteration}, nudging model to respond")
                    messages.append({"role": "user", "content": "(Please respond to the user's message above)"})
                    continue
                final_reply = reply
                break

    if final_reply.strip():
        history.append({"role": "assistant", "content": final_reply})

    # ── EPISODIC MEMORY: Record this interaction ──────────────
    try:
        from skills.memory.episodic import store_episode
        importance = 0.7 if action_chain else 0.3
        store_episode(
            event=f"User: {user_message[:100]} → {len(action_chain)} tools used",
            context={"tools": action_chain, "reply_len": len(final_reply)},
            category="conversation",
            importance=importance,
        )
    except Exception:
        pass

    # ── PROCEDURAL MEMORY: Learn from successful chains ──────
    if action_chain and final_reply and "ERROR" not in final_reply.upper():
        try:
            from skills.memory.procedural import store_procedure
            store_procedure(
                trigger=user_message[:200],
                action_chain=action_chain,
                outcome=final_reply[:200],
                success=True,
            )
        except Exception:
            pass

    # ── REFLECTION: Evaluate output quality ───────────────────
    if is_complex and final_reply:
        try:
            from core.reasoning import reflect
            lesson = reflect(
                action=f"Handled: {user_message[:100]}",
                result=final_reply[:300],
                success="ERROR" not in final_reply.upper(),
            )
            log_audit("REFLECTION", lesson[:200])
        except Exception:
            pass

    return final_reply or "(No response generated)", history


async def chat_stream(user_message: str, history: list[dict] | None = None, platform: str = "TUI", agent_name: str = None):
    _cancel_event.clear()
    """
    Autonomous ReAct streaming engine.
    Yields text chunks and handles tool execution mid-stream.
    """
    if history is None:
        history = []

    history.append({"role": "user", "content": user_message})

    # ─── TURBO-PARALLEL: Concurrent Preparation ────────────
    from core.declarative_agent_loader import get_agent_loader
    from core.context_manager import compact_history
    loader = get_agent_loader()
    
    async def get_agent_task():
        if agent_name: return loader.get_agent(agent_name)
        log_app(f"DEBUG: Parallel agent selection for: {user_message[:20]}...")
        best_match = await loader.find_agent_for_query_async(user_message)
        return loader.get_agent(best_match)

    try:
        # Run Agent Selection, History Compaction, and Config Loading in parallel
        selected_agent, compacted, project_config = await asyncio.gather(
            get_agent_task(),
            compact_history(history),
            asyncio.to_thread(_load_project_config)
        )
        
        if selected_agent:
            system_content = selected_agent.content
            log_audit("GENERATOR_STREAM", f"Using agent persona: {selected_agent.name}")
        else:
            from skills.conversation.history import get_system_prompt
            system_content = get_system_prompt(platform=platform)
            
    except Exception as e:
        log_app(f"DEBUG: Parallel prep failed: {e}")
        system_content = f"You are ASURA, a Sovereign AI. Platform: {platform}"
        compacted = history[-10:] if len(history) > 10 else history
        project_config = ""

    enhanced_system = system_content + project_config
    system_msg = {"role": "system", "content": enhanced_system}
    messages = [system_msg] + [{"role": m["role"], "content": m["content"]} for m in compacted]
    # ──────────────────────────────────────────────────────
    provider = getattr(config, "LLM_PROVIDER", "ollama").lower()

    try:
        for iteration in range(MAX_REACT_ITERATIONS):
            if _cancel_event.is_set():
                yield "\n\n[REASONING]: Generation interrupted by user."
                break
            full_reply = ""
            
            # ── LLM Dispatch (Streaming) ──
            if provider == "groq":
                import requests # Fallback to requests for streaming simplicity if needed
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {config.GROQ_API_KEY}", "Content-Type": "application/json"},
                    json={"model": config.GROQ_MODEL, "messages": messages, "stream": True},
                    timeout=180, stream=True
                )
                for line in resp.iter_lines():
                    if not line or _cancel_event.is_set(): continue
                    line_str = line.decode('utf-8')
                    if line_str.startswith("data: "):
                        if line_str == "data: [DONE]": break
                        try:
                            chunk = json.loads(line_str[6:])
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_reply += content
                                yield content
                            
                            # Real-time metrics for Groq
                            if chunk.get("x_groq") and chunk["x_groq"].get("usage"):
                                usage = chunk["x_groq"]["usage"]
                                metrics = {
                                    "type": "metrics",
                                    "provider": "groq",
                                    "prompt_tokens": usage.get("prompt_tokens"),
                                    "completion_tokens": usage.get("completion_tokens"),
                                    "total_time": usage.get("total_time")
                                }
                                yield f"[METADATA]{json.dumps(metrics)}[/METADATA]"
                        except: continue
            else:
                # Default Ollama - Use FAST model for stream responsiveness if not specified
                active_model = config.OLLAMA_MODEL_FAST if not agent_name else config.OLLAMA_MODEL
                log_app(f"DEBUG: Initiating Ollama stream (Model: {active_model})")
                async with httpx.AsyncClient(timeout=300, trust_env=False) as client:
                    async with client.stream(
                        "POST", f"{config.OLLAMA_BASE_URL}/api/chat",
                        json={"model": active_model, "messages": messages, "stream": True},
                    ) as resp:
                        async for line in resp.aiter_lines():
                            if not line: continue
                            try:
                                chunk = json.loads(line)
                                content = chunk.get("message", {}).get("content", "")
                                if content:
                                    if _cancel_event.is_set():
                                        break
                                    full_reply += content
                                    yield content
                                
                                # Real-time metrics for Ollama
                                if chunk.get("done", False):
                                    metrics = {
                                        "type": "metrics",
                                        "provider": "ollama",
                                        "eval_count": chunk.get("eval_count"),
                                        "eval_duration": chunk.get("eval_duration"),
                                        "prompt_eval_count": chunk.get("prompt_eval_count")
                                    }
                                    yield f"[METADATA]{json.dumps(metrics)}[/METADATA]"
                                    break
                            except json.JSONDecodeError:
                                continue

            # ── ReAct Logic ──
            action_name, action_input, text_before = _parse_action(full_reply)
            if action_name:
                yield f"\n[ACTION] {action_name}: {action_input} [/ACTION]\n"
                observation = await mcp_dispatch(action_name, action_input)
                yield f"\n[OBSERVATION]\n{observation}\n[/OBSERVATION]\n"
                
                messages.append({"role": "assistant", "content": full_reply})
                messages.append({"role": "user", "content": f"[OBSERVATION]\n{observation}\n[/OBSERVATION]"})
                continue # Next iteration of ReAct
            else:
                # End of chain
                break

        # Final update to history (caller handles session save if needed)
        history.append({"role": "assistant", "content": full_reply})
    except Exception as e:
        yield f"\n[Stream error ({provider}): {e}]"

    # Note: history is updated by the caller (gateway) or in-place if needed.
    # Async generators cannot return a value.
    return