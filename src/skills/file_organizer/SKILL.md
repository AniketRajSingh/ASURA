---
name: file_organizer
description: "OS-independent smart file organization, global search, and project statistics reporting."
entry_point: organizer.py
---

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
