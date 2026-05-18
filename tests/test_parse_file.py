"""Integration tests for parse_file, the file-based parser entry point."""

from __future__ import annotations

from pathlib import Path

import pytest

from codemap.ast_engine.models import FileAnalysis
from codemap.ast_engine.parser import parse_file

# ---------------------------------------------------------------------------
# Successful parsing
# ---------------------------------------------------------------------------


def test_parse_file_returns_file_analysis(tmp_path: Path) -> None:
    """parse_file returns a FileAnalysis with the given path."""
    target = tmp_path / "sample.py"
    target.write_text("x = 1\n", encoding="utf-8")
    result = parse_file(target)
    assert isinstance(result, FileAnalysis)
    assert result.path == target


def test_parse_file_extracts_all_categories(tmp_path: Path) -> None:
    """parse_file populates imports, functions, classes, and calls."""
    source = "\n".join(
        [
            "import os",
            "from pathlib import Path",
            "",
            "def greet(name):",
            "    print(name)",
            "",
            "class Dog:",
            "    def bark(self):",
            "        print('woof')",
        ]
    )
    target = tmp_path / "rich.py"
    target.write_text(source, encoding="utf-8")

    result = parse_file(target)

    assert len(result.imports) == 2
    assert len(result.functions) == 1
    assert result.functions[0].name == "greet"
    assert len(result.classes) == 1
    assert result.classes[0].name == "Dog"
    # 'print' appears twice (in greet and in bark), plus no other calls.
    print_calls = [c for c in result.calls if c.callee == "print"]
    assert len(print_calls) == 2


def test_parse_file_accepts_string_path(tmp_path: Path) -> None:
    """parse_file works when given a string path instead of a Path."""
    target = tmp_path / "sample.py"
    target.write_text("import os\n", encoding="utf-8")
    result = parse_file(str(target))
    assert isinstance(result, FileAnalysis)
    assert len(result.imports) == 1


def test_parse_file_with_empty_file(tmp_path: Path) -> None:
    """An empty file produces a FileAnalysis with all empty tuples."""
    target = tmp_path / "empty.py"
    target.write_text("", encoding="utf-8")
    result = parse_file(target)
    assert result.imports == ()
    assert result.functions == ()
    assert result.classes == ()
    assert result.calls == ()


# ---------------------------------------------------------------------------
# Error handling: parse_file lets exceptions propagate
# ---------------------------------------------------------------------------


def test_parse_file_raises_for_missing_file(tmp_path: Path) -> None:
    """A missing file raises FileNotFoundError."""
    missing = tmp_path / "does_not_exist.py"
    with pytest.raises(FileNotFoundError):
        parse_file(missing)


def test_parse_file_raises_for_directory(tmp_path: Path) -> None:
    """A path pointing to a directory raises IsADirectoryError."""
    with pytest.raises(IsADirectoryError):
        parse_file(tmp_path)


def test_parse_file_raises_for_syntax_error(tmp_path: Path) -> None:
    """A file with invalid Python raises SyntaxError."""
    target = tmp_path / "broken.py"
    target.write_text("def !!!", encoding="utf-8")
    with pytest.raises(SyntaxError):
        parse_file(target)
