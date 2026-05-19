"""Integration tests for the ``codemap scan`` CLI command."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from codemap.cli import app

runner = CliRunner()


def _touch(path: Path, content: str = "") -> None:
    """Create parent dirs if needed and write content to path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Successful scans
# ---------------------------------------------------------------------------


def test_scan_empty_directory_exits_zero(tmp_path: Path) -> None:
    """An empty directory scans cleanly with exit code 0."""
    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "CodeMap Dependency Graph" in result.output


def test_scan_simple_project_shows_stats(tmp_path: Path) -> None:
    """A small project's scan output includes the stats panel."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "core.py", "import os\n")

    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "Stats" in result.output
    assert "Modules" in result.output


def test_scan_lists_top_imported_modules(tmp_path: Path) -> None:
    """The Top imported panel appears for a project with internal edges."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "hub.py")
    _touch(tmp_path / "pkg" / "a.py", "from pkg import hub\n")
    _touch(tmp_path / "pkg" / "b.py", "from pkg import hub\n")

    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "Top imported" in result.output
    assert "hub" in result.output


# ---------------------------------------------------------------------------
# Cycle handling
# ---------------------------------------------------------------------------


def test_scan_cycle_exits_with_code_two(tmp_path: Path) -> None:
    """A project with a circular import exits with code 2."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "a.py", "from pkg import b\n")
    _touch(tmp_path / "pkg" / "b.py", "from pkg import a\n")

    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 2
    assert "Cycles" in result.output


def test_scan_cycle_shows_arrow_chain(tmp_path: Path) -> None:
    """Detected cycles are rendered with arrow notation."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "a.py", "from pkg import b\n")
    _touch(tmp_path / "pkg" / "b.py", "from pkg import a\n")

    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 2
    assert "->" in result.output
    assert "pkg.a" in result.output
    assert "pkg.b" in result.output


def test_scan_clean_project_exits_zero(tmp_path: Path) -> None:
    """A project without cycles exits with code 0."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "a.py")
    _touch(tmp_path / "pkg" / "b.py", "from pkg import a\n")

    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Parse error handling
# ---------------------------------------------------------------------------


def test_scan_reports_parse_errors_but_continues(tmp_path: Path) -> None:
    """Files with syntax errors appear in the Parse errors section."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "broken.py", "def def def\n")
    _touch(tmp_path / "pkg" / "good.py", "x = 1\n")

    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "Parse errors" in result.output
    assert "pkg.broken" in result.output


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------


def test_scan_missing_directory_exits_nonzero(tmp_path: Path) -> None:
    """A nonexistent directory causes a nonzero exit code."""
    missing = tmp_path / "does_not_exist"
    result = runner.invoke(app, ["scan", str(missing)])
    assert result.exit_code != 0


def test_scan_file_instead_of_directory_exits_nonzero(tmp_path: Path) -> None:
    """Passing a file instead of a directory causes a nonzero exit code."""
    f = tmp_path / "not_a_dir.py"
    f.write_text("", encoding="utf-8")
    result = runner.invoke(app, ["scan", str(f)])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Help and discoverability
# ---------------------------------------------------------------------------


def test_scan_help_mentions_src_layout(tmp_path: Path) -> None:
    """The scan --help text guides users toward the right input path."""
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0
    assert "src/" in result.output


def test_scan_appears_in_top_level_help() -> None:
    """The scan command shows up in `codemap --help`."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "scan" in result.output
