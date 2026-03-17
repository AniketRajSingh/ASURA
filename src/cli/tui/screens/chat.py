from __future__ import annotations
from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Input, Static, Label, Markdown
from textual.binding import Binding
from textual.message import Message
import json
import re
import os
import asyncio
from rich.syntax import Syntax
from textual.suggester import SuggestFromList
from cli.tui.widgets.action_box import ActionBox

class ChatScreen(Static):
    """Main Chat interface for ASURA."""
    SUGGESTIONS = [
        "/agents", "/compress", "/debug", "/diff", "/export", "/history", 
        "/help", "/init", "/model", "/plan", "/processes", "/remind", 
        "/resume", "/rewind", "/sandbox", "/sessions", "/skills", 
        "/stats", "/status", "/theme", "/vault", "/evolve", "/zero",
        "🚀", "🧠", "🛠️", "🎯", "⚡", "🔒"
    ]

    BINDINGS = [
        Binding("escape", "handle_escape", "Stop/Clear (Esc)", show=True, priority=True),
        Binding("ctrl+s", "toggle_stats", "Stats", show=True),
        Binding("ctrl+x", "open_editor", "Editor (Ctrl+X)", show=True),
        Binding("ctrl+r", "search_history", "Search (Ctrl+R)", show=True),
        Binding("shift+tab", "cycle_mode", "Cycle Mode", show=True),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_escape_time = 0
        self._modes = ["default", "reasoning", "coding", "fast"]
        self._current_mode_idx = 0

    def action_cycle_mode(self) -> None:
        """Cycle through AI reasoning modes."""
        self._current_mode_idx = (self._current_mode_idx + 1) % len(self._modes)
        mode = self._modes[self._current_mode_idx]
        self.app.notify(f"Mode switched to: {mode.upper()}")
        self.app.sub_title = f"ASURA — {mode.upper()} Mode"

    @on(Input.Changed)
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle '@' file selection trigger."""
        if event.value.endswith("@"):
            self.app.notify("File selection coming soon (Phase 2)", severity="information")

    async def action_handle_escape(self) -> None:
        """Handle Esc key: Single = Stop, Double = Clear."""
        now = asyncio.get_event_loop().time()
        if now - self._last_escape_time < 0.5:
            # Double tap detected: Clear screen
            self.query_one("#message-list").query("*").remove()
            self.app.notify("Context cleared")
            self._last_escape_time = 0
        else:
            # Single tap: Stop generation
            from core.gateway import handle_command
            await handle_command(f"tui_{os.getenv('USER', 'local')}", "/cancel", channel="cli")
            self.app.sub_title = "🛑 Generation stopped"
            self._last_escape_time = now
        
        self.query_one("#chat-input").focus()

    async def action_open_editor(self) -> None:
        """Open current input in external editor."""
        input_widget = self.query_one("#chat-input")
        initial_text = input_widget.value
        
        # Simple temp file strategy
        import tempfile
        import subprocess
        
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w+", delete=False) as tf:
            tf.write(initial_text)
            temp_path = tf.name
            
        editor = os.environ.get("EDITOR", "nano")
        try:
            # Suspend Textual UI to let editor take over terminal
            with self.app.suspend():
                subprocess.run([editor, temp_path])
            
            with open(temp_path, "r") as f:
                new_text = f.read().strip()
            
            input_widget.value = new_text
            input_widget.focus()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def action_search_history(self) -> None:
        self.app.notify("Reverse-search history coming soon", severity="information")

    def compose(self) -> ComposeResult:
        with Vertical(id="chat-container"):
            yield Vertical(id="message-list")
            with Horizontal(id="input-area"):
                yield Label("🧠 You: ", id="prompt-label")
                yield Input(
                    placeholder="Type your message here...", 
                    id="chat-input",
                    suggester=SuggestFromList(self.SUGGESTIONS)
                )

    async def on_chat_screen_message_request(self, event: MessageRequest) -> None:
        """Handle a message request from the UI."""
        from core.gateway import handle_message, handle_command

        # Check for /resume or /rename first
        if event.text.startswith("/"):
            res = await handle_command(f"tui_{os.getenv('USER', 'local')}", event.text, channel="cli")
            if res:
                self.add_message("assistant", res)
            if "/resume" in event.text or "/clear" in event.text:
                # Reload screen history
                self.query_one("#message-list").query("*").remove()
                self.on_mount()
            return

        session_id = f"tui_{os.getenv('USER', 'local')}"
        
        # Create a placeholder for the assistant response
        assistant_widget = Markdown("", classes="assistant-message")
        self.query_one("#message-list").mount(assistant_widget)
        self.query_one("#message-list").scroll_end()

        full_response = ""
        last_update_time = 0
        UPDATE_INTERVAL = 0.15 # 150ms buffer for rendering smoothness
        
        try:
            response_stream = await handle_message(
                user_id=session_id, message=event.text, channel="cli", stream=True
            )
            
            async for chunk in response_stream:
                # 1. Handle Metadata Chunks (Performance/Cost metrics)
                if "[METADATA]" in chunk:
                    try:
                        meta_str = chunk.replace("[METADATA]", "").replace("[/METADATA]", "")
                        meta = json.loads(meta_str)
                        if meta.get("type") == "metrics":
                            self.update_footer_metrics(meta)
                    except: 
                        pass
                    continue

                # 2. Extract and show Actions in dedicated Boxes
                if "[ACTION]" in chunk:
                    action_match = re.search(r"\[ACTION\]\s*(.*?):\s*(.*?)\s*\[/ACTION\]", chunk, re.DOTALL)
                    if action_match:
                        act_name = action_match.group(1).strip()
                        act_input = action_match.group(2).strip()
                        self.query_one("#message-list").mount(ActionBox(act_name, act_input))
                        self.app.sub_title = f"Acting: {act_name}..."
                    continue
                
                if "[OBSERVATION]" in chunk:
                    self.app.sub_title = "Processing observation..."
                    continue

                # 3. Clean and append to full response
                # Only strip EXPLICIT tags, don't use greedy patterns that might hit Markdown tables
                clean_chunk = chunk
                clean_chunk = clean_chunk.replace("[ACTION]", "").replace("[/ACTION]", "")
                clean_chunk = clean_chunk.replace("[OBSERVATION]", "").replace("[/OBSERVATION]", "")
                
                # If there's content left, buffer it
                full_response += clean_chunk
                
                # 4. Buffered Rendering (Rate-limited UI updates)
                now = asyncio.get_event_loop().time()
                if now - last_update_time > UPDATE_INTERVAL:
                    # Final safety: hide any trailing partial tags from display
                    display_text = full_response
                    for tag in ["[ACTION", "[/ACTION", "[OBSERVATION", "[/OBSERVATION"]:
                        if tag in display_text:
                            display_text = display_text.split(tag)[0]
                    
                    await assistant_widget.update(display_text)
                    self.query_one("#message-list").scroll_end()
                    last_update_time = now
            
            # Final 100% update to ensure nothing is missed after stream ends
            await assistant_widget.update(full_response)
            self.query_one("#message-list").scroll_end()
            self.app.sub_title = "ASURA — Autonomous AI"
                
        except Exception as e:
            await assistant_widget.update(f"**Error:** {str(e)}")

    def update_footer_metrics(self, meta: dict) -> None:
        """Forward metrics to the main app footer."""
        app = self.app
        if meta["provider"] == "ollama":
            eval_count = meta.get("eval_count", 0)
            eval_duration = meta.get("eval_duration", 1)
            tps = (eval_count / eval_duration) * 1e9 if eval_duration > 0 else 0
            app.update_metrics(f" Tokens: {eval_count} | TPS: {tps:.1f} ")
        elif meta["provider"] == "groq":
            prompt = meta.get("prompt_tokens", 0)
            comp = meta.get("completion_tokens", 0)
            # Rough cost for 70B: $0.79 per 1M output
            cost = (comp / 1_000_000) * 0.79
            app.update_metrics(f" Tokens: {prompt}+{comp} | Cost: ${cost:.4f} ")

    def on_mount(self) -> None:
        """Load session history on startup."""
        from core.gateway import get_or_create_session
        
        session = get_or_create_session(f"tui_{os.getenv('USER', 'local')}", "cli")
        for msg in session.history[-20:]:  # Load last 20 messages
            self.add_message(msg["role"], msg["content"])
        
        self.query_one("#chat-input").focus()

    @on(Input.Submitted)
    async def on_submit(self, event: Input.Submitted) -> None:
        message = event.value.strip()
        if not message:
            return
        
        # 1. Intercept '!' Shell shortcut
        if message.startswith("!"):
            shell_cmd = message[1:].strip()
            if shell_cmd:
                # Add command to UI
                self.add_message("user", message)
                event.input.value = ""
                # Convert to /run command for the gateway
                self.post_message(self.MessageRequest(f"/run {shell_cmd}"))
                return

        # 2. Intercept /theme commands
        if message.lower().startswith("/theme "):
            parts = message.lower().split()
            if len(parts) > 1:
                target = parts[1]
                if target == "light":
                    self.app.dark = False
                    self.add_message("system", "Theme switched to light mode")
                elif target == "dark":
                    self.app.dark = True
                    self.add_message("system", "Theme switched to dark mode")
            event.input.value = "" # Clear input after theme command
            return

        # Add user message to list
        self.add_message("user", message)
        event.input.value = ""
        
        # Trigger ASURA processing
        self.post_message(self.MessageRequest(message))

    def add_message(self, role: str, content: str) -> None:
        # Ultimate Null Guard
        if content is None:
            return
            
        content = str(content) # Ensure it's a string
        
        message_list = self.query_one("#message-list")
        if role == "user":
            message_list.mount(Label(f"🧠 You: {content}", classes="user-message"))
        else:
            # Check for diffs in the content
            if "```diff" in content:
                # Basic diff highlighting using Rich Syntax
                parts = content.split("```diff")
                for i, part in enumerate(parts):
                    if i == 0:
                        if part.strip(): message_list.mount(Markdown(part, classes="assistant-message"))
                    else:
                        try:
                            diff_content, remaining = part.split("```", 1)
                            # Adaptive syntax theme based on parent class
                            syntax_theme = "github-light" if self.app.has_class("light-mode") else "github-dark"
                            message_list.mount(Static(Syntax(diff_content, "diff", theme=syntax_theme), classes="assistant-message"))
                            if remaining.strip(): message_list.mount(Markdown(remaining, classes="assistant-message"))
                        except ValueError:
                            # If no closing ```, just treat as Markdown
                            message_list.mount(Markdown(f"```diff{part}", classes="assistant-message"))
            else:
                message_list.mount(Markdown(content, classes="assistant-message"))
        message_list.scroll_end()

    class MessageRequest(Message):
        """Custom message to request a response from ASURA."""
        def __init__(self, text: str) -> None:
            self.text = text
            super().__init__()
