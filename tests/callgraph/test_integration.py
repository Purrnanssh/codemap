"""End-to-end integration tests over a committed fixture project.

The fixture under ``tests/fixtures/callgraph_sample/`` is a small
fake project deliberately built to exercise every Phase 4 feature
exactly once: internal calls, self calls, cross-module internal
calls (both from-import and import-then-attribute), external calls,
two flavors of unresolved calls, async functions, methods, and
high-complexity branchy code.

The fixture root is ``tests/fixtures/callgraph_sample/`` itself, so
dotted module paths come out relative to that root: the top-level
files are ``utils`` and ``config``, and the subpackage file is
``services.processor``. There is no ``callgraph_sample.`` prefix.

These tests run ``build_call_graph`` against the fixture and assert
on the resulting graph at every layer of the pipeline:

    - Function-node presence and attributes (module, class, async,
      complexity).
    - Edge presence and ``kind`` (internal, self, external,
      unresolved).
    - The hotspot ranking and the identity of the top hotspot.

The tests live as a separate file from the unit tests in
``test_builder.py`` and friends because their failure mode is
different: if one of these breaks, the regression is in *how the
layers compose*, not in any single layer. The fixture is the
canonical end-to-end smoke test for Phase 4.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import pytest

from codemap.callgraph.builder import build_call_graph
from codemap.callgraph.hotspots import compute_hotspots


FIXTURE_ROOT = (
    Path(__file__).parent.parent / "fixtures" / "callgraph_sample"
)


@pytest.fixture(scope="module")
def fixture_graph() -> nx.DiGraph:
    """Build the call graph once and reuse it across tests."""
    graph, parse_errors = build_call_graph(FIXTURE_ROOT)
    assert parse_errors == {}, (
        f"Fixture project failed to parse: {parse_errors}"
    )
    return graph


class TestFunctionNodes:
    """Every expected function or method exists with the right attrs."""

    EXPECTED_FUNCTIONS = {
        "utils.helper": {
            "is_method": False,
            "is_async": False,
        },
        "config.load": {
            "is_method": False,
            "is_async": False,
        },
        "services.processor.Processor.run": {
            "is_method": True,
            "is_async": False,
        },
        "services.processor.Processor.transform": {
            "is_method": True,
            "is_async": False,
        },
        "services.processor.Processor.fetch_remote": {
            "is_method": True,
            "is_async": True,
        },
        "services.processor.orchestrate": {
            "is_method": False,
            "is_async": False,
        },
        "services.processor.invoke_run_directly": {
            "is_method": False,
            "is_async": False,
        },
        "services.processor.use_dynamic_call": {
            "is_method": False,
            "is_async": False,
        },
        "services.processor.use_deep_self_chain": {
            "is_method": False,
            "is_async": False,
        },
    }

    def test_all_expected_functions_present(
        self, fixture_graph: nx.DiGraph
    ) -> None:
        for qname in self.EXPECTED_FUNCTIONS:
            assert qname in fixture_graph.nodes, (
                f"Missing function node: {qname}"
            )
            assert (
                fixture_graph.nodes[qname]["kind"] == "function"
            ), f"{qname} is not a function node"

    def test_method_flag_correct(
        self, fixture_graph: nx.DiGraph
    ) -> None:
        for qname, expected in self.EXPECTED_FUNCTIONS.items():
            assert (
                fixture_graph.nodes[qname]["is_method"]
                == expected["is_method"]
            ), f"is_method wrong for {qname}"

    def test_async_flag_correct(
        self, fixture_graph: nx.DiGraph
    ) -> None:
        for qname, expected in self.EXPECTED_FUNCTIONS.items():
            assert (
                fixture_graph.nodes[qname]["is_async"]
                == expected["is_async"]
            ), f"is_async wrong for {qname}"

    def test_no_unexpected_functions(
        self, fixture_graph: nx.DiGraph
    ) -> None:
        function_nodes = {
            n
            for n, attrs in fixture_graph.nodes(data=True)
            if attrs.get("kind") == "function"
        }
        assert function_nodes == set(self.EXPECTED_FUNCTIONS), (
            "Function set drifted from fixture expectations"
        )


class TestEdgeKinds:
    """Each edge kind shows up at least once with the expected target."""

    def test_self_edge_run_to_transform(
        self, fixture_graph: nx.DiGraph
    ) -> None:
        caller = "services.processor.Processor.run"
        callee = "services.processor.Processor.transform"
        assert fixture_graph.has_edge(caller, callee)
        assert fixture_graph[caller][callee]["kind"] == "self"

    def test_internal_cross_module_from_import(
        self, fixture_graph: nx.DiGraph
    ) -> None:
        # Processor.transform calls helper, imported via
        # 'from utils import helper'.
        caller = "services.processor.Processor.transform"
        callee = "utils.helper"
        assert fixture_graph.has_edge(caller, callee)
        assert fixture_graph[caller][callee]["kind"] == "internal"

    def test_internal_cross_module_attribute_chain(
        self, fixture_graph: nx.DiGraph
    ) -> None:
        # Processor.run calls config.load(), imported via
        # 'import config'.
        caller = "services.processor.Processor.run"
        callee = "config.load"
        assert fixture_graph.has_edge(caller, callee)
        assert fixture_graph[caller][callee]["kind"] == "internal"

    def test_internal_class_dot_method_call(
        self, fixture_graph: nx.DiGraph
    ) -> None:
        # invoke_run_directly calls Processor.run via the class.
        # This resolves: Processor is in the names table (class),
        # Processor.run is a real function node, so the edge stays
        # INTERNAL after builder validation.
        caller = "services.processor.invoke_run_directly"
        callee = "services.processor.Processor.run"
        assert fixture_graph.has_edge(caller, callee)
        assert fixture_graph[caller][callee]["kind"] == "internal"

    def test_internal_same_module_call(
        self, fixture_graph: nx.DiGraph
    ) -> None:
        # orchestrate calls Processor() (class instantiation). The
        # resolver finds Processor in the local names table pointing
        # at the class qualified name, but the class is not in the
        # function index, so the builder downgrades the edge to
        # UNRESOLVED. This is the correct behavior: Phase 4 does not
        # treat class instantiations as edges to __init__.
        caller = "services.processor.orchestrate"
        callee_class = "services.processor.Processor"
        unresolved_target = f"<unresolved>:{callee_class}"
        assert fixture_graph.has_edge(caller, unresolved_target)

    def test_external_edge_to_stdlib(
        self, fixture_graph: nx.DiGraph
    ) -> None:
        caller = "services.processor.Processor.fetch_remote"
        callee = "os.environ.get"
        assert fixture_graph.has_edge(caller, callee)
        assert fixture_graph[caller][callee]["kind"] == "external"

    def test_unresolved_unknown_sentinel(
        self, fixture_graph: nx.DiGraph
    ) -> None:
        # use_dynamic_call has a lambda call. Phase 2 names it
        # <unknown>; the resolver wraps it with <unresolved>:.
        caller = "services.processor.use_dynamic_call"
        callee = "<unresolved>:<unknown>"
        assert fixture_graph.has_edge(caller, callee)
        assert (
            fixture_graph[caller][callee]["kind"] == "unresolved"
        )

    def test_unresolved_deep_self_chain(
        self, fixture_graph: nx.DiGraph
    ) -> None:
        # use_deep_self_chain has 'self.processor.run([...])'.
        # Bare 'self' is not in the names table (it's a module-level
        # function), so the head fails to resolve and the whole
        # chain ends up UNRESOLVED.
        caller = "services.processor.use_deep_self_chain"
        callee = "<unresolved>:self.processor.run"
        assert fixture_graph.has_edge(caller, callee)
        assert (
            fixture_graph[caller][callee]["kind"] == "unresolved"
        )


class TestComplexity:
    """Each function's McCabe score matches the fixture's hand-counted value."""

    EXPECTED_COMPLEXITIES = {
        "utils.helper": 1,
        "config.load": 1,
        "services.processor.Processor.run": 6,
        "services.processor.Processor.transform": 1,
        "services.processor.Processor.fetch_remote": 1,
        "services.processor.orchestrate": 1,
        "services.processor.invoke_run_directly": 1,
        "services.processor.use_dynamic_call": 1,
        "services.processor.use_deep_self_chain": 1,
    }

    def test_complexity_per_function(
        self, fixture_graph: nx.DiGraph
    ) -> None:
        for qname, expected in self.EXPECTED_COMPLEXITIES.items():
            actual = fixture_graph.nodes[qname]["complexity"]
            assert actual == expected, (
                f"{qname}: expected complexity {expected}, "
                f"got {actual}"
            )


class TestHotspots:
    """Top hotspot is the most branchy function with at least one caller."""

    def test_processor_run_is_top_hotspot(
        self, fixture_graph: nx.DiGraph
    ) -> None:
        # Processor.run: complexity 6, fan-in 1 (from
        # invoke_run_directly via Processor.run). Score 6. Every
        # other function has complexity 1; the best any of them
        # could do is fan-in N with score N. None of them gets that
        # high, so Processor.run wins.
        hotspots = compute_hotspots(fixture_graph)
        assert hotspots[0].qualified_name == (
            "services.processor.Processor.run"
        )
        assert hotspots[0].score == 6
        assert hotspots[0].complexity == 6
        assert hotspots[0].fan_in == 1
