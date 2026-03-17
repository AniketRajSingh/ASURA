---
name: codebase_investigator
description: "Deep static analysis of ASURA's source code. Performs grep searches, symbol finding, import tracing, and architectural reporting."
entry_point: investigator.py
---

# Codebase Investigator

Provides ASURA with deep introspection into its own source code. It uses AST parsing and optimized search tools to map the project's architecture, trace dependencies, locate symbols, and detect common code quality issues or bugs.

### 🔧 Tools / Functions
- `grep(pattern, path, case_sensitive)`: Perform a regex-based text search across the codebase with file and line number output.
- `find_symbol(name)`: Locate all definitions and call sites of a specific function, class, or variable across the project.
- `trace_imports(filepath)`: Analyze a file's imports to show direct and transitive local and third-party dependencies.
- `architecture_report()`: Generate a comprehensive summary of the project's structure, including file counts, LoC, and module analysis.
- `detect_issues()`: Run static analysis to identify broad except clauses, hardcoded paths, bare prints, and async inconsistencies.
- `investigate(query)`: Unified entry point for dispatching investigation commands (grep, find, imports, etc.).

### 📝 Examples
- "Find all usages of handle_message" -> Returns a list of every file and line where the function is called.
- "Show me an architecture report" -> Displays a high-level overview of ASURA's core and skills.

### 🛠️ Requirements
- `ast`, `pathlib`
- `grep` (system-level, with fallback to pure-Python implementation)
