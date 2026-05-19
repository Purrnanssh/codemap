"""Tests for codemap.graph.builder."""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import pytest

from codemap.graph.builder import build_graph


def _touch(path: Path, content: str = "") -> None:
    """Create parent dirs if needed and write content to path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


# ---------------------------------------------------------------------------
# Basic graph shape
# ---------------------------------------------------------------------------


def test_empty_project_yields_empty_graph(tmp_path: Path) -> None:
    """An empty directory produces a graph with no nodes."""
    graph = build_graph(tmp_path)
    assert isinstance(graph, nx.DiGraph)
    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0


def test_single_module_no_imports(tmp_path: Path) -> None:
    """A single .py file with no imports yields one node and no edges."""
    _touch(tmp_path / "lone.py", "x = 1\n")
    graph = build_graph(tmp_path)
    assert set(graph.nodes) == {"lone"}
    assert len(graph.edges) == 0


def test_node_attributes_set_correctly(tmp_path: Path) -> None:
    """Each node carries file_path, is_package, external_imports, parse_error."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "core.py", "import os\n")

    graph = build_graph(tmp_path)

    pkg_attrs = graph.nodes["pkg"]
    assert pkg_attrs["is_package"] is True
    assert pkg_attrs["file_path"].name == "__init__.py"
    assert pkg_attrs["parse_error"] is None

    core_attrs = graph.nodes["pkg.core"]
    assert core_attrs["is_package"] is False
    assert core_attrs["file_path"].name == "core.py"
    assert core_attrs["external_imports"] == 1  # os is external
    assert core_attrs["parse_error"] is None


# ---------------------------------------------------------------------------
# Edge creation: internal imports
# ---------------------------------------------------------------------------


def test_internal_import_creates_edge(tmp_path: Path) -> None:
    """An absolute import of an internal module creates an edge."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "core.py", "x = 1\n")
    _touch(tmp_path / "pkg" / "cli.py", "from pkg import core\n")

    graph = build_graph(tmp_path)
    assert ("pkg.cli", "pkg.core") in graph.edges


def test_from_import_name_edges_to_parent(tmp_path: Path) -> None:
    """`from pkg import a_function` edges to pkg, not pkg.a_function."""
    _touch(tmp_path / "pkg" / "__init__.py", "def a_function(): pass\n")
    _touch(tmp_path / "pkg" / "cli.py", "from pkg import a_function\n")

    graph = build_graph(tmp_path)
    assert ("pkg.cli", "pkg") in graph.edges
    assert "pkg.a_function" not in graph.nodes


def test_relative_import_creates_edge(tmp_path: Path) -> None:
    """A relative import resolves correctly and creates an edge."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "core.py", "x = 1\n")
    _touch(tmp_path / "pkg" / "cli.py", "from . import core\n")

    graph = build_graph(tmp_path)
    assert ("pkg.cli", "pkg.core") in graph.edges


def test_multiple_imports_create_multiple_edges(tmp_path: Path) -> None:
    """A module importing several internal modules gets edges to each."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "a.py")
    _touch(tmp_path / "pkg" / "b.py")
    _touch(tmp_path / "pkg" / "c.py")
    _touch(
        tmp_path / "pkg" / "main.py",
        "from pkg import a\nfrom pkg import b\nfrom pkg import c\n",
    )

    graph = build_graph(tmp_path)
    assert ("pkg.main", "pkg.a") in graph.edges
    assert ("pkg.main", "pkg.b") in graph.edges
    assert ("pkg.main", "pkg.c") in graph.edges
    assert graph.out_degree("pkg.main") == 3


# ---------------------------------------------------------------------------
# External imports
# ---------------------------------------------------------------------------


def test_external_import_no_edge(tmp_path: Path) -> None:
    """Importing an external package does not create an edge."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "core.py", "import pathlib\nimport os\n")

    graph = build_graph(tmp_path)
    assert len(graph.edges) == 0
    assert graph.nodes["pkg.core"]["external_imports"] == 2


def test_mixed_imports_count_correctly(tmp_path: Path) -> None:
    """Mix of internal and external imports is counted separately."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "core.py")
    _touch(
        tmp_path / "pkg" / "cli.py",
        "import os\nfrom pkg import core\nimport typer\n",
    )

    graph = build_graph(tmp_path)
    assert ("pkg.cli", "pkg.core") in graph.edges
    assert graph.nodes["pkg.cli"]["external_imports"] == 2


# ---------------------------------------------------------------------------
# Self-imports and degenerate cases
# ---------------------------------------------------------------------------


def test_self_import_does_not_create_edge(tmp_path: Path) -> None:
    """A module that imports itself does not get a self-loop edge."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "weird.py", "import pkg.weird\n")

    graph = build_graph(tmp_path)
    assert ("pkg.weird", "pkg.weird") not in graph.edges


def test_unresolved_internal_looking_import(tmp_path: Path) -> None:
    """An import that looks internal but points nowhere counts as external."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "cli.py", "from pkg import nonexistent_module\n")

    graph = build_graph(tmp_path)
    # `from pkg import nonexistent_module` resolves to pkg (the parent
    # package), so we DO get an edge to pkg. The submodule case is the
    # one that disappears.
    assert ("pkg.cli", "pkg") in graph.edges


# ---------------------------------------------------------------------------
# Parse error tolerance
# ---------------------------------------------------------------------------


def test_syntax_error_recorded_not_propagated(tmp_path: Path) -> None:
    """A file with a syntax error is added as a node with parse_error set."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "broken.py", "def def def\n")

    graph = build_graph(tmp_path)
    assert "pkg.broken" in graph.nodes
    err = graph.nodes["pkg.broken"]["parse_error"]
    assert err is not None
    assert "SyntaxError" in err


def test_one_broken_file_does_not_stop_others(tmp_path: Path) -> None:
    """Other modules still parse and get edges even if one file is broken."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "broken.py", "def def def\n")
    _touch(tmp_path / "pkg" / "good.py")
    _touch(tmp_path / "pkg" / "cli.py", "from pkg import good\n")

    graph = build_graph(tmp_path)
    assert "pkg.broken" in graph.nodes
    assert graph.nodes["pkg.broken"]["parse_error"] is not None
    assert ("pkg.cli", "pkg.good") in graph.edges


# ---------------------------------------------------------------------------
# Project shape
# ---------------------------------------------------------------------------


def test_nested_packages_full_graph(tmp_path: Path) -> None:
    """A realistic nested project produces the expected graph."""
    _touch(tmp_path / "myapp" / "__init__.py")
    _touch(tmp_path / "myapp" / "cli.py", "from myapp.core import service\n")
    _touch(tmp_path / "myapp" / "core" / "__init__.py")
    _touch(tmp_path / "myapp" / "core" / "service.py", "from myapp.utils import helpers\n")
    _touch(tmp_path / "myapp" / "utils" / "__init__.py")
    _touch(tmp_path / "myapp" / "utils" / "helpers.py", "x = 1\n")

    graph = build_graph(tmp_path)

    expected_nodes = {
        "myapp",
        "myapp.cli",
        "myapp.core",
        "myapp.core.service",
        "myapp.utils",
        "myapp.utils.helpers",
    }
    assert set(graph.nodes) == expected_nodes
    assert ("myapp.cli", "myapp.core.service") in graph.edges
    assert ("myapp.core.service", "myapp.utils.helpers") in graph.edges


def test_returns_actual_digraph(tmp_path: Path) -> None:
    """Return type is networkx.DiGraph, not a subclass or other graph type."""
    _touch(tmp_path / "lone.py")
    graph = build_graph(tmp_path)
    assert type(graph) is nx.DiGraph


# ---------------------------------------------------------------------------
# Error propagation
# ---------------------------------------------------------------------------


def test_missing_root_raises(tmp_path: Path) -> None:
    """A nonexistent root propagates FileNotFoundError from discovery."""
    with pytest.raises(FileNotFoundError):
        build_graph(tmp_path / "does_not_exist")
