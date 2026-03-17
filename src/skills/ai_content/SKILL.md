---
name: ai_content
description: "Core content generation engine for text, ReAct-based autonomous tasks, and multimodal interactions."
entry_point: generator.py
---

# AI Content Generator

The primary engine for autonomous interaction. It manages the ReAct (Reasoning and Acting) loop, tool execution via MCP, and memory-enhanced chat responses.

### 🔧 Tools / Functions
- `chat(user_message: str, history: list)`: Synchronous autonomous ReAct engine.
- `chat_stream(user_message: str, history: list)`: Async streaming engine for real-time interaction.
- `generate_topics()`: Get 3 trending AI/Tech topics.
- `generate_caption(topic: str)`: Create engaging social media captions.
- `cancel_current_task()`: Gracefully stop the running ReAct loop.

### 📝 Examples
- "Build a python script to scrape news" -> AI enters a ReAct loop to implement the request.
- "What are today's trending topics?" -> Returns a list of topics.

### 🛠️ Requirements
- Configured LLM Provider (Ollama or Groq).
- `httpx` for API communication.
