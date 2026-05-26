"""Smoke tests for the codemap CLI.

These tests use Typer's CliRunner to invoke the CLI in-process, without
spawning a real subprocess. They verify that:

  1. Each command runs without raising an exception (exit code 0).
  2. The output contains the expected content.

If any of these break, something is fundamentally wrong with the CLI.
"""

from __future__ import annotations

from typer.testing import CliRunner

from codemap import __version__
from codemap.cli import app

runner = CliRunner()


def test_hello_default_name() -> None:
    """`codemap hello` should greet 'world' and report the version."""
    result = runner.invoke(app, ["hello"])

    assert result.exit_code == 0, f"hello exited with {result.exit_code}: {result.output}"
    assert "Hello, world!" in result.output
    assert __version__ in result.output


def test_version_command() -> None:
    """`codemap version` should print the current package version."""
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert __version__ in result.output


def test_no_args_shows_help() -> None:
    """`codemap` with no args should show the help screen (because of no_args_is_help=True)."""
    result = runner.invoke(app, [])

    # Typer exits with code 0 or 2 when showing help, depending on version.
    assert result.exit_code in (0, 2)
    assert "Usage:" in result.output
    assert "hello" in result.output
    assert "version" in result.output


