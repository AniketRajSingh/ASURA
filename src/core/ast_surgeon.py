"""
core/ast_surgeon.py
============================================================
Surgical instrumentation for ASURA.
Uses Python's AST module to identify precise line ranges for functions
and classes, allowing for targeted code mutation without destroying
formatting or comments in the rest of the file.
"""

import ast
import os
from typing import Optional, Tuple
from skills.logger import log_audit


def get_symbol_range(filepath: str, symbol_name: str) -> Optional[Tuple[int, int]]:
    """
    Finds the start and end line numbers for a function or class definition.
    Returns (start_line, end_line) 1-indexed, or None if not found.
    """
    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name == symbol_name:
                    # Note: end_lineno is in Python 3.8+
                    return (node.lineno, getattr(node, "end_lineno", node.lineno))
    except Exception as e:
        log_audit("SURGEON_ERR", f"AST Parse failed for {filepath}: {e}")
    
    return None


def suture_code(filepath: str, start_line: int, end_line: int, new_code: str) -> bool:
    """
    Surgically replaces a range of lines with new code.
    Preserves surrounding code, formatting, and comments.
    """
    if not os.path.exists(filepath):
        return False

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Lines are 1-indexed, handle the slice
        # start_line-1 to end_line
        head = lines[:start_line - 1]
        tail = lines[end_line:]
        
        # Ensure new_code ends with a newline
        if not new_code.endswith("\n"):
            new_code += "\n"

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(head)
            f.write(new_code)
            f.writelines(tail)
            
        return True
    except Exception as e:
        log_audit("SURGEON_ERR", f"Suture failed for {filepath}: {e}")
        return False


def verify_suture(filepath: str) -> Tuple[bool, str]:
    """
    Checks if the sutured file is still syntactically valid.
    """
    import py_compile
    try:
        py_compile.compile(filepath, doraise=True)
        return True, "OK"
    except py_compile.PyCompileError as e:
        return False, str(e)


def surgical_replace(filepath: str, symbol_name: str, new_code: str) -> Tuple[bool, str]:
    """
    High-level API: Find symbol, replace it, and verify.
    """
    loc = get_symbol_range(filepath, symbol_name)
    if not loc:
        return False, f"Symbol '{symbol_name}' not found in {filepath}"
    
    start, end = loc
    if suture_code(filepath, start, end, new_code):
        valid, msg = verify_suture(filepath)
        if valid:
            return True, f"Successfully replaced {symbol_name} (lines {start}-{end})"
        else:
            return False, f"Suture corruption: {msg}"
    
    return False, "Suture operation failed"
