from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Vertical, Horizontal
from rich.panel import Panel
from rich.text import Text

class ActionBox(Static):
    """
    A specialized widget for displaying AI actions (tool calls) 
    in a distinct, boxed format within the TUI.
    """
    
    DEFAULT_CSS = """
    ActionBox {
        margin: 1 0;
        padding: 0;
        height: auto;
        border: none;
    }
    
    .action-header {
        background: $primary 20%;
        color: $primary;
        text-style: bold;
        padding: 0 1;
        width: 100%;
    }
    
    .action-body {
        border-left: solid $primary;
        padding: 0 2;
        color: $foreground 70%;
        background: $surface;
    }
    """

    def __init__(self, action_name: str, action_input: str, **kwargs):
        super().__init__(**kwargs)
        self.action_name = action_name
        self.action_input = action_input

    def compose(self) -> ComposeResult:
        yield Label(f" 🛠️  EXECUTING: {self.action_name.upper()} ", classes="action-header")
        yield Label(f"{self.action_input}", classes="action-body")
