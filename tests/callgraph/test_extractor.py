"""Tests for the call graph extractor.

Covers function node extraction (top-level, async, methods, nested),
call site attribution (which function owns each call), the boundary
cases inherited from Phase 2 (nested functions and lambdas do not
become nodes), and the handling of top-level calls.

Tests use ``tmp_path`` to write small source files to disk and run
the extractor against them, mirroring the approach in Phase 2's
parser tests.
"""

from __future__ import annotations

from pathlib import Path

from codemap.callgraph.extractor import extract_module


def _write(tmp_path: Path, source: str) -> Path:
    """Write source to a temp file and return its path."""
    file = tmp_path / "sample.py"
    file.write_text(source, encoding="utf-8")
    return file


class TestFunctionNodeExtraction:
    def test_single_top_level_function(self, tmp_path: Path) -> None:
        source = "def foo():\n    pass\n"
        file = _write(tmp_path, source)

        functions, _ = extract_module(file, "pkg.mod")

        assert len(functions) == 1
        assert functions[0].qualified_name == "pkg.mod.foo"
        assert functions[0].name == "foo"
        assert functions[0].module == "pkg.mod"
        assert functions[0].class_name is None
        assert functions[0].is_method is False
        assert functions[0].is_async is False
        assert functions[0].line == 1

    def test_async_function(self, tmp_path: Path) -> None:
        source = "async def fetch():\n    pass\n"
        file = _write(tmp_path, source)

        functions, _ = extract_module(file, "pkg.mod")

        assert len(functions) == 1
        assert functions[0].is_async is True
        assert functions[0].is_method is False

    def test_method_extraction(self, tmp_path: Path) -> None:
        source = (
            "class Widget:\n"
            "    def render(self):\n"
            "        pass\n"
        )
        file = _write(tmp_path, source)

        functions, _ = extract_module(file, "pkg.mod")

        assert len(functions) == 1
        method = functions[0]
        assert method.qualified_name == "pkg.mod.Widget.render"
        assert method.class_name == "Widget"
        assert method.name == "render"
        assert method.is_method is True

    def test_async_method(self, tmp_path: Path) -> None:
        source = (
            "class Client:\n"
            "    async def fetch(self):\n"
            "        pass\n"
        )
        file = _write(tmp_path, source)

        functions, _ = extract_module(file, "pkg.mod")

        assert len(functions) == 1
        assert functions[0].is_method is True
        assert functions[0].is_async is True

    def test_multiple_top_level_functions(self, tmp_path: Path) -> None:
        source = (
            "def a():\n    pass\n"
            "def b():\n    pass\n"
            "def c():\n    pass\n"
        )
        file = _write(tmp_path, source)

        functions, _ = extract_module(file, "pkg.mod")

        names = [f.name for f in functions]
        assert names == ["a", "b", "c"]

    def test_class_with_multiple_methods(self, tmp_path: Path) -> None:
        source = (
            "class Widget:\n"
            "    def one(self):\n        pass\n"
            "    def two(self):\n        pass\n"
        )
        file = _write(tmp_path, source)

        functions, _ = extract_module(file, "pkg.mod")

        qnames = [f.qualified_name for f in functions]
        assert qnames == ["pkg.mod.Widget.one", "pkg.mod.Widget.two"]

    def test_nested_function_does_not_become_node(
        self, tmp_path: Path
    ) -> None:
        source = (
            "def outer():\n"
            "    def inner():\n"
            "        pass\n"
        )
        file = _write(tmp_path, source)

        functions, _ = extract_module(file, "pkg.mod")

        assert len(functions) == 1
        assert functions[0].name == "outer"

    def test_nested_method_does_not_become_node(
        self, tmp_path: Path
    ) -> None:
        source = (
            "class Widget:\n"
            "    def render(self):\n"
            "        def helper():\n"
            "            pass\n"
        )
        file = _write(tmp_path, source)

        functions, _ = extract_module(file, "pkg.mod")

        assert len(functions) == 1
        assert functions[0].qualified_name == "pkg.mod.Widget.render"


class TestCallSiteAttribution:
    def test_call_attributed_to_enclosing_function(
        self, tmp_path: Path
    ) -> None:
        source = (
            "def foo():\n"
            "    bar()\n"
        )
        file = _write(tmp_path, source)

        _, call_sites = extract_module(file, "pkg.mod")

        assert len(call_sites) == 1
        assert call_sites[0].caller == "pkg.mod.foo"
        assert call_sites[0].callee_expression == "bar"
        assert call_sites[0].line == 2

    def test_attribute_chain_call(self, tmp_path: Path) -> None:
        source = (
            "def foo():\n"
            "    os.path.join(a, b)\n"
        )
        file = _write(tmp_path, source)

        _, call_sites = extract_module(file, "pkg.mod")

        assert len(call_sites) == 1
        assert call_sites[0].callee_expression == "os.path.join"

    def test_self_method_call_attributed_to_method(
        self, tmp_path: Path
    ) -> None:
        source = (
            "class Widget:\n"
            "    def render(self):\n"
            "        self.helper()\n"
        )
        file = _write(tmp_path, source)

        _, call_sites = extract_module(file, "pkg.mod")

        assert len(call_sites) == 1
        assert call_sites[0].caller == "pkg.mod.Widget.render"
        assert call_sites[0].callee_expression == "self.helper"

    def test_multiple_calls_in_one_function(
        self, tmp_path: Path
    ) -> None:
        source = (
            "def foo():\n"
            "    a()\n"
            "    b()\n"
            "    c()\n"
        )
        file = _write(tmp_path, source)

        _, call_sites = extract_module(file, "pkg.mod")

        callees = [cs.callee_expression for cs in call_sites]
        assert callees == ["a", "b", "c"]
        assert all(cs.caller == "pkg.mod.foo" for cs in call_sites)

    def test_calls_in_nested_function_attribute_to_outer(
        self, tmp_path: Path
    ) -> None:
        source = (
            "def outer():\n"
            "    def inner():\n"
            "        helper()\n"
            "    inner()\n"
        )
        file = _write(tmp_path, source)

        _, call_sites = extract_module(file, "pkg.mod")

        assert len(call_sites) == 2
        # Both calls attribute to outer, since inner is not a node.
        assert all(cs.caller == "pkg.mod.outer" for cs in call_sites)
        callees = sorted(cs.callee_expression for cs in call_sites)
        assert callees == ["helper", "inner"]

    def test_call_in_nested_call_argument_captured(
        self, tmp_path: Path
    ) -> None:
        source = (
            "def foo():\n"
            "    outer(inner())\n"
        )
        file = _write(tmp_path, source)

        _, call_sites = extract_module(file, "pkg.mod")

        callees = sorted(cs.callee_expression for cs in call_sites)
        assert callees == ["inner", "outer"]

    def test_unknown_callee_preserved(self, tmp_path: Path) -> None:
        source = (
            "def foo():\n"
            "    (lambda x: x)()\n"
        )
        file = _write(tmp_path, source)

        _, call_sites = extract_module(file, "pkg.mod")

        assert len(call_sites) == 1
        assert call_sites[0].callee_expression == "<unknown>"

    def test_top_level_calls_ignored(self, tmp_path: Path) -> None:
        source = (
            "print('hello')\n"
            "def foo():\n"
            "    bar()\n"
        )
        file = _write(tmp_path, source)

        _, call_sites = extract_module(file, "pkg.mod")

        # Only the call inside foo is captured. The print at module
        # top level has no enclosing function so it is dropped.
        assert len(call_sites) == 1
        assert call_sites[0].caller == "pkg.mod.foo"
        assert call_sites[0].callee_expression == "bar"


class TestIntegration:
    def test_realistic_module(self, tmp_path: Path) -> None:
        """A small module that exercises several features at once."""
        source = (
            "def helper():\n"
            "    pass\n"
            "\n"
            "class Service:\n"
            "    def run(self):\n"
            "        helper()\n"
            "        self.process()\n"
            "\n"
            "    def process(self):\n"
            "        result = compute()\n"
            "        log.info(result)\n"
            "\n"
            "async def main():\n"
            "    s = Service()\n"
            "    s.run()\n"
        )
        file = _write(tmp_path, source)

        functions, call_sites = extract_module(file, "pkg.mod")

        # Four nodes: helper, Service.run, Service.process, main.
        qnames = sorted(f.qualified_name for f in functions)
        assert qnames == [
            "pkg.mod.Service.process",
            "pkg.mod.Service.run",
            "pkg.mod.helper",
            "pkg.mod.main",
        ]

        # main is async, others are not.
        async_names = [f.qualified_name for f in functions if f.is_async]
        assert async_names == ["pkg.mod.main"]

        # Methods correctly flagged.
        methods = [f.qualified_name for f in functions if f.is_method]
        assert sorted(methods) == [
            "pkg.mod.Service.process",
            "pkg.mod.Service.run",
        ]

        # Six call sites total: helper(), self.process() in run;
        # compute(), log.info() in process; Service(), s.run() in main.
        assert len(call_sites) == 6

        # Check a few specific attributions.
        by_caller: dict[str, list[str]] = {}
        for cs in call_sites:
            by_caller.setdefault(cs.caller, []).append(
                cs.callee_expression
            )

        assert sorted(by_caller["pkg.mod.Service.run"]) == [
            "helper",
            "self.process",
        ]
        assert sorted(by_caller["pkg.mod.Service.process"]) == [
            "compute",
            "log.info",
        ]
        assert sorted(by_caller["pkg.mod.main"]) == [
            "Service",
            "s.run",
        ]
