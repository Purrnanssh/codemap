"""Rich-based renderers for AST analysis results.

This module turns ``FileAnalysis`` objects into Rich renderables
that can be printed to the terminal. It contains no parsing logic
and no CLI logic; it is a pure presentation layer so it can be
tested in isolation.
"""

from __future__ import annotations

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from codemap.ast_engine.models import FileAnalysis


def render_analysis(analysis: FileAnalysis) -> Group:
    """Render a FileAnalysis as a Rich Group of panels.

    The Group contains, in order:
        - A header panel naming the file
        - One panel per category (imports, functions, classes, calls)

    Args:
        analysis: The parsed file analysis to render.

    Returns:
        A Rich Group that can be printed to a Console.
    """
    return Group(
        _header_panel(analysis),
        _imports_panel(analysis),
        _functions_panel(analysis),
        _classes_panel(analysis),
        _calls_panel(analysis),
    )


def _header_panel(analysis: FileAnalysis) -> Panel:
    """Build the top header panel naming the file under analysis."""
    title = Text("🗺️  CodeMap Analysis", style="bold cyan")
    subtitle = Text(str(analysis.path), style="dim")
    return Panel(
        Group(title, subtitle),
        border_style="cyan",
    )


def _imports_panel(analysis: FileAnalysis) -> Panel:
    """Build a panel listing every import in the file."""
    if not analysis.imports:
        return _empty_panel("Imports")

    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Module")
    table.add_column("Name")
    table.add_column("Alias")
    table.add_column("Line", justify="right")

    for imp in analysis.imports:
        table.add_row(
            imp.module or "(relative)",
            imp.name,
            imp.alias or "-",
            str(imp.line),
        )

    return Panel(table, title=f"Imports ({len(analysis.imports)})", border_style="magenta")


def _functions_panel(analysis: FileAnalysis) -> Panel:
    """Build a panel listing every top-level function in the file."""
    if not analysis.functions:
        return _empty_panel("Functions")

    table = Table(show_header=True, header_style="bold green", expand=True)
    table.add_column("Name")
    table.add_column("Args")
    table.add_column("Async", justify="center")
    table.add_column("Line", justify="right")

    for fn in analysis.functions:
        args_repr = "(" + ", ".join(fn.args) + ")" if fn.args else "()"
        table.add_row(
            fn.name,
            args_repr,
            "yes" if fn.is_async else "no",
            str(fn.line),
        )

    return Panel(table, title=f"Functions ({len(analysis.functions)})", border_style="green")


def _classes_panel(analysis: FileAnalysis) -> Panel:
    """Build a panel listing every top-level class and its methods."""
    if not analysis.classes:
        return _empty_panel("Classes")

    table = Table(show_header=True, header_style="bold yellow", expand=True)
    table.add_column("Class")
    table.add_column("Method")
    table.add_column("Args")
    table.add_column("Async", justify="center")
    table.add_column("Line", justify="right")

    for cls in analysis.classes:
        if not cls.methods:
            table.add_row(cls.name, "(no methods)", "", "", str(cls.line))
            continue
        for i, method in enumerate(cls.methods):
            args_repr = "(" + ", ".join(method.args) + ")" if method.args else "()"
            table.add_row(
                cls.name if i == 0 else "",
                method.name,
                args_repr,
                "yes" if method.is_async else "no",
                str(method.line),
            )

    return Panel(table, title=f"Classes ({len(analysis.classes)})", border_style="yellow")


def _calls_panel(analysis: FileAnalysis) -> Panel:
    """Build a panel listing every call site in the file."""
    if not analysis.calls:
        return _empty_panel("Calls")

    table = Table(show_header=True, header_style="bold blue", expand=True)
    table.add_column("Callee")
    table.add_column("Line", justify="right")

    for call in analysis.calls:
        table.add_row(call.callee, str(call.line))

    return Panel(table, title=f"Calls ({len(analysis.calls)})", border_style="blue")


def _empty_panel(label: str) -> Panel:
    """Build a placeholder panel for a category that has no entries."""
    return Panel(
        Text("(none)", style="dim italic"),
        title=f"{label} (0)",
        border_style="dim",
    )
