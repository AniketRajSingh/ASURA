import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from settings import settings as config
from skills.memory import store_memory, initialize

def teach_tf():
    initialize()
    print("🧠 Starting Deep Knowledge Transfer...")
    
    handbooks = [
        {
            "title": "Architectural Handbook: The Evolution Loop",
            "content": """
## THE EVOLUTION LOOP (Core Intelligence Path)
ASURA follows a strict 10-step cycle for self-improvement:
0. Health check: Verify CPU/RAM/Disk.
1. Analyze: Read codebase, memories, and hardware state.
2. Ideate: Pick a TODO or propose a self-contained feature.
3. Generate: Write the COMPLETE Python file (no fences).
4. Validate: 3-layer safety check (Syntax -> Dangerous Pattern -> AST analysis).
5. Backup: Snapshot the target file.
6. Apply: Write to disk.
7. Test: Subprocess import test to prevent crashes.
7.5 Reflect: Post-apply LLM verification against original intent.
8. Rollback: Immediate revert on test/reflection failure.
9. Log: Register success/failure and update skills.md.

CRITICAL: Never skip Step 7.5. It catches logic bugs that syntax and import tests miss.
"""
        },
        {
            "title": "Data Standard: TODOs and Descriptions",
            "content": """
## DATA INVARIANTS: TODOs & Dictionary Keys
ASURA uses specific keys for system-level data structures.
- TODO Objects: ALWAYS use 'description' for the task text. Do NOT use 'title' or 'task'.
- Priority Levels: 'critical', 'high', 'medium', 'low'.
- Status: 'open', 'done', 'failed', 'abandoned'.

When generating code to iterate over TODOs, always use t.get('description', t) to ensure robustness. Mismatching these keys causes UI breakage (raw JSON rendering).
"""
        },
        {
            "title": "Coding Standard: OS Independence",
            "content": """
## ARCHITECTURAL GOAL: OS Independence
ASURA must be completely decoupled from the host OS (Linux, Mac, Windows).
- Paths: Use os.path.join() or pathlib.Path. Never use hardcoded slashes like 'data/logs'.
- Commands: Avoid shell-specific commands (ls, rm, grep). Use Python-native libraries (os, shutil, glob).
- Process Management: Use psutil for cross-platform process lifecycle tracking.
- Settings: Use Pydantic-based settings.py for type-safety and environment variable loading.
"""
        },
        {
            "title": "Self-Awareness: The Skills Registry",
            "content": """
## SKILL REGISTRY & SELF-AWARENESS
ASURA defines itself through its Skills.
- Location: src/skills/
- Registry: Registered in src/skills/skill_registry.py via discover_skills().
- Documentation: docs/skills.md is the 'Self-Awareness' document. It must be updated after every evolution cycle to reflect the new state of the AI.

A true autonomous evolution is only complete when the registry and docs reflect the change.
"""
        }
    ]
    
    for hb in handbooks:
        doc_id = store_memory(
            text=f"# {hb['title']}\n{hb['content']}",
            metadata={"type": "architectural_handbook", "title": hb['title']}
        )
        print(f"✅ Ingested: {hb['title']} (ID: {doc_id})")

    print("🚀 Deep Knowledge Transfer Complete. ASURA is now self-aware of its own standards.")

if __name__ == "__main__":
    teach_tf()
