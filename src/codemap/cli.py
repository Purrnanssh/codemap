"""Command-line interface for CodeMap.

Built on Typer for command parsing and Rich for terminal output.
Each command is a small function decorated with ``@app.command()``.
Rendering is delegated to ``codemap.rendering`` so this module
stays focused on command parsing and error handling.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from codemap.ast_engine.parser import parse_file
from codemap.rendering import render_analysis
from codemap.version import __version__

app = typer.Typer(
    help="CodeMap: static analysis for Python codebases.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def hello() -> None:
    """Print a friendly greeting to confirm the CLI is working."""
    console.print(
        Panel.fit(
            f"Hello, world!\nCodeMap v{__version__} is alive.",
            title="🗺️  CodeMap",
        )
    )


@app.command()
def version() -> None:
    """Print the installed CodeMap version."""
    console.print(f"codemap {__version__}")


@app.command()
def analyze(
    path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to a Python file to analyze.",
        ),
    ],
) -> None:
    """Parse a Python file and print its structural analysis."""
    try:
        analysis = parse_file(path)
    except SyntaxError as exc:
        console.print(f"[bold red]Syntax error in {path}:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    except UnicodeDecodeError as exc:
        console.print(f"[bold red]Cannot decode {path}:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(render_analysis(analysis))


def main() -> None:
    """Entry point for the codemap CLI."""
    app()
