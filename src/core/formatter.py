"""
ASURA - Self-Updating AI System
Module: src/core/formatter.py
Owner: Aniket Raj Singh

Purpose:
    Provides a unified interface for formatting LLM responses across different output platforms
    (CLI, Telegram, Web) within the ASURA architecture. It handles markdown rendering, ASCII table conversion,
    and HTML escaping depending on the target environment.

Architecture:
    This module implements a dependency-safe strategy for the `rich` library. Since `rich` is optional 
    but preferred for CLI output, this module catches ImportError during initialization. If `rich` is missing,
    a fallback `RichMarkdown` class is defined to ensure system stability without crashing on import.

Usage:
    Import and use the `format_message` function with the appropriate platform identifier:
        - "cli": Uses Rich (or fallback) for terminal output.
        - "telegram": Converts markdown to HTML-safe text.
        - "web": Returns raw markdown for frontend rendering.

Dependencies:
    - re (Standard Library): Regex for pattern matching.
    - rich (Optional): High-level Markdown rendering for CLI.

Version Control:
    Managed by ASURA Self-Updater and Sovereign Vault.
"""

import re

# Dependency Handling Strategy:
# Attempt to import 'rich' for enhanced CLI formatting. If unavailable, define a fallback 
# class that returns raw text to prevent ModuleNotFoundError crashes during system startup.
try:
    from rich.markdown import Markdown as RichMarkdown
except ImportError:
    # Fallback class ensures the module loads and functions gracefully without 'rich'.
    class RichMarkdown:
        """Fallback implementation of RichMarkdown when the library is not installed."""
        def __init__(self, text):
            self.text = text

        def __str__(self):
            return str(self.text)

        def __repr__(self):
            return f"RichMarkdown({self.text!r})"


def markdown_to_ascii_table(text):
    """
    Finds markdown tables in text and converts them to ASCII/monospaced format.
    Simple but effective for Telegram <pre> blocks.
    
    Args:
        text (str): Input text containing markdown tables.
        
    Returns:
        str: Text with markdown tables preserved or wrapped for safe rendering.
    """
    lines = text.split('\n')
    result = []
    in_table = False
    table_lines = []

    for line in lines:
        if '|' in line and (line.count('|') >= 2):
            in_table = True
            table_lines.append(line)
        elif in_table:
            # Table ended
            if table_lines:
                # Basic ASCII conversion: just keep as is, but we could pad if needed
                # For now, we'll wrap the whole chunk in <pre> later
                result.append('\n'.join(table_lines))
                table_lines = []
            in_table = False
            result.append(line)
        else:
            result.append(line)
    
    if table_lines:
        result.append('\n'.join(table_lines))
        
    return '\n'.join(result)


def format_message(text: str, platform: str = "cli"):
    """
    Unified entry point for formatting LLM responses based on the target platform.
    
    Args:
        text (str): The raw markdown text to be formatted.
        platform (str): Target environment ('cli', 'telegram', 'web'). Defaults to 'cli'.
        
    Returns:
        str or RichMarkdown: Formatted content suitable for the specified platform.
    """
    if not text:
        return ""

    if platform == "cli":
        # Rich handles Markdown beautifully in terminal environments.
        # Falls back to simple string representation if 'rich' is not installed.
        return RichMarkdown(text)

    elif platform == "telegram":
        # Telegram HTML mode is more robust for mobile clients.
        # 1. Strip internal RAG/Memory tags
        processed = re.sub(r'\[(EPISODIC|VAULT|ARCH)\]\s*', '', text)
        
        # 2. Strip Action/Observation markers
        processed = re.sub(r'\[/?(ACTION|OBSERVATION)\]', '', processed)

        # 3. Handle Mermaid diagrams
        processed = re.sub(r'```mermaid.*?```', r'📊 <b>[Mermaid Diagram]</b>\n<i>(Use a Mermaid viewer for full visualization)</i>', processed, flags=re.DOTALL)

        # 4. Detect and Extract Markdown Tables
        table_pattern = r'((?:\|.*\|(?:\n|$))+(?:\|[- :|]*\|(?:\n|$))+(?:\|.*\|(?:\n|$))+)'
        # Wrap tables in <pre> tags so they render elegantly with monospaced font
        def wrap_table(match): return f"\n<pre>{match.group(1).strip()}</pre>\n"
        processed = re.sub(table_pattern, wrap_table, processed, flags=re.MULTILINE)
        
        # 5. Escape HTML entities
        processed = processed.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        processed = processed.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
        processed = processed.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
        processed = processed.replace("&lt;code&gt;", "<code>").replace("&lt;/code&gt;", "</code>")
        processed = processed.replace("&lt;pre&gt;", "<pre>").replace("&lt;/pre&gt;", "</pre>")
        
        # 6. Bold/Italic/Code mapping
        processed = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', processed)
        processed = re.sub(r'\*(.*?)\*', r'<i>\1</i>', processed)
        processed = re.sub(r'`(.*?)`', r'<code>\1</code>', processed)
        
        return processed

    elif platform == "web":
        # Web just needs the raw markdown; the frontend (marked.js) will handle the rest
        return text

    return text