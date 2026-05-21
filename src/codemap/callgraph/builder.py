"""Build a symbol-level call graph for a Python project.

This is the public entry point of the call graph layer. Given a
project root, it discovers every internal module, extracts its
functions and call sites, resolves each call to a typed edge, and
assembles a directed graph where:

    - Each function or method is a node, keyed by qualified name.
    - External callees and unresolved expressions are synthetic
      nodes, also keyed by qualified name.
    - Each edge represents one or more call sites from the source
      function to the target.

The builder reuses Phase 3's ``discover_modules`` so the notion of
"internal module" is consistent across the two graphs. It also
performs cross-module validation: INTERNAL edges emitted by the
resolver are checked against the full project-wide function index
and downgraded to UNRESOLVED if the target does not exist as a real
function in the project.

Each function node also carries its McCabe cyclomatic complexity as
a node attribute, computed by ``callgraph.complexity``. Exporters
and hotspot analysis can read it directly from the graph without
threading a separate dict through their call signatures.

Files that fail to parse do not contribute nodes (no functions can
be extracted). Their paths are returned separately so the CLI can
surface them, mirroring Phase 3's parse-error tolerance.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx

from codemap.ast_engine.parser import parse_file
from codemap.callgraph.complexity import compute_complexities
from codemap.callgraph.context import ModuleContext, build_module_context
from codemap.callgraph.extractor import extract_module
from codemap.callgraph.models import (
    CallEdge,
    CallEdgeKind,
    CallSite,
    FunctionNode,
)
from codemap.callgraph.resolver import (
    UNRESOLVED_PREFIX,
    resolve_call,
)
from codemap.graph.discovery import ModuleRecord, discover_modules


def build_call_graph(
    root: Path,
) -> tuple[nx.DiGraph, dict[Path, str]]:
    """Build a call graph for a Python project.

    Walks the project at ``root``, parses every ``.py`` file, extracts
    every function and call site, and assembles a directed graph of
    function-to-function call relationships. Also computes McCabe
    cyclomatic complexity per function and attaches it as a node
    attribute.

    Args:
        root: Project root directory. As with Phase 3's
            ``build_graph``, point this at the directory whose dotted
            paths match the project's import strings (typically the
            ``src/<pkg>`` directory or the repo root for flat layouts).

    Returns:
        A pair ``(graph, parse_errors)`` where:

            - ``graph`` is an ``nx.DiGraph`` whose nodes are qualified
              names. Function nodes carry the attributes of a
              ``FunctionNode`` plus ``kind="function"`` and
              ``complexity`` (int). External and unresolved nodes
              carry ``kind="external"`` or ``kind="unresolved"``
              respectively, and no other attributes. Edges carry
              ``kind`` (the string value of the ``CallEdgeKind``),
              ``call_count`` (number of call sites collapsed into
              this edge), and ``first_line`` (line of the earliest
              collapsed call site).

            - ``parse_errors`` maps each failed file's path to the
              short error string for that file.

    Raises:
        FileNotFoundError: If ``root`` does not exist.
        NotADirectoryError: If ``root`` exists but is not a directory.
    """
    records = discover_modules(root)
    internal_modules = {record.dotted_path for record in records}

    # First pass: parse every module and extract its functions, call
    # sites, and complexity scores. We do this in one pass so we can
    # build the project-wide function index before any edges are
    # emitted, which is required for cross-module validation.
    parsed: dict[str, _ParsedModule] = {}
    parse_errors: dict[Path, str] = {}

    for record in records:
        outcome = _parse_one_module(record, internal_modules)
        if isinstance(outcome, _ParseFailure):
            parse_errors[record.file_path] = outcome.message
            continue
        parsed[record.dotted_path] = outcome

    # Build the project-wide function index for cross-module validation.
    function_index: set[str] = set()
    for module in parsed.values():
        for func in module.functions:
            function_index.add(func.qualified_name)

    # Second pass: assemble the graph.
    graph: nx.DiGraph = nx.DiGraph()

    for module in parsed.values():
        for func in module.functions:
            complexity = module.complexities.get(func.qualified_name, 1)
            _add_function_node(graph, func, complexity)

    for module in parsed.values():
        for call_site in module.call_sites:
            edge = resolve_call(call_site, module.context)
            edge = _validate_internal_edge(edge, function_index)
            _add_edge(graph, edge)

    return graph, parse_errors


class _ParsedModule:
    """Internal: bundle of per-module outputs used during graph building."""

    __slots__ = ("functions", "call_sites", "context", "complexities")

    def __init__(
        self,
        functions: tuple[FunctionNode, ...],
        call_sites: tuple[CallSite, ...],
        context: ModuleContext,
        complexities: dict[str, int],
    ) -> None:
        self.functions = functions
        self.call_sites = call_sites
        self.context = context
        self.complexities = complexities


class _ParseFailure:
    """Internal: marker for a module that failed to parse."""

    __slots__ = ("message",)

    def __init__(self, message: str) -> None:
        self.message = message


def _parse_one_module(
    record: ModuleRecord,
    internal_modules: set[str],
) -> _ParsedModule | _ParseFailure:
    """Parse one module and run the call graph extraction over it.

    Returns either the parsed bundle (functions + call sites +
    context + complexities) or a parse failure marker. Errors are
    caught at the same boundary Phase 3 catches them: ``SyntaxError``
    and ``UnicodeDecodeError``.
    """
    is_package = record.file_path.name == "__init__.py"

    try:
        analysis = parse_file(record.file_path)
    except (SyntaxError, UnicodeDecodeError) as exc:
        return _ParseFailure(f"{type(exc).__name__}: {exc}")

    context = build_module_context(
        module_dotted=record.dotted_path,
        analysis=analysis,
        internal_modules=internal_modules,
        importer_is_package=is_package,
    )

    functions, call_sites = extract_module(
        record.file_path,
        record.dotted_path,
    )

    # Complexity is computed from the same file. We already know it
    # parses (parse_file above succeeded), so this call cannot raise
    # SyntaxError in practice; we still let it propagate if it does.
    complexities = compute_complexities(
        record.file_path,
        record.dotted_path,
    )

    return _ParsedModule(
        functions=functions,
        call_sites=call_sites,
        context=context,
        complexities=complexities,
    )


def _add_function_node(
    graph: nx.DiGraph,
    func: FunctionNode,
    complexity: int,
) -> None:
    """Add a real function node to the graph with its attributes."""
    graph.add_node(
        func.qualified_name,
        module=func.module,
        class_name=func.class_name,
        name=func.name,
        line=func.line,
        is_method=func.is_method,
        is_async=func.is_async,
        kind="function",
        complexity=complexity,
    )


def _validate_internal_edge(
    edge: CallEdge,
    function_index: set[str],
) -> CallEdge:
    """Downgrade INTERNAL edges whose target is not a real function.

    The resolver emits INTERNAL optimistically: if a name resolves
    to an internal module, the resolver constructs a target like
    ``pkg.helpers.do_thing`` without verifying ``do_thing`` actually
    exists in ``pkg.helpers``. This pass checks the constructed
    target against the project-wide function index; if it is not
    found, the edge is rewritten as UNRESOLVED so the rest of the
    pipeline does not treat a phantom target as a real call.

    SELF edges are not validated here. The resolver only emits SELF
    when the target method exists in the caller's class methods
    index, so they are already trustworthy at that point.

    EXTERNAL and UNRESOLVED edges pass through unchanged.
    """
    if edge.kind is not CallEdgeKind.INTERNAL:
        return edge

    if edge.callee in function_index:
        return edge

    return CallEdge(
        caller=edge.caller,
        callee=f"{UNRESOLVED_PREFIX}{edge.callee}",
        line=edge.line,
        kind=CallEdgeKind.UNRESOLVED,
    )


def _add_edge(graph: nx.DiGraph, edge: CallEdge) -> None:
    """Add or update an edge for one resolved call.

    If the edge already exists, increments ``call_count``. If not,
    creates the edge with ``call_count=1`` and the line of the first
    call. The synthetic target node is created if needed, with the
    appropriate ``kind`` attribute.
    """
    _ensure_target_node(graph, edge)

    if graph.has_edge(edge.caller, edge.callee):
        graph[edge.caller][edge.callee]["call_count"] += 1
        return

    graph.add_edge(
        edge.caller,
        edge.callee,
        kind=edge.kind.value,
        call_count=1,
        first_line=edge.line,
    )


def _ensure_target_node(graph: nx.DiGraph, edge: CallEdge) -> None:
    """Create a synthetic target node for EXTERNAL or UNRESOLVED edges.

    Real function nodes are added up front by ``_add_function_node``,
    so for INTERNAL and SELF edges this is a no-op. For EXTERNAL and
    UNRESOLVED edges, the target may not exist yet; we add it with
    the appropriate ``kind`` attribute and no other metadata.
    """
    if graph.has_node(edge.callee):
        return

    if edge.kind is CallEdgeKind.EXTERNAL:
        graph.add_node(edge.callee, kind="external")
    elif edge.kind is CallEdgeKind.UNRESOLVED:
        graph.add_node(edge.callee, kind="unresolved")
    # INTERNAL and SELF should already exist in the graph as real
    # function nodes. If somehow they don't, leave node creation to
    # the default add_edge path (no attributes).
