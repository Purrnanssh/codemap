"""Unit tests for call extraction in the AST parser."""

from __future__ import annotations

import pytest

from codemap.ast_engine.models import CallInfo
from codemap.ast_engine.parser import UNKNOWN_CALLEE, extract_calls

# ---------------------------------------------------------------------------
# Simple Name calls
# ---------------------------------------------------------------------------


def test_extract_single_name_call() -> None:
    """A bare function call captures the function name."""
    result = extract_calls("print('hello')")
    assert result == (CallInfo(callee="print", line=1),)


def test_extract_multiple_name_calls() -> None:
    """Multiple top-level calls are each captured."""
    source = "\n".join(
        [
            "print('a')",
            "len('b')",
            "abs(-1)",
        ]
    )
    result = extract_calls(source)
    callees = {c.callee for c in result}
    assert callees == {"print", "len", "abs"}


# ---------------------------------------------------------------------------
# Attribute (dotted) calls
# ---------------------------------------------------------------------------


def test_extract_single_attribute_call() -> None:
    """A two-level attribute call is captured as a dotted name."""
    result = extract_calls("obj.method()")
    assert result == (CallInfo(callee="obj.method", line=1),)


def test_extract_deeply_nested_attribute_call() -> None:
    """A multi-level attribute call captures the full dotted path."""
    result = extract_calls("a.b.c.d.method()")
    assert result == (CallInfo(callee="a.b.c.d.method", line=1),)


def test_extract_self_method_call() -> None:
    """A method call on self is captured as 'self.method'."""
    source = "\n".join(
        [
            "class App:",
            "    def run(self):",
            "        self.helper()",
        ]
    )
    result = extract_calls(source)
    # The method definition is not a call; only self.helper() is.
    assert len(result) == 1
    assert result[0].callee == "self.helper"


# ---------------------------------------------------------------------------
# Calls happen anywhere (not just top-level)
# ---------------------------------------------------------------------------


def test_calls_inside_functions_are_captured() -> None:
    """Calls inside function bodies are captured."""
    source = "\n".join(
        [
            "def greet():",
            "    print('hi')",
        ]
    )
    result = extract_calls(source)
    assert any(c.callee == "print" for c in result)


def test_calls_inside_classes_are_captured() -> None:
    """Calls inside class methods are captured."""
    source = "\n".join(
        [
            "class App:",
            "    def run(self):",
            "        print('starting')",
            "        self.execute()",
        ]
    )
    result = extract_calls(source)
    callees = {c.callee for c in result}
    assert "print" in callees
    assert "self.execute" in callees


# ---------------------------------------------------------------------------
# Unknown callee shapes
# ---------------------------------------------------------------------------


def test_call_on_call_result_is_unknown() -> None:
    """Calling the result of another call marks the outer call as unknown."""
    source = "get_handler()('x')"
    result = extract_calls(source)
    callees = [c.callee for c in result]
    # Two calls: the outer one is unknown, the inner is 'get_handler'.
    assert UNKNOWN_CALLEE in callees
    assert "get_handler" in callees


def test_call_on_subscript_is_unknown() -> None:
    """Calling a value retrieved by subscript is marked as unknown."""
    result = extract_calls("handlers['name']()")
    assert any(c.callee == UNKNOWN_CALLEE for c in result)


def test_call_on_lambda_is_unknown() -> None:
    """Calling a lambda inline is marked as unknown."""
    result = extract_calls("(lambda x: x)(5)")
    assert any(c.callee == UNKNOWN_CALLEE for c in result)


# ---------------------------------------------------------------------------
# Line numbers and edge cases
# ---------------------------------------------------------------------------


def test_line_numbers_are_accurate() -> None:
    """Line numbers reflect the position of each call."""
    source = "\n".join(
        [
            "print('a')",
            "",
            "len('b')",
        ]
    )
    result = extract_calls(source)
    by_callee = {c.callee: c.line for c in result}
    assert by_callee["print"] == 1
    assert by_callee["len"] == 3


def test_empty_source_returns_empty_tuple() -> None:
    """Source with no calls returns an empty tuple."""
    result = extract_calls("x = 1\ny = 2")
    assert result == ()


def test_invalid_syntax_raises_syntax_error() -> None:
    """Malformed Python source raises SyntaxError."""
    with pytest.raises(SyntaxError):
        extract_calls("print(!!!)")


def test_returns_tuple_not_list() -> None:
    """The return type is a tuple, matching the model contract."""
    result = extract_calls("print()")
    assert isinstance(result, tuple)
