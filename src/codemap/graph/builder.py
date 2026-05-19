"""Build a networkx DiGraph of module-level dependencies.

This is the public entry point of the ``codemap.graph`` package.
Given a project root, it discovers all internal modules, parses
each one, resolves their imports, and assembles a directed graph
where:

    - Each node is an internal module (identified by dotted path).
    - Each edge ``A -> B`` means module A imports module B.
    - Node attributes capture the file path, package status, count
      of external imports, and any parse errors encountered.

Files that fail to parse are still added as nodes (with no edges
and a ``parse_error`` attribute set), so the graph remains useful
even for partially-broken projects.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx

from codemap.ast_engine.parser import parse_file
from codemap.graph.discovery import ModuleRecord, discover_modules
from codemap.graph.resolver import resolve_import


def build_graph(root: Path) -> nx.DiGraph:
    """Build a module-level dependency graph for a Python project.

    Walks the project at ``root``, parses every ``.py`` file, and
    creates an edge from each module to every internal module it
    imports. External imports (stdlib, third-party) are counted but
    not modelled as edges.

    Args:
        root: Project root directory. For projects using a ``src/``
            layout, point at the package directory (e.g. ``src/mypkg``)
            rather than the repo root, so that dotted paths match
            what import statements actually use.

    Returns:
        A directed graph where nodes are dotted module paths and
        edges represent import relationships. Node attributes:

            - ``file_path`` (Path): the module's source file.
            - ``is_package`` (bool): True for ``__init__.py`` modules.
            - ``external_imports`` (int): count of unresolved imports.
            - ``parse_error`` (str | None): error message if parsing
              failed, else None.

    Raises:
        FileNotFoundError: If ``root`` does not exist.
        NotADirectoryError: If ``root`` exists but is not a directory.
    """
    records = discover_modules(root)
    internal_modules = {record.dotted_path for record in records}

    graph: nx.DiGraph = nx.DiGraph()

    # First pass: add all nodes so every internal module exists in the
    # graph even if it has no imports or fails to parse.
    for record in records:
        graph.add_node(
            record.dotted_path,
            file_path=record.file_path,
            is_package=_is_package(record),
            external_imports=0,
            parse_error=None,
        )

    # Second pass: parse each file and add edges for resolved imports.
    for record in records:
        _process_module(record, graph, internal_modules)

    return graph


def _is_package(record: ModuleRecord) -> bool:
    """Return True if the record represents an ``__init__.py`` file."""
    return record.file_path.name == "__init__.py"


def _process_module(
    record: ModuleRecord,
    graph: nx.DiGraph,
    internal_modules: set[str],
) -> None:
    """Parse one module and add edges for its resolved imports.

    On parse failure, records the error on the node and returns
    without adding edges. The node itself remains in the graph.
    """
    try:
        analysis = parse_file(record.file_path)
    except (SyntaxError, UnicodeDecodeError) as exc:
        graph.nodes[record.dotted_path]["parse_error"] = f"{type(exc).__name__}: {exc}"
        return

    is_package = _is_package(record)
    external_count = 0

    for import_info in analysis.imports:
        target = resolve_import(
            import_info,
            importer_dotted=record.dotted_path,
            importer_is_package=is_package,
            internal_modules=internal_modules,
        )
        if target is None:
            external_count += 1
            continue
        if target == record.dotted_path:
            # Self-imports are legal but uninteresting; skip the edge
            # to avoid polluting cycle detection with trivial loops.
            continue
        graph.add_edge(record.dotted_path, target)

    graph.nodes[record.dotted_path]["external_imports"] = external_count


def find_cycles(graph: nx.DiGraph) -> list[list[str]]:
    """Find all simple cycles in the dependency graph.

    A simple cycle is a closed path that visits no node more than
    once (except for the start node, which is also the end). In a
    dependency graph, each cycle represents a set of modules that
    form a circular import.

    The result is deterministic: cycles are sorted by length, then
    lexicographically by their member nodes, so the output is stable
    across runs.

    Args:
        graph: A directed graph produced by ``build_graph``.

    Returns:
        A list of cycles. Each cycle is a list of node dotted paths
        in traversal order. Returns an empty list if the graph is
        acyclic.
    """
    cycles = [list(cycle) for cycle in nx.simple_cycles(graph)]
    cycles.sort(key=lambda c: (len(c), c))
    return cycles
