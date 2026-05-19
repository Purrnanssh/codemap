"""Rich-based renderers for AST analysis results.

This module turns ``FileAnalysis`` objects into Rich renderables
that can be printed to the terminal. It contains no parsing logic
and no CLI logic; it is a pure presentation layer so it can be
tested in isolation.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from codemap.ast_engine.models import FileAnalysis


def render_analysis(analysis: FileAnalysis) -> Group:
    """Render a FileAnalysis as a Rich Group of panels.

    The Group contains, in order:
        - A header panel naming the file
        - One panel per category (imports, functions, classes, calls)

    Args:
        analysis: The parsed file analysis to render.

    Returns:
        A Rich Group that can be printed to a Console.
    """
    return Group(
        _header_panel(analysis),
        _imports_panel(analysis),
        _functions_panel(analysis),
        _classes_panel(analysis),
        _calls_panel(analysis),
    )


def _header_panel(analysis: FileAnalysis) -> Panel:
    """Build the top header panel naming the file under analysis."""
    title = Text("🗺️  CodeMap Analysis", style="bold cyan")
    subtitle = Text(str(analysis.path), style="dim")
    return Panel(
        Group(title, subtitle),
        border_style="cyan",
    )


def _imports_panel(analysis: FileAnalysis) -> Panel:
    """Build a panel listing every import in the file."""
    if not analysis.imports:
        return _empty_panel("Imports")

    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Module")
    table.add_column("Name")
    table.add_column("Alias")
    table.add_column("Line", justify="right")

    for imp in analysis.imports:
        table.add_row(
            imp.module or "(relative)",
            imp.name,
            imp.alias or "-",
            str(imp.line),
        )

    return Panel(table, title=f"Imports ({len(analysis.imports)})", border_style="magenta")


def _functions_panel(analysis: FileAnalysis) -> Panel:
    """Build a panel listing every top-level function in the file."""
    if not analysis.functions:
        return _empty_panel("Functions")

    table = Table(show_header=True, header_style="bold green", expand=True)
    table.add_column("Name")
    table.add_column("Args")
    table.add_column("Async", justify="center")
    table.add_column("Line", justify="right")

    for fn in analysis.functions:
        args_repr = "(" + ", ".join(fn.args) + ")" if fn.args else "()"
        table.add_row(
            fn.name,
            args_repr,
            "yes" if fn.is_async else "no",
            str(fn.line),
        )

    return Panel(table, title=f"Functions ({len(analysis.functions)})", border_style="green")


def _classes_panel(analysis: FileAnalysis) -> Panel:
    """Build a panel listing every top-level class and its methods."""
    if not analysis.classes:
        return _empty_panel("Classes")

    table = Table(show_header=True, header_style="bold yellow", expand=True)
    table.add_column("Class")
    table.add_column("Method")
    table.add_column("Args")
    table.add_column("Async", justify="center")
    table.add_column("Line", justify="right")

    for cls in analysis.classes:
        if not cls.methods:
            table.add_row(cls.name, "(no methods)", "", "", str(cls.line))
            continue
        for i, method in enumerate(cls.methods):
            args_repr = "(" + ", ".join(method.args) + ")" if method.args else "()"
            table.add_row(
                cls.name if i == 0 else "",
                method.name,
                args_repr,
                "yes" if method.is_async else "no",
                str(method.line),
            )

    return Panel(table, title=f"Classes ({len(analysis.classes)})", border_style="yellow")


def _calls_panel(analysis: FileAnalysis) -> Panel:
    """Build a panel listing every call site in the file."""
    if not analysis.calls:
        return _empty_panel("Calls")

    table = Table(show_header=True, header_style="bold blue", expand=True)
    table.add_column("Callee")
    table.add_column("Line", justify="right")

    for call in analysis.calls:
        table.add_row(call.callee, str(call.line))

    return Panel(table, title=f"Calls ({len(analysis.calls)})", border_style="blue")


def _empty_panel(label: str) -> Panel:
    """Build a placeholder panel for a category that has no entries."""
    return Panel(
        Text("(none)", style="dim italic"),
        title=f"{label} (0)",
        border_style="dim",
    )


# ===========================================================================
# Phase 3: Graph summary rendering
# ===========================================================================


def render_graph_summary(
    graph: nx.DiGraph,
    cycles: list[list[str]],
    root: Path,
) -> Group:
    """Render a dependency-graph summary as a Rich Group of panels.

    The Group contains, in order:
        - A header panel naming the scanned root
        - A stats panel (totals: modules, edges, externals, cycles, errors)
        - A top-imported-modules panel (modules ranked by in-degree)
        - A cycles panel (only if cycles exist)
        - A parse-errors panel (only if errors exist)

    Args:
        graph: The dependency graph produced by ``build_graph``.
        cycles: The cycle list produced by ``find_cycles``.
        root: The scanned project root (for display only).

    Returns:
        A Rich Group that can be printed to a Console.
    """
    panels: list[Panel] = [
        _graph_header_panel(root),
        _stats_panel(graph, cycles),
        _top_imported_panel(graph),
    ]
    if cycles:
        panels.append(_cycles_panel(cycles))
    if _has_parse_errors(graph):
        panels.append(_parse_errors_panel(graph))
    return Group(*panels)


def _graph_header_panel(root: Path) -> Panel:
    """Build the top header panel naming the scanned project."""
    title = Text("🕸️  CodeMap Dependency Graph", style="bold cyan")
    subtitle = Text(str(root), style="dim")
    return Panel(
        Group(title, subtitle),
        border_style="cyan",
    )


def _stats_panel(graph: nx.DiGraph, cycles: list[list[str]]) -> Panel:
    """Build a panel showing top-level counts."""
    total_external = sum(
        int(attrs.get("external_imports", 0)) for _, attrs in graph.nodes(data=True)
    )
    error_count = sum(1 for _, attrs in graph.nodes(data=True) if attrs.get("parse_error"))

    table = Table(show_header=False, expand=True, box=None)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Modules", str(graph.number_of_nodes()))
    table.add_row("Internal edges", str(graph.number_of_edges()))
    table.add_row("External imports", str(total_external))
    table.add_row("Cycles", str(len(cycles)))
    table.add_row("Parse errors", str(error_count))

    return Panel(table, title="Stats", border_style="magenta")


def _top_imported_panel(graph: nx.DiGraph, limit: int = 10) -> Panel:
    """Build a panel listing modules with the highest in-degree."""
    if graph.number_of_nodes() == 0:
        return _empty_panel("Top imported")

    # Rank modules by in-degree (how many other modules import them).
    # Ties broken alphabetically for stable output.
    ranked = sorted(
        graph.nodes(),
        key=lambda n: (-graph.in_degree(n), n),
    )[:limit]

    table = Table(show_header=True, header_style="bold green", expand=True)
    table.add_column("Rank", justify="right")
    table.add_column("Module")
    table.add_column("Imported by", justify="right")

    for i, name in enumerate(ranked, start=1):
        table.add_row(str(i), name, str(graph.in_degree(name)))

    return Panel(
        table,
        title=f"Top imported (max {limit})",
        border_style="green",
    )


def _cycles_panel(cycles: list[list[str]]) -> Panel:
    """Build a panel listing every detected circular dependency."""
    table = Table(show_header=True, header_style="bold red", expand=True)
    table.add_column("#", justify="right")
    table.add_column("Length", justify="right")
    table.add_column("Cycle")

    for i, cycle in enumerate(cycles, start=1):
        # Render as A -> B -> C -> A to make the loop visually obvious.
        path = " -> ".join([*cycle, cycle[0]])
        table.add_row(str(i), str(len(cycle)), path)

    return Panel(table, title=f"Cycles ({len(cycles)})", border_style="red")


def _has_parse_errors(graph: nx.DiGraph) -> bool:
    """Return True if any node has a non-None parse_error attribute."""
    return any(attrs.get("parse_error") for _, attrs in graph.nodes(data=True))


def _parse_errors_panel(graph: nx.DiGraph) -> Panel:
    """Build a panel listing modules that failed to parse."""
    rows = [
        (name, str(attrs["parse_error"]))
        for name, attrs in graph.nodes(data=True)
        if attrs.get("parse_error")
    ]
    rows.sort(key=lambda row: row[0])

    table = Table(show_header=True, header_style="bold yellow", expand=True)
    table.add_column("Module")
    table.add_column("Error")

    for name, err in rows:
        table.add_row(name, err)

    return Panel(table, title=f"Parse errors ({len(rows)})", border_style="yellow")
