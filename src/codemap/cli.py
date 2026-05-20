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
from codemap.callgraph.builder import build_call_graph
from codemap.callgraph.exporters import to_dot, to_json
from codemap.graph.builder import build_graph, find_cycles
from codemap.rendering import (
    render_analysis,
    render_callgraph_summary,
    render_graph_summary,
)
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


@app.command()
def callgraph(
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
                "repo root. Dotted paths in the output will match your "
                "code's import strings."
            ),
        ),
    ],
    format: Annotated[
        str | None,
        typer.Option(
            "--format",
            help=(
                "Export format. When set, also requires --output. "
                "Choices: 'dot' (Graphviz) or 'json'."
            ),
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help=(
                "Write the exported graph to this file. Required when "
                "--format is set. Without --format, the file is not "
                "written and only the terminal summary is shown."
            ),
        ),
    ] = None,
    hotspots: Annotated[
        int,
        typer.Option(
            "--hotspots",
            help="How many hotspots to show in the terminal summary.",
            min=0,
        ),
    ] = 10,
    min_complexity: Annotated[
        int,
        typer.Option(
            "--min-complexity",
            help=(
                "Hide functions below this McCabe complexity from the "
                "hotspot table. When combined with --output, also "
                "filters the exported graph."
            ),
            min=1,
        ),
    ] = 1,
) -> None:
    """Build a symbol-level call graph and surface complexity hotspots.

    Discovers every Python module under the directory, extracts every
    function and call site, resolves calls to typed edges (internal,
    self, external, unresolved), computes McCabe complexity per
    function, and reports the top hotspots ranked by complexity times
    fan-in. Optionally exports the assembled graph to Graphviz DOT or
    JSON for external visualization.

    Files that fail to parse are reported but do not stop the scan.
    """
    if format is not None and output is None:
        console.print(
            "[bold red]Error:[/bold red] --format requires --output."
        )
        raise typer.Exit(code=1)
    if output is not None and format is None:
        console.print(
            "[bold red]Error:[/bold red] --output requires --format."
        )
        raise typer.Exit(code=1)
    if format is not None and format not in {"dot", "json"}:
        console.print(
            f"[bold red]Error:[/bold red] unknown --format '{format}'. "
            f"Choices: dot, json."
        )
        raise typer.Exit(code=1)

    try:
        graph, parse_errors = build_call_graph(directory)
    except (FileNotFoundError, NotADirectoryError) as exc:
        console.print(
            f"[bold red]Cannot scan {directory}:[/bold red] {exc}"
        )
        raise typer.Exit(code=1) from exc

    console.print(
        render_callgraph_summary(
            graph=graph,
            parse_errors=parse_errors,
            root=directory,
            hotspots_limit=hotspots,
            min_complexity=min_complexity,
        )
    )

    if format is not None and output is not None:
        if format == "json":
            payload = to_json(graph, min_complexity=min_complexity)
        else:
            payload = to_dot(graph, min_complexity=min_complexity)
        output.write_text(payload, encoding="utf-8")
        console.print(
            f"[dim]Wrote {format.upper()} export to {output}[/dim]"
        )

    if parse_errors:
        raise typer.Exit(code=2)
