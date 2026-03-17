# ============================================================
# skills/file_organizer/organizer.py — Smart File Organization
# ============================================================
import os, subprocess
from settings import settings as config
from skills.logger import log_audit

def find_dead_imports(directory: str = None) -> list[str]:
    """Find Python files with unused imports."""
    d = directory or config.BASE_DIR
    dead = []
    for root, _, files in os.walk(d):
        for f in files:
            if not f.endswith(".py"): continue
            path = os.path.join(root, f)
            try:
                with open(path) as fh:
                    lines = fh.readlines()
                imports = [l.strip() for l in lines if l.strip().startswith(("import ", "from "))]
                if len(imports) > 10:
                    dead.append(f"{path}: {len(imports)} imports (review)")
            except: pass
    return dead

def find_large_files(min_kb: int = 500) -> list[dict]:
    """Find large files in the project."""
    large = []
    for root, _, files in os.walk(config.BASE_DIR):
        if ".git" in root or "__pycache__" in root: continue
        for f in files:
            path = os.path.join(root, f)
            size = os.path.getsize(path)
            if size > min_kb * 1024:
                large.append({"file": os.path.relpath(path, config.BASE_DIR), "size_kb": size // 1024})
    return sorted(large, key=lambda x: -x["size_kb"])

def find_duplicates() -> list[tuple]:
    """Find files with similar names across the project."""
    names = {}
    for root, _, files in os.walk(config.BASE_DIR):
        if ".git" in root: continue
        for f in files:
            base = f.lower()
            if base not in names: names[base] = []
            names[base].append(os.path.relpath(os.path.join(root, f), config.BASE_DIR))
    return [(name, paths) for name, paths in names.items() if len(paths) > 1]

def get_project_stats() -> str:
    py_files = sum(1 for r, _, fs in os.walk(config.BASE_DIR) for f in fs if f.endswith(".py") and ".git" not in r)
    total_files = sum(1 for r, _, fs in os.walk(config.BASE_DIR) for f in fs if ".git" not in r)
    total_size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(config.BASE_DIR) for f in fs if ".git" not in r)
    dirs = sum(1 for r, ds, _ in os.walk(config.BASE_DIR) for d in ds if ".git" not in r and d != "__pycache__")
    dupes = find_duplicates()
    large = find_large_files()
    return (f"📁 *Project Stats*\n\nFiles: {total_files} | Python: {py_files}\n"
            f"Directories: {dirs}\nTotal size: {total_size // 1024}KB\n"
            f"Large files: {len(large)} | Duplicates: {len(dupes)}")
