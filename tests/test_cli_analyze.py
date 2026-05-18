"""Integration tests for the ``codemap analyze`` CLI command."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from codemap.cli import app

runner = CliRunner()


def test_analyze_prints_file_path(tmp_path: Path) -> None:
    """Output mentions the analyzed file's path."""
    target = tmp_path / "sample.py"
    target.write_text("x = 1\n", encoding="utf-8")
    result = runner.invoke(app, ["analyze", str(target)])
    assert result.exit_code == 0
    assert "sample.py" in result.output


def test_analyze_shows_imports(tmp_path: Path) -> None:
    """Output includes the Imports panel when imports are present."""
    target = tmp_path / "with_imports.py"
    target.write_text("import os\nfrom pathlib import Path\n", encoding="utf-8")
    result = runner.invoke(app, ["analyze", str(target)])
    assert result.exit_code == 0
    assert "Imports" in result.output
    assert "os" in result.output
    assert "pathlib" in result.output


def test_analyze_shows_functions(tmp_path: Path) -> None:
    """Output includes the Functions panel when functions are present."""
    target = tmp_path / "with_funcs.py"
    target.write_text("def greet(name): pass\n", encoding="utf-8")
    result = runner.invoke(app, ["analyze", str(target)])
    assert result.exit_code == 0
    assert "Functions" in result.output
    assert "greet" in result.output


def test_analyze_shows_classes(tmp_path: Path) -> None:
    """Output includes the Classes panel when classes are present."""
    target = tmp_path / "with_classes.py"
    target.write_text("class Dog:\n    def bark(self): pass\n", encoding="utf-8")
    result = runner.invoke(app, ["analyze", str(target)])
    assert result.exit_code == 0
    assert "Classes" in result.output
    assert "Dog" in result.output
    assert "bark" in result.output


def test_analyze_shows_calls(tmp_path: Path) -> None:
    """Output includes the Calls panel when calls are present."""
    target = tmp_path / "with_calls.py"
    target.write_text("print('hi')\n", encoding="utf-8")
    result = runner.invoke(app, ["analyze", str(target)])
    assert result.exit_code == 0
    assert "Calls" in result.output
    assert "print" in result.output


def test_analyze_exits_nonzero_for_syntax_error(tmp_path: Path) -> None:
    """A file with invalid Python causes a nonzero exit code."""
    target = tmp_path / "broken.py"
    target.write_text("def !!!", encoding="utf-8")
    result = runner.invoke(app, ["analyze", str(target)])
    assert result.exit_code != 0
    assert "Syntax error" in result.output


def test_analyze_exits_nonzero_for_missing_file(tmp_path: Path) -> None:
    """A missing file causes Typer's validation to fail with nonzero exit."""
    missing = tmp_path / "does_not_exist.py"
    result = runner.invoke(app, ["analyze", str(missing)])
    assert result.exit_code != 0


def test_analyze_empty_file_succeeds(tmp_path: Path) -> None:
    """An empty file is analyzed successfully with the header visible."""
    target = tmp_path / "empty.py"
    target.write_text("", encoding="utf-8")
    result = runner.invoke(app, ["analyze", str(target)])
    assert result.exit_code == 0
    # Header still appears even with no findings.
    assert "CodeMap Analysis" in result.output
