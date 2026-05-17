"""CodeMap command-line interface.

This module wires up the `codemap` command using Typer. Each subcommand
(analyze, version, etc.) is a function decorated with `@app.command()`.

Typer turns these Python functions into a real CLI with argument parsing,
help text, type validation, and colored output — for free.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

from codemap.version import __version__

# The Typer application. `no_args_is_help=True` means: if a user runs
# `codemap` with no arguments, show the help menu instead of doing nothing.
app = typer.Typer(
    name="codemap",
    help="Static analysis tool that maps Python codebases.",
    no_args_is_help=True,
    add_completion=False,
)

# A shared Rich Console for pretty output. One instance, reused everywhere.
console = Console()


@app.command()
def hello(name: str = "world") -> None:
    """Say hello — a tiny smoke test to confirm the CLI is wired up correctly."""
    console.print(
        Panel.fit(
            f"[bold cyan]Hello, {name}![/bold cyan]\n[dim]CodeMap v{__version__} is alive.[/dim]",
            border_style="cyan",
            title="🗺️  CodeMap",
        )
    )


@app.command()
def version() -> None:
    """Print the installed CodeMap version."""
    console.print(f"[bold]codemap[/bold] [cyan]{__version__}[/cyan]")


def main() -> None:
    """Entry point referenced by `[project.scripts]` in pyproject.toml."""
    app()


if __name__ == "__main__":
    main()
