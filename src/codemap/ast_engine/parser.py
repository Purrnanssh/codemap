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

from codemap.ast_engine.models import ImportInfo


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
            # Form: import x, import x as y, import x.y.z
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
            # Form: from x import y, from x import y as z
            # node.module is the part after 'from' (can be None for relative imports)
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
