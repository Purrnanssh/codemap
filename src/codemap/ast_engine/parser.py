"""Parser that extracts structural facts from Python source code.

This module uses Python's built-in ``ast`` module to parse source
code into an abstract syntax tree, then walks the tree to extract
the structural facts defined in ``codemap.ast_engine.models``.

The parser is intentionally tolerant: it captures what it can and
does not try to resolve names to actual definitions. Resolution
happens later in the graph-building phase.
"""

from __future__ import annotations

import ast
from pathlib import Path

from codemap.ast_engine.models import (
    CallInfo,
    ClassInfo,
    FileAnalysis,
    FunctionInfo,
    ImportInfo,
)

# Sentinel value used when a call's callee expression is not a simple
# name or dotted attribute chain (for example, a call on the result
# of another call, a subscript, or a lambda).
UNKNOWN_CALLEE = "<unknown>"


def parse_file(path: Path | str) -> FileAnalysis:
    """Parse a Python source file into a FileAnalysis.

    Reads the file from disk, parses its content, and runs every
    extractor in this module against it. Returns a single
    FileAnalysis bundling all results.

    Args:
        path: Path to a Python file. May be a Path or a string;
            strings are coerced to Path.

    Returns:
        A FileAnalysis containing every import, function, class,
        and call site found in the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path points to a directory.
        UnicodeDecodeError: If the file is not valid UTF-8.
        SyntaxError: If the file is not valid Python.
    """
    path = Path(path)
    source = path.read_text(encoding="utf-8")

    return FileAnalysis(
        path=path,
        imports=extract_imports(source),
        functions=extract_functions(source),
        classes=extract_classes(source),
        calls=extract_calls(source),
    )


def extract_imports(source: str) -> tuple[ImportInfo, ...]:
    """Extract all import statements from Python source code.

    Handles both forms of imports:
        ``import x`` and ``import x as y``
        ``from x import y`` and ``from x import y as z``

    Args:
        source: Python source code as a string.

    Returns:
        A tuple of ImportInfo objects, one per imported name. A
        single statement like ``from os import path, sep`` produces
        two ImportInfo objects.

    Raises:
        SyntaxError: If the source is not valid Python.
    """
    tree = ast.parse(source)
    imports: list[ImportInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    ImportInfo(
                        module=alias.name,
                        name=alias.name,
                        alias=alias.asname,
                        line=node.lineno,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            level = node.level
            for alias in node.names:
                imports.append(
                    ImportInfo(
                        module=module_name,
                        name=alias.name,
                        alias=alias.asname,
                        line=node.lineno,
                        level=level,
                    )
                )

    return tuple(imports)


def extract_functions(source: str) -> tuple[FunctionInfo, ...]:
    """Extract all top-level function definitions from Python source code.

    Only top-level functions are returned. Methods defined inside
    classes are intentionally excluded; they are captured by
    ``extract_classes`` instead. Nested functions (functions defined
    inside other functions) are also excluded.

    Both ``def`` and ``async def`` definitions are captured. The
    ``is_async`` flag distinguishes them.

    Args:
        source: Python source code as a string.

    Returns:
        A tuple of FunctionInfo objects, one per top-level function.

    Raises:
        SyntaxError: If the source is not valid Python.
    """
    tree = ast.parse(source)
    functions: list[FunctionInfo] = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            functions.append(_build_function_info(node))

    return tuple(functions)


def extract_classes(source: str) -> tuple[ClassInfo, ...]:
    """Extract all top-level class definitions from Python source code.

    Only top-level classes are returned. Nested classes (a class
    defined inside another class or inside a function) are
    intentionally excluded.

    For each class, every direct method (``def`` or ``async def`` in
    the class body) is captured as a FunctionInfo and stored in the
    ``methods`` field. Nested methods (functions defined inside a
    method) are not captured.

    Args:
        source: Python source code as a string.

    Returns:
        A tuple of ClassInfo objects, one per top-level class.

    Raises:
        SyntaxError: If the source is not valid Python.
    """
    tree = ast.parse(source)
    classes: list[ClassInfo] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = tuple(
                _build_function_info(child)
                for child in node.body
                if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef)
            )
            classes.append(
                ClassInfo(
                    name=node.name,
                    line=node.lineno,
                    methods=methods,
                )
            )

    return tuple(classes)


def extract_calls(source: str) -> tuple[CallInfo, ...]:
    """Extract all function and method call sites from Python source code.

    Calls are captured wherever they appear, including inside
    functions, methods, and nested blocks. Both simple name calls
    (``print()``) and attribute calls (``os.path.join()``) are
    represented by their textual dotted name.

    Calls whose callee expression cannot be cleanly named (calls on
    the result of another call, subscript expressions, lambdas) are
    still captured, with the callee set to ``"<unknown>"``. The line
    number is always recorded.

    Args:
        source: Python source code as a string.

    Returns:
        A tuple of CallInfo objects, one per call site.

    Raises:
        SyntaxError: If the source is not valid Python.
    """
    tree = ast.parse(source)
    calls: list[CallInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            calls.append(
                CallInfo(
                    callee=_resolve_callee(node.func),
                    line=node.lineno,
                )
            )

    return tuple(calls)


def _build_function_info(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> FunctionInfo:
    """Convert an AST function node into a FunctionInfo model.

    Internal helper shared by ``extract_functions`` and
    ``extract_classes`` (for methods). The leading underscore
    signals that this is not part of the public API.
    """
    return FunctionInfo(
        name=node.name,
        line=node.lineno,
        args=tuple(arg.arg for arg in node.args.args),
        is_async=isinstance(node, ast.AsyncFunctionDef),
    )


def _resolve_callee(func: ast.expr) -> str:
    """Resolve the callee expression of a Call node to a dotted name.

    Handles the two common shapes:
        ``Name`` nodes -> returns the name directly
        ``Attribute`` chains -> returns the full dotted path

    For all other shapes (calls on calls, subscripts, lambdas,
    starred expressions), returns ``UNKNOWN_CALLEE``.
    """
    if isinstance(func, ast.Name):
        return func.id

    if isinstance(func, ast.Attribute):
        parts: list[str] = [func.attr]
        current: ast.expr = func.value
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
            return ".".join(reversed(parts))
        return UNKNOWN_CALLEE

    return UNKNOWN_CALLEE
