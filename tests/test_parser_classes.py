"""Unit tests for class extraction in the AST parser."""

from __future__ import annotations

import pytest

from codemap.ast_engine.models import ClassInfo, FunctionInfo
from codemap.ast_engine.parser import extract_classes

# ---------------------------------------------------------------------------
# Basic class extraction
# ---------------------------------------------------------------------------


def test_extract_single_empty_class() -> None:
    """A class with no methods produces a ClassInfo with an empty methods tuple."""
    source = "\n".join(
        [
            "class Empty:",
            "    pass",
        ]
    )
    result = extract_classes(source)
    assert result == (ClassInfo(name="Empty", line=1, methods=()),)


def test_extract_class_with_one_method() -> None:
    """A class with a single method captures the method as FunctionInfo."""
    source = "\n".join(
        [
            "class Dog:",
            "    def bark(self): pass",
        ]
    )
    result = extract_classes(source)
    assert result == (
        ClassInfo(
            name="Dog",
            line=1,
            methods=(FunctionInfo(name="bark", line=2, args=("self",), is_async=False),),
        ),
    )


def test_extract_class_with_multiple_methods() -> None:
    """All direct methods are captured in source order."""
    source = "\n".join(
        [
            "class Dog:",
            "    def bark(self): pass",
            "    def wag(self): pass",
            "    def fetch(self, item): pass",
        ]
    )
    result = extract_classes(source)
    assert len(result) == 1
    cls = result[0]
    assert cls.name == "Dog"
    assert [m.name for m in cls.methods] == ["bark", "wag", "fetch"]
    assert cls.methods[2].args == ("self", "item")


def test_extract_class_with_async_method() -> None:
    """Async methods are flagged with is_async=True."""
    source = "\n".join(
        [
            "class Client:",
            "    async def fetch(self, url): pass",
        ]
    )
    result = extract_classes(source)
    assert result[0].methods[0].is_async is True


def test_extract_multiple_classes() -> None:
    """Multiple top-level classes are all captured."""
    source = "\n".join(
        [
            "class A: pass",
            "class B: pass",
            "class C: pass",
        ]
    )
    result = extract_classes(source)
    assert [c.name for c in result] == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# Scope discipline: nested classes and indirect children are excluded
# ---------------------------------------------------------------------------


def test_nested_classes_are_excluded() -> None:
    """A class defined inside another class is not returned."""
    source = "\n".join(
        [
            "class Outer:",
            "    class Inner:",
            "        pass",
        ]
    )
    result = extract_classes(source)
    assert len(result) == 1
    assert result[0].name == "Outer"


def test_classes_inside_functions_are_excluded() -> None:
    """A class defined inside a function is not returned."""
    source = "\n".join(
        [
            "def make_class():",
            "    class Local: pass",
            "    return Local",
        ]
    )
    result = extract_classes(source)
    assert result == ()


def test_nested_methods_inside_methods_are_excluded() -> None:
    """A function defined inside a method is not captured as a method."""
    source = "\n".join(
        [
            "class App:",
            "    def run(self):",
            "        def helper(): pass",
            "        return helper",
        ]
    )
    result = extract_classes(source)
    assert len(result) == 1
    methods = result[0].methods
    assert [m.name for m in methods] == ["run"]


def test_top_level_functions_are_not_in_classes() -> None:
    """Top-level functions outside any class are not associated with any class."""
    source = "\n".join(
        [
            "def standalone(): pass",
            "class App:",
            "    def run(self): pass",
        ]
    )
    result = extract_classes(source)
    assert len(result) == 1
    assert result[0].name == "App"
    assert [m.name for m in result[0].methods] == ["run"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_line_numbers_are_accurate() -> None:
    """Class line numbers reflect the position of the class keyword."""
    source = "\n".join(
        [
            "",
            "class First: pass",
            "",
            "class Second: pass",
        ]
    )
    result = extract_classes(source)
    assert [c.line for c in result] == [2, 4]


def test_empty_source_returns_empty_tuple() -> None:
    """Source with no classes returns an empty tuple."""
    result = extract_classes("x = 1\ndef f(): pass")
    assert result == ()


def test_invalid_syntax_raises_syntax_error() -> None:
    """Malformed Python source raises SyntaxError."""
    with pytest.raises(SyntaxError):
        extract_classes("class !!!")


def test_returns_tuple_not_list() -> None:
    """The return type is a tuple, matching the model contract."""
    result = extract_classes("class A: pass")
    assert isinstance(result, tuple)
