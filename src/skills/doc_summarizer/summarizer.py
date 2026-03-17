"""
Document Summarizer Skill.

Provides utilities to condense long text, fetch and summarize web URLs, 
and extract/summarize content from local files (including PDFs).

Capabilities:
- summarize_text: LLM-driven text shortening with multiple styles (bullets, paragraph, tldr).
- summarize_url: Web scraping integrated with summarization.
- summarize_file: Multi-format file support (txt, md, py, pdf).
"""

import os
import asyncio
from settings import settings as config
from core.llm import call_llm
from skills.logger import log_audit
from skills.web_intelligence import scrape_url


def summarize_text(text: str, style: str = "bullets", max_length: int = 500) -> str:
    """Summarize long text into concise points."""
    if len(text) < 100:
        return text

    style_instruction = {
        "bullets": "Use bullet points. Be concise.",
        "paragraph": "Write a single cohesive paragraph.",
        "tldr": "Give a one-sentence TL;DR.",
        "detailed": "Provide a detailed summary with key points.",
    }.get(style, "Use bullet points.")

    # Chunk if too long
    if len(text) > 8000:
        text = text[:8000] + "\n\n[...truncated...]"

    prompt = f"""Summarize the following text. {style_instruction}
Keep the summary under {max_length} words.

TEXT:
{text}

SUMMARY:"""

    try:
        model = config.OLLAMA_MODELS.get("summary", config.OLLAMA_MODEL)
        summary = asyncio.run(call_llm(prompt, model=model, stream=False))
        log_audit("SUMMARIZE", f"Summarized {len(text)} chars → {len(summary)} chars")
        return summary

    except Exception as e:
        log_audit("SUMMARIZE_ERROR", f"Failed: {e}")
        return f"Summarization failed: {e}"


def summarize_url(url: str, style: str = "bullets") -> str:
    """Fetch a URL and summarize its content."""
    try:
        content = scrape_url(url)
        if not content:
            return f"Could not fetch content from {url}"
        return summarize_text(content, style)
    except Exception as e:
        return f"URL summarization failed: {e}"


def summarize_file(filepath: str, style: str = "bullets") -> str:
    """Summarize a local file (text, PDF, etc.)."""
    full_path = os.path.join(config.BASE_DIR, filepath)

    if not os.path.isfile(full_path):
        return f"File not found: {filepath}"

    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".pdf":
        return _summarize_pdf(full_path, style)
    elif ext in (".txt", ".md", ".py", ".json", ".csv", ".log"):
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return summarize_text(text, style)
    else:
        return f"Unsupported file type: {ext}"


def _summarize_pdf(path: str, style: str) -> str:
    """Extract text from PDF and summarize."""
    try:
        import subprocess
        # Try pdftotext first (often available on macOS)
        result = subprocess.run(
            ["pdftotext", path, "-"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return summarize_text(result.stdout, style)
    except Exception:
        pass

    # Fallback: try PyPDF2
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if text.strip():
            return summarize_text(text, style)
    except ImportError:
        pass

    return "PDF extraction failed. Install PyPDF2: pip install PyPDF2"
