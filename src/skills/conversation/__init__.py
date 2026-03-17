"""
skills.conversation package initialization.

This module re‑exports the most frequently used conversation history utilities.
If the underlying module `skills.conversation.history` is missing symbols
(e.g. `get_recent_context`), the imports are wrapped in a `try/except` block
and lightweight fallback functions are provided so that the rest of the
framework can continue to operate without crashing.

All operations are logged via :func:`core.logger.log_audit` and
:func:`core.logger.log_app` to aid debugging and auditability.
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, List, Dict

# Logging helpers
try:
    from skills.logger import log_audit, log_app
except ImportError:
    # Fallback to standard logging if core.logger is unavailable
    logging.basicConfig(level=logging.INFO)
    def log_audit(msg: str) -> None:  # pragma: no cover
        logging.info(f"[AUDIT] {msg}")

    def log_app(msg: str) -> None:  # pragma: no cover
        logging.info(f"[APP] {msg}")

# Attempt to import the real implementation
try:
    from skills.conversation.history import (
        add_message,
        get_recent_context,
        get_system_prompt,
        build_chat_messages,
        search_history,
        get_history_stats,
    )
except ImportError as exc:  # pragma: no cover
    log_audit(
        f"Unable to import conversation history utilities: {exc}. "
        "Using lightweight stubs."
    )

    def add_message(message: Any, **kwargs: Any) -> None:
        """
        Stub for adding a message to history.

        Parameters
        ----------
        message : Any
            The message to add.
        **kwargs : Any
            Additional keyword arguments are ignored.

        Returns
        -------
        None
        """
        log_app(f"add_message stub called with message: {message!r}")
        # No-op

    def get_recent_context(limit: int = 5, **kwargs: Any) -> List[Dict[str, Any]]:
        """
        Stub for retrieving recent conversation context.

        Parameters
        ----------
        limit : int, optional
            Number of recent messages to return. Defaults to 5.

        Returns
        -------
        list
            Empty list, indicating no context is available.
        """
        log_app(f"get_recent_context stub called with limit={limit}")
        return []

    def get_system_prompt() -> str:
        """
        Stub for retrieving the system prompt.

        Returns
        -------
        str
            Empty string, indicating no system prompt is configured.
        """
        log_app("get_system_prompt stub called")
        return ""

    def build_chat_messages(messages: Iterable[Dict[str, Any]], **kwargs: Any) -> List[Dict[str, Any]]:
        """
        Stub for constructing chat message payloads.

        Parameters
        ----------
        messages : Iterable[Dict[str, Any]]
            The raw messages.

        Returns
        -------
        list
            Empty list, indicating no messages were built.
        """
        log_app(f"build_chat_messages stub called with messages: {list(messages)!r}")
        return []

    def search_history(query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        """
        Stub for searching conversation history.

        Parameters
        ----------
        query : str
            The search query.

        Returns
        -------
        list
            Empty list, indicating no results.
        """
        log_app(f"search_history stub called with query: {query!r}")
        return []

    def get_history_stats() -> Dict[str, Any]:
        """
        Stub for retrieving statistics about the conversation history.

        Returns
        -------
        dict
            Empty dict, indicating no statistics are available.
        """
        log_app("get_history_stats stub called")
        return {}

__all__ = [
    "add_message",
    "get_recent_context",
    "get_system_prompt",
    "build_chat_messages",
    "search_history",
    "get_history_stats",
]