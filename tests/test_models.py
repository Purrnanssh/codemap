"""Unit tests for the AST engine domain models.

These tests verify that the dataclasses in codemap.ast_engine.models
behave as expected: they construct correctly, they are immutable,
they support value equality, and they are hashable.
"""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from codemap.ast_engine.models import (
    CallInfo,
    ClassInfo,
    FileAnalysis,
    FunctionInfo,
    ImportInfo,
)

# ---------------------------------------------------------------------------
# Construction tests: each model can be built and its fields are accessible.
# ---------------------------------------------------------------------------


def test_import_info_construction() -> None:
    """ImportInfo stores all four fields correctly."""
    imp = ImportInfo(module="os", name="path", alias=None, line=1)
    assert imp.module == "os"
    assert imp.name == "path"
    assert imp.alias is None
    assert imp.line == 1


def test_import_info_with_alias() -> None:
    """ImportInfo correctly stores an alias when provided."""
    imp = ImportInfo(module="numpy", name="numpy", alias="np", line=3)
    assert imp.alias == "np"


def test_function_info_construction() -> None:
    """FunctionInfo stores all four fields correctly."""
    func = FunctionInfo(name="greet", line=10, args=("name", "greeting"), is_async=False)
    assert func.name == "greet"
    assert func.line == 10
    assert func.args == ("name", "greeting")
    assert func.is_async is False


def test_function_info_async() -> None:
    """FunctionInfo correctly flags async functions."""
    func = FunctionInfo(name="fetch", line=5, args=("url",), is_async=True)
    assert func.is_async is True


def test_class_info_construction() -> None:
    """ClassInfo stores its name, line, and methods tuple."""
    method = FunctionInfo(name="bark", line=12, args=("self",), is_async=False)
    cls = ClassInfo(name="Dog", line=10, methods=(method,))
    assert cls.name == "Dog"
    assert cls.line == 10
    assert cls.methods == (method,)


def test_call_info_construction() -> None:
    """CallInfo stores the callee name and line number."""
    call = CallInfo(callee="print", line=42)
    assert call.callee == "print"
    assert call.line == 42


def test_file_analysis_construction_with_defaults() -> None:
    """FileAnalysis can be built with only a path; other fields default to empty."""
    analysis = FileAnalysis(path=Path("example.py"))
    assert analysis.path == Path("example.py")
    assert analysis.imports == ()
    assert analysis.functions == ()
    assert analysis.classes == ()
    assert analysis.calls == ()


def test_file_analysis_construction_full() -> None:
    """FileAnalysis can be built with all fields populated."""
    imp = ImportInfo(module="os", name="path", alias=None, line=1)
    func = FunctionInfo(name="main", line=3, args=(), is_async=False)
    cls = ClassInfo(name="App", line=5, methods=())
    call = CallInfo(callee="print", line=8)

    analysis = FileAnalysis(
        path=Path("app.py"),
        imports=(imp,),
        functions=(func,),
        classes=(cls,),
        calls=(call,),
    )

    assert analysis.imports == (imp,)
    assert analysis.functions == (func,)
    assert analysis.classes == (cls,)
    assert analysis.calls == (call,)


# ---------------------------------------------------------------------------
# Immutability tests: frozen=True prevents mutation after construction.
# ---------------------------------------------------------------------------


def test_import_info_is_immutable() -> None:
    """Mutating an ImportInfo raises FrozenInstanceError."""
    imp = ImportInfo(module="os", name="path", alias=None, line=1)
    with pytest.raises(FrozenInstanceError):
        imp.module = "sys"  # type: ignore[misc]


def test_function_info_is_immutable() -> None:
    """Mutating a FunctionInfo raises FrozenInstanceError."""
    func = FunctionInfo(name="f", line=1, args=(), is_async=False)
    with pytest.raises(FrozenInstanceError):
        func.line = 99  # type: ignore[misc]


def test_file_analysis_is_immutable() -> None:
    """Mutating a FileAnalysis raises FrozenInstanceError."""
    analysis = FileAnalysis(path=Path("x.py"))
    with pytest.raises(FrozenInstanceError):
        analysis.path = Path("y.py")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Equality tests: two models with identical fields compare equal.
# ---------------------------------------------------------------------------


def test_import_info_equality() -> None:
    """Two ImportInfo objects with the same fields are equal."""
    a = ImportInfo(module="os", name="path", alias=None, line=1)
    b = ImportInfo(module="os", name="path", alias=None, line=1)
    assert a == b


def test_function_info_inequality() -> None:
    """Two FunctionInfo objects with different fields are not equal."""
    a = FunctionInfo(name="f", line=1, args=(), is_async=False)
    b = FunctionInfo(name="g", line=1, args=(), is_async=False)
    assert a != b


# ---------------------------------------------------------------------------
# Hashability tests: frozen dataclasses can be used in sets and as dict keys.
# ---------------------------------------------------------------------------


def test_import_info_is_hashable() -> None:
    """ImportInfo can be added to a set."""
    a = ImportInfo(module="os", name="path", alias=None, line=1)
    b = ImportInfo(module="os", name="path", alias=None, line=1)
    assert len({a, b}) == 1  # duplicates collapse


def test_function_info_is_hashable() -> None:
    """FunctionInfo can be added to a set and used as a dict key."""
    func = FunctionInfo(name="f", line=1, args=("x",), is_async=False)
    container = {func: "metadata"}
    assert container[func] == "metadata"
