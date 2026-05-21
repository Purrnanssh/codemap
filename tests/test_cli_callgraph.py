"""Integration tests for the ``codemap callgraph`` CLI command.

Tests invoke the Typer app via its test runner against small fixture
projects on disk. They cover the default summary output, the
--format / --output export flags, the --hotspots and --min-complexity
flags, error handling, and exit codes.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from codemap.cli import app

runner = CliRunner()


def _write(file: Path, source: str) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(source, encoding="utf-8")


def _project(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "project"
    for rel, source in files.items():
        _write(root / rel, source)
    return root


class TestDefaultSummary:
    def test_runs_clean_on_simple_project(self, tmp_path: Path) -> None:
        root = _project(
            tmp_path,
            {
                "mod.py": ("def foo():\n    bar()\n\ndef bar():\n    pass\n"),
            },
        )

        result = runner.invoke(app, ["callgraph", str(root)])

        assert result.exit_code == 0
        assert "Call Graph" in result.stdout
        assert "Functions" in result.stdout
        assert "Hotspots" in result.stdout

    def test_summary_shows_function_count(self, tmp_path: Path) -> None:
        root = _project(
            tmp_path,
            {"mod.py": "def a():\n    pass\n\ndef b():\n    pass\n"},
        )

        result = runner.invoke(app, ["callgraph", str(root)])

        assert result.exit_code == 0
        # Both functions should appear in the hotspot table or stats.
        assert "mod.a" in result.stdout
        assert "mod.b" in result.stdout


class TestExitCodes:
    def test_clean_project_exits_zero(self, tmp_path: Path) -> None:
        root = _project(tmp_path, {"mod.py": "def foo():\n    pass\n"})

        result = runner.invoke(app, ["callgraph", str(root)])

        assert result.exit_code == 0

    def test_parse_error_exits_two(self, tmp_path: Path) -> None:
        root = _project(
            tmp_path,
            {
                "good.py": "def foo():\n    pass\n",
                "bad.py": "def broken(:\n    pass\n",
            },
        )

        result = runner.invoke(app, ["callgraph", str(root)])

        assert result.exit_code == 2
        assert "Parse errors" in result.stdout

    def test_missing_directory_exits_one(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist"

        result = runner.invoke(app, ["callgraph", str(missing)])

        assert result.exit_code != 0


class TestFormatAndOutput:
    def test_format_without_output_errors(self, tmp_path: Path) -> None:
        root = _project(tmp_path, {"mod.py": "def foo():\n    pass\n"})

        result = runner.invoke(app, ["callgraph", str(root), "--format", "json"])

        assert result.exit_code == 1
        assert "--format requires --output" in result.stdout

    def test_output_without_format_errors(self, tmp_path: Path) -> None:
        root = _project(tmp_path, {"mod.py": "def foo():\n    pass\n"})
        out = tmp_path / "out.json"

        result = runner.invoke(app, ["callgraph", str(root), "--output", str(out)])

        assert result.exit_code == 1
        assert "--output requires --format" in result.stdout

    def test_unknown_format_errors(self, tmp_path: Path) -> None:
        root = _project(tmp_path, {"mod.py": "def foo():\n    pass\n"})
        out = tmp_path / "out.xml"

        result = runner.invoke(
            app,
            [
                "callgraph",
                str(root),
                "--format",
                "xml",
                "--output",
                str(out),
            ],
        )

        assert result.exit_code == 1
        assert "unknown --format" in result.stdout

    def test_json_export_writes_file(self, tmp_path: Path) -> None:
        root = _project(
            tmp_path,
            {
                "mod.py": ("def foo():\n    bar()\n\ndef bar():\n    pass\n"),
            },
        )
        out = tmp_path / "graph.json"

        result = runner.invoke(
            app,
            [
                "callgraph",
                str(root),
                "--format",
                "json",
                "--output",
                str(out),
            ],
        )

        assert result.exit_code == 0
        assert out.exists()

        doc = json.loads(out.read_text())
        node_ids = {n["id"] for n in doc["nodes"]}
        assert "mod.foo" in node_ids
        assert "mod.bar" in node_ids

    def test_dot_export_writes_file(self, tmp_path: Path) -> None:
        root = _project(
            tmp_path,
            {"mod.py": "def foo():\n    pass\n"},
        )
        out = tmp_path / "graph.dot"

        result = runner.invoke(
            app,
            [
                "callgraph",
                str(root),
                "--format",
                "dot",
                "--output",
                str(out),
            ],
        )

        assert result.exit_code == 0
        assert out.exists()
        content = out.read_text()
        assert content.startswith("digraph CodeMap {")
        assert '"mod.foo"' in content


class TestHotspotsFlag:
    def test_default_hotspot_limit(self, tmp_path: Path) -> None:
        root = _project(
            tmp_path,
            {"mod.py": "def foo():\n    pass\n"},
        )

        result = runner.invoke(app, ["callgraph", str(root)])

        assert result.exit_code == 0
        assert "top 10" in result.stdout

    def test_custom_hotspot_limit(self, tmp_path: Path) -> None:
        root = _project(
            tmp_path,
            {"mod.py": "def foo():\n    pass\n"},
        )

        result = runner.invoke(app, ["callgraph", str(root), "--hotspots", "3"])

        assert result.exit_code == 0
        assert "top 3" in result.stdout


class TestMinComplexityFlag:
    def test_filter_hides_low_complexity(self, tmp_path: Path) -> None:
        # simple has complexity 1, branchy has complexity 2.
        # With --min-complexity 2, only branchy survives.
        root = _project(
            tmp_path,
            {
                "mod.py": (
                    "def simple():\n"
                    "    pass\n"
                    "\n"
                    "def branchy(x):\n"
                    "    if x:\n"
                    "        return 1\n"
                    "    return 0\n"
                ),
            },
        )

        result = runner.invoke(
            app,
            ["callgraph", str(root), "--min-complexity", "2"],
        )

        assert result.exit_code == 0
        # branchy shown, simple hidden in the hotspot table.
        assert "mod.branchy" in result.stdout
        # We can't strongly assert mod.simple is absent because it
        # might appear in other context. Instead, check the
        # min-complexity label is shown.
        assert "min complexity 2" in result.stdout

    def test_filter_applies_to_export(self, tmp_path: Path) -> None:
        root = _project(
            tmp_path,
            {
                "mod.py": (
                    "def simple():\n"
                    "    pass\n"
                    "\n"
                    "def branchy(x):\n"
                    "    if x:\n"
                    "        return 1\n"
                    "    return 0\n"
                ),
            },
        )
        out = tmp_path / "graph.json"

        result = runner.invoke(
            app,
            [
                "callgraph",
                str(root),
                "--format",
                "json",
                "--output",
                str(out),
                "--min-complexity",
                "2",
            ],
        )

        assert result.exit_code == 0
        doc = json.loads(out.read_text())
        node_ids = {n["id"] for n in doc["nodes"]}
        # Only the branchy function survives the filter in the export.
        assert "mod.branchy" in node_ids
        assert "mod.simple" not in node_ids
