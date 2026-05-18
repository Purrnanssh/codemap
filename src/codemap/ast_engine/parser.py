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

from codemap.ast_engine.models import FunctionInfo, ImportInfo


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
            for alias in node.names:
                imports.append(
                    ImportInfo(
                        module=module_name,
                        name=alias.name,
                        alias=alias.asname,
                        line=node.lineno,
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

    # Iterate only over the direct children of the module, not the
    # full tree. This naturally excludes methods (inside classes) and
    # nested functions (inside other functions).
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            functions.append(
                FunctionInfo(
                    name=node.name,
                    line=node.lineno,
                    args=tuple(arg.arg for arg in node.args.args),
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                )
            )

    return tuple(functions)
