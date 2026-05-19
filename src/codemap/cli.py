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
from codemap.graph.builder import build_graph, find_cycles
from codemap.rendering import render_analysis, render_graph_summary
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


@app.command()
def scan(
    directory: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            help=(
                "Path to scan. Point at the directory that contains your "
                "package(s). For a src/ layout that is 'src'; for a flat "
                "layout where 'mypkg/' lives at the repo root, that is the "
                "repo root. Dotted paths in the output will be relative to "
                "this directory."
            ),
        ),
    ],
) -> None:
    """Scan a project directory and print its dependency graph summary.

    Discovers every Python module under the directory, parses each,
    resolves imports, builds a module-level dependency graph, and
    detects circular dependencies. Files that fail to parse are
    reported but do not stop the scan.
    """
    try:
        graph = build_graph(directory)
    except (FileNotFoundError, NotADirectoryError) as exc:
        console.print(f"[bold red]Cannot scan {directory}:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    cycles = find_cycles(graph)
    console.print(render_graph_summary(graph, cycles, directory))

    # Exit with nonzero status if cycles were detected. This makes the
    # command CI-friendly: a project can run `codemap scan` as a check
    # step and fail the build on circular dependencies.
    if cycles:
        raise typer.Exit(code=2)
