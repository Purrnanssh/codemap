"""Tests for graph-summary rendering in codemap.rendering."""

from __future__ import annotations

from pathlib import Path

import networkx as nx
from rich.console import Console

from codemap.rendering import render_graph_summary


def _render_to_text(renderable: object, width: int = 200) -> str:
    """Render a Rich renderable into plain text for substring assertions.

    Width defaults to 200 (wider than a typical terminal) to avoid line
    wrapping interfering with substring matching. Tests that specifically
    care about wrap behavior can override.
    """
    console = Console(record=True, width=width, color_system=None)
    console.print(renderable)
    return console.export_text()


def _make_graph(
    nodes: list[tuple[str, dict[str, object]]],
    edges: list[tuple[str, str]],
) -> nx.DiGraph:
    """Helper: build a DiGraph from explicit nodes/edges with attributes."""
    graph: nx.DiGraph = nx.DiGraph()
    for name, attrs in nodes:
        graph.add_node(name, **attrs)
    for src, dst in edges:
        graph.add_edge(src, dst)
    return graph


# ---------------------------------------------------------------------------
# Structural panels
# ---------------------------------------------------------------------------


def test_header_includes_root_path(tmp_path: Path) -> None:
    """The header panel shows the scanned root path."""
    graph: nx.DiGraph = nx.DiGraph()
    # Use a wide console so the path doesn't wrap mid-string.
    output = _render_to_text(render_graph_summary(graph, [], tmp_path), width=400)
    assert str(tmp_path) in output


def test_stats_panel_shows_zero_counts_on_empty_graph(tmp_path: Path) -> None:
    """An empty graph reports zero modules, edges, etc."""
    graph: nx.DiGraph = nx.DiGraph()
    output = _render_to_text(render_graph_summary(graph, [], tmp_path))
    assert "Modules" in output
    assert "Internal edges" in output
    assert "External imports" in output
    assert "Cycles" in output
    assert "Parse errors" in output


def test_stats_panel_reflects_graph_size(tmp_path: Path) -> None:
    """Stats counts match the graph contents."""
    graph = _make_graph(
        nodes=[
            ("a", {"external_imports": 3, "parse_error": None}),
            ("b", {"external_imports": 1, "parse_error": None}),
            ("c", {"external_imports": 0, "parse_error": None}),
        ],
        edges=[("a", "b"), ("b", "c")],
    )
    output = _render_to_text(render_graph_summary(graph, [], tmp_path))
    # 3 modules, 2 edges, 4 external imports total
    assert "Modules" in output
    assert "3" in output  # modules count
    assert "External imports" in output


# ---------------------------------------------------------------------------
# Top-imported ranking
# ---------------------------------------------------------------------------


def test_top_imported_shows_modules_by_in_degree(tmp_path: Path) -> None:
    """Modules with more incoming edges rank higher."""
    graph = _make_graph(
        nodes=[
            ("hub", {"external_imports": 0, "parse_error": None}),
            ("a", {"external_imports": 0, "parse_error": None}),
            ("b", {"external_imports": 0, "parse_error": None}),
            ("c", {"external_imports": 0, "parse_error": None}),
        ],
        edges=[("a", "hub"), ("b", "hub"), ("c", "hub")],
    )
    output = _render_to_text(render_graph_summary(graph, [], tmp_path))
    assert "Top imported" in output
    assert "hub" in output


# ---------------------------------------------------------------------------
# Cycles panel: conditional rendering
# ---------------------------------------------------------------------------


def test_no_cycles_panel_when_no_cycles(tmp_path: Path) -> None:
    """The cycles panel is omitted when the cycle list is empty."""
    graph: nx.DiGraph = nx.DiGraph()
    output = _render_to_text(render_graph_summary(graph, [], tmp_path))
    # The stats panel still has a "Cycles" row, but no dedicated panel.
    # Heuristic: the cycles PANEL title says "Cycles (N)" with a count.
    assert "Cycles (0)" not in output  # no zero-count panel
    assert "Cycles (1)" not in output  # no panel at all when empty


def test_cycles_panel_renders_arrow_chain(tmp_path: Path) -> None:
    """Each cycle is rendered as A -> B -> A to make the loop visible."""
    graph = _make_graph(
        nodes=[
            ("pkg.a", {"external_imports": 0, "parse_error": None}),
            ("pkg.b", {"external_imports": 0, "parse_error": None}),
        ],
        edges=[("pkg.a", "pkg.b"), ("pkg.b", "pkg.a")],
    )
    cycles = [["pkg.a", "pkg.b"]]
    output = _render_to_text(render_graph_summary(graph, cycles, tmp_path))
    assert "pkg.a -> pkg.b -> pkg.a" in output


def test_cycles_panel_shows_count(tmp_path: Path) -> None:
    """The cycles panel title shows the number of cycles."""
    graph: nx.DiGraph = nx.DiGraph()
    graph.add_node("a", external_imports=0, parse_error=None)
    graph.add_node("b", external_imports=0, parse_error=None)
    cycles = [["a", "b"]]
    output = _render_to_text(render_graph_summary(graph, cycles, tmp_path))
    assert "Cycles (1)" in output


# ---------------------------------------------------------------------------
# Parse errors panel: conditional rendering
# ---------------------------------------------------------------------------


def test_no_parse_errors_panel_when_clean(tmp_path: Path) -> None:
    """The parse-errors panel is omitted when every node parsed cleanly."""
    graph = _make_graph(
        nodes=[("a", {"external_imports": 0, "parse_error": None})],
        edges=[],
    )
    output = _render_to_text(render_graph_summary(graph, [], tmp_path))
    assert "Parse errors (0)" not in output
    assert "Parse errors (1)" not in output


def test_parse_errors_panel_shows_broken_modules(tmp_path: Path) -> None:
    """The parse-errors panel lists each broken module and its error."""
    graph = _make_graph(
        nodes=[
            ("good", {"external_imports": 0, "parse_error": None}),
            ("bad", {"external_imports": 0, "parse_error": "SyntaxError: invalid syntax"}),
        ],
        edges=[],
    )
    output = _render_to_text(render_graph_summary(graph, [], tmp_path))
    assert "Parse errors (1)" in output
    assert "bad" in output
    assert "SyntaxError" in output
