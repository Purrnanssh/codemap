"""Extract function definitions and call sites from a single module.

This module walks a Python AST with function-context tracking, so
that each ``ast.Call`` node encountered is attributed to the
enclosing function or method. This is the key difference from
Phase 2's ``extract_calls``, which captures calls flat with no
containing function.

The extractor produces two outputs per module:

    - A list of ``FunctionNode`` objects for every top-level function
      and direct class method in the module.
    - A list of ``CallSite`` objects, each tagged with the qualified
      name of its containing function.

The extractor is intentionally limited to match Phase 2's boundary:
nested functions, lambdas, and comprehensions do not become nodes.
Calls *inside* a nested function are attributed to the outermost
top-level function or method that contains it. Calls *to* a nested
function will resolve to ``UNRESOLVED`` later, since the target has
no node.

Resolution of callee expressions to qualified names happens in
``callgraph.resolver``; this layer only collects raw expressions.
"""

from __future__ import annotations

import ast
from pathlib import Path

from codemap.ast_engine.parser import _resolve_callee
from codemap.callgraph.models import (
    CallSite,
    FunctionNode,
    build_qualified_name,
)


def extract_module(
    path: Path | str,
    module_dotted: str,
) -> tuple[tuple[FunctionNode, ...], tuple[CallSite, ...]]:
    """Extract function nodes and call sites from one source file.

    Reads the file, parses it, walks the tree with function-context
    tracking, and returns every top-level function and direct class
    method as a ``FunctionNode``, together with every call site
    attributed to the enclosing function.

    Args:
        path: Path to a Python source file. May be a Path or string.
        module_dotted: The dotted module path that the source file
            represents, e.g. ``codemap.cli``. Used to build qualified
            names for the function nodes.

    Returns:
        A pair ``(functions, call_sites)`` where ``functions`` is the
        tuple of every captured ``FunctionNode`` and ``call_sites`` is
        the tuple of every captured ``CallSite``.

    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path points to a directory.
        UnicodeDecodeError: If the file is not valid UTF-8.
        SyntaxError: If the file is not valid Python.
    """
    path = Path(path)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    visitor = _CallGraphVisitor(module_dotted)
    visitor.visit(tree)

    return tuple(visitor.functions), tuple(visitor.call_sites)


class _CallGraphVisitor(ast.NodeVisitor):
    """AST visitor that tracks the enclosing function and class.

    Maintains two stacks while walking the tree:

        - ``_function_stack`` holds the qualified name of every
          function or method currently being visited. The top of the
          stack is the immediate enclosing function; the bottom (when
          the stack is non-empty) is the outermost top-level function
          or method, which is who we attribute calls to.
        - ``_class_stack`` holds the name of every class currently
          being visited. The top of the stack tells us whether we are
          inside a class body when we encounter a function definition,
          which determines whether that definition becomes a method.

    Functions defined inside other functions (nested functions,
    closures) are visited so we can pick up their calls, but they do
    not become ``FunctionNode`` entries. Classes nested inside other
    classes or inside functions are also visited but do not create
    method nodes.
    """

    def __init__(self, module_dotted: str) -> None:
        self._module = module_dotted
        self._function_stack: list[str] = []
        self._class_stack: list[str] = []
        self.functions: list[FunctionNode] = []
        self.call_sites: list[CallSite] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit a synchronous function or method definition."""
        self._handle_function_def(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit an asynchronous function or method definition."""
        self._handle_function_def(node, is_async=True)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit a class definition, tracking its name for methods."""
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        """Visit a call expression and attribute it to the enclosing
        function if there is one.

        Calls at module top level (outside any function) are ignored.
        They are real, but they have no caller in the call graph
        sense; nothing in this project would be a node for them.
        """
        if self._function_stack:
            caller_qname = self._function_stack[0]
            self.call_sites.append(
                CallSite(
                    caller=caller_qname,
                    callee_expression=_resolve_callee(node.func),
                    line=node.lineno,
                )
            )
        # Recurse into arguments so that calls inside the args of
        # this call are also captured (e.g. foo(bar()) records both).
        self.generic_visit(node)

    def _handle_function_def(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        is_async: bool,
    ) -> None:
        """Shared logic for synchronous and asynchronous defs.

        Decides whether this definition becomes a ``FunctionNode``
        (it does when the stack of enclosing functions is empty,
        i.e. it is top-level in the module or directly inside a
        class). Either way, pushes the qualified name onto the stack
        so calls inside the body get attributed correctly, then
        recurses, then pops.
        """
        is_nested_in_function = bool(self._function_stack)
        enclosing_class = self._class_stack[-1] if self._class_stack else None
        is_method = enclosing_class is not None and not is_nested_in_function

        if not is_nested_in_function:
            # Top-level function or direct class method: becomes a node.
            qname = build_qualified_name(
                module=self._module,
                name=node.name,
                class_name=enclosing_class if is_method else None,
            )
            self.functions.append(
                FunctionNode(
                    qualified_name=qname,
                    module=self._module,
                    class_name=enclosing_class if is_method else None,
                    name=node.name,
                    line=node.lineno,
                    is_method=is_method,
                    is_async=is_async,
                )
            )
            push_name = qname
        else:
            # Nested function: do not create a node, but still attribute
            # any calls inside it to the outermost enclosing function.
            # We push the outermost name again so the top of the stack
            # stays consistent (calls attribute to function_stack[0]
            # anyway, but keeping the stack balanced is clearer).
            push_name = self._function_stack[0]

        self._function_stack.append(push_name)
        self.generic_visit(node)
        self._function_stack.pop()
