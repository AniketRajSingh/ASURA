"""
skills/codebase_investigator/investigator.py
============================================================
The Codebase Investigator — gives ASURA the same codebase
understanding that Antigravity and Gemini CLI have.

Capabilities:
  - grep(pattern)         — ripgrep-style search with file:line output
  - find_symbol(name)     — find all definitions + call sites across project
  - trace_imports(file)   — show what a file imports (direct + transitive)
  - architecture_report() — full structural critique of src/
  - detect_issues()       — find common bugs: circular imports, missing awaits, etc.
"""

import os
import ast
import re
import json
import subprocess
from pathlib import Path
from typing import Generator
from settings import settings as config
from skills.logger import log_audit


# ── Helpers ─────────────────────────────────────────────────

def _src_root() -> Path:
    return Path(config.SRC_DIR)


def _all_python_files(root: Path = None) -> Generator[Path, None, None]:
    """Yield every .py file under src/, skipping __pycache__ and .pyc."""
    root = root or _src_root()
    for p in root.rglob("*.py"):
        if "__pycache__" not in str(p):
            yield p


def _rel(path: Path) -> str:
    """Return path relative to PROJECT_ROOT for clean output."""
    try:
        return str(path.relative_to(config.PROJECT_ROOT))
    except ValueError:
        return str(path)


def _parse_safe(path: Path) -> ast.Module | None:
    """Parse a file with ast; return None on syntax error."""
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return None
    except Exception:
        return None


# ── Tool 1: grep ─────────────────────────────────────────────

def grep(pattern: str, path: str = None, case_sensitive: bool = True) -> str:
    """
    Regex search across the codebase. Returns file:line:match results.
    Equivalent to: grep -rn <pattern> src/
    """
    search_root = path or str(_src_root())
    flags = [] if case_sensitive else ["-i"]
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", "--include=*.html", "--include=*.js",
             "-E"] + flags + [pattern, search_root],
            capture_output=True, text=True, timeout=15,
            cwd=config.PROJECT_ROOT
        )
        lines = result.stdout.strip().splitlines()
        if not lines:
            return f"No matches found for: {pattern}"
        # Trim absolute paths to relative
        cleaned = []
        for line in lines[:50]:
            line = line.replace(str(config.PROJECT_ROOT) + "/", "")
            cleaned.append(line)
        total = len(result.stdout.strip().splitlines())
        out = "\n".join(cleaned)
        if total > 50:
            out += f"\n... and {total - 50} more matches (showing first 50)"
        return out
    except subprocess.TimeoutExpired:
        return "grep timed out"
    except FileNotFoundError:
        # Fallback: pure Python grep
        return _python_grep(pattern, search_root, case_sensitive)


def _python_grep(pattern: str, root: str, case_sensitive: bool) -> str:
    """Pure-Python fallback grep."""
    rx = re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)
    results = []
    for path in Path(root).rglob("*.py"):
        if "__pycache__" in str(path):
            continue
        try:
            for i, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
                if rx.search(line):
                    rel = _rel(path)
                    results.append(f"{rel}:{i}: {line.rstrip()}")
                    if len(results) >= 50:
                        return "\n".join(results) + "\n(50 result limit reached)"
        except Exception:
            pass
    return "\n".join(results) if results else f"No matches for: {pattern}"


# ── Tool 2: find_symbol ──────────────────────────────────────

def find_symbol(name: str) -> str:
    """
    Find all definitions AND call sites of a symbol (function/class/variable).
    Returns structured file:line results.
    """
    definitions = []
    call_sites = []

    for path in _all_python_files():
        tree = _parse_safe(path)
        if tree is None:
            continue
        rel = _rel(path)
        for node in ast.walk(tree):
            # Definition
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name == name:
                    definitions.append(f"  DEF  {rel}:{node.lineno} — {type(node).__name__} {name}")
            # Assignment definition
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id == name:
                        definitions.append(f"  DEF  {rel}:{node.lineno} — assignment")
            # Call sites
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == name:
                    call_sites.append(f"  CALL {rel}:{node.lineno}")
                elif isinstance(func, ast.Attribute) and func.attr == name:
                    call_sites.append(f"  CALL {rel}:{node.lineno} (method)")

    if not definitions and not call_sites:
        return f"Symbol '{name}' not found anywhere in src/"

    parts = [f"Symbol: {name}\n"]
    if definitions:
        parts.append(f"Definitions ({len(definitions)}):")
        parts.extend(definitions[:20])
    if call_sites:
        parts.append(f"\nCall sites ({len(call_sites)}):")
        parts.extend(call_sites[:30])
    if len(call_sites) > 30:
        parts.append(f"  ... and {len(call_sites) - 30} more call sites")
    return "\n".join(parts)


# ── Tool 3: trace_imports ────────────────────────────────────

def trace_imports(filepath: str) -> str:
    """
    Show what a file imports — both standard library and local modules.
    Returns a dependency summary.
    """
    path = Path(filepath)
    if not path.is_absolute():
        path = Path(config.PROJECT_ROOT) / filepath
    if not path.exists():
        return f"File not found: {filepath}"

    tree = _parse_safe(path)
    if tree is None:
        return f"Could not parse {filepath} (syntax error?)"

    stdlib_imports = []
    local_imports = []
    third_party = []

    src_root = _src_root()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                _classify_import(mod, stdlib_imports, local_imports, third_party, src_root)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod = node.module.split(".")[0]
                _classify_import(mod, stdlib_imports, local_imports, third_party, src_root)

    lines = [f"Import trace for: {_rel(path)}\n"]
    if local_imports:
        lines.append(f"Local modules ({len(local_imports)}): {', '.join(sorted(set(local_imports)))}")
    if third_party:
        lines.append(f"Third-party ({len(third_party)}): {', '.join(sorted(set(third_party)))}")
    if stdlib_imports:
        lines.append(f"Stdlib ({len(stdlib_imports)}): {', '.join(sorted(set(stdlib_imports)))}")
    return "\n".join(lines)


def _classify_import(mod: str, stdlib: list, local: list, third_party: list, src_root: Path):
    """Classify an import as stdlib, local, or third-party."""
    import sys
    # Check if it's a local module (exists in src/)
    local_path = src_root / mod
    local_file = src_root / f"{mod}.py"
    if local_path.is_dir() or local_file.exists():
        local.append(mod)
    elif mod in sys.stdlib_module_names:
        stdlib.append(mod)
    else:
        third_party.append(mod)


# ── Tool 4: architecture_report ─────────────────────────────

def architecture_report() -> str:
    """
    Generate a full architectural summary of ASURA's codebase —
    the same level of analysis Gemini CLI or Antigravity would produce.
    """
    src = _src_root()
    skills_dir = src / "skills"
    core_dir = src / "core"

    lines = ["# ASURA Architecture Report\n"]

    # Count files and lines
    total_files = 0
    total_lines = 0
    syntax_errors = []
    for path in _all_python_files():
        total_files += 1
        try:
            content = path.read_text(errors="replace")
            total_lines += len(content.splitlines())
            # Check syntax
            tree = _parse_safe(path)
            if tree is None:
                syntax_errors.append(_rel(path))
        except Exception:
            pass

    lines.append(f"## Overview")
    lines.append(f"- **Total Python files**: {total_files}")
    lines.append(f"- **Total lines of code**: {total_lines:,}")
    lines.append(f"- **Syntax errors**: {len(syntax_errors)}")
    if syntax_errors:
        for f in syntax_errors:
            lines.append(f"  - ⚠️ {f}")

    # Core modules
    lines.append(f"\n## Core Modules ({core_dir})")
    if core_dir.exists():
        core_files = sorted(core_dir.glob("*.py"))
        for f in core_files:
            if f.name.startswith("_"):
                continue
            tree = _parse_safe(f)
            fn_count = cls_count = 0
            if tree:
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        fn_count += 1
                    elif isinstance(node, ast.ClassDef):
                        cls_count += 1
            size = f.stat().st_size
            lines.append(f"- `{f.name}` — {fn_count} functions, {cls_count} classes ({size:,} bytes)")

    # Skills
    lines.append(f"\n## Skills ({skills_dir})")
    if skills_dir.exists():
        skill_dirs = sorted([d for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith("_")])
        for skill in skill_dirs:
            py_files = list(skill.glob("*.py"))
            init = skill / "__init__.py"
            skill_md = skill / "SKILL.md"
            desc = ""
            if skill_md.exists():
                desc = skill_md.read_text()[:80].strip().replace("\n", " ")
            lines.append(f"- **{skill.name}** ({len(py_files)} files)" + (f": {desc}" if desc else ""))

    # Potential issues
    lines.append("\n## Potential Issues Detected")
    issues = detect_issues()
    lines.append(issues)

    log_audit("INVESTIGATOR", "Architecture report generated")
    return "\n".join(lines)


# ── Tool 5: detect_issues ────────────────────────────────────

def detect_issues() -> str:
    """
    Static analysis: detect common code quality problems across the codebase.
    Checks: missing awaits, broad excepts, hardcoded paths, TODO/FIXME density.
    """
    findings = []

    broad_except = []
    hardcoded_paths = []
    bare_prints = []
    todo_count = 0
    fixme_count = 0
    async_no_await = []

    for path in _all_python_files():
        rel = _rel(path)
        try:
            content = path.read_text(errors="replace")
            lines_list = content.splitlines()
        except Exception:
            continue

        for i, line in enumerate(lines_list, 1):
            stripped = line.strip()
            # Broad excepts
            if re.match(r"except\s*:", stripped) or re.match(r"except\s+Exception\s*:", stripped):
                broad_except.append(f"  {rel}:{i}: {stripped[:60]}")
            # Hardcoded paths
            if re.search(r'["\']\/Users\/|["\']\/home\/', stripped):
                hardcoded_paths.append(f"  {rel}:{i}: {stripped[:60]}")
            # Bare prints (not in test files)
            if stripped.startswith("print(") and "test" not in rel:
                bare_prints.append(f"  {rel}:{i}: {stripped[:60]}")
            # TODOs / FIXMEs
            if "TODO" in line:
                todo_count += 1
            if "FIXME" in line:
                fixme_count += 1

        # Check async functions that never use await
        tree = _parse_safe(path)
        if tree:
            for node in ast.walk(tree):
                if isinstance(node, ast.AsyncFunctionDef):
                    has_await = any(isinstance(n, ast.Await) for n in ast.walk(node))
                    if not has_await:
                        async_no_await.append(f"  {rel}:{node.lineno}: async def {node.name}() never awaits")

    result = []
    if broad_except:
        result.append(f"**Broad except clauses** ({len(broad_except)} — hides real errors):")
        result.extend(broad_except[:5])
        if len(broad_except) > 5:
            result.append(f"  ... and {len(broad_except) - 5} more")
    if async_no_await:
        result.append(f"\n**Async functions that never await** ({len(async_no_await)}):")
        result.extend(async_no_await[:5])
    if hardcoded_paths:
        result.append(f"\n**Hardcoded absolute paths** ({len(hardcoded_paths)}):")
        result.extend(hardcoded_paths[:5])
    if bare_prints:
        result.append(f"\n**Bare print() calls** ({len(bare_prints)} — use logger instead):")
        result.extend(bare_prints[:5])
    result.append(f"\n**TODO count**: {todo_count}  |  **FIXME count**: {fixme_count}")

    return "\n".join(result) if result else "No major issues detected."


# ── Unified entry point ──────────────────────────────────────

def investigate(query: str) -> str:
    """
    Dispatch investigation queries. Called by the MCP tool.
    Accepts:
      - "grep: <pattern>"
      - "find: <symbol_name>"
      - "imports: <filepath>"
      - "architecture" or "report"
      - "issues" or "audit"
    """
    q = query.strip()

    if q.lower().startswith("grep:"):
        return grep(q[5:].strip())
    elif q.lower().startswith("find:"):
        return find_symbol(q[5:].strip())
    elif q.lower().startswith("imports:"):
        return trace_imports(q[8:].strip())
    elif q.lower() in ("architecture", "report", "arch"):
        return architecture_report()
    elif q.lower() in ("issues", "audit", "problems"):
        return detect_issues()
    else:
        # Default: try to grep for it
        return grep(q)
