# ASURA Capabilities Registry
> This file is autonomously maintained by the DocUpdater daemon.
> Last updated: Wed Mar 18 06:35:55 2026

ASURA possesses a modular 'Skill' architecture. Each skill is a self-contained capability that registers one or more tools into the MCP-Lite protocol.

---

## 🛠️ Active Skills Registry

| Skill | Description | Path |
|---|---|---|
| **ai_content** | "Core content generation engine for text, ReAct-based autonomous tasks, and multimodal interactions." | `src/skills/ai_content` |
| **api_server** | "FastAPI REST server that exposes ASURA's skills, chat, and management features as secure API endpoints." | `src/skills/api_server` |
| **audio_generator** | "Generates pure audio tones and converts text to speech using the gTTS library." | `src/skills/audio_generator` |
| **audio_say** | "Converts text to speech and saves it as an MP3 file using gTTS." | `src/skills/audio_say` |
| **auto_tester** | "Automated self-testing. Syntax checks, import validation, LLM-generated tests, and pytest runner." | `src/skills/auto_tester` |
| **backup_manager** | "Provides a project snapshot and restore system with automatic rotation and safety checks." | `src/skills/backup_manager` |
| **browser** | "Autonomous web interaction skill using Playwright. Can navigate, click, type, and take screenshots for visual analysis." | `src/skills/browser` |
| **calendar_manager** | "Calendar and reminder management system for scheduling events and setting notifications." | `src/skills/calendar_manager` |
| **cloud_sync** | "Cloud synchronization and backup skill. Supports local backups and rclone-based sync to Google Drive, S3, and other remotes." | `src/skills/cloud_sync` |
| **codebase_investigator** | "Deep static analysis of ASURA's source code. Performs grep searches, symbol finding, import tracing, and architectural reporting." | `src/skills/codebase_investigator` |
| **conversation** | "Manages conversation history, context retrieval, and system prompt construction for human-AI interaction." | `src/skills/conversation` |
| **dashboard** | "Observability web dashboard. Shows system status, skills, TODOs, hardware metrics, and audit log." | `src/skills/dashboard` |
| **disk_usage** | "Monitors disk space utilization and provides detailed statistics for specified paths." | `src/skills/disk_usage` |
| **doc_summarizer** | "Document summarization skill. Summarizes text, URLs, and PDFs into bullets, paragraphs, or TL;DR using LLM." | `src/skills/doc_summarizer` |
| **dream_machine** | "Long-term background goals engine for managing and tracking AI autonomous tasks during idle time." | `src/skills/dream_machine` |
| **email_manager** | "Email integration skill. Send emails via SMTP, check inboxes via IMAP, and format summaries for notifications." | `src/skills/email_manager` |
| **emotion** | "Emotion-aware response engine that detects user sentiment and adapts AI personality and style." | `src/skills/emotion` |
| **encryption** | "Core skill for encrypting and decrypting data at rest using Fernet or XOR fallback." | `src/skills/encryption` |
| **feature_tracker** | "Feature evolution tracker. Registers capabilities, detects when a new skill can replace an old one, and tracks upgrade history." | `src/skills/feature_tracker` |
| **feedback** | "Feedback loop learning. Records user sentiment, detects mood, and learns preferences to adapt AI behavior over time." | `src/skills/feedback` |
| **file_organizer** | "OS-independent smart file organization, global search, and project statistics reporting." | `src/skills/file_organizer` |
| **git_manager** | "Git integration skill. Provides auto-commits, branch management, status, diffs, and logs to track system evolution." | `src/skills/git_manager` |
| **graceful_mode** | "Graceful degradation system. Caches responses and queues tasks when offline, auto-processing them when services return." | `src/skills/graceful_mode` |
| **habit_tracker** | "Habit and pattern recognition. Logs events, detects peak usage hours/days, and provides proactive insights." | `src/skills/habit_tracker` |
| **hardware_monitor** | "System resource monitoring. Tracks CPU, RAM, disk, and GPU (Apple Silicon + NVIDIA) for resource-aware operations." | `src/skills/hardware_monitor` |
| **health_alerter** | "Proactive system health monitoring that alerts and triggers auto-remediation when resource thresholds are exceeded." | `src/skills/health_alerter` |
| **instagram_poster** | "Instagram content publishing skill. Renders HTML/CSS templates to images, uploads to Cloudinary, and publishes via Instagram Graph API." | `src/skills/instagram_poster` |
| **knowledge_graph** | "Maintains a structured graph of concepts, entities, and their relationships for context retrieval." | `src/skills/knowledge_graph` |
| **log_cleanup** | "Automatically rotate and prune old log entries to prevent storage bloat and maintain system performance." | `src/skills/log_cleanup` |
| **logger** | "Core thread-safe logging system for audit trails and application lifecycle events." | `src/skills/logger` |
| **memory** | "Multi-layered RAG memory system featuring semantic (FAISS), episodic, and procedural storage." | `src/skills/memory` |
| **multi_model** | "Task-aware LLM manager for dynamic model selection and capability-based routing." | `src/skills/multi_model` |
| **nl_commands** | "Translates natural language messages into specific internal skill function calls using regex pattern matching." | `src/skills/nl_commands` |
| **notification_router** | "Intelligent notification routing system for dispatching alerts across Telegram, email, and dashboard." | `src/skills/notification_router` |
| **scheduler** | "Core skill: Cron-style task scheduler. Add arbitrary recurring tasks (shell, python, notify, evolve) with persistent schedules and a background daemon." | `src/skills/scheduler` |
| **shell_executor** | "Core skill: Sandboxed shell execution. Runs commands inside the project freely, blocks/asks master for commands outside the project or destructive operations. File read/write/list helpers." | `src/skills/shell_executor` |
| **skill_hotreload** | "Dynamically hot-reload skill modules without restarting the ASURA system." | `src/skills/skill_hotreload` |
| **smart_deps** | "Automatically detects and upgrades outdated Python dependencies." | `src/skills/smart_deps` |
| **sub_agent_manager** | "Manager for spawning, commanding, and inspecting specialized sub-agents with isolated memory vaults." | `src/skills/sub_agent_manager` |
| **system_health** | "Generates a concise, human-readable report of system health metrics including CPU, memory, disk, and uptime." | `src/skills/system_health` |
| **telegram_bot** | "Provides a Telegram Bot interface for system interaction, Instagram posting workflows, and conversational chat." | `src/skills/telegram_bot` |
| **time_tracker** | "Lightweight session-based time tracking for monitoring task duration and generating weekly reports." | `src/skills/time_tracker` |
| **todo_manager** | "AI-driven TODO tracking system for managing improvements, bugfixes, and features." | `src/skills/todo_manager` |
| **visual** | "Visual understanding skill optimized for Qwen3.5 Vision models, supporting image analysis, OCR, and UI debugging." | `src/skills/visual` |
| **voice** | "Voice interface for high-quality speech-to-text (Whisper) and cross-platform text-to-speech conversion." | `src/skills/voice` |
| **voice_chat** | "Real-time voice interaction layer for hands-free command and response." | `src/skills/voice_chat` |
| **web_intelligence** | "Web search and scraping engine with multi-engine fallback and content extraction." | `src/skills/web_intelligence` |
| **webhook_handler** | "Incoming webhook handler. Accepts GitHub or generic webhooks, verifies signatures, and triggers appropriate system actions." | `src/skills/webhook_handler` |

## 📦 Detailed Functional Breakdowns

### Ai Content
**Path:** `src/skills/ai_content`  
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

### Api Server
**Path:** `src/skills/api_server`  
# API Server

Exposes the AI's capabilities through a robust REST API with SSE streaming support. Enables integration with web frontends, mobile apps, and external services.

### 🔧 Tools / Functions
- `start_api_server()`: Start the FastAPI/Uvicorn server in a background thread.

### 📝 Examples
- "Launch the API" -> Starts the server on the configured host and port (default 8000).

### 🛠️ Requirements
- `fastapi`, `uvicorn`, `httpx`.
- `X-ASURA-Key` for authenticated requests.

### Audio Generator
**Path:** `src/skills/audio_generator`  
# Audio Generator

Creates simple audio files, including pure frequency tones for alerts and speech from text for audible responses.

### 🔧 Tools / Functions
- `generate_tone(freq: float, duration: float, filename: str)`: Create a WAV file with a pure sine wave tone.
- `generate_audio(text: str, output_path: str, driver: str = "gtts")`: High-level text-to-speech generation.
- `speak_text(text: str, filename: str)`: Directly use gTTS to create an MP3 speech file.

### 📝 Examples
- "Generate a beep sound" -> Creates a short high-frequency WAV file.
- "Create an audio version of this summary" -> Generates an MP3 file of the provided text.

### 🛠️ Requirements
- `gtts` (Google Text-to-Speech) library.

### Audio Say
**Path:** `src/skills/audio_say`  
# Audio Say Skill

Provides text-to-speech (TTS) capabilities, allowing the system to generate audio files from text input. It primarily uses the `gTTS` (Google Text-to-Speech) library, with a silent fallback if the library is unavailable.

### 🔧 Tools / Functions
- `generate_audio(text, output_path="output.mp3")`: Converts the provided text into an MP3 audio file and returns the absolute path to the generated file.

### 📝 Examples
- "Say 'Hello, how are you?'" -> Generates `output.mp3` with the spoken text.
- "Generate audio for the summary" -> Creates an audio file of the summary text.

### 🛠️ Requirements
- `gtts` library (recommended for actual audio generation)
- Internet connection (required by gTTS for speech synthesis)

### Auto Tester
**Path:** `src/skills/auto_tester`  
# Auto Tester

Automated self-testing system for the ASURA framework. It performs syntax checks, validates module imports, uses LLM to generate tests for new code, and runs them using pytest to ensure system integrity.

### 🔧 Tools / Functions
- `run_syntax_check(filepath)`: Check Python file for syntax errors.
- `run_import_check(module)`: Check if a module imports cleanly.
- `run_all_skill_imports()`: Test that all skills in the registry import cleanly.
- `generate_test(code, purpose)`: Use LLM to generate a pytest test for the given code.
- `run_test_string(test_code)`: Run a test string in a temporary file using pytest.
- `verify_code_intent(code, intent)`: Compare generated code against original intent using LLM for logical consistency.

### 📝 Examples
- "Check if my new skill imports correctly" -> Passes if `import skills.new_skill` works.
- "Generate a test for this function" -> Returns a `test_*.py` snippet.

### 🛠️ Requirements
- `pytest`
- `ollama` (configured in `config.py` for LLM-based verification)

### Backup Manager
**Path:** `src/skills/backup_manager`  
# Backup Manager

A core safety skill that handles project-wide snapshots and restoration. It ensures system state can be recovered by creating timestamped backups, enforcing size limits, and automatically rotating old snapshots to save space.

### 🔧 Tools / Functions
- `create_snapshot(reason="")`: Generates a compressed ZIP archive of the project source, excluding heavy directories like `.git`, `node_modules`, and `.venv`.
- `restore_snapshot(snapshot_name)`: Replaces current project files with those from a named snapshot. Always creates a pre-restore safety backup.
- `list_snapshots()`: Returns a metadata list of all available snapshots currently stored in the backup directory.

### 📝 Examples
- "Create a backup before I change the core" -> `create_snapshot("Manual backup before core change")`
- "Show me my backups" -> `list_snapshots()`

### 🛠️ Requirements
- `shutil`, `zipfile`, `tempfile` (standard library)
- `BACKUP_DIR` and `MAX_BACKUPS` configured in `config.py`

### Browser
**Path:** `src/skills/browser`  
# Browser

Enables autonomous web browsing and interaction. ASURA can navigate complex websites, fill out and submit forms, extract clean text content for analysis, and capture screenshots to facilitate visual reasoning.

### 🔧 Tools / Functions
- `browse_url(url, screenshot)`: Navigate to a URL using Playwright and extract the page title and body content.
- `fill_form(url, fields, submit_selector)`: Automatically populate form fields and trigger a submission.
- `take_screenshot(url)`: Capture a high-resolution screenshot of a webpage and save it to the local project directory.
- `_browse_fallback(url)`: Internal fallback to `requests` and `BeautifulSoup` if Playwright is unavailable.

### 📝 Examples
- "Search for the latest news on Google" -> Navigates to Google and extracts result summaries.
- "Take a screenshot of https://example.com" -> Saves `browser_screenshot.png` to the project root.

### 🛠️ Requirements
- `playwright`
- `chromium` (installed via `playwright install chromium`)

### Calendar Manager
**Path:** `src/skills/calendar_manager`  
# Calendar Manager

Manage your schedule and set reminders. Integrates with the system's background scheduler to trigger notifications when events are due.

### 🔧 Tools / Functions
- `add_event(title, when, description, remind_minutes)`: Add a new event with an optional reminder.
- `remove_event(event_id)`: Remove an existing event.
- `get_upcoming(hours)`: Retrieve events occurring within the specified window.
- `format_calendar_summary()`: Get a human-readable list of upcoming events.

### 📝 Examples
- "Schedule a meeting for tomorrow at 2 PM" -> Event added with a default 30-minute reminder.
- "What's on my calendar?" -> Shows upcoming events for the next 48 hours.

### 🛠️ Requirements
- `CALENDAR_PATH` in `config.py` (defaults to `calendar.json`).

### Cloud Sync
**Path:** `src/skills/cloud_sync`  
# Cloud Sync

Provides automated backup and synchronization services for the ASURA project. It supports creating timestamped local backups and utilizes `rclone` for secure synchronization to various cloud storage providers like Google Drive and AWS S3.

### 🔧 Tools / Functions
- `sync_to_local_backup(dest)`: Create a local timestamped backup of the project directory, excluding environment and cache files.
- `sync_rclone(remote)`: Synchronize the project directory to a configured cloud remote using `rclone`.
- `get_sync_status()`: Retrieve a summary of existing local backups.

### 📝 Examples
- "Backup my project to the cloud" -> Executes `rclone sync` to the default remote.
- "Create a local backup" -> Creates a new timestamped folder in the `backups/` directory.

### 🛠️ Requirements
- `rclone` (optional, required for cloud synchronization)

### Codebase Investigator
**Path:** `src/skills/codebase_investigator`  
# Codebase Investigator

Provides ASURA with deep introspection into its own source code. It uses AST parsing and optimized search tools to map the project's architecture, trace dependencies, locate symbols, and detect common code quality issues or bugs.

### 🔧 Tools / Functions
- `grep(pattern, path, case_sensitive)`: Perform a regex-based text search across the codebase with file and line number output.
- `find_symbol(name)`: Locate all definitions and call sites of a specific function, class, or variable across the project.
- `trace_imports(filepath)`: Analyze a file's imports to show direct and transitive local and third-party dependencies.
- `architecture_report()`: Generate a comprehensive summary of the project's structure, including file counts, LoC, and module analysis.
- `detect_issues()`: Run static analysis to identify broad except clauses, hardcoded paths, bare prints, and async inconsistencies.
- `investigate(query)`: Unified entry point for dispatching investigation commands (grep, find, imports, etc.).

### 📝 Examples
- "Find all usages of handle_message" -> Returns a list of every file and line where the function is called.
- "Show me an architecture report" -> Displays a high-level overview of ASURA's core and skills.

### 🛠️ Requirements
- `ast`, `pathlib`
- `grep` (system-level, with fallback to pure-Python implementation)

### Conversation
**Path:** `src/skills/conversation`  
# Conversation Manager

The central hub for managing the dialogue between the user and the AI. It handles message history, context pruning, and dynamic system prompt generation.

### 🔧 Tools / Functions
- `add_message(message, role)`: Append a new turn to the conversation history.
- `get_recent_context(limit)`: Retrieve recent messages for LLM context injection.
- `search_history(query)`: Query past conversations using text search.
- `get_history_stats()`: Retrieve statistics on message counts and session duration.
- `get_system_prompt()`: Construct the master system prompt including dynamic personality and project rules.

### 📝 Examples
- "What did I ask you earlier?" -> Searches history for matching queries.

### 🛠️ Requirements
- `history.json` for conversation persistence.

### Dashboard
**Path:** `src/skills/dashboard`  
# Dashboard

The Sovereign Command Center for ASURA. It provides a real-time web interface to monitor system health, manage active skills, track ongoing tasks, and review audit logs. It includes a built-in JWT-based authentication layer and a robust template rendering engine.

### 🔧 Tools / Functions
- `start_dashboard()`: Initialize and start the multi-threaded HTTP dashboard server on the configured port.
- `render_template(template_name, context)`: Render HTML templates with support for recursive includes and context variable substitution.
- `_build_html()`: Internal helper to gather system state and render the main dashboard view.

### 📝 Examples
- "Open the dashboard" -> System starts the server on `http://localhost:DASHBOARD_PORT`.
- "Check system metrics via web" -> User can view CPU, RAM, and Disk usage in the browser.

### 🛠️ Requirements
- `http.server`, `http.cookies`
- `jwt` (configured in `core.auth` for secure access)
- `templates/` and `static/` directories must be present within the skill folder.

### Disk Usage
**Path:** `src/skills/disk_usage`  
# Disk Usage

Specialized skill for monitoring disk space consumption. It provides detailed statistics including total, used, and free space in gigabytes, as well as the usage percentage for any given filesystem path.

### 🔧 Tools / Functions
- `get_usage(path)`: Retrieve detailed disk usage statistics (total_gb, used_gb, free_gb, percent) for a specific path.

### 📝 Examples
- "Check disk space on /" -> "Disk usage for '/': {'total_gb': 494.38, 'used_gb': 320.1, ...}"

### 🛠️ Requirements
- `psutil` (recommended; falls back to `os.statvfs` on Unix systems)

### Doc Summarizer
**Path:** `src/skills/doc_summarizer`  
# Document Summarizer

Provides advanced summarization capabilities for various content types. It can condense raw text, fetch and summarize web pages, and extract content from local documents including PDFs, source code, and logs.

### 🔧 Tools / Functions
- `summarize_text(text, style, max_length)`: Summarize raw text into a specific style (bullets, paragraph, tldr, detailed).
- `summarize_url(url, style)`: Fetch content from a URL and summarize it using the specified style.
- `summarize_file(filepath, style)`: Summarize local files (txt, md, py, pdf, etc.).
- `_summarize_pdf(path, style)`: Internal helper to extract and summarize PDF content.

### 📝 Examples
- "Summarize https://example.com" -> Returns a bulleted summary of the webpage.
- "TL;DR this file" -> Returns a one-sentence summary of the provided file.

### 🛠️ Requirements
- `ollama` (configured in `config.py`)
- `PyPDF2` (optional, for PDF extraction)
- `pdftotext` (optional, system-level PDF tool)

### Dream Machine
**Path:** `src/skills/dream_machine`  
# Dream Machine

A background execution engine for long-term goals. It allows the AI to track progress on complex tasks that persist across sessions.

### 🔧 Tools / Functions
- `add_goal(title: str, description: str = "", priority: int = 5) -> dict`: Add a new long-term goal.
- `update_progress(goal_id: int, step: str, progress: int)`: Mark a step as done and update the percentage of completion.
- `get_active_goals() -> list`: Retrieve all goals currently in "active" status.
- `format_goals() -> str`: Generate a formatted summary with progress bars for TUI/Telegram display.

### 📝 Examples
- "Add a goal to learn Rust" -> Initializes a new goal in the dream machine.
- "Show my active dreams" -> Displays a list of goals with progress status.

### 🛠️ Requirements
- `goals.json` in the data directory for persistence.

### Email Manager
**Path:** `src/skills/email_manager`  
# Email Manager

Provides full email lifecycle management via standard SMTP and IMAP protocols. It allows ASURA to send reports and alerts to the master, monitor inboxes for incoming commands, and format email summaries for quick review.

### 🔧 Tools / Functions
- `send_email(to, subject, body, html)`: Send an email using SMTP (supports plain text and HTML content).
- `check_inbox(folder, limit)`: Connect to an IMAP server and retrieve the most recent emails from a specified folder.
- `format_inbox_summary(emails)`: Generate a human-readable Markdown summary of recent inbox activity.

### 📝 Examples
- "Email the audit log to master@example.com" -> Sends a plain-text email with the recent log content.
- "Check my inbox for updates" -> Displays a list of recent email subjects and senders.

### 🛠️ Requirements
- `smtplib`, `imaplib`
- Valid SMTP/IMAP credentials configured in `config.py` (EMAIL_ADDRESS, EMAIL_PASSWORD, etc.)

### Emotion
**Path:** `src/skills/emotion`  
# Emotion Engine

Analyzes user input for emotional signals and provides personality adaptations to make the AI more empathetic and responsive to user state.

### 🔧 Tools / Functions
- `detect_emotion(message: str) -> dict`: Analyzes tone, punctuation, and keywords to identify emotional state.
- `get_adaptive_prefix(emotion: str) -> str`: Returns a contextual prefix to modify the AI's response style.
- `should_suggest_break(message: str) -> bool`: Monitors for fatigue or late-night usage to suggest user rest.

### 📝 Examples
- "Detect emotion in 'This is so frustrating!'" -> Identifies 'frustrated' with high confidence.

### 🛠️ Requirements
- None (Pattern-based detection).

### Encryption
**Path:** `src/skills/encryption`  
# Encryption Skill

Provides secure storage and data protection by encrypting strings, JSON objects, and files. It uses Fernet encryption when the `cryptography` library is available, falling back to XOR obfuscation otherwise.

### 🔧 Tools / Functions
- `encrypt(data)`: Encrypts a string and returns base64-encoded ciphertext.
- `decrypt(ciphertext)`: Decrypts a base64-encoded ciphertext string.
- `encrypt_file(filepath)`: Encrypts a file in-place, renaming it with a `.enc` extension.
- `decrypt_file(filepath)`: Decrypts a `.enc` file in-place.
- `encrypt_json(data)`: Serializes a dictionary to JSON and encrypts it.
- `decrypt_json(ciphertext)`: Decrypts a ciphertext string and deserializes it back to a dictionary.

### 📝 Examples
- "Encrypt the message 'secret'" -> Returns an encrypted string.
- "Decrypt this file" -> Restores the original file from its `.enc` version.

### 🛠️ Requirements
- `cryptography` (optional, for Fernet encryption)
- Encryption key stored at `config.ENCRYPTION_KEY_PATH`

### Feature Tracker
**Path:** `src/skills/feature_tracker`  
# Feature Tracker

Manages the lifecycle and evolution of features within ASURA. It maintains a registry of capabilities and uses LLM-based reasoning to suggest upgrades or replacements for existing implementations based on efficiency and performance.

### 🔧 Tools / Functions
- `register_feature(name, category, capability, implementation, version)`: Register a new feature or skill capability.
- `check_for_upgrades()`: Analyze active features and check for better local/lightweight alternatives using LLM.
- `apply_replacement(old_name, new_name, reason)`: Mark a feature as deprecated/replaced and track the upgrade.
- `get_active_features()`: Retrieve a list of all currently active system features.
- `format_tracker_summary()`: Generate a formatted summary of active features and upgrade history.

### 📝 Examples
- "Register the new RAG skill" -> Adds 'rag_memory' to the feature registry.
- "Check for feature upgrades" -> LLM suggests replacing 'gTTS' with 'Kokoro' for better quality.

### 🛠️ Requirements
- `requests`
- `ollama` (configured in `config.py` for upgrade analysis)

### Feedback
**Path:** `src/skills/feedback`  
# Feedback

Enables ASURA to learn and adapt based on direct user interactions. It records user sentiment, identifies preferences through keyword analysis, and stores feedback in semantic memory to refine system prompts and behavioral patterns over time.

### 🔧 Tools / Functions
- `record_feedback(context, feedback, sentiment)`: Log user feedback along with its context and sentiment (positive, negative, or neutral).
- `auto_detect_sentiment(message)`: Analyze message content for emotional keywords to automatically determine sentiment.
- `get_learned_preferences()`: Extract a summary of user likes and dislikes from the feedback history.
- `get_feedback_stats()`: Generate a statistical breakdown of recorded feedback and sentiment distribution.

### 📝 Examples
- "That was a great explanation" -> Sentiment: Positive, Feedback: "That was a great explanation".
- "Stop using f-strings in this file" -> Sentiment: Negative, Feedback recorded for preference learning.

### 🛠️ Requirements
- None (Uses local `feedback.json` for persistence and RAG memory for recall)

### File Organizer
**Path:** `src/skills/file_organizer`  
# File Organizer

A set of utilities for maintaining project hygiene and analyzing file distribution. It identifies dead code (unused imports), locates large files for cleanup, detects duplicate files across the project, and provides detailed aggregate statistics.

### 🔧 Tools / Functions
- `find_dead_imports(directory)`: Scan Python files to identify potentially unused or excessive import statements.
- `find_large_files(min_kb)`: Locate files exceeding a specific size threshold to help manage project footprint.
- `find_duplicates()`: Identify files with identical or very similar names across different subdirectories.
- `get_project_stats()`: Generate a comprehensive summary of file counts, directory structure, total size, and hygiene issues.

### 📝 Examples
- "Show me my project stats" -> Displays total file count, Python file count, and project size.
- "Find large files in the project" -> Lists all files larger than 500KB.

### 🛠️ Requirements
- None (Uses standard Python `os` and `subprocess` libraries)

### Git Manager
**Path:** `src/skills/git_manager`  
# Git Manager

Integrates version control into the ASURA ecosystem. It enables the system to track its own evolution through automated commits, manage development branches, and provide detailed insights into code changes via status, diff, and log summaries.

### 🔧 Tools / Functions
- `init_repo()`: Initialize a new Git repository in the project root if one does not already exist.
- `status()`: Retrieve the current Git status in a concise porcelain format.
- `diff(staged)`: Generate a diff of current changes (optionally restricted to staged files).
- `auto_commit(message)`: Automatically stage all changes and create a commit with a timestamped message.
- `create_branch(name)`: Create and immediately switch to a new Git branch.
- `switch_branch(name)`: Switch between existing Git branches.
- `log(n)`: Display the last `n` commit messages in a condensed oneline format.
- `format_git_summary()`: Generate a formatted Markdown summary of the current branch, status, and recent history.

### 📝 Examples
- "Check my git status" -> Displays current branch and modified files.
- "Commit these changes" -> Automatically stages all files and creates a new commit.

### 🛠️ Requirements
- `git` (system-level installation)

### Graceful Mode
**Path:** `src/skills/graceful_mode`  
# Graceful Mode

Ensures ASURA remains functional during connectivity issues or service outages. It provides a local response cache for LLM queries and a task queue for operations that require online services, automatically processing them when the system detects restored connectivity.

### 🔧 Tools / Functions
- `cache_response(prompt_key, response)`: Store an LLM response locally for future offline hits.
- `get_cached(prompt_key)`: Retrieve a previously cached response based on the prompt.
- `queue_for_later(task, args)`: Queue a task (e.g., an API call) for execution when the system is back online.
- `process_offline_queue()`: Attempt to execute all queued tasks if services (like Ollama) are available.
- `get_offline_status()`: Get a summary of cached responses and queued tasks.

### 📝 Examples
- "Is the LLM down?" -> System provides cached responses for common queries.
- "Queue this email for later" -> Task is added to `offline_queue.json`.

### 🛠️ Requirements
- None (Uses local `response_cache.json` and `offline_queue.json` for persistence)

### Habit Tracker
**Path:** `src/skills/habit_tracker`  
# Habit Tracker

Tracks and analyzes user interaction patterns within the ASURA ecosystem. It identifies peak usage times and common actions to provide proactive suggestions and insights into system usage.

### 🔧 Tools / Functions
- `log_event(event_type, details)`: Log a usage event with timestamp, hour, and day metadata.
- `get_patterns()`: Analyze logged events to find peak hours, peak days, and top actions.
- `get_proactive_insight()`: Generate a text insight if the current time matches peak activity patterns.
- `format_habits()`: Generate a human-readable Markdown summary of habit patterns.

### 📝 Examples
- "Show my usage patterns" -> Displays peak hours and most frequent actions.
- "What's my most active day?" -> "Your peak day is Wednesday."

### 🛠️ Requirements
- None (Uses local `usage_patterns.json` for storage)

### Hardware Monitor
**Path:** `src/skills/hardware_monitor`  
# Hardware Monitor

Monitors system health and resource utilization. It provides real-time data on CPU usage, memory availability, disk space, and GPU performance, enabling ASURA to make resource-aware decisions and trigger proactive maintenance.

### 🔧 Tools / Functions
- `get_system_info()`: Gather comprehensive system information (CPU cores/usage, RAM, disk, GPU details).
- `get_resource_summary()`: Generate a human-readable Markdown summary of current system resources.
- `check_resources_ok(min_memory_gb, min_disk_gb)`: Verify if the system meets the minimum resource requirements for an operation.

### 📝 Examples
- "Check system health" -> Returns a summary of CPU, RAM, and Disk usage.
- "Is there enough space for an update?" -> Returns True/False based on disk availability.

### 🛠️ Requirements
- `psutil` (recommended for accurate resource tracking)
- `nvidia-smi` (optional, for NVIDIA GPU monitoring)
- `system_profiler` (on macOS for Apple Silicon GPU details)

### Health Alerter
**Path:** `src/skills/health_alerter`  
# Health Alerter

Background monitor that keeps an eye on CPU, Memory, and Disk usage. It proactively notifies the user and can trigger the Resource Governor for auto-remediation.

### 🔧 Tools / Functions
- `HealthAlerter().start()`: Launch the monitoring thread.
- `HealthAlerter().stop()`: Gracefully shut down the monitor.

### 📝 Examples
- "Start system health monitoring" -> Begins background checks every 2 minutes.

### 🛠️ Requirements
- `psutil` library.
- `ResourceGovernor` for active remediation support.

### Instagram Poster
**Path:** `src/skills/instagram_poster`  
# Instagram Poster

Automated Instagram publishing pipeline. It takes content, renders it into high-quality 1080x1080 images using HTML/CSS templates, uploads them to a CDN, and publishes them to an Instagram Business account.

### 🔧 Tools / Functions
- `upload_image(file_path)`: Upload a local image to Cloudinary and return the public URL.
- `create_media_container(image_url, caption)`: Create an Instagram media container for the given image and caption.
- `publish_media(creation_id)`: Finalize and publish the media container to the Instagram feed.
- `post_to_instagram(image_url, caption)`: Execute the full posting pipeline (create → publish).

### 📝 Examples
- "Post this image to Instagram with caption 'Hello World'" -> Post appears on the linked IG account.

### 🛠️ Requirements
- `cloudinary`, `requests`
- Instagram Business Account with Graph API Access Token
- Cloudinary API credentials (configured in `config.py`)

### Knowledge Graph
**Path:** `src/skills/knowledge_graph`  
# Knowledge Graph Skill

Manages a persistent knowledge base structured as a directed graph. It allows for the creation of nodes (representing entities or concepts) and edges (representing relationships), enabling complex context retrieval and reasoning support for the system.

### 🔧 Tools / Functions
- `add_node(name, category="concept", properties=None)`: Adds a new node to the knowledge graph with optional properties.
- `add_edge(from_node, to_node, relation, weight=1.0)`: Creates a directed relationship between two existing nodes.
- `query_node(name)`: Retrieves detailed information about a specific node, including its incoming and outgoing connections.
- `search_nodes(query, category=None)`: Searches for nodes by name or category matching the provided query.
- `get_graph_stats()`: Returns a formatted summary of the number of nodes, edges, and category distributions.
- `build_context_from_topic(topic)`: Generates a text-based context string from the graph related to a specific topic for LLM use.

### 📝 Examples
- "Add a concept node for 'Machine Learning'" -> Creates a new node in the graph.
- "Link 'Python' to 'Programming Language' with relation 'is a'" -> Creates an edge between the two nodes.
- "Show stats for the knowledge graph" -> Displays the current count of nodes and edges.

### 🛠️ Requirements
- Persistent storage at `config.KNOWLEDGE_GRAPH_PATH`

### Log Cleanup
**Path:** `src/skills/log_cleanup`  
# Log Cleanup

Keep the system's audit trail and application logs healthy by pruning old entries and preventing massive file growth.

### 🔧 Tools / Functions
- `LogCleanupSkill().run()`: Prunes `audit.txt`, `log.txt`, and `audit.jsonl` based on retention settings.

### 📝 Examples
- "Clean up my logs" -> Removes log entries older than the configured retention period (default 7 days).

### 🛠️ Requirements
- `LOG_RETENTION_DAYS` in `config.py`.
- `psutil` for emergency truncation of large log files.

### Logger
**Path:** `src/skills/logger`  
# Logger Skill

Provides a dual logging system that maintains both human-readable text logs and structured JSONL files. It supports thread-safe concurrent writes to ensure data integrity during parallel operations and allows for programmatic querying of system events.

### 🔧 Tools / Functions
- `log_audit(step, message, **extra)`: Logs security-sensitive events to `audit.txt` and `audit.jsonl` without console output.
- `log_app(message, **extra)`: Logs general application events to `log.txt`, `audit.jsonl`, and prints them to the console.
- `query_logs(step=None, since=None, limit=50)`: Retrieves a list of structured log entries filtered by step, timestamp, or limit.

### 📝 Examples
- "Log a successful login event" -> Records the event in the audit logs.
- "Show me the last 10 application logs" -> Queries the log files and returns the recent entries.

### 🛠️ Requirements
- `structlog` library
- Write permissions for log paths defined in `config`

### Memory
**Path:** `src/skills/memory`  
# Memory Skill

Provides a sophisticated, multi-layered persistent memory system for the AI. It uses FAISS vector stores for semantic retrieval (RAG), a JSONL-based episodic store for timestamped events, and a procedural store for learning successful action chains over time.

### 🔧 Tools / Functions
- `store_memory(text, metadata=None)`: Stores a text chunk in the semantic memory using FAISS embeddings for future recall.
- `recall(query, top_k=5)`: Performs a semantic search across stored memories and returns the most relevant matches.
- `store_episode(event, context=None, category="general", importance=0.5)`: Records a timestamped event in the episodic memory.
- `recall_episodes(query=None, category=None, limit=20)`: Retrieves past events based on keyword, category, or time filters.
- `store_procedure(trigger, action_chain, outcome, success, context=None)`: Records a sequence of actions taken in response to a trigger for future optimization.
- `recall_procedures(situation, min_score=0.3, limit=5)`: Suggests previously successful action chains for a given situation.
- `get_all_memories_summary()`: Generates a high-level summary of all memory layers for system context.

### 📝 Examples
- "Remember that the user's favorite color is blue" -> Stores the fact in semantic memory.
- "What did we do yesterday?" -> Recalls events from episodic memory.
- "How did we fix the last dependency error?" -> Retrieves a successful procedure from procedural memory.

### 🛠️ Requirements
- `faiss-cpu` or `faiss-gpu` library
- `sentence-transformers` or access to an embedding API (e.g., Ollama)
- Persistent storage directory at `config.MEMORY_STORE_DIR`

### Multi Model
**Path:** `src/skills/multi_model`  
# Multi-Model Manager

Orchestrates the use of multiple LLM models based on the task at hand (e.g., using a large model for reasoning and a small one for planning).

### 🔧 Tools / Functions
- `get_model(task_type)`: Determine the assigned model for a specific task (chat, vision, coding).
- `generate(prompt, task_type)`: Execute a generation request using the appropriate model.
- `list_available_models()`: Check which models are currently reachable on the provider.
- `format_models_summary()`: Display a map of task-to-model assignments and their availability.

### 📝 Examples
- "Switch to a faster model" -> Adjusts routing via ModelManager.
- "Show configured models" -> Displays the model registry status.

### 🛠️ Requirements
- `model_manager` core module.
- Active LLM provider (Ollama, Groq, or SGLang).

### Nl Commands
**Path:** `src/skills/nl_commands`  
# Natural Language Commands

A parser that maps human-intent messages (e.g., "check my emails") to specific internal skill function calls. It uses a registry of regex patterns to detect intents and extract relevant arguments.

### 🔧 Tools / Functions
- `parse_intent(message)`: Analyzes a string to find a matching skill and function. Returns a dictionary with match status, skill name, and function name.
- `extract_args(message, intent)`: Processes the raw message to extract arguments for the identified function, stripping common filler words.

### 📝 Examples
- "Check my emails" -> `{"matched": True, "skill": "email_manager", "function": "check_inbox", ...}`
- "Add a todo to buy milk" -> `{"matched": True, "skill": "todo_manager", "function": "add_todo", "needs_args": True, ...}`

### 🛠️ Requirements
- `re` module (standard library)

### Notification Router
**Path:** `src/skills/notification_router`  
# Notification Router

Routes system alerts, reminders, and notifications to the correct channel based on their importance and category.

### 🔧 Tools / Functions
- `route_notification(message, category)`: Dispatches a message to Telegram, Email, or other configured sinks.
- `set_route(category, channels)`: Dynamically update where certain categories of alerts are sent.
- `format_routes()`: Show the current routing table.

### 📝 Examples
- "Notify me on Telegram if the build fails" -> Routes critical notifications to the bot.

### 🛠️ Requirements
- `telegram_bot` and/or `email_manager` skills enabled.

### Scheduler
**Path:** `src/skills/scheduler`  
# Scheduler Skill

### Shell Executor
**Path:** `src/skills/shell_executor`  
# Shell Executor Skill

## Safety Model
- **Inside project dir** → execute freely, log everything
- **Outside project dir** → BLOCK, ask master via Telegram
- **Destructive commands** (rm, sudo, kill, etc.) → BLOCK, ask master

## Capabilities
- `execute(cmd)` — Run shell command with safety analysis
- `execute_python(code)` — Run Python snippet
- `list_project_files(pattern)` — Find files by glob
- `read_file(path)` — Read file content
- `write_file(path, content)` — Write/create file
- `start_interactive_session(session_id, cmd)` — Start a long-running process
- `send_session_input(session_id, text)` — Send text to a process's stdin
- `get_session_status(session_id)` — Get output and status of a session

### Skill Hotreload
**Path:** `src/skills/skill_hotreload`  
# Skill Hot-Reload

Hot-reload individual or all skills dynamically to apply code changes without a full system restart.

### 🔧 Tools / Functions
- `reload_skill(skill_name: str) -> dict`: Hot-reload a specific skill module by name.
- `reload_all_skills() -> dict`: Discover and reload all available skill modules.

### 📝 Examples
- "Reload the weather skill" -> Hot-reloads `skills.weather`.
- "Apply changes to all skills" -> Triggers a full reload of the skill registry.

### 🛠️ Requirements
- Skill modules must be located in the `skills/` package.

### Smart Deps
**Path:** `src/skills/smart_deps`  
# Smart Dependency Skill

Provides automated dependency management by monitoring the current environment for outdated Python packages and facilitating their upgrade. It ensures the system remains secure and up-to-date with the latest library versions.

### 🔧 Tools / Functions
- `check_outdated()`: Uses `pip` to list all currently installed packages that have newer versions available.
- `upgrade_package(name)`: Upgrades a specified package to its latest version using `pip install --upgrade`.
- `format_deps_report()`: Generates a human-readable summary report of all outdated dependencies.

### 📝 Examples
- "Are any of my packages outdated?" -> Returns a report of outdated dependencies.
- "Upgrade the 'requests' library" -> Upgrades the specified library and logs the result.

### 🛠️ Requirements
- `pip` executable available in the system path.
- Write permissions for the environment's site-packages.

### Sub Agent Manager
**Path:** `src/skills/sub_agent_manager`  
# Sub-Agent Manager

Lifecycle management for specialized sub-agents. Allows ASURA to delegate tasks to personas with isolated memory and focused roles.

### 🔧 Tools / Functions
- `spawn_subagent(name, role, persistent)`: Create a new specialized agent.
- `run_subagent_task(name, task)`: Direct a sub-agent to perform a specific action.
- `list_subagents()`: Show all active and dormant sub-agents.
- `inspect_subagent_memory(name)`: View the internal memory vault of an agent.
- `kill_subagent(name)`: Terminate an agent and optionally purge its memory.

### 📝 Examples
- "Spawn a security auditor agent" -> Creates a new persona for specialized tasks.
- "Ask the auditor to check this script" -> Executes task via the sub-agent.

### 🛠️ Requirements
- `SubAgentMemory` core module.

### System Health
**Path:** `src/skills/system_health`  
# System Health

Provides a high-level overview of the system's vital signs, including CPU load, memory utilization, disk space, and system uptime.

### 🔧 Tools / Functions
- `run() -> str`: Generates and returns a formatted system health report.

### 📝 Examples
- "How is the system doing?" -> "CPU Usage: 15.4% | Memory: 45.2% used (7.2 GB / 16.0 GB) | Disk: 60.1% used | Uptime: 2d 5h"

### 🛠️ Requirements
- `psutil` library.

### Telegram Bot
**Path:** `src/skills/telegram_bot`  
# Telegram Bot

A comprehensive Telegram interface for managing the ASURA system. It supports command-based interaction, role-based access control, automated Instagram posting workflows, and proactive notifications.

### 🔧 Tools / Functions
- `start_bot()`: Initializes and starts the Telegram bot polling service.
- `notify_master(message)`: Sends a thread-safe notification message to the configured admin chat.
- `send_file_to_master(file_path, caption="")`: Uploads and sends a file (image, document, etc.) to the admin chat.

### 📝 Examples
- "Start the bot" -> [Bot starts polling]
- `notify_master("System update complete!")` -> [Message sent to admin]

### 🛠️ Requirements
- `python-telegram-bot` library
- `TELEGRAM_BOT_TOKEN` in `.env`
- `TELEGRAM_ADMIN_CHAT_ID` in `.env`

### Time Tracker
**Path:** `src/skills/time_tracker`  
# Time Tracker

Keep track of how much time you spend on different tasks. Logs sessions and generates reports to help monitor productivity.

### 🔧 Tools / Functions
- `start_timer(task: str)`: Start a new timing session for a task.
- `stop_timer(task: str)`: End the session and persist the elapsed time.
- `get_weekly_report()`: Generate a summary of time spent on tasks over the last 7 days.

### 📝 Examples
- "Start timer for 'Refactoring'" -> Begins tracking.
- "Stop timer" -> Saves session and displays duration.

### 🛠️ Requirements
- `time_logs.json` for persistent storage.

### Todo Manager
**Path:** `src/skills/todo_manager`  
# TODO Manager

A task tracking system designed for both users and the AI's self-improvement cycle. Supports priorities, categories, and completion tracking.

### 🔧 Tools / Functions
- `add_todo(description, source, priority, category)`: Create a new task.
- `complete_todo(todo_id, result)`: Mark a task as done with a summary of the outcome.
- `get_open_todos(priority, category)`: List tasks based on filters.
- `get_next_todo()`: Retrieve the highest priority task for the AI to work on.
- `format_todos_summary()`: Get a formatted status report of all tasks.

### 📝 Examples
- "Add a TODO to fix the login bug" -> Creates a high-priority bugfix task.
- "Show my tasks" -> Displays the current TODO list.

### 🛠️ Requirements
- `state_manager` for persistent task storage.

### Visual
**Path:** `src/skills/visual`  
# Visual Intelligence

Multimodal vision capabilities optimized for **Qwen3.5 Vision (0.8B and 35B)**. Features direct routing to vision-capable LLMs for zero overhead.

### 🔧 Tools / Functions
- `analyze_image(image_path, question, heavy)`: Multi-purpose visual understanding and captioning.
- `ocr_image(image_path)`: Fast text extraction from any visual source.
- `describe_screenshot(image_path)`: Detailed UI element mapping and application identification.
- `take_screenshot(output_path)`: Capture the current system screen (macOS native).
- `debug_ui_screenshot(image_path, bug_description)`: Specialized 35B analysis for UI bug detection and CSS/HTML fix recommendations.

### 📝 Examples
- "What's in this screenshot?" -> Detailed breakdown of UI elements and content.
- "Find the bug in this UI" -> Analysis of visual glitches with suggested fixes.

### 🛠️ Requirements
- `screencapture` utility (macOS).
- Multimodal LLM (e.g., Qwen2-VL or Qwen2.5-VL).

### Voice
**Path:** `src/skills/voice`  
# Voice Skill

Provides multimodal capabilities for processing audio inputs and generating spoken responses. Supports macOS, Windows, and Linux.

### 🔧 Tools / Functions
- `transcribe_audio(audio_path: str) -> str`: Convert audio files to text using Whisper (local or via Ollama).
- `text_to_speech(text: str, output_path: str = None) -> str`: Convert text to audio using the best available system engine (say, PowerShell, espeak).

### 📝 Examples
- "Transcribe this voice note" -> Processes audio file and returns text.
- "Say 'System online'" -> Generates and plays/saves an audio file of the speech.

### 🛠️ Requirements
- `ffmpeg` for audio format conversion.
- `whisper` model (local or Ollama).
- `espeak` or `pico2wave` (Linux only).

### Voice Chat
**Path:** `src/skills/voice_chat`  
# Voice Chat

Enables real-time, hands-free voice interaction with ASURA. It handles the full pipeline from audio recording and speech-to-text (STT) to LLM processing and text-to-speech (TTS) synthesis.

### 🔧 Tools / Functions
- `voice_chat_loop()`: Interactive voice chat loop with VAD (Voice Activity Detection), STT, LLM, and streaming TTS.
- `voice_chat_single(audio_bytes)`: Process a single voice turn for external integrations (e.g., Telegram).

### 📝 Examples
- "Start voice chat" -> Activates the microphone and waits for speech.
- "Process this audio message" -> Returns the synthesized AI response as audio bytes.

### 🛠️ Requirements
- `sounddevice`, `numpy`, `soundfile`
- Remote voice server running `faster-whisper` and `Kokoro` (configured via `VOICE_SERVER_URL`)

### Web Intelligence
**Path:** `src/skills/web_intelligence`  
# Web Intelligence

Provides the AI with real-time access to the internet. Uses a tiered fallback system (DuckDuckGo HTML -> SearXNG -> DDG API) for maximum reliability.

### 🔧 Tools / Functions
- `web_search(query: str, max_results: int)`: Perform a search across multiple engines.
- `scrape_url(url: str)`: Extract clean, readable text from any webpage (removing scripts/styles).
- `research_topic(topic: str)`: High-level tool that searches and scrapes top results for deep analysis.

### 📝 Examples
- "Search for the latest NVIDIA stock price" -> Returns search snippets.
- "Research the Model Context Protocol" -> Aggregates content from multiple web sources.

### 🛠️ Requirements
- `beautifulsoup4` for HTML parsing.
- `duckduckgo_search` (optional fallback).

### Webhook Handler
**Path:** `src/skills/webhook_handler`  
# Webhook Handler

Allows ASURA to receive and respond to external events via HTTP webhooks. It supports GitHub-style HMAC-SHA256 signature verification, processes incoming event payloads (like push, issues, or PRs), and notifies the master of relevant activity.

### 🔧 Tools / Functions
- `verify_signature(payload, signature, secret)`: Verify the authenticity of an incoming webhook using HMAC-SHA256.
- `process_webhook(event_type, payload)`: Parse incoming event data and trigger internal notifications or actions.
- `get_webhook_log(limit)`: Retrieve a history of recently received webhook events.
- `start_webhook_server()`: Initialize and start a background HTTP server to listen for incoming webhooks on the configured port.

### 📝 Examples
- "Listen for GitHub pushes" -> Starts the server and begins logging repository activity.
- "Show me recent webhooks" -> Displays a list of the last 10 received events.

### 🛠️ Requirements
- None (Uses standard `http.server` and `hmac` libraries)
- Configured `WEBHOOK_PORT` and `WEBHOOK_SECRET` in `config.py`
