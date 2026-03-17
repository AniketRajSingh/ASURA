---
name: auto_tester
description: "Automated self-testing. Syntax checks, import validation, LLM-generated tests, and pytest runner."
entry_point: tester.py
---

# Auto Tester

Automated self-testing system for the ASURA framework. It performs syntax checks, validates module imports, uses LLM to generate tests for new code, and runs them using pytest to ensure system integrity.

### 🔧 Tools / Functions
- `run_syntax_check(filepath)`: Check Python file for syntax errors.
- `run_import_check(module)`: Check if a module imports cleanly.
- `run_all_skill_imports()`: Test that all skills in the registry import cleanly.
- `generate_test(code, purpose)`: Use LLM to generate a pytest test for the given code.
- `run_test_string(test_code)`: Run a test string in a temporary file using pytest.
- `verify_code_intent(code, intent)`: Compare generated code against original intent using LLM for logical consistency.

### 📝 Examples
- "Check if my new skill imports correctly" -> Passes if `import skills.new_skill` works.
- "Generate a test for this function" -> Returns a `test_*.py` snippet.

### 🛠️ Requirements
- `pytest`
- `ollama` (configured in `config.py` for LLM-based verification)
