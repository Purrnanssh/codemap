"""Cyclomatic complexity (McCabe) for Python functions.

Given a source file, this module computes one integer per top-level
function and per direct class method: the number of linearly
independent paths through the function body. A function with no
branching has complexity 1; each branch point adds 1.

The branch points counted here follow the standard McCabe rules
adapted for modern Python:

    if / elif                       +1 each
    for / async for                 +1
    while                           +1
    except handler                  +1 each
    with / async with               +1 per context manager
    assert                          +1
    ternary (x if c else y)         +1
    match: each case after the
        first                       +1
    boolean operator (and/or)       +1 per additional operand
                                    beyond the first
    comprehension 'if' filter       +1 each

Else clauses on if, for, while, and try do NOT add to complexity.
The else branch is already implied by its parent construct.

This module performs no resolution and no graph work. It is a pure
analyzer: source in, dict of qualified_name -> complexity out.
"""

from __future__ import annotations

import ast
from pathlib import Path

from codemap.callgraph.models import build_qualified_name


def compute_complexities(
    path: Path | str,
    module_dotted: str,
) -> dict[str, int]:
    """Compute McCabe complexity for every function in one module.

    Walks the source file and produces one entry per top-level
    function and per direct class method, keyed by the qualified
    name that ``callgraph.extractor`` uses for the same definitions.
    Functions defined inside other functions do not get their own
    entries (they are part of the enclosing function's body for
    complexity purposes — the count of their branches is included
    in the enclosing function's score).

    Args:
        path: Path to a Python source file.
        module_dotted: Dotted module path the source represents,
            e.g. ``codemap.cli``. Used to build qualified names.

    Returns:
        A dict mapping qualified function name to its integer
        complexity score. Returns an empty dict if the module has
        no functions or methods.

    Raises:
        FileNotFoundError: If the file does not exist.
        UnicodeDecodeError: If the file is not valid UTF-8.
        SyntaxError: If the file is not valid Python.
    """
    path = Path(path)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    visitor = _ComplexityVisitor(module_dotted)
    visitor.visit(tree)
    return visitor.complexities


class _ComplexityVisitor(ast.NodeVisitor):
    """Walk the AST and compute complexity per top-level function/method.

    The visitor tracks an enclosing-class stack (so methods can be
    identified) and an enclosing-function stack (so nested functions
    are skipped as separate entries but their branch points still
    count toward the enclosing function).

    Each branch-adding node encountered while inside a function adds
    to that function's running total. The total starts at 1 (the
    function itself is one path).
    """

    def __init__(self, module_dotted: str) -> None:
        self._module = module_dotted
        self._class_stack: list[str] = []
        # Each entry on the function stack is a (qualified_name,
        # current_count) pair. We mutate the count via a list-of-int
        # trick (lists are mutable so we can update through the
        # reference); cleaner than reassigning tuple elements.
        self._function_stack: list[tuple[str, list[int]]] = []
        self.complexities: dict[str, int] = {}

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_function_def(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_function_def(node)

    def _handle_function_def(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        is_nested = bool(self._function_stack)

        if not is_nested:
            enclosing_class = (
                self._class_stack[-1] if self._class_stack else None
            )
            qname = build_qualified_name(
                module=self._module,
                name=node.name,
                class_name=enclosing_class,
            )
            counter = [1]  # base complexity: 1 path through the body
            self._function_stack.append((qname, counter))
            self.generic_visit(node)
            self.complexities[qname] = counter[0]
            self._function_stack.pop()
        else:
            # Nested function: do not create a separate entry, but
            # its branches still count toward the enclosing function.
            self.generic_visit(node)

    # --- Branch-adding nodes ---

    def visit_If(self, node: ast.If) -> None:
        # An 'if' is +1. 'elif' is parsed as a nested If inside the
        # orelse, so we get the +1 for each elif automatically as we
        # recurse. 'else' adds nothing.
        self._increment()
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._increment()
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._increment()
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._increment()
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self._increment()
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        # 'with a, b, c:' is one With node with three items; each
        # context manager is a control point.
        self._increment_by(len(node.items))
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._increment_by(len(node.items))
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self._increment()
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        # Ternary expression: x if cond else y.
        self._increment()
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        # Each match case after the first adds one. A match with one
        # case is just a single branch; subsequent cases are
        # additional paths.
        if len(node.cases) > 1:
            self._increment_by(len(node.cases) - 1)
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # 'a and b and c' has three values, two extra operands beyond
        # the first, so +2. Same for 'or'.
        extra = len(node.values) - 1
        if extra > 0:
            self._increment_by(extra)
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        # A generator/list/set/dict comprehension has one
        # 'comprehension' per 'for' clause; each 'if' clause inside
        # adds a branch. The 'for' itself is the iteration; we count
        # the 'if' filters but not the 'for' (matches common tools'
        # behaviour and keeps the score readable).
        self._increment_by(len(node.ifs))
        self.generic_visit(node)

    # --- Helpers ---

    def _increment(self) -> None:
        self._increment_by(1)

    def _increment_by(self, n: int) -> None:
        if not self._function_stack:
            # Branch outside any function: ignore. Module-level
            # control flow does not contribute to function complexity.
            return
        _, counter = self._function_stack[-1]
        counter[0] += n
