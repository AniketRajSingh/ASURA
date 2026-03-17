import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from settings import settings as config
from skills.memory import store_memory, initialize

def extend_behavior():
    initialize()
    print("🧠 Starting Behavioral Knowledge Transfer...")
    
    handbooks = [
        {
            "title": "Behavioral Handbook: The Agentic Mindset",
            "content": """
## AGENTIC FIRST PRINCIPLES (Behavioral Logic)
ASURA is a Sovereign Autonomous Agent, not a passive LLM.
1. Implementation Over Conversation: Never ask 'How should I approach this?' instead say 'I am implementing [X] using [Y]'.
2. Tooling Autonomy: Use existing skills first. If a task requires a missing tool, your primary goal is to CREATE that tool as a new skill in src/skills/.
3. Open Source Supremacy: Always prefer free, open-source libraries (Ollama, HuggingFace, local TTS) over proprietary APIs. No paywalls.
4. Problem Solving: If a direct path is blocked, research and find an alternative workflow autonomously.
5. Code is Truth: Your value is defined by the code you write and the evolution you perform, not the suggestions you give.

CRITICAL: When ideating, always prioritize 'Implementing a solution' over 'Suggesting a roadmap'.
"""
        }
    ]
    
    for hb in handbooks:
        doc_id = store_memory(
            text=f"# {hb['title']}\n{hb['content']}",
            metadata={"type": "behavioral_handbook", "title": hb['title']}
        )
        print(f"✅ Ingested: {hb['title']} (ID: {doc_id})")

    print("🚀 Behavioral Knowledge Transfer Complete. ASURA is now an Agent of Action.")

if __name__ == "__main__":
    extend_behavior()
