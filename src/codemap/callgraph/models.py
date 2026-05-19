"""Domain models for the symbol-level call graph.

Each class here represents a structural fact about function-to-function
relationships in a Python project: a function or method node, a raw
call site found in a function body, or a resolved edge between two
nodes. All models are immutable dataclasses with __slots__, mirroring
the style of ``codemap.ast_engine.models``.

These models hold data only. Extraction logic lives in
``callgraph.extractor``; resolution lives in ``callgraph.resolver``;
graph assembly lives in ``callgraph.builder``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CallEdgeKind(Enum):
    """The resolution status of a call edge.

    Every edge in the call graph carries one of these kinds, which
    tells consumers (hotspot analysis, exporters, CLI summaries) how
    much to trust the edge and whether the callee node is real
    project code or a synthetic placeholder.

    INTERNAL
        The callee resolves to a function or method defined in this
        project. Both endpoints are real ``FunctionNode`` instances.

    SELF
        The callee is a ``self.method()`` call resolved against the
        caller's enclosing class. A specialisation of INTERNAL kept
        distinct so consumers can count or filter self-calls.

    EXTERNAL
        The callee resolves to something outside the project
        (stdlib, third-party). The target node exists in the graph
        as a synthetic external node, named after the callee
        expression (e.g. ``requests.get``).

    UNRESOLVED
        The callee looked like it might be project code (an attribute
        chain we could not follow, a bare name with no matching
        binding) but could not be pinned down. The target node is a
        synthetic ``<unresolved>:<expression>`` placeholder.
    """

    INTERNAL = "internal"
    SELF = "self"
    EXTERNAL = "external"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class FunctionNode:
    """A function or method that can appear as a node in the call graph.

    Captures the surface identity of a function definition. The body
    is not represented here; call sites inside the body are modelled
    separately by ``CallSite`` and ``CallEdge``.

    The ``qualified_name`` is the canonical identifier used as the
    node key in the graph. The individual components are also kept
    as fields so consumers do not have to parse the qualified name
    back apart.

    Examples of source that produce this model:
        def foo() in module ``pkg.mod``
            -> qualified_name='pkg.mod.foo', module='pkg.mod',
               class_name=None, name='foo', is_method=False
        async def bar() in module ``pkg.mod``
            -> qualified_name='pkg.mod.bar', module='pkg.mod',
               class_name=None, name='bar', is_method=False,
               is_async=True
        def baz() inside ``class Widget`` in module ``pkg.mod``
            -> qualified_name='pkg.mod.Widget.baz', module='pkg.mod',
               class_name='Widget', name='baz', is_method=True
    """

    qualified_name: str
    module: str
    class_name: str | None
    name: str
    line: int
    is_method: bool
    is_async: bool


@dataclass(frozen=True, slots=True)
class CallSite:
    """A raw call site found inside a function body.

    Captures one ``ast.Call`` node together with the function that
    contains it. The ``callee_expression`` field stores the textual
    form of the callee (a name like ``foo`` or a dotted chain like
    ``self.bar.baz``) before resolution. The same string conventions
    used by ``codemap.ast_engine.parser._resolve_callee`` apply here,
    including ``"<unknown>"`` for shapes that cannot be cleanly named.

    Resolution to a qualified name happens later, in
    ``callgraph.resolver``, which consumes ``CallSite`` and produces
    ``CallEdge``.

    Examples of source that produce this model (inside ``def foo``
    in module ``pkg.mod``):
        bar()
            -> caller='pkg.mod.foo', callee_expression='bar'
        self.helper()
            -> caller='pkg.mod.foo', callee_expression='self.helper'
        os.path.join(a, b)
            -> caller='pkg.mod.foo', callee_expression='os.path.join'
        (lambda x: x)()
            -> caller='pkg.mod.foo', callee_expression='<unknown>'
    """

    caller: str
    callee_expression: str
    line: int


@dataclass(frozen=True, slots=True)
class CallEdge:
    """A resolved edge from one function to another in the call graph.

    Produced by ``callgraph.resolver`` from a ``CallSite`` plus the
    project's name-lookup context. The ``caller`` and ``callee`` fields
    are qualified names; both endpoints will exist as nodes in the
    assembled graph, though only INTERNAL and SELF endpoints are real
    project functions. EXTERNAL and UNRESOLVED endpoints are synthetic
    nodes whose qualified names follow these conventions:

        EXTERNAL    The callee expression itself, e.g. ``requests.get``.
        UNRESOLVED  ``<unresolved>:<callee_expression>``.

    The ``line`` field is the line of the call site, not of the
    callee's definition.

    Examples of source that produce this model (call inside
    ``pkg.mod.foo``):
        bar()  where bar is defined in pkg.mod
            -> caller='pkg.mod.foo', callee='pkg.mod.bar',
               kind=INTERNAL
        self.helper()  inside a method of class Widget
            -> caller='pkg.mod.Widget.method',
               callee='pkg.mod.Widget.helper', kind=SELF
        requests.get(url)
            -> caller='pkg.mod.foo', callee='requests.get',
               kind=EXTERNAL
        self.client.session.get(url)
            -> caller='pkg.mod.foo',
               callee='<unresolved>:self.client.session.get',
               kind=UNRESOLVED
    """

    caller: str
    callee: str
    line: int
    kind: CallEdgeKind


def build_qualified_name(
    module: str,
    name: str,
    class_name: str | None = None,
) -> str:
    """Build a qualified name string from its components.

    The canonical format is ``module.name`` for module-level functions
    and ``module.ClassName.name`` for methods. This helper exists so
    that the format is defined in exactly one place; every caller that
    needs a qualified name should go through here rather than
    concatenating strings inline.

    Args:
        module: Dotted module path, e.g. ``codemap.cli``.
        name: Bare function or method name.
        class_name: Enclosing class name for methods, or None for
            module-level functions.

    Returns:
        The qualified name as a single dotted string.
    """
    if class_name is None:
        return f"{module}.{name}"
    return f"{module}.{class_name}.{name}"
