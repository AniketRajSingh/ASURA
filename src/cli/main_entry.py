import re
import os
import sys
import time
import argparse
import asyncio
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.live import Live
from rich.text import Text
from rich.markup import escape
from core.gateway import handle_message, handle_command
from core.formatter import format_message
from cli.agent_selector import AgentSelector
from settings import settings
from skills.logger import log_audit, log_app

# Global Rich Console for cross-platform ANSI handling
console = Console()

def print_asura_banner():
    """Print ASURA CLI banner with premium Rich styling."""
    banner_text = Text.assemble(
        ("ASURA", "bold cyan"),
        (" — Unified Command Interface\n", "white"),
        ("Sovereign AI Agentic System", "bold magenta")
    )
    
    commands_table = Table.grid(padding=(0, 2))
    commands_table.add_column(style="bold yellow")
    commands_table.add_column(style="dim")
    
    commands_table.add_row("/help", "List all available gateway & AI commands")
    commands_table.add_row("/theme", "Toggle UI appearance (Light/Dark)")
    commands_table.add_row("/compress", "Agentic context compaction")
    commands_table.add_row("/evolve", "Initiate system self-improvement cycle")
    commands_table.add_row("/stats", "View session & performance analytics")
    commands_table.add_row("/history", "Display conversation history")
    commands_table.add_row("/clear", "Reset current meeting context")
    commands_table.add_row("/exit", "Terminate session")

    console.print(Panel(
        banner_text,
        subtitle="v4.1.0-PREMIUM",
        expand=False,
        border_style="cyan"
    ))
    console.print("\n[bold yellow]Commands:[/bold yellow]")
    console.print(commands_table)
    console.print()

async def run_standalone_task(prompt: str, mode: str = "task", agent: str = None) -> int:
    """Run a single task through the gateway."""
    session_id = f"cli_{os.getenv('USER', 'local')}_{int(time.time())}"
    
    exec_prompt = prompt
    if agent and agent != "auto":
        exec_prompt = f"[AGENT:{agent.upper()}] {prompt}"
        console.print(f"⚡ [yellow]Using specified agent:[/yellow] [bold cyan]{agent}[/bold cyan]")

    from rich.markdown import Markdown
    from rich.status import Status
    
    try:
        console.print(f"\n[bold green]🤖 ASURA > [/bold green][dim]Processing: {prompt[:50]}...[/dim]")
        
        # Start a status spinner
        with Status("[bold cyan]ASURA is thinking...", console=console) as status:
            response_stream = await handle_message(
                user_id=session_id, message=exec_prompt, channel="cli", stream=True
            )

            full_reply = ""
            from rich.markdown import Markdown
            
            # Stream the response with a Live display for better formatting
            with Live(Markdown(""), console=console, refresh_per_second=8, vertical_overflow="visible") as live:
                async for chunk in response_stream:
                    if "[METADATA]" in chunk:
                        continue
                        
                    # Handle Action/Observation status updates
                    if "[ACTION]" in chunk:
                        action_match = re.search(r"\[ACTION\]\s*(.*?)\s*\[/ACTION\]", chunk, re.DOTALL)
                        if action_match:
                            status.update(f"[bold yellow]Acting: {action_match.group(1).strip()}...")
                        continue
                    
                    if "[OBSERVATION]" in chunk:
                        status.update("[bold magenta]Processing observation...")
                        continue

                    # Basic tag stripping for other internal markers
                    clean_chunk = re.sub(r"\[/?(ACTION|OBSERVATION).*?\]", "", chunk)
                    full_reply += clean_chunk
                    
                    # Update the live Markdown display
                    live.update(Markdown(full_reply))
            
            # Final touch: ensure footer is clean
            console.print("─" * console.width + "\n")
            
        console.print("[bold cyan]✓ Task completed.[/bold cyan]")
        return 0
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {escape(str(e))}", style="red")
        return 1

async def run_interactive_cli(selected_agent: str = "auto"):
    """Start interactive CLI using the new Textual TUI."""
    try:
        from cli.tui.app import AsuraApp
        app = AsuraApp()
        await app.run_async()
    except ImportError as e:
        console.print(f"[bold red]Error:[/bold red] Textual TUI components not found. ({e})")
        console.print("[yellow]Falling back to legacy interactive mode...[/yellow]")
        # (Legacy fallback or exit)
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]TUI Error:[/bold red] {e}")
        sys.exit(1)
