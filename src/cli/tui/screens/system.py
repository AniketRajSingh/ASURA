from __future__ import annotations
from textual.app import ComposeResult
from textual.widgets import Static, Label, Digits
from textual.containers import Vertical, Grid
import psutil
import asyncio

class SystemScreen(Static):
    """System Monitoring interface for ASURA."""
    
    def compose(self) -> ComposeResult:
        with Vertical(id="system-container"):
            yield Label("[bold magenta]System Monitor[/bold magenta]", id="system-title")
            with Grid(id="stats-grid"):
                with Vertical(classes="stat-card"):
                    yield Label("CPU Usage")
                    yield Digits("0%", id="cpu-digits")
                with Vertical(classes="stat-card"):
                    yield Label("Memory Usage")
                    yield Digits("0%", id="mem-digits")
                with Vertical(classes="stat-card"):
                    yield Label("Context Tokens")
                    yield Digits("0", id="token-digits")

    def on_mount(self) -> None:
        self.set_interval(2.0, self.update_stats)

    def update_stats(self) -> None:
        import os
        from core.gateway import get_or_create_session
        from core.context_manager import estimate_tokens
        
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        self.query_one("#cpu-digits").update(f"{cpu}%")
        self.query_one("#mem-digits").update(f"{mem}%")
        
        # Update tokens
        session_id = f"tui_{os.getenv('USER', 'local')}"
        session = get_or_create_session(session_id)
        tokens = estimate_tokens(session.history)
        self.query_one("#token-digits").update(str(tokens))
