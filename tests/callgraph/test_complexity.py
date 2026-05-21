"""Tests for the McCabe complexity analyzer.

Each test writes a small source file to ``tmp_path``, runs
``compute_complexities`` against it, and asserts on the per-function
score. Tests are organised by the construct they exercise.

Complexity numbers come from the standard McCabe definition: 1 + the
count of branch points. Else clauses are not counted. Nested
functions do not get their own entry but their branches roll up into
the enclosing function.
"""

from __future__ import annotations

from pathlib import Path

from codemap.callgraph.complexity import compute_complexities


def _write(tmp_path: Path, source: str) -> Path:
    file = tmp_path / "sample.py"
    file.write_text(source, encoding="utf-8")
    return file


class TestBaseline:
    def test_empty_function(self, tmp_path: Path) -> None:
        file = _write(tmp_path, "def foo():\n    pass\n")

        assert compute_complexities(file, "mod") == {"mod.foo": 1}

    def test_function_with_only_return(self, tmp_path: Path) -> None:
        file = _write(tmp_path, "def foo():\n    return 42\n")

        assert compute_complexities(file, "mod") == {"mod.foo": 1}

    def test_multiple_top_level_functions(self, tmp_path: Path) -> None:
        source = "def a():\n    pass\ndef b():\n    pass\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {
            "mod.a": 1,
            "mod.b": 1,
        }

    def test_module_with_no_functions(self, tmp_path: Path) -> None:
        file = _write(tmp_path, "x = 1\nprint(x)\n")

        assert compute_complexities(file, "mod") == {}


class TestIfFamily:
    def test_single_if(self, tmp_path: Path) -> None:
        source = "def foo(x):\n    if x:\n        return 1\n    return 0\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 2}

    def test_if_else_no_extra(self, tmp_path: Path) -> None:
        # else does not add to complexity.
        source = "def foo(x):\n    if x:\n        return 1\n    else:\n        return 0\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 2}

    def test_elif_chain(self, tmp_path: Path) -> None:
        # if + elif + elif + else = 3 branch points.
        source = (
            "def foo(x):\n"
            "    if x == 1:\n"
            "        return 'a'\n"
            "    elif x == 2:\n"
            "        return 'b'\n"
            "    elif x == 3:\n"
            "        return 'c'\n"
            "    else:\n"
            "        return 'd'\n"
        )
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 4}

    def test_nested_ifs(self, tmp_path: Path) -> None:
        source = "def foo(x, y):\n    if x:\n        if y:\n            return 1\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 3}

    def test_ternary(self, tmp_path: Path) -> None:
        source = "def foo(x):\n    return 1 if x else 0\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 2}


class TestLoops:
    def test_for_loop(self, tmp_path: Path) -> None:
        source = "def foo(items):\n    for item in items:\n        pass\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 2}

    def test_while_loop(self, tmp_path: Path) -> None:
        source = "def foo():\n    while True:\n        break\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 2}

    def test_async_for(self, tmp_path: Path) -> None:
        source = "async def foo(items):\n    async for item in items:\n        pass\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 2}


class TestExceptions:
    def test_single_except(self, tmp_path: Path) -> None:
        source = "def foo():\n    try:\n        do_it()\n    except ValueError:\n        pass\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 2}

    def test_multiple_except_clauses(self, tmp_path: Path) -> None:
        source = (
            "def foo():\n"
            "    try:\n"
            "        do_it()\n"
            "    except ValueError:\n"
            "        pass\n"
            "    except KeyError:\n"
            "        pass\n"
            "    except Exception:\n"
            "        pass\n"
        )
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 4}


class TestWith:
    def test_single_with(self, tmp_path: Path) -> None:
        source = "def foo():\n    with open('x') as f:\n        pass\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 2}

    def test_multi_context_with(self, tmp_path: Path) -> None:
        # with a, b, c: counts as +3.
        source = (
            "def foo():\n    with open('a') as f, open('b') as g, open('c') as h:\n        pass\n"
        )
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 4}


class TestBooleanOps:
    def test_single_and(self, tmp_path: Path) -> None:
        # 'a and b' has two values, one extra beyond the first, so +1.
        source = "def foo(a, b):\n    return a and b\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 2}

    def test_chained_and(self, tmp_path: Path) -> None:
        # 'a and b and c' has three values, two extras, so +2.
        source = "def foo(a, b, c):\n    return a and b and c\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 3}

    def test_or_inside_if(self, tmp_path: Path) -> None:
        # if (a or b): one if (+1) plus one extra or operand (+1) = 3.
        source = "def foo(a, b):\n    if a or b:\n        return 1\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 3}


class TestComprehensions:
    def test_list_comp_no_filter(self, tmp_path: Path) -> None:
        # No 'if' filter, so no extra complexity from the comprehension.
        source = "def foo(items):\n    return [x for x in items]\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 1}

    def test_list_comp_with_filter(self, tmp_path: Path) -> None:
        source = "def foo(items):\n    return [x for x in items if x > 0]\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 2}

    def test_dict_comp_with_filter(self, tmp_path: Path) -> None:
        source = "def foo(items):\n    return {x: x*x for x in items if x > 0}\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 2}


class TestAssert:
    def test_assert(self, tmp_path: Path) -> None:
        source = "def foo(x):\n    assert x > 0\n    return x\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 2}


class TestMatch:
    def test_match_single_case(self, tmp_path: Path) -> None:
        # Single case is just one path; +0 extra.
        source = "def foo(x):\n    match x:\n        case 1:\n            return 'one'\n"
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 1}

    def test_match_multiple_cases(self, tmp_path: Path) -> None:
        # Three cases: +2 beyond the first.
        source = (
            "def foo(x):\n"
            "    match x:\n"
            "        case 1:\n"
            "            return 'a'\n"
            "        case 2:\n"
            "            return 'b'\n"
            "        case _:\n"
            "            return 'c'\n"
        )
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {"mod.foo": 3}


class TestMethods:
    def test_method_qname(self, tmp_path: Path) -> None:
        source = (
            "class Widget:\n"
            "    def render(self, x):\n"
            "        if x:\n"
            "            return 1\n"
            "        return 0\n"
        )
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {
            "mod.Widget.render": 2,
        }

    def test_multiple_methods(self, tmp_path: Path) -> None:
        source = (
            "class Service:\n"
            "    def run(self):\n"
            "        pass\n"
            "    def process(self, x):\n"
            "        if x:\n"
            "            return 1\n"
        )
        file = _write(tmp_path, source)

        assert compute_complexities(file, "mod") == {
            "mod.Service.run": 1,
            "mod.Service.process": 2,
        }


class TestNestedFunctions:
    def test_nested_function_branches_roll_up(self, tmp_path: Path) -> None:
        # outer has one if (+1). inner has one if (+1). The nested
        # function doesn't get its own entry, but its branches count
        # toward outer. Total: 1 + 1 + 1 = 3.
        source = (
            "def outer(x):\n"
            "    if x:\n"
            "        def inner(y):\n"
            "            if y:\n"
            "                return 1\n"
            "        inner(x)\n"
        )
        file = _write(tmp_path, source)

        result = compute_complexities(file, "mod")
        assert result == {"mod.outer": 3}
        assert "mod.inner" not in result


class TestRealistic:
    def test_realistic_function(self, tmp_path: Path) -> None:
        # A genuinely branchy function exercising several constructs.
        source = (
            "def process(items, filter_fn):\n"
            "    results = []\n"
            "    for item in items:\n"  # +1 for
            "        if item is None:\n"  # +1 if
            "            continue\n"
            "        if filter_fn(item) and item > 0:\n"  # +1 if, +1 and
            "            try:\n"
            "                results.append(item * 2)\n"
            "            except ValueError:\n"  # +1 except
            "                pass\n"
            "    return results\n"
        )
        file = _write(tmp_path, source)

        # Base 1 + 1 (for) + 1 (if) + 1 (if) + 1 (and) + 1 (except) = 6
        assert compute_complexities(file, "mod") == {"mod.process": 6}
