"""Tests for the hotspot scoring analyzer.

Tests construct nx.DiGraph instances directly rather than going
through build_call_graph, so each test sets up exactly the node and
edge configuration it needs. The graph attribute conventions match
what build_call_graph produces: function nodes carry
``kind="function"`` and ``complexity``; synthetic nodes carry
``kind="external"`` or ``kind="unresolved"``.
"""

from __future__ import annotations

import networkx as nx
import pytest

from codemap.callgraph.hotspots import (
    HotspotEntry,
    compute_hotspots,
    top_hotspots,
)


def _function(complexity: int = 1) -> dict:
    """Attribute dict for a real function node."""
    return {"kind": "function", "complexity": complexity}


def _external() -> dict:
    return {"kind": "external"}


def _unresolved() -> dict:
    return {"kind": "unresolved"}


class TestEmptyAndTrivial:
    def test_empty_graph(self) -> None:
        graph: nx.DiGraph = nx.DiGraph()

        assert compute_hotspots(graph) == []

    def test_graph_with_only_synthetic_nodes(self) -> None:
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("os.path.join", **_external())
        graph.add_node("<unresolved>:mystery", **_unresolved())

        assert compute_hotspots(graph) == []

    def test_single_function_no_edges(self) -> None:
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("mod.foo", **_function(complexity=1))

        result = compute_hotspots(graph)

        assert result == [
            HotspotEntry(
                qualified_name="mod.foo",
                fan_in=0,
                fan_out=0,
                complexity=1,
                score=0,
            ),
        ]


class TestFanInAndOut:
    def test_simple_caller_callee_pair(self) -> None:
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("mod.caller", **_function(complexity=1))
        graph.add_node("mod.callee", **_function(complexity=1))
        graph.add_edge("mod.caller", "mod.callee", kind="internal")

        result = compute_hotspots(graph)
        by_name = {e.qualified_name: e for e in result}

        assert by_name["mod.caller"].fan_in == 0
        assert by_name["mod.caller"].fan_out == 1
        assert by_name["mod.callee"].fan_in == 1
        assert by_name["mod.callee"].fan_out == 0

    def test_function_with_many_callers(self) -> None:
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("mod.popular", **_function(complexity=1))
        for caller in ("mod.a", "mod.b", "mod.c", "mod.d"):
            graph.add_node(caller, **_function(complexity=1))
            graph.add_edge(caller, "mod.popular", kind="internal")

        result = compute_hotspots(graph)
        by_name = {e.qualified_name: e for e in result}

        assert by_name["mod.popular"].fan_in == 4
        assert by_name["mod.popular"].fan_out == 0

    def test_function_with_many_callees(self) -> None:
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("mod.orchestrator", **_function(complexity=1))
        for callee in ("mod.x", "mod.y", "mod.z"):
            graph.add_node(callee, **_function(complexity=1))
            graph.add_edge("mod.orchestrator", callee, kind="internal")

        result = compute_hotspots(graph)
        by_name = {e.qualified_name: e for e in result}

        assert by_name["mod.orchestrator"].fan_in == 0
        assert by_name["mod.orchestrator"].fan_out == 3

    def test_self_edge_contributes_to_fan_in(self) -> None:
        # A SELF edge points at a real method, so it counts toward
        # that method's fan-in just like an INTERNAL edge.
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("mod.Widget.run", **_function(complexity=1))
        graph.add_node("mod.Widget.helper", **_function(complexity=1))
        graph.add_edge("mod.Widget.run", "mod.Widget.helper", kind="self")

        result = compute_hotspots(graph)
        by_name = {e.qualified_name: e for e in result}

        assert by_name["mod.Widget.helper"].fan_in == 1
        assert by_name["mod.Widget.run"].fan_out == 1

    def test_fan_in_ignores_repeated_calls(self) -> None:
        # Edge collapsing in the builder means three calls to the
        # same target from one caller is still one edge. Fan-in
        # follows edges, not call_count.
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("mod.caller", **_function(complexity=1))
        graph.add_node("mod.target", **_function(complexity=1))
        graph.add_edge(
            "mod.caller",
            "mod.target",
            kind="internal",
            call_count=3,
        )

        result = compute_hotspots(graph)
        by_name = {e.qualified_name: e for e in result}

        assert by_name["mod.target"].fan_in == 1


class TestExternalAndUnresolvedTargets:
    def test_external_targets_do_not_inflate_fan_out(self) -> None:
        # A function that calls os.path.join still has fan_out=1
        # (the edge exists), but the external node is not in the
        # result list.
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("mod.foo", **_function(complexity=1))
        graph.add_node("os.path.join", **_external())
        graph.add_edge("mod.foo", "os.path.join", kind="external")

        result = compute_hotspots(graph)

        assert len(result) == 1
        assert result[0].qualified_name == "mod.foo"
        assert result[0].fan_out == 1

    def test_external_node_not_scored(self) -> None:
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("os.path.join", **_external())

        assert compute_hotspots(graph) == []

    def test_unresolved_node_not_scored(self) -> None:
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("<unresolved>:mystery", **_unresolved())

        assert compute_hotspots(graph) == []


class TestComplexityIntegration:
    def test_complexity_pulled_from_node_attr(self) -> None:
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("mod.simple", **_function(complexity=1))
        graph.add_node("mod.branchy", **_function(complexity=7))

        result = compute_hotspots(graph)
        by_name = {e.qualified_name: e for e in result}

        assert by_name["mod.simple"].complexity == 1
        assert by_name["mod.branchy"].complexity == 7

    def test_missing_complexity_attr_defaults_to_one(self) -> None:
        # Defensive: if for any reason a function node lacks the
        # complexity attribute, treat it as 1 rather than crashing.
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("mod.foo", kind="function")  # no complexity

        result = compute_hotspots(graph)

        assert result[0].complexity == 1


class TestScoreAndOrdering:
    def test_score_is_complexity_times_fan_in(self) -> None:
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("mod.target", **_function(complexity=4))
        for caller in ("mod.a", "mod.b", "mod.c"):
            graph.add_node(caller, **_function(complexity=1))
            graph.add_edge(caller, "mod.target", kind="internal")

        result = compute_hotspots(graph)
        by_name = {e.qualified_name: e for e in result}

        # 4 * 3 = 12
        assert by_name["mod.target"].score == 12

    def test_score_zero_when_no_callers(self) -> None:
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("mod.lonely", **_function(complexity=10))

        result = compute_hotspots(graph)

        assert result[0].score == 0

    def test_sorted_by_score_descending(self) -> None:
        # Three functions with different scores. low < mid < high.
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("mod.low", **_function(complexity=1))
        graph.add_node("mod.mid", **_function(complexity=2))
        graph.add_node("mod.high", **_function(complexity=5))
        graph.add_node("mod.caller1", **_function(complexity=1))
        graph.add_node("mod.caller2", **_function(complexity=1))

        # Give each target a distinct fan-in:
        graph.add_edge("mod.caller1", "mod.low", kind="internal")
        # mid: complexity 2, fan_in 2  -> score 4
        graph.add_edge("mod.caller1", "mod.mid", kind="internal")
        graph.add_edge("mod.caller2", "mod.mid", kind="internal")
        # high: complexity 5, fan_in 2 -> score 10
        graph.add_edge("mod.caller1", "mod.high", kind="internal")
        graph.add_edge("mod.caller2", "mod.high", kind="internal")

        result = compute_hotspots(graph)
        # Drop the callers from the comparison; we only care about
        # the relative ordering of the three targets.
        scored_targets = [
            e.qualified_name
            for e in result
            if e.qualified_name in {"mod.low", "mod.mid", "mod.high"}
        ]
        assert scored_targets == ["mod.high", "mod.mid", "mod.low"]

    def test_qname_tiebreaker_on_equal_score(self) -> None:
        # Two functions with the same score: they should be ordered
        # by qualified name ascending for determinism.
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("mod.zebra", **_function(complexity=2))
        graph.add_node("mod.apple", **_function(complexity=2))
        graph.add_node("mod.caller", **_function(complexity=1))

        graph.add_edge("mod.caller", "mod.zebra", kind="internal")
        graph.add_edge("mod.caller", "mod.apple", kind="internal")

        result = compute_hotspots(graph)
        names = [e.qualified_name for e in result if e.qualified_name in {"mod.apple", "mod.zebra"}]

        assert names == ["mod.apple", "mod.zebra"]


class TestTopHotspots:
    def test_returns_first_n(self) -> None:
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("mod.caller", **_function(complexity=1))
        for i, c in enumerate([5, 4, 3, 2, 1]):
            name = f"mod.t{i}"
            graph.add_node(name, **_function(complexity=c))
            graph.add_edge("mod.caller", name, kind="internal")

        result = top_hotspots(graph, n=3)

        assert len(result) == 3
        assert [e.qualified_name for e in result] == [
            "mod.t0",
            "mod.t1",
            "mod.t2",
        ]

    def test_n_zero_returns_empty(self) -> None:
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("mod.foo", **_function(complexity=1))

        assert top_hotspots(graph, n=0) == []

    def test_n_larger_than_total_returns_all(self) -> None:
        graph: nx.DiGraph = nx.DiGraph()
        graph.add_node("mod.a", **_function(complexity=1))
        graph.add_node("mod.b", **_function(complexity=1))

        result = top_hotspots(graph, n=10)

        assert len(result) == 2

    def test_negative_n_raises(self) -> None:
        graph: nx.DiGraph = nx.DiGraph()

        with pytest.raises(ValueError, match="n must be >= 0"):
            top_hotspots(graph, n=-1)


class TestEntryProperties:
    def test_entry_is_immutable(self) -> None:
        entry = HotspotEntry(
            qualified_name="mod.foo",
            fan_in=1,
            fan_out=2,
            complexity=3,
            score=3,
        )

        with pytest.raises(AttributeError):
            entry.score = 99  # type: ignore[misc]

    def test_entry_equality_by_value(self) -> None:
        a = HotspotEntry("mod.foo", 1, 2, 3, 3)
        b = HotspotEntry("mod.foo", 1, 2, 3, 3)

        assert a == b
        assert hash(a) == hash(b)
