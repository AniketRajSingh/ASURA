# ============================================================
# core/reasoning.py — Chain-of-Thought Reasoning Engine
#
# Gives the AI structured thinking: break down tasks, plan
# multi-step actions, reflect on results, and decide next steps.
# ============================================================

import json
from settings import settings as config
from core.llm import call_llm
from core.utils import extract_json
from skills.logger import log_audit, log_app


async def _generate_thought(task: str, context: str = "", max_steps: int = 5) -> dict:
    """
    Generate a single chain-of-thought step.
    """
    log_audit("REASONING", f"Thinking about: {task[:80]}")

    prompt = f"""[INST] You are the Sovereign Engine of ASURA (Instance: {config.INSTANCE_NAME}).
Host Master: {config.MASTER_NAME}. You control a multi-device cluster via precision tool calls.

TASK: {task}

CLUSTER CONTEXT:
- Local Instance: {config.INSTANCE_NAME}
- Peer Instances: {config.ASURA_PEERS}
- Recent history: {context[:2000]}

PROTOCOL:
1. DECONSTRUCT: Isolate core intent.
2. INVENTORY: Map intent to technical signatures (respect AST precision).
3. DELEGATE: If local resources are high, suggest actions on peer instances via [PeerName] prefix.
4. VALIDATE: Ensure non-destructive, sovereign alignment.

Respond ONLY with valid JSON:
{{
    "thought_process": ["step 1", "step 2"],
    "conclusion": "one sentence action",
    "actions": ["[InstanceName] shell_cmd", "local_tool"],
    "confidence": 0.0-1.0
}} [/INST]"""

    try:
        raw = await call_llm(prompt)

        # Parse JSON using centralized utility
        result = extract_json(raw)
        if result and "conclusion" in result:
            log_audit("REASONING", f"Conclusion: {result['conclusion'][:100]}")
            return result

        # Fallback: return raw as conclusion
        return {
            "thought_process": ["Direct response generated due to JSON parsing failure"],
            "conclusion": raw[:500],
            "actions": [],
            "confidence": 0.5,
        }

    except Exception as e:
        log_audit("REASONING_ERROR", f"Thinking failed: {e}")
        return {
            "thought_process": [f"Error: {e}"],
            "conclusion": "Unable to reason about this task.",
            "actions": [],
            "confidence": 0.0,
        }


async def plan_task(task: str, available_skills: list[str]) -> dict:
    """
    Create a multi-step execution plan for a complex task.
    """
    log_audit("REASONING", f"Planning task: {task[:80]}")

    prompt = f"""You are the planning engine of ASURA Sovereign AI.
Your goal is to build an optimal execution path using your available skills.

TASK: {task}

AVAILABLE SKILLS: {', '.join(available_skills)}

Create a detailed execution plan. Use your internal knowledge of tool signatures.
Respond ONLY with JSON:
{{
    "plan": [
        {{"step": 1, "action": "description", "skill": "skill_name", "details": "specifics"}},
        ...
    ],
    "estimated_steps": 3,
    "risks": ["potential risk 1", ...]
}}"""

    try:
        raw = await call_llm(prompt)

        result = extract_json(raw)
        if result and "plan" in result:
            log_audit("REASONING", f"Plan created with {len(result['plan'])} steps")
            return result

        return {"plan": [], "estimated_steps": 0, "risks": ["Failed to parse plan"]}

    except Exception as e:
        log_audit("REASONING_ERROR", f"Planning failed: {e}")
        return {"plan": [], "estimated_steps": 0, "risks": [str(e)]}


async def reflect(action: str, result: str, success: bool) -> str:
    """
    Reflect on an action's outcome and generate lessons learned.
    """
    prompt = f"""As ASURA, reflect on the following system interaction. 
How does this result improve your future reasoning or tool selection?

ACTION: {action}
RESULT: {result}
SUCCESS: {success}

Respond with a brief 1-2 sentence lesson learned. Be specific and actionable."""

    try:
        lesson = await call_llm(prompt)
        log_audit("REASONING", f"Reflection: {lesson[:100]}")
        return lesson
    except Exception:
        return "No reflection available."


async def _recursive_think_async(task: str, max_recursion: int = None, context: str = "") -> dict:
    """
    ASURA Zero: Recursive reasoning loop (Think -> Act -> Observe -> Reflect).
    """
    history = []
    current_context = context
    actions_taken = []
    
    max_recursion = max_recursion or config.REASONING_MAX_RECURSION
    log_audit("REASONING_ZERO", f"Recursive loop started: {task[:60]}")
    
    # --- Autonomous Scaling Logic ---
    if max_recursion > 3 or len(task) > config.REASONING_COMPLEXITY_THRESHOLD:
        log_audit("REASONING_ZERO", "Complexity detected. Querying specialist agents.")
        try:
            from core.declarative_agent_loader import get_agent_loader, init_declarative_agents
            init_declarative_agents()
            loader = get_agent_loader()
            from core.tool_protocol import dispatch
            
            best_agent = loader.find_agent_for_query(task)
            if best_agent:
                log_audit("REASONING_ZERO", f"Spawning specialist agent: {best_agent}")
                await dispatch("spawn_subagent", {"name": best_agent.lower(), "role": f"Specialized {best_agent} for task: {task[:50]}"})
            else:
                await dispatch("spawn_subagent", {"name": "explorer", "role": "Map codebase and trace execution"})
                await dispatch("spawn_subagent", {"name": "reviewer", "role": "Audit changes for security and quality"})
        except Exception as e:
            log_audit("REASONING_WARN", f"Autonomous scaling failed: {e}")
    # -------------------------------
    
    for i in range(max_recursion):
        # 1. Think
        thought = await _generate_thought(task, context=current_context + "\n" + "\n".join(history))
        
        # 2. Architect Pass: Validate the plan if it contains critical actions
        if thought.get("actions") and i == 0:
            log_audit("REASONING", "Metacognitive Pass: Auditing initial plan...")
            validation_prompt = f"""Task: {task}
Proposed Actions: {json.dumps(thought['actions'])}

As an Architect, identify any technical flaws or missing dependencies in this plan.
If the plan is flawed, suggest a corrected version.
Respond with a JSON object: {{"status": "VALID" | "FLAWED", "feedback": "...", "corrected_actions": [...]}}"""
            
            try:
                val_raw = await call_llm(validation_prompt, model=config.OLLAMA_MODEL_FAST, format="json")
                validation = extract_json(val_raw)
                if validation and validation.get("status") == "FLAWED":
                    log_audit("REASONING", f"Plan Adjusted by Architect: {validation.get('feedback')}")
                    thought["actions"] = validation.get("corrected_actions", thought["actions"])
                    history.append(f"Architect Feedback: {validation.get('feedback')}")
            except Exception: pass

        history.append(f"Step {i+1} Thought: {thought['conclusion']}")
        
        # 2. Are we done?
        if thought.get("confidence", 0) > 0.9 and not thought.get("actions"):
            break
            
        # 3. Actions
        actions = thought.get("actions", [])
        if not actions:
            break
            
        step_results = []
        from core.tool_protocol import dispatch
        
        for action in actions:
            actions_taken.append(action)
            log_audit("REASONING_ZERO", f"Executing sub-action: {action}")
            try:
                res = await dispatch("shell", action)
                step_results.append(f"Action: {action} | Result: {res[:200]}")
            except Exception as e:
                step_results.append(f"Action: {action} | Failed: {e}")
        
        # 4. Observe & Reflect
        observation = "\n".join(step_results)
        reflection = await reflect(str(actions), observation, True)
        history.append(f"Step {i+1} Observation: {observation[:200]}...")
        history.append(f"Step {i+1} Reflection: {reflection}")
        
        current_context += f"\n\n[Previous Results]:\n{observation}"

    # --- Cleanup Evaluation (Despawner Integration) ---
    try:
        log_audit("REASONING_ZERO", "Task cycle complete. Consulting Despawner for cleanup...")
        from core.tool_protocol import dispatch
        await dispatch("run_subagent_task", {
            "name": "asura-despawner", 
            "task": f"Evaluate the active sub-agents for task: '{task}'. Kill any redundant or idle specialists."
        })
    except Exception as e:
        log_audit("REASONING_WARN", f"Despawner cleanup skipped: {e}")
    # --------------------------------------------------

    return {
        "final_conclusion": history[-1] if history else "No progress made.",
        "history": history,
        "actions": actions_taken,
        "recursion_depth": i + 1
    }


def think(task: str, context: str = "", max_steps: int = 5) -> dict:
    """
    Chain-of-thought reasoning exposed synchronously.
    """
    import asyncio
    try:
        # Improved loop handling
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(lambda: asyncio.run(_recursive_think_async(task, max_steps, context))).result()
        else:
            result = asyncio.run(_recursive_think_async(task, max_recursion=max_steps, context=context))
    except Exception as e:
        log_audit("REASONING_ERROR", f"Recursive thinking failed: {e}")
        return {
            "thought_process": [str(e)],
            "conclusion": "Error during iterative thinking.",
            "actions": [],
            "confidence": 0.0
        }

    return {
        "thought_process": result.get("history", []),
        "conclusion": result.get("final_conclusion", "Done."),
        "actions": result.get("actions", []),
        "confidence": 0.9
    }


async def recursive_think(task: str, max_recursion: int = None, context: str = "") -> dict:
    """
    Async alias for the new iterative reasoning loop.
    """
    return await _recursive_think_async(task, max_recursion, context)
