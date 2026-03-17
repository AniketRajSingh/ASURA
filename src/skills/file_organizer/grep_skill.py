# ============================================================
# skills/file_organizer/grep_skill.py — OS-Independent Search
# ============================================================
import os
import re
import concurrent.futures
from settings import settings as config
from skills.logger import log_audit

def grep_search(query: str, pattern: str = "*.py", case_insensitive: bool = True) -> list[dict]:
    """
    Search for a literal string or regex across the codebase.
    Pure Python multi-threaded implementation for OS independence.
    """
    results = []
    search_dir = config.BASE_DIR
    
    # Pre-compile regex for speed
    flags = re.IGNORECASE if case_insensitive else 0
    try:
        regex = re.compile(query, flags)
    except re.error as e:
        log_audit("GREP_ERROR", f"Invalid regex '{query}': {e}")
        return []

    # Filter files by pattern (glob)
    import fnmatch
    files_to_scan = []
    for root, _, files in os.walk(search_dir):
        if any(exc in root for exc in [".git", "__pycache__", ".venv", "node_modules", "data"]):
            continue
        for f in fnmatch.filter(files, pattern):
            files_to_scan.append(os.path.join(root, f))

    def scan_file(fpath):
        matches = []
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    if regex.search(line):
                        matches.append({
                            "file": os.path.relpath(fpath, search_dir),
                            "line": i,
                            "content": line.strip()
                        })
        except Exception:
            pass
        return matches

    log_audit("GREP", f"Searching for '{query}' in {len(files_to_scan)} files...")

    # Use ThreadPoolExecutor for I/O bound tasks
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_file = {executor.submit(scan_file, f): f for f in files_to_scan}
        for future in concurrent.futures.as_completed(future_to_file):
            results.extend(future.result())

    # Sort results by file and line
    results.sort(key=lambda x: (x["file"], x["line"]))
    
    log_audit("GREP", f"Found {len(results)} matches for '{query}'")
    return results[:100]  # Cap at 100 results for safety
