"""Unit tests for function extraction in the AST parser."""

from __future__ import annotations

import pytest

from codemap.ast_engine.models import FunctionInfo
from codemap.ast_engine.parser import extract_functions

# ---------------------------------------------------------------------------
# Basic function extraction
# ---------------------------------------------------------------------------


def test_extract_single_function() -> None:
    """A single top-level def produces one FunctionInfo."""
    result = extract_functions("def greet(): pass")
    assert result == (FunctionInfo(name="greet", line=1, args=(), is_async=False),)


def test_extract_function_with_args() -> None:
    """Positional arguments are captured in order."""
    result = extract_functions("def add(x, y, z): pass")
    assert result == (FunctionInfo(name="add", line=1, args=("x", "y", "z"), is_async=False),)


def test_extract_async_function() -> None:
    """async def is captured with is_async=True."""
    result = extract_functions("async def fetch(url): pass")
    assert result == (FunctionInfo(name="fetch", line=1, args=("url",), is_async=True),)


def test_extract_multiple_functions() -> None:
    """Multiple top-level functions are all captured."""
    source = "\n".join(
        [
            "def a(): pass",
            "def b(): pass",
            "def c(): pass",
        ]
    )
    result = extract_functions(source)
    assert len(result) == 3
    assert [f.name for f in result] == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# Scope discipline: methods and nested functions are excluded
# ---------------------------------------------------------------------------


def test_methods_inside_classes_are_excluded() -> None:
    """Functions defined inside classes (methods) are not returned."""
    source = "\n".join(
        [
            "def standalone(): pass",
            "class Dog:",
            "    def bark(self): pass",
            "    def wag(self): pass",
        ]
    )
    result = extract_functions(source)
    assert len(result) == 1
    assert result[0].name == "standalone"


def test_nested_functions_are_excluded() -> None:
    """Functions defined inside other functions are not returned."""
    source = "\n".join(
        [
            "def outer():",
            "    def inner():",
            "        pass",
            "    return inner",
        ]
    )
    result = extract_functions(source)
    assert len(result) == 1
    assert result[0].name == "outer"


# ---------------------------------------------------------------------------
# Line numbers and edge cases
# ---------------------------------------------------------------------------


def test_line_numbers_are_accurate() -> None:
    """Line numbers reflect the position of the def keyword."""
    source = "\n".join(
        [
            "",  # line 1: blank
            "def first(): pass",  # line 2
            "",  # line 3: blank
            "def second(): pass",  # line 4
        ]
    )
    result = extract_functions(source)
    lines = [f.line for f in result]
    assert lines == [2, 4]


def test_empty_source_returns_empty_tuple() -> None:
    """Source with no functions returns an empty tuple."""
    result = extract_functions("x = 1\nimport os")
    assert result == ()


def test_invalid_syntax_raises_syntax_error() -> None:
    """Malformed Python source raises SyntaxError."""
    with pytest.raises(SyntaxError):
        extract_functions("def !!!")


def test_returns_tuple_not_list() -> None:
    """The return type is a tuple, matching the model contract."""
    result = extract_functions("def f(): pass")
    assert isinstance(result, tuple)
