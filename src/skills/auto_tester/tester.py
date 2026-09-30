# ============================================================
# skills/auto_tester/tester.py — Automated Self-Testing
# AI writes + runs tests before applying evolution changes
# ============================================================
import os, subprocess, tempfile, json
from settings import settings as config
from skills.logger import log_audit
import asyncio

def run_async(coro):
    """Run an async coroutine synchronously, even if an event loop is already running."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
        
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)

def run_syntax_check(filepath: str) -> dict:
    """Check Python file for syntax errors."""
    try:
        result = subprocess.run(["python", "-m", "py_compile", filepath],
                                capture_output=True, text=True, timeout=10)
        return {"passed": result.returncode == 0, "error": result.stderr.strip()}
    except Exception as e:
        return {"passed": False, "error": str(e)}

def run_import_check(module: str) -> dict:
    """Check if a module imports cleanly."""
    try:
        result = subprocess.run(
            ["python", "-c", f"import {module}; print('OK')"],
            capture_output=True, text=True, timeout=15, cwd=config.BASE_DIR)
        return {"passed": result.returncode == 0,
                "output": result.stdout.strip(), "error": result.stderr.strip()}
    except Exception as e:
        return {"passed": False, "error": str(e)}

def run_all_skill_imports() -> dict:
    """Test that all skills import cleanly."""
    from skills.skill_registry import discover_skills
    registry = discover_skills()
    results = {}
    for name in sorted(registry.keys()):
        check = run_import_check(f"skills.{name}")
        results[name] = check["passed"]
    passed = sum(1 for v in results.values() if v)
    log_audit("TEST", f"Import check: {passed}/{len(results)} passed")
    return {"total": len(results), "passed": passed, "results": results}

def generate_test(code: str, purpose: str) -> str:
    """Use LLM to generate a test for given code."""
    try:
        from core.llm import call_llm
        return run_async(call_llm(prompt, model=config.OLLAMA_MODEL_REVIEWER, stream=False))
    except: return ""

def run_test_string(test_code: str) -> dict:
    """Run a test string in a temp file."""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(test_code)
        f.flush()
        try:
            result = subprocess.run(["python", "-m", "pytest", f.name, "-v", "--tb=short"],
                                    capture_output=True, text=True, timeout=30, cwd=config.BASE_DIR)
            return {"passed": result.returncode == 0, "output": result.stdout[-500:], "error": result.stderr[-500:]}
        except Exception as e:
            return {"passed": False, "error": str(e)}
        finally:
            os.unlink(f.name)

def format_test_report(results: dict) -> str:
    total, passed = results["total"], results["passed"]
    emoji = "✅" if passed == total else "⚠️"
    lines = [f"🧪 *Test Report*\n\n{emoji} {passed}/{total} skills importing cleanly\n"]
    failures = [k for k, v in results["results"].items() if not v]
    if failures:
        lines.append("*Failed:*")
        for f in failures: lines.append(f"  ❌ {f}")
    return "\n".join(lines)

def verify_code_intent(code: str, intent: str) -> dict:
    """Compare generated code against original intent using LLM."""
    import requests
    prompt = f"""You are an expert Python code reviewer.
Compare the GENERATED CODE against the ORIGINAL INTENT.

ORIGINAL INTENT:
{intent}

GENERATED CODE:
{code}

Analyze for:
1. Logic errors or data structure mismatches (e.g. using 'title' instead of 'description').
2. Missing requirements from the intent.
3. UI or UX inconsistencies.

Return ONLY a JSON object:
{{"passed": true/false, "feedback": "detailed explanation of any flaws or 'OK'"}}
"""
    try:
        from core.llm import call_llm
        raw = run_async(call_llm(prompt, model=config.OLLAMA_MODEL_REVIEWER, stream=False))
        # Extract JSON from potential markdown fences
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        return json.loads(raw)
    except Exception as e:
        return {"passed": False, "error": str(e), "feedback": "Verification failed to run."}
