"""Hotspot scoring for the symbol-level call graph.

A hotspot is a function whose combination of complexity and call
patterns makes it interesting to look at first when reading or
refactoring an unfamiliar codebase. This module computes three
independent metrics per function and a composite score:

    fan_in       Number of distinct functions that call this one.
                 High fan-in = critical; breaking it breaks a lot.

    fan_out      Number of distinct functions this one calls.
                 High fan-out = coordinator; hard to test in
                 isolation.

    complexity   McCabe cyclomatic complexity, already attached to
                 the node by the builder.

    score        complexity * fan_in. The default ranking. Surfaces
                 functions that are both branchy and widely depended
                 on, which are the riskiest to change.

Only real function nodes (``kind="function"``) are scored. External
and unresolved synthetic nodes are skipped because they are not
project code. Fan-in naturally counts only INTERNAL and SELF edges,
since those are the only edge kinds that target real functions.

This module performs no graph construction. It is a pure read-only
analyzer over a graph built by ``callgraph.builder``.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx


@dataclass(frozen=True, slots=True)
class HotspotEntry:
    """One function's hotspot metrics.

    All fields are derived from the call graph and the node's
    complexity attribute. Equality is by value; sorting is by score
    descending then qualified name ascending, but that ordering is
    applied by ``compute_hotspots`` when building the list, not by
    this class itself.
    """

    qualified_name: str
    fan_in: int
    fan_out: int
    complexity: int
    score: int


def compute_hotspots(graph: nx.DiGraph) -> list[HotspotEntry]:
    """Compute hotspot metrics for every function in the call graph.

    Walks the graph once and produces one ``HotspotEntry`` per real
    function node, with fan-in, fan-out, complexity, and the default
    composite score (``complexity * fan_in``).

    The returned list is sorted by score descending, with qualified
    name as a deterministic tiebreaker (ascending). Functions with
    score 0 (typically because they have no callers) still appear in
    the list; consumers can filter or limit the output as needed.

    Args:
        graph: A call graph produced by ``build_call_graph``. Real
            function nodes must carry the ``kind="function"`` and
            ``complexity`` attributes set by the builder.

    Returns:
        A list of ``HotspotEntry`` instances, sorted as described
        above. Returns an empty list if the graph contains no real
        function nodes.
    """
    entries: list[HotspotEntry] = []

    for node, attrs in graph.nodes(data=True):
        if attrs.get("kind") != "function":
            continue

        fan_in = graph.in_degree(node)
        fan_out = graph.out_degree(node)
        complexity = attrs.get("complexity", 1)
        score = complexity * fan_in

        entries.append(
            HotspotEntry(
                qualified_name=node,
                fan_in=fan_in,
                fan_out=fan_out,
                complexity=complexity,
                score=score,
            )
        )

    entries.sort(key=lambda e: (-e.score, e.qualified_name))
    return entries


def top_hotspots(
    graph: nx.DiGraph,
    n: int,
) -> list[HotspotEntry]:
    """Return the top ``n`` hotspots, ordered by descending score.

    A thin convenience wrapper over ``compute_hotspots`` that takes
    the first ``n`` entries. Useful for CLI summaries.

    Args:
        graph: A call graph produced by ``build_call_graph``.
        n: Maximum number of entries to return. Must be >= 0. If
            zero, returns an empty list. If larger than the number
            of function nodes, returns all of them.

    Returns:
        A list of up to ``n`` ``HotspotEntry`` instances.

    Raises:
        ValueError: If ``n`` is negative.
    """
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    return compute_hotspots(graph)[:n]
