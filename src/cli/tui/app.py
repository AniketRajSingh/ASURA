from __future__ import annotations
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Footer, TabbedContent, TabPane
from cli.tui.screens.chat import ChatScreen
from cli.tui.screens.system import SystemScreen

from textual.theme import Theme

ASURA_DARK = Theme(
    name="asura-dark",
    primary="#58a6ff",
    secondary="#79c0ff",
    accent="#238636",
    foreground="#c9d1d9",
    background="#0d1117",
    surface="#161b22",
    panel="#161b22",
    success="#238636",
    warning="#ffd60a",
    error="#f85149",
)

ASURA_LIGHT = Theme(
    name="asura-light",
    primary="#0366d6",
    secondary="#005cc5",
    accent="#28a745",
    foreground="#1a1a1a",
    background="#fdfdfd",
    surface="#f6f8fa",
    panel="#f6f8fa",
    success="#28a745",
    warning="#f9c513",
    error="#d73a49",
)

class AsuraApp(App):
    """ASURA Terminal User Interface."""
    
    TITLE = "ASURA — Autonomous AI"
    SUB_TITLE = "v4.1.0"
    CSS_PATH = "styles.tcss"
    
    # Register native themes
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_theme(ASURA_DARK)
        self.register_theme(ASURA_LIGHT)
        # Default to dark
        self.theme = "asura-dark"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "cycle_theme", "Toggle Theme"),
        ("escape", "cancel_generation", "Stop (Esc)"),
        ("ctrl+c", "switch_tab('chat')", "Chat"),
        ("ctrl+s", "switch_tab('system')", "System Stats"),
    ]

    def action_cycle_theme(self) -> None:
        """Cycle between Asura Light and Dark themes."""
        if self.theme == "asura-dark":
            self.theme = "asura-light"
        else:
            self.theme = "asura-dark"

    def compose(self) -> ComposeResult:
        from textual.widgets import Label
        yield Header()
        with TabbedContent(id="tabs"):
            with TabPane("Chat", id="chat"):
                yield ChatScreen()
            with TabPane("System Stats", id="system"):
                yield SystemScreen()
        yield Footer()
        with Horizontal(id="custom-footer"):
            yield Label(" ASURA v4.1.0 ", id="asura-status")
            yield Label(" Tokens: 0 | TPS: 0.0 ", id="token-stats")

    def action_cancel_generation(self) -> None:
        """Interrupt ongoing AI generation."""
        from skills.ai_content.generator import cancel_current_task
        cancel_current_task()
        self.notify("Generation stopped", severity="warning")

    def update_metrics(self, text: str) -> None:
        """Update metrics in the footer."""
        try:
            self.query_one("#token-stats", Label).update(text)
        except:
            pass

    def action_switch_tab(self, tab: str) -> None:
        self.query_one(TabbedContent).active = tab

if __name__ == "__main__":
    app = AsuraApp()
    app.run()
