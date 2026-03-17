# ============================================================
# skills/file_organizer/code_nav_skill.py — Semantic Navigation
# ============================================================
import os
import ast
from settings import settings as config
from skills.logger import log_audit

def list_code_items(query: str = None) -> list[dict]:
    """
    Search for classes and functions by name using AST.
    Pure Python and OS-independent.
    """
    items = []
    search_dir = config.BASE_DIR
    
    # Filter files by pattern (glob)
    import fnmatch
    files_to_scan = []
    for root, _, files in os.walk(search_dir):
        if any(exc in root for exc in [".git", "__pycache__", ".venv", "node_modules", "data"]):
            continue
        for f in fnmatch.filter(files, "*.py"):
            files_to_scan.append(os.path.join(root, f))

    for fpath in files_to_scan:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                    # If query exists, filter by name
                    if query and query.lower() not in node.name.lower():
                        continue
                        
                    items.append({
                        "name": node.name,
                        "type": "class" if isinstance(node, ast.ClassDef) else "function",
                        "file": os.path.relpath(fpath, search_dir),
                        "line": node.lineno
                    })
        except Exception:
            pass

    # Sort results by name
    items.sort(key=lambda x: x["name"])
    
    log_audit("CODE_NAV", f"Found {len(items)} items matching '{query or '*'}'")
    return items[:100]

def get_item_source(name: str) -> dict:
    """Find a function or class by name and return its source code range."""
    items = list_code_items(name)
    if not items:
        return {"success": False, "error": f"Item '{name}' not found."}
        
    # Pick the first exact match or best match
    best = items[0]
    for item in items:
        if item["name"] == name:
            best = item
            break
            
    fpath = os.path.join(config.BASE_DIR, best["file"])
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        # We only have start line from AST easily, for end line we'd need more logic
        # but for navigation, start line + file is enough for ASURA to read.
        return {
            "success": True,
            "name": best["name"],
            "type": best["type"],
            "file": best["file"],
            "line": best["line"],
            "path": fpath
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
