---
name: doc_summarizer
description: "Document summarization skill. Summarizes text, URLs, and PDFs into bullets, paragraphs, or TL;DR using LLM."
entry_point: summarizer.py
---

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
