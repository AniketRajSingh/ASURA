# ============================================================
# skills/skill_registry.py — Skill Discovery & Registration
# ============================================================

import os
import re
import ast
from settings import settings as config
from skills.logger import log_app


def discover_skills() -> dict[str, dict]:
    """
    Scan the skills/ directory for subdirectories containing SKILL.md.
    Parse the YAML frontmatter to build a registry.

    Returns:
        {skill_name: {path, description, entry_point, full_content}}
    """
    registry = {}
    skills_dir = config.SKILLS_DIR

    if not os.path.isdir(skills_dir):
        log_app("Skills directory not found")
        return registry

    for entry in os.listdir(skills_dir):
        skill_path = os.path.join(skills_dir, entry)
        skill_md = os.path.join(skill_path, "SKILL.md")

        if not os.path.isdir(skill_path) or not os.path.isfile(skill_md):
            continue

        with open(skill_md, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse YAML frontmatter
        fm_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not fm_match: continue

        frontmatter = fm_match.group(1)
        meta = {}
        for line in frontmatter.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip()] = val.strip()

        # Deep Indexing: Extract function signatures from Python files
        functions = []
        for fname in os.listdir(skill_path):
            if fname.endswith(".py") and not fname.startswith("__"):
                fpath = os.path.join(skill_path, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read())
                    for node in tree.body:
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                            args = []
                            for a in node.args.args:
                                arg_info = {"name": a.arg}
                                if a.annotation:
                                    try: 
                                        arg_info["type"] = ast.unparse(a.annotation)
                                    except: pass
                                args.append(arg_info)
                            
                            ret_type = "Any"
                            if node.returns:
                                try: ret_type = ast.unparse(node.returns)
                                except: pass
                                
                            doc = ast.get_docstring(node) or ""
                            functions.append({
                                "name": node.name,
                                "args": args,
                                "return_type": ret_type,
                                "docstring": doc,
                                "is_async": isinstance(node, (ast.AsyncFunctionDef))
                            })
                except Exception:
                    pass

        name = meta.get("name", entry)
        registry[name] = {
            "path": skill_path,
            "description": meta.get("description", ""),
            "functions": functions,
            "full_content": content,
            "entry_point": meta.get("entry_point")
        }
    return registry


def load_skills():
    """Actually import the discovered skills to trigger their tool registrations."""
    import importlib
    import sys
    
    registry = discover_skills()
    log_app(f"Loading {len(registry)} skills...")
    
    for name, info in registry.items():
        entry_point = info.get("entry_point")
        if not entry_point:
            # Fallback to __init__.py if no entry_point specified
            if os.path.exists(os.path.join(info["path"], "__init__.py")):
                entry_point = "__init__.py"
            else:
                continue

        # Convert path to module name (e.g., skills.sub_agent_manager.manager)
        try:
            rel_path = os.path.relpath(info["path"], config.PROJECT_ROOT)
            # Remove 'src.' prefix if present in the rel_path conversion
            module_path = rel_path.replace(os.sep, ".")
            if module_path.startswith("src."):
                module_path = module_path[4:]
        except Exception:
            # Fallback for complex paths
            module_path = f"skills.{name}"
        
        if entry_point.endswith(".py"):
            module_name = f"{module_path}.{entry_point[:-3]}"
        else:
            module_name = module_path
            
        try:
            importlib.import_module(module_name)
            log_app(f"Successfully loaded skill: {name}")
        except Exception as e:
            import traceback
            log_app(f"Error loading skill {name}: {e}")
            from skills.logger import log_audit
            log_audit("SKILL_LOAD_ERROR", f"Critical failure loading skill '{name}':\n{traceback.format_exc()}")

    return registry


def list_skills(registry: dict = None, detailed: bool = False) -> str:
    """Return a formatted string listing all registered skills."""
    if registry is None:
        registry = discover_skills()

    if not registry:
        return "No skills found."

    lines = ["📦 **Registered Skills:**\n"]
    for name, info in sorted(registry.items()):
        desc = info['description'][:80].replace("_", "\\_").replace("*", "\\*")
        lines.append(f"  • **{name}** — {desc}")
        if detailed and info.get("functions"):
            for func in info["functions"][:5]:
                lines.append(f"    - `{func}`")
    
    output = "\n".join(lines)
    if len(output) > 4000:
        output = output[:3900] + "\n\n...(truncated)"
    return output


def get_skill_code(skill_name: str, registry: dict = None) -> str:
    """
    Read all .py files in a skill folder and return their combined content.
    Used by the self-updater to understand existing skill implementations.
    """
    if registry is None:
        registry = discover_skills()

    if skill_name not in registry:
        return f"Skill '{skill_name}' not found."

    skill_path = registry[skill_name]["path"]
    code_parts = []

    for fname in sorted(os.listdir(skill_path)):
        if fname.endswith(".py"):
            fpath = os.path.join(skill_path, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                code_parts.append(f"# === {fname} ===\n{f.read()}")

    return "\n\n".join(code_parts) if code_parts else "No Python files found."


def get_tool_count() -> int:
    """Return the number of effectively discovered tools/skills."""
    return len(discover_skills())
