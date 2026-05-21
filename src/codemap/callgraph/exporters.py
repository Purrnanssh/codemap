"""Export the symbol-level call graph to DOT and JSON.

This module provides two exporters that consume a call graph
produced by ``callgraph.builder`` and serialize it for use outside
the pipeline:

    to_json     A flat ``{"nodes": [...], "edges": [...]}`` shape.
                Round-trips every node and edge attribute. Suitable
                for consumption by any external tool or for diffing
                between runs.

    to_dot      Graphviz DOT format. Function nodes are colored by
                complexity (light at 1, dark red at high values),
                external and unresolved nodes use dashed outlines,
                and edges are colored by kind. Render with
                ``dot -Tpng output.dot -o output.png``.

Both exporters accept an optional ``min_complexity`` filter. When
set, function nodes below the threshold are dropped along with any
edges touching them. Synthetic nodes (external, unresolved) whose
only edges got filtered out are dropped too.

The exporters are pure: graph in, string out. Writing to disk is
the caller's responsibility (this is the CLI's job in step 8).
"""

from __future__ import annotations

import json
from typing import Any

import networkx as nx

# Maximum complexity at which the color gradient saturates.
# Functions above this value all get the darkest color.
_COMPLEXITY_GRADIENT_CEILING = 10

# Color gradient from low complexity (cool blue) to high (warm red).
# Indexed 0..10, corresponding to complexity 1..11+.
_COMPLEXITY_PALETTE = (
    "#e0f3ff",  # 1: very light blue
    "#c7e9f1",  # 2
    "#a8d5e2",  # 3
    "#80c1d4",  # 4
    "#fce7c5",  # 5: shifting to warm
    "#fbcfa0",  # 6
    "#f9a875",  # 7
    "#f47e51",  # 8
    "#e45a3a",  # 9
    "#c93a2c",  # 10
    "#9b1e1e",  # 11+: saturated dark red
)

_SYNTHETIC_KINDS = frozenset({"external", "unresolved"})


def to_json(
    graph: nx.DiGraph,
    min_complexity: int = 0,
    pretty: bool = True,
) -> str:
    """Serialize the call graph to a flat JSON document.

    The shape is::

        {
          "nodes": [
            {"id": "<qname>", "kind": "function|external|unresolved",
             ...further attributes for function nodes...},
            ...
          ],
          "edges": [
            {"source": "<qname>", "target": "<qname>",
             "kind": "internal|self|external|unresolved",
             "call_count": int, "first_line": int},
            ...
          ]
        }

    Function node attributes are emitted verbatim. Synthetic nodes
    (external, unresolved) carry only ``id`` and ``kind``.

    Args:
        graph: A call graph from ``build_call_graph``.
        min_complexity: Drop function nodes below this McCabe score,
            along with edges touching them. Default 0 means no
            filtering.
        pretty: If True (default), the output is pretty-printed with
            two-space indentation. If False, the output is compact.

    Returns:
        The JSON string. Always ends with a trailing newline when
        pretty, no trailing newline when compact.
    """
    filtered = _filter_graph(graph, min_complexity)

    nodes_payload = [
        _json_node(node_id, attrs) for node_id, attrs in sorted(filtered.nodes(data=True))
    ]
    edges_payload = [
        _json_edge(source, target, attrs)
        for source, target, attrs in sorted(
            filtered.edges(data=True),
            key=lambda e: (e[0], e[1]),
        )
    ]

    document = {"nodes": nodes_payload, "edges": edges_payload}

    if pretty:
        return json.dumps(document, indent=2, sort_keys=False) + "\n"
    return json.dumps(document, separators=(",", ":"))


def to_dot(
    graph: nx.DiGraph,
    min_complexity: int = 0,
) -> str:
    """Serialize the call graph to Graphviz DOT format.

    Function nodes are filled boxes colored by complexity. Methods
    have a thicker border; async functions have a doubled border.
    External nodes are dashed gray ellipses. Unresolved nodes are
    dotted gray ellipses with the ``<unresolved>:`` prefix stripped
    from their display label.

    Edges are colored by kind:
        internal    solid black
        self        solid steel blue
        external    dashed light gray
        unresolved  dotted light gray

    Args:
        graph: A call graph from ``build_call_graph``.
        min_complexity: Drop function nodes below this McCabe score,
            along with edges touching them. Default 0 means no
            filtering.

    Returns:
        The DOT source as a string. Includes a trailing newline.
        Render with ``dot -Tpng output.dot -o output.png``.
    """
    filtered = _filter_graph(graph, min_complexity)

    lines: list[str] = []
    lines.append("digraph CodeMap {")
    lines.append("  rankdir=LR;")
    lines.append('  node [fontname="Helvetica", fontsize=10];')
    lines.append('  edge [fontname="Helvetica", fontsize=9];')
    lines.append("")

    for node_id, attrs in sorted(filtered.nodes(data=True)):
        lines.append(_dot_node_line(node_id, attrs))

    if filtered.nodes:
        lines.append("")

    for source, target, attrs in sorted(
        filtered.edges(data=True),
        key=lambda e: (e[0], e[1]),
    ):
        lines.append(_dot_edge_line(source, target, attrs))

    lines.append("}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def _filter_graph(
    graph: nx.DiGraph,
    min_complexity: int,
) -> nx.DiGraph:
    """Return a graph filtered by minimum complexity.

    Function nodes whose complexity is below ``min_complexity`` are
    dropped. Edges touching dropped nodes vanish with them. Synthetic
    nodes (external, unresolved) that lose all their edges after the
    filter are dropped too, so the output is not littered with orphan
    targets.

    If ``min_complexity`` is 0 or negative the original graph is
    returned unchanged (no copy).
    """
    if min_complexity <= 0:
        return graph

    kept = _select_kept_nodes(graph, min_complexity)
    subgraph = graph.subgraph(kept).copy()
    _drop_orphan_synthetic_nodes(subgraph)
    return subgraph


def _select_kept_nodes(
    graph: nx.DiGraph,
    min_complexity: int,
) -> set[str]:
    """Return the set of node ids that survive the complexity filter.

    Function nodes survive only when their complexity meets the
    threshold. Synthetic nodes (external, unresolved) survive the
    first pass unconditionally; pruning their orphans is the second
    pass's responsibility.
    """
    kept: set[str] = set()
    for node, attrs in graph.nodes(data=True):
        if attrs.get("kind") != "function":
            kept.add(node)
            continue
        if attrs.get("complexity", 1) >= min_complexity:
            kept.add(node)
    return kept


def _drop_orphan_synthetic_nodes(subgraph: nx.DiGraph) -> None:
    """Mutate ``subgraph`` in place to remove synthetic nodes with no edges.

    Synthetic nodes only earn their place in the graph by being the
    target of some function's call. Once filtering has removed every
    function that referenced them, they no longer carry meaning and
    would just clutter the output.
    """
    orphans = [
        node
        for node, attrs in subgraph.nodes(data=True)
        if attrs.get("kind") in _SYNTHETIC_KINDS and subgraph.degree(node) == 0
    ]
    subgraph.remove_nodes_from(orphans)


# ---------------------------------------------------------------------------
# JSON serialization
# ---------------------------------------------------------------------------


_JSON_FUNCTION_ATTRS = (
    "module",
    "class_name",
    "name",
    "line",
    "is_method",
    "is_async",
    "complexity",
)


def _json_node(node_id: str, attrs: dict[str, Any]) -> dict[str, Any]:
    """Build the JSON payload for one node."""
    payload: dict[str, Any] = {
        "id": node_id,
        "kind": attrs.get("kind", "function"),
    }
    if attrs.get("kind") == "function":
        for key in _JSON_FUNCTION_ATTRS:
            if key in attrs:
                payload[key] = attrs[key]
    return payload


def _json_edge(source: str, target: str, attrs: dict[str, Any]) -> dict[str, Any]:
    """Build the JSON payload for one edge."""
    payload: dict[str, Any] = {
        "source": source,
        "target": target,
        "kind": attrs.get("kind", "internal"),
    }
    if "call_count" in attrs:
        payload["call_count"] = attrs["call_count"]
    if "first_line" in attrs:
        payload["first_line"] = attrs["first_line"]
    return payload


# ---------------------------------------------------------------------------
# DOT serialization
# ---------------------------------------------------------------------------


def _dot_node_line(node_id: str, attrs: dict[str, Any]) -> str:
    """Format one node as a DOT statement."""
    kind = attrs.get("kind", "function")

    if kind == "function":
        return _dot_function_node(node_id, attrs)
    if kind == "external":
        return _dot_synthetic_node(node_id, kind, style="dashed", color="#666666")
    if kind == "unresolved":
        return _dot_synthetic_node(node_id, kind, style="dotted", color="#888888")
    # Unknown kind: bare node.
    return f'  "{node_id}";'


def _dot_function_node(node_id: str, attrs: dict[str, Any]) -> str:
    """Format a function node with complexity-driven color and decorations."""
    label = _dot_label(node_id, "function")
    complexity = attrs.get("complexity", 1)
    color = _complexity_color(complexity)

    parts = [
        f'label="{label}"',
        "shape=box",
        "style=filled",
        f'fillcolor="{color}"',
    ]
    if attrs.get("is_async"):
        parts.append("peripheries=2")
    elif attrs.get("is_method"):
        parts.append("penwidth=2")
    return f'  "{node_id}" [{", ".join(parts)}];'


def _dot_synthetic_node(
    node_id: str,
    kind: str,
    style: str,
    color: str,
) -> str:
    """Format an external or unresolved node with dashed/dotted styling."""
    label = _dot_label(node_id, kind)
    parts = [
        f'label="{label}"',
        "shape=ellipse",
        f"style={style}",
        f'color="{color}"',
        f'fontcolor="{color}"',
    ]
    return f'  "{node_id}" [{", ".join(parts)}];'


_EDGE_STYLE_BY_KIND = {
    "self": 'style=solid, color="#4682b4"',
    "external": 'style=dashed, color="#999999"',
    "unresolved": 'style=dotted, color="#999999"',
}
_INTERNAL_EDGE_STYLE = 'style=solid, color="black"'


def _dot_edge_line(source: str, target: str, attrs: dict[str, Any]) -> str:
    """Format one edge as a DOT statement."""
    kind = attrs.get("kind", "internal")
    style = _EDGE_STYLE_BY_KIND.get(kind, _INTERNAL_EDGE_STYLE)
    return f'  "{source}" -> "{target}" [{style}];'


def _dot_label(node_id: str, kind: str) -> str:
    """Build a human-readable label for one node.

    Function nodes use their qualified name as-is. Unresolved nodes
    strip the ``<unresolved>:`` prefix so the label shows just the
    callee expression that couldn't be pinned down. External nodes
    use the qualified name unchanged.

    Special characters that would break DOT (quotes, backslashes)
    are escaped.
    """
    if kind == "unresolved" and node_id.startswith("<unresolved>:"):
        label = node_id[len("<unresolved>:") :]
    else:
        label = node_id

    label = label.replace("\\", "\\\\").replace('"', '\\"')
    return label


def _complexity_color(complexity: int) -> str:
    """Pick a fill color from the complexity gradient.

    Complexity 1 maps to index 0 (lightest), complexity 11+ maps to
    index 10 (darkest). Values are clamped at both ends.
    """
    if complexity < 1:
        index = 0
    elif complexity > _COMPLEXITY_GRADIENT_CEILING + 1:
        index = _COMPLEXITY_GRADIENT_CEILING
    else:
        index = complexity - 1
    return _COMPLEXITY_PALETTE[index]
