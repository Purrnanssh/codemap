"""Unit tests for import extraction in the AST parser."""

from __future__ import annotations

import pytest

from codemap.ast_engine.models import ImportInfo
from codemap.ast_engine.parser import extract_imports

# ---------------------------------------------------------------------------
# Plain `import x` form
# ---------------------------------------------------------------------------


def test_extract_single_import() -> None:
    """A single `import x` produces one ImportInfo with matching module and name."""
    result = extract_imports("import os")
    assert result == (ImportInfo(module="os", name="os", alias=None, line=1),)


def test_extract_import_with_alias() -> None:
    """`import x as y` correctly captures the alias."""
    result = extract_imports("import numpy as np")
    assert result == (ImportInfo(module="numpy", name="numpy", alias="np", line=1),)


def test_extract_multiple_imports_on_one_line() -> None:
    """`import a, b, c` produces one ImportInfo per name."""
    result = extract_imports("import os, sys, json")
    assert len(result) == 3
    assert {imp.module for imp in result} == {"os", "sys", "json"}


def test_extract_dotted_import() -> None:
    """`import x.y.z` captures the full dotted path as a single name."""
    result = extract_imports("import os.path")
    assert result == (ImportInfo(module="os.path", name="os.path", alias=None, line=1),)


# ---------------------------------------------------------------------------
# `from x import y` form
# ---------------------------------------------------------------------------


def test_extract_from_import() -> None:
    """`from x import y` separates module and name."""
    result = extract_imports("from pathlib import Path")
    assert result == (ImportInfo(module="pathlib", name="Path", alias=None, line=1),)


def test_extract_from_import_with_alias() -> None:
    """`from x import y as z` captures the alias."""
    result = extract_imports("from pathlib import Path as P")
    assert result == (ImportInfo(module="pathlib", name="Path", alias="P", line=1),)


def test_extract_from_import_multiple_names() -> None:
    """`from x import a, b, c` produces one ImportInfo per name."""
    result = extract_imports("from os import path, sep, linesep")
    assert len(result) == 3
    assert all(imp.module == "os" for imp in result)
    assert {imp.name for imp in result} == {"path", "sep", "linesep"}


def test_extract_relative_import() -> None:
    """`from . import x` is captured with empty module and level=1."""
    result = extract_imports("from . import helpers")
    assert result == (ImportInfo(module="", name="helpers", alias=None, line=1, level=1),)


def test_extract_relative_import_with_module() -> None:
    """`from .sibling import x` captures module='sibling' and level=1."""
    result = extract_imports("from .sibling import foo")
    assert result == (ImportInfo(module="sibling", name="foo", alias=None, line=1, level=1),)


def test_extract_relative_import_with_double_dot() -> None:
    """`from ..pkg import x` captures module='pkg' and level=2."""
    result = extract_imports("from ..pkg import bar")
    assert result == (ImportInfo(module="pkg", name="bar", alias=None, line=1, level=2),)


def test_extract_absolute_import_has_level_zero() -> None:
    """Absolute imports always have level=0."""
    result = extract_imports("from pathlib import Path")
    assert result == (ImportInfo(module="pathlib", name="Path", alias=None, line=1, level=0),)


# ---------------------------------------------------------------------------
# Line numbers and ordering
# ---------------------------------------------------------------------------


def test_line_numbers_are_accurate() -> None:
    """Line numbers reflect the actual position of each import in source."""
    source = "\n".join(
        [
            "import os",
            "",
            "import sys",
            "from json import loads",
        ]
    )
    result = extract_imports(source)
    lines = [imp.line for imp in result]
    assert lines == [1, 3, 4]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_source_returns_empty_tuple() -> None:
    """Source with no imports returns an empty tuple."""
    result = extract_imports("x = 1\ny = 2\n")
    assert result == ()


def test_invalid_syntax_raises_syntax_error() -> None:
    """Malformed Python source raises SyntaxError."""
    with pytest.raises(SyntaxError):
        extract_imports("import !!!")


def test_returns_tuple_not_list() -> None:
    """The return type is a tuple, matching the model contract."""
    result = extract_imports("import os")
    assert isinstance(result, tuple)
