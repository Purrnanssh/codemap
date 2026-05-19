"""Tests for the call graph builder.

Tests build small fixture projects on disk under ``tmp_path``, run
the builder, and assert on the resulting graph: node presence,
node attributes, edge presence, edge kinds, and the cross-module
validation behaviour where the resolver's optimistic INTERNAL edges
get downgraded to UNRESOLVED when the target is not a real function.
"""

from __future__ import annotations

from pathlib import Path

from codemap.callgraph.builder import build_call_graph


def _write(file: Path, source: str) -> None:
    """Write source to a file, ensuring its parent directory exists."""
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(source, encoding="utf-8")


def _make_project(tmp_path: Path, files: dict[str, str]) -> Path:
    """Build a fixture project under tmp_path.

    ``files`` is a mapping of relative path -> source. Returns the
    project root, which is ``tmp_path / project``.
    """
    root = tmp_path / "project"
    for rel, source in files.items():
        _write(root / rel, source)
    return root


class TestSingleModule:
    def test_single_function_no_calls(self, tmp_path: Path) -> None:
        root = _make_project(
            tmp_path,
            {"mod.py": "def foo():\n    pass\n"},
        )

        graph, errors = build_call_graph(root)

        assert errors == {}
        assert "mod.foo" in graph.nodes
        assert graph.nodes["mod.foo"]["kind"] == "function"
        assert graph.nodes["mod.foo"]["is_method"] is False
        assert graph.number_of_edges() == 0

    def test_internal_call_within_module(self, tmp_path: Path) -> None:
        source = (
            "def foo():\n"
            "    bar()\n"
            "\n"
            "def bar():\n"
            "    pass\n"
        )
        root = _make_project(tmp_path, {"mod.py": source})

        graph, _ = build_call_graph(root)

        assert graph.has_edge("mod.foo", "mod.bar")
        assert graph["mod.foo"]["mod.bar"]["kind"] == "internal"
        assert graph["mod.foo"]["mod.bar"]["call_count"] == 1

    def test_repeated_call_increments_count(
        self, tmp_path: Path
    ) -> None:
        source = (
            "def foo():\n"
            "    bar()\n"
            "    bar()\n"
            "    bar()\n"
            "\n"
            "def bar():\n"
            "    pass\n"
        )
        root = _make_project(tmp_path, {"mod.py": source})

        graph, _ = build_call_graph(root)

        assert graph["mod.foo"]["mod.bar"]["call_count"] == 3

    def test_self_method_edge(self, tmp_path: Path) -> None:
        source = (
            "class Widget:\n"
            "    def run(self):\n"
            "        self.helper()\n"
            "\n"
            "    def helper(self):\n"
            "        pass\n"
        )
        root = _make_project(tmp_path, {"mod.py": source})

        graph, _ = build_call_graph(root)

        assert graph.has_edge(
            "mod.Widget.run", "mod.Widget.helper"
        )
        assert (
            graph["mod.Widget.run"]["mod.Widget.helper"]["kind"]
            == "self"
        )


class TestExternalCalls:
    def test_external_call_creates_external_node(
        self, tmp_path: Path
    ) -> None:
        source = (
            "import os\n"
            "\n"
            "def foo():\n"
            "    os.path.join(a, b)\n"
        )
        root = _make_project(tmp_path, {"mod.py": source})

        graph, _ = build_call_graph(root)

        assert "os.path.join" in graph.nodes
        assert graph.nodes["os.path.join"]["kind"] == "external"
        assert graph["mod.foo"]["os.path.join"]["kind"] == "external"

    def test_aliased_external(self, tmp_path: Path) -> None:
        source = (
            "import numpy as np\n"
            "\n"
            "def foo():\n"
            "    np.array(x)\n"
        )
        root = _make_project(tmp_path, {"mod.py": source})

        graph, _ = build_call_graph(root)

        assert graph.has_edge("mod.foo", "numpy.array")
        assert graph["mod.foo"]["numpy.array"]["kind"] == "external"


class TestUnresolvedCalls:
    def test_unknown_bare_name(self, tmp_path: Path) -> None:
        source = (
            "def foo():\n"
            "    mystery()\n"
        )
        root = _make_project(tmp_path, {"mod.py": source})

        graph, _ = build_call_graph(root)

        target = "<unresolved>:mystery"
        assert target in graph.nodes
        assert graph.nodes[target]["kind"] == "unresolved"
        assert graph.has_edge("mod.foo", target)

    def test_lambda_call(self, tmp_path: Path) -> None:
        source = (
            "def foo():\n"
            "    (lambda x: x)()\n"
        )
        root = _make_project(tmp_path, {"mod.py": source})

        graph, _ = build_call_graph(root)

        target = "<unresolved>:<unknown>"
        assert target in graph.nodes
        assert graph.has_edge("mod.foo", target)


class TestCrossModuleValidation:
    def test_resolved_cross_module_call(self, tmp_path: Path) -> None:
        # mod_a imports do_thing from mod_b and calls it.
        # Since do_thing exists in mod_b, the edge should be INTERNAL.
        root = _make_project(
            tmp_path,
            {
                "mod_a.py": (
                    "from mod_b import do_thing\n"
                    "\n"
                    "def foo():\n"
                    "    do_thing()\n"
                ),
                "mod_b.py": "def do_thing():\n    pass\n",
            },
        )

        graph, _ = build_call_graph(root)

        assert graph.has_edge("mod_a.foo", "mod_b.do_thing")
        assert graph["mod_a.foo"]["mod_b.do_thing"]["kind"] == "internal"

    def test_phantom_cross_module_call_downgraded(
        self, tmp_path: Path
    ) -> None:
        # mod_a imports the mod_b module and calls a name that
        # doesn't exist there. The resolver emits an optimistic
        # INTERNAL edge to 'mod_b.phantom'; the builder should
        # downgrade it to UNRESOLVED.
        root = _make_project(
            tmp_path,
            {
                "mod_a.py": (
                    "import mod_b\n"
                    "\n"
                    "def foo():\n"
                    "    mod_b.phantom()\n"
                ),
                "mod_b.py": "def real_thing():\n    pass\n",
            },
        )

        graph, _ = build_call_graph(root)

        target = "<unresolved>:mod_b.phantom"
        assert target in graph.nodes
        assert graph.has_edge("mod_a.foo", target)
        assert graph["mod_a.foo"][target]["kind"] == "unresolved"
        # And the phantom name itself must not appear as a function.
        assert "mod_b.phantom" not in graph.nodes


class TestParseErrors:
    def test_broken_file_recorded_not_aborting(
        self, tmp_path: Path
    ) -> None:
        # mod_good is valid; mod_bad has a syntax error.
        root = _make_project(
            tmp_path,
            {
                "mod_good.py": "def foo():\n    pass\n",
                "mod_bad.py": "def broken(:\n    pass\n",
            },
        )

        graph, errors = build_call_graph(root)

        # mod_good was parsed fine.
        assert "mod_good.foo" in graph.nodes
        # mod_bad produced no nodes (we have no functions to add).
        assert not any(
            isinstance(n, str) and n.startswith("mod_bad")
            for n in graph.nodes
        )
        # The error was recorded.
        bad_path = root / "mod_bad.py"
        assert bad_path in errors
        assert "SyntaxError" in errors[bad_path]


class TestRealisticProject:
    def test_multi_module_with_methods(self, tmp_path: Path) -> None:
        # Two modules: services.py defines a Service class that
        # uses helpers.do_work. utils.py has a helper that calls
        # an external function.
        root = _make_project(
            tmp_path,
            {
                "services.py": (
                    "from helpers import do_work\n"
                    "\n"
                    "class Service:\n"
                    "    def run(self):\n"
                    "        do_work()\n"
                    "        self.cleanup()\n"
                    "\n"
                    "    def cleanup(self):\n"
                    "        pass\n"
                ),
                "helpers.py": (
                    "import os\n"
                    "\n"
                    "def do_work():\n"
                    "    os.path.join('a', 'b')\n"
                ),
            },
        )

        graph, errors = build_call_graph(root)

        assert errors == {}

        # Function nodes for both modules.
        for qname in (
            "services.Service.run",
            "services.Service.cleanup",
            "helpers.do_work",
        ):
            assert qname in graph.nodes
            assert graph.nodes[qname]["kind"] == "function"

        # Cross-module internal call.
        assert graph.has_edge(
            "services.Service.run", "helpers.do_work"
        )
        assert (
            graph["services.Service.run"]["helpers.do_work"]["kind"]
            == "internal"
        )

        # Self-call inside Service.run.
        assert graph.has_edge(
            "services.Service.run", "services.Service.cleanup"
        )
        assert (
            graph["services.Service.run"][
                "services.Service.cleanup"
            ]["kind"]
            == "self"
        )

        # External call inside helpers.do_work.
        assert graph.has_edge("helpers.do_work", "os.path.join")
        assert (
            graph["helpers.do_work"]["os.path.join"]["kind"]
            == "external"
        )


class TestComplexityAttribute:
    def test_simple_function_complexity_one(
        self, tmp_path: Path
    ) -> None:
        root = _make_project(
            tmp_path,
            {"mod.py": "def foo():\n    pass\n"},
        )

        graph, _ = build_call_graph(root)

        assert graph.nodes["mod.foo"]["complexity"] == 1

    def test_branchy_function_higher_complexity(
        self, tmp_path: Path
    ) -> None:
        source = (
            "def foo(x):\n"
            "    if x:\n"
            "        return 1\n"
            "    return 0\n"
        )
        root = _make_project(tmp_path, {"mod.py": source})

        graph, _ = build_call_graph(root)

        assert graph.nodes["mod.foo"]["complexity"] == 2

    def test_method_complexity(self, tmp_path: Path) -> None:
        source = (
            "class Widget:\n"
            "    def render(self, x):\n"
            "        if x:\n"
            "            return 1\n"
            "        return 0\n"
        )
        root = _make_project(tmp_path, {"mod.py": source})

        graph, _ = build_call_graph(root)

        assert graph.nodes["mod.Widget.render"]["complexity"] == 2

    def test_external_nodes_have_no_complexity(
        self, tmp_path: Path
    ) -> None:
        # Synthetic nodes (external, unresolved) should not carry a
        # complexity attribute; they are not project functions.
        source = (
            "import os\n"
            "\n"
            "def foo():\n"
            "    os.path.join(a, b)\n"
            "    mystery()\n"
        )
        root = _make_project(tmp_path, {"mod.py": source})

        graph, _ = build_call_graph(root)

        assert "complexity" not in graph.nodes["os.path.join"]
        assert "complexity" not in graph.nodes["<unresolved>:mystery"]

    def test_complexities_attached_to_all_functions(
        self, tmp_path: Path
    ) -> None:
        # Mixed-complexity functions in two modules. Each function
        # node should have its complexity attribute set.
        root = _make_project(
            tmp_path,
            {
                "a.py": (
                    "def simple():\n"
                    "    pass\n"
                    "\n"
                    "def branchy(x):\n"
                    "    if x and x > 0:\n"  # +1 if, +1 and
                    "        return 1\n"
                    "    return 0\n"
                ),
                "b.py": (
                    "class Service:\n"
                    "    def run(self, items):\n"
                    "        for item in items:\n"  # +1
                    "            self.process(item)\n"
                    "    def process(self, x):\n"
                    "        pass\n"
                ),
            },
        )

        graph, _ = build_call_graph(root)

        assert graph.nodes["a.simple"]["complexity"] == 1
        assert graph.nodes["a.branchy"]["complexity"] == 3
        assert graph.nodes["b.Service.run"]["complexity"] == 2
        assert graph.nodes["b.Service.process"]["complexity"] == 1
