"""Tests for the DOT and JSON exporters.

Tests construct nx.DiGraph instances directly to keep the focus on
serialization. Both exporters are pure: graph in, string out. We
parse the JSON output back for structural assertions, and we
substring-check the DOT output for the styling we care about
without trying to lock down the exact byte layout.
"""

from __future__ import annotations

import json

import networkx as nx

from codemap.callgraph.exporters import to_dot, to_json


def _function(complexity: int = 1, **extra: object) -> dict:
    base = {
        "kind": "function",
        "complexity": complexity,
        "module": "mod",
        "name": "fn",
        "line": 1,
        "is_method": False,
        "is_async": False,
        "class_name": None,
    }
    base.update(extra)
    return base


def _external() -> dict:
    return {"kind": "external"}


def _unresolved() -> dict:
    return {"kind": "unresolved"}


def _two_func_graph() -> nx.DiGraph:
    """A minimal graph: two functions, one calls the other."""
    g: nx.DiGraph = nx.DiGraph()
    g.add_node("mod.foo", **_function(complexity=1, name="foo"))
    g.add_node("mod.bar", **_function(complexity=3, name="bar"))
    g.add_edge(
        "mod.foo",
        "mod.bar",
        kind="internal",
        call_count=1,
        first_line=2,
    )
    return g


class TestJsonShape:
    def test_empty_graph(self) -> None:
        result = to_json(nx.DiGraph())
        doc = json.loads(result)

        assert doc == {"nodes": [], "edges": []}

    def test_top_level_keys(self) -> None:
        doc = json.loads(to_json(_two_func_graph()))

        assert set(doc.keys()) == {"nodes", "edges"}

    def test_function_node_carries_attributes(self) -> None:
        doc = json.loads(to_json(_two_func_graph()))

        by_id = {n["id"]: n for n in doc["nodes"]}
        foo = by_id["mod.foo"]

        assert foo["kind"] == "function"
        assert foo["name"] == "foo"
        assert foo["module"] == "mod"
        assert foo["complexity"] == 1
        assert foo["is_method"] is False
        assert foo["is_async"] is False

    def test_synthetic_nodes_carry_only_id_and_kind(self) -> None:
        g: nx.DiGraph = nx.DiGraph()
        g.add_node("mod.foo", **_function())
        g.add_node("os.path.join", **_external())
        g.add_node("<unresolved>:mystery", **_unresolved())
        g.add_edge("mod.foo", "os.path.join", kind="external")
        g.add_edge("mod.foo", "<unresolved>:mystery", kind="unresolved")

        doc = json.loads(to_json(g))
        by_id = {n["id"]: n for n in doc["nodes"]}

        assert by_id["os.path.join"] == {
            "id": "os.path.join",
            "kind": "external",
        }
        assert by_id["<unresolved>:mystery"] == {
            "id": "<unresolved>:mystery",
            "kind": "unresolved",
        }

    def test_edges_carry_kind_and_metadata(self) -> None:
        doc = json.loads(to_json(_two_func_graph()))

        assert len(doc["edges"]) == 1
        edge = doc["edges"][0]
        assert edge["source"] == "mod.foo"
        assert edge["target"] == "mod.bar"
        assert edge["kind"] == "internal"
        assert edge["call_count"] == 1
        assert edge["first_line"] == 2

    def test_nodes_and_edges_sorted_deterministically(self) -> None:
        # Build a graph with nodes inserted in non-sorted order.
        g: nx.DiGraph = nx.DiGraph()
        g.add_node("mod.zebra", **_function())
        g.add_node("mod.apple", **_function())
        g.add_node("mod.mango", **_function())
        g.add_edge("mod.zebra", "mod.apple", kind="internal")
        g.add_edge("mod.mango", "mod.apple", kind="internal")

        doc = json.loads(to_json(g))
        node_ids = [n["id"] for n in doc["nodes"]]
        edge_pairs = [(e["source"], e["target"]) for e in doc["edges"]]

        assert node_ids == sorted(node_ids)
        assert edge_pairs == sorted(edge_pairs)

    def test_pretty_vs_compact(self) -> None:
        g = _two_func_graph()
        pretty = to_json(g, pretty=True)
        compact = to_json(g, pretty=False)

        # Pretty has newlines, compact does not.
        assert "\n" in pretty
        assert "\n" not in compact
        # Compact has no spaces after separators.
        assert ", " not in compact
        # Both parse to the same object.
        assert json.loads(pretty) == json.loads(compact)


class TestJsonFiltering:
    def test_min_complexity_drops_low_functions(self) -> None:
        g: nx.DiGraph = nx.DiGraph()
        g.add_node("mod.low", **_function(complexity=1, name="low"))
        g.add_node("mod.high", **_function(complexity=5, name="high"))

        doc = json.loads(to_json(g, min_complexity=3))
        node_ids = {n["id"] for n in doc["nodes"]}

        assert node_ids == {"mod.high"}

    def test_filtered_edges_dropped(self) -> None:
        g: nx.DiGraph = nx.DiGraph()
        g.add_node("mod.low", **_function(complexity=1))
        g.add_node("mod.high", **_function(complexity=5))
        g.add_edge("mod.low", "mod.high", kind="internal")

        doc = json.loads(to_json(g, min_complexity=3))

        assert doc["edges"] == []

    def test_orphan_external_nodes_dropped(self) -> None:
        # mod.low calls os.path.join. After filtering mod.low out,
        # os.path.join has no edges and should disappear too.
        g: nx.DiGraph = nx.DiGraph()
        g.add_node("mod.low", **_function(complexity=1))
        g.add_node("os.path.join", **_external())
        g.add_edge("mod.low", "os.path.join", kind="external")

        doc = json.loads(to_json(g, min_complexity=3))

        assert doc["nodes"] == []

    def test_external_node_kept_if_still_referenced(self) -> None:
        # mod.low (complexity 1) and mod.high (complexity 5) both
        # call os.path.join. After filtering, mod.high remains and
        # so does the external node.
        g: nx.DiGraph = nx.DiGraph()
        g.add_node("mod.low", **_function(complexity=1))
        g.add_node("mod.high", **_function(complexity=5))
        g.add_node("os.path.join", **_external())
        g.add_edge("mod.low", "os.path.join", kind="external")
        g.add_edge("mod.high", "os.path.join", kind="external")

        doc = json.loads(to_json(g, min_complexity=3))
        node_ids = {n["id"] for n in doc["nodes"]}

        assert node_ids == {"mod.high", "os.path.join"}


class TestDotShape:
    def test_empty_graph_still_valid_dot(self) -> None:
        result = to_dot(nx.DiGraph())

        assert result.startswith("digraph CodeMap {")
        assert result.rstrip().endswith("}")

    def test_function_node_styling(self) -> None:
        g: nx.DiGraph = nx.DiGraph()
        g.add_node("mod.foo", **_function(complexity=1))

        result = to_dot(g)

        assert '"mod.foo"' in result
        assert "shape=box" in result
        assert "style=filled" in result

    def test_method_gets_thicker_border(self) -> None:
        g: nx.DiGraph = nx.DiGraph()
        g.add_node(
            "mod.Widget.render",
            **_function(complexity=1, is_method=True),
        )

        result = to_dot(g)

        assert "penwidth=2" in result

    def test_async_function_gets_double_border(self) -> None:
        g: nx.DiGraph = nx.DiGraph()
        g.add_node(
            "mod.fetch",
            **_function(complexity=1, is_async=True),
        )

        result = to_dot(g)

        assert "peripheries=2" in result

    def test_external_node_dashed(self) -> None:
        g: nx.DiGraph = nx.DiGraph()
        g.add_node("os.path.join", **_external())

        result = to_dot(g)

        assert '"os.path.join"' in result
        assert "style=dashed" in result

    def test_unresolved_label_strips_prefix(self) -> None:
        g: nx.DiGraph = nx.DiGraph()
        g.add_node("<unresolved>:mystery", **_unresolved())

        result = to_dot(g)

        # The label is the bare expression; the id keeps the prefix.
        assert 'label="mystery"' in result

    def test_edge_kinds_have_different_styles(self) -> None:
        g: nx.DiGraph = nx.DiGraph()
        g.add_node("mod.a", **_function())
        g.add_node("mod.b", **_function())
        g.add_node("mod.Widget.x", **_function(is_method=True))
        g.add_node("mod.Widget.y", **_function(is_method=True))
        g.add_node("os.path", **_external())
        g.add_node("<unresolved>:zzz", **_unresolved())

        g.add_edge("mod.a", "mod.b", kind="internal")
        g.add_edge("mod.Widget.x", "mod.Widget.y", kind="self")
        g.add_edge("mod.a", "os.path", kind="external")
        g.add_edge("mod.a", "<unresolved>:zzz", kind="unresolved")

        result = to_dot(g)

        # Internal edge: solid black.
        assert '"mod.a" -> "mod.b" [style=solid, color="black"]' in result
        # Self edge: steel blue.
        assert "#4682b4" in result
        # External edge: dashed gray.
        assert '"mod.a" -> "os.path" [style=dashed, color="#999999"]' in result
        # Unresolved edge: dotted gray.
        assert "style=dotted" in result

    def test_complexity_drives_fill_color(self) -> None:
        # A low-complexity and a high-complexity function should
        # have different fill colors.
        g: nx.DiGraph = nx.DiGraph()
        g.add_node("mod.low", **_function(complexity=1))
        g.add_node("mod.high", **_function(complexity=10))

        result = to_dot(g)

        # The lightest color in the palette appears for mod.low.
        assert "#e0f3ff" in result
        # The darkest color in the palette (saturated red) appears
        # for mod.high.
        assert "#c93a2c" in result

    def test_special_chars_in_label_escaped(self) -> None:
        # Construct an unresolved node whose label contains a double
        # quote. The exporter should escape it.
        g: nx.DiGraph = nx.DiGraph()
        g.add_node('<unresolved>:weird"name', **_unresolved())

        result = to_dot(g)

        # The escaped form appears in the label.
        assert 'weird\\"name' in result


class TestDotFiltering:
    def test_min_complexity_filters_function_nodes(self) -> None:
        g: nx.DiGraph = nx.DiGraph()
        g.add_node("mod.low", **_function(complexity=1, name="low"))
        g.add_node("mod.high", **_function(complexity=5, name="high"))

        result = to_dot(g, min_complexity=3)

        assert '"mod.high"' in result
        assert '"mod.low"' not in result


class TestRoundTrip:
    def test_json_round_trip_preserves_structure(self) -> None:
        # A graph with one of each kind of edge.
        g: nx.DiGraph = nx.DiGraph()
        g.add_node("mod.caller", **_function(complexity=2))
        g.add_node("mod.target", **_function(complexity=4))
        g.add_node("mod.Widget.method", **_function(is_method=True))
        g.add_node("mod.Widget.helper", **_function(is_method=True))
        g.add_node("os.getenv", **_external())
        g.add_node("<unresolved>:zzz", **_unresolved())

        g.add_edge(
            "mod.caller",
            "mod.target",
            kind="internal",
            call_count=2,
            first_line=5,
        )
        g.add_edge(
            "mod.Widget.method",
            "mod.Widget.helper",
            kind="self",
            call_count=1,
            first_line=10,
        )
        g.add_edge(
            "mod.caller",
            "os.getenv",
            kind="external",
            call_count=1,
            first_line=8,
        )
        g.add_edge(
            "mod.caller",
            "<unresolved>:zzz",
            kind="unresolved",
            call_count=1,
            first_line=9,
        )

        doc = json.loads(to_json(g))

        assert len(doc["nodes"]) == 6
        assert len(doc["edges"]) == 4

        edge_kinds = {e["kind"] for e in doc["edges"]}
        assert edge_kinds == {
            "internal",
            "self",
            "external",
            "unresolved",
        }
