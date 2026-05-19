"""Tests for codemap.graph.resolver."""

from __future__ import annotations

import pytest

from codemap.ast_engine.models import ImportInfo
from codemap.graph.resolver import resolve_import

# ---------------------------------------------------------------------------
# Absolute imports: `import x` and `import x.y.z`
# ---------------------------------------------------------------------------


def test_absolute_import_hits_internal_module() -> None:
    """`import pkg.core` where pkg.core is internal resolves to pkg.core."""
    info = ImportInfo(module="pkg.core", name="pkg.core", alias=None, line=1)
    result = resolve_import(
        info,
        importer_dotted="pkg.cli",
        importer_is_package=False,
        internal_modules={"pkg", "pkg.cli", "pkg.core"},
    )
    assert result == "pkg.core"


def test_absolute_import_external_returns_none() -> None:
    """`import typer` is external, resolves to None."""
    info = ImportInfo(module="typer", name="typer", alias=None, line=1)
    result = resolve_import(
        info,
        importer_dotted="pkg.cli",
        importer_is_package=False,
        internal_modules={"pkg", "pkg.cli"},
    )
    assert result is None


def test_absolute_import_with_alias() -> None:
    """Aliasing (`import x as y`) does not affect resolution."""
    info = ImportInfo(module="pkg.core", name="pkg.core", alias="core", line=1)
    result = resolve_import(
        info,
        importer_dotted="pkg.cli",
        importer_is_package=False,
        internal_modules={"pkg", "pkg.cli", "pkg.core"},
    )
    assert result == "pkg.core"


# ---------------------------------------------------------------------------
# `from X import Y`: the submodule-vs-name ambiguity
# ---------------------------------------------------------------------------


def test_from_import_submodule_resolves_to_submodule() -> None:
    """`from pkg import core` where pkg.core is internal resolves to pkg.core."""
    info = ImportInfo(module="pkg", name="core", alias=None, line=1)
    result = resolve_import(
        info,
        importer_dotted="pkg.cli",
        importer_is_package=False,
        internal_modules={"pkg", "pkg.cli", "pkg.core"},
    )
    assert result == "pkg.core"


def test_from_import_name_resolves_to_parent() -> None:
    """`from pkg import some_function` resolves to pkg (the parent package)."""
    info = ImportInfo(module="pkg", name="some_function", alias=None, line=1)
    result = resolve_import(
        info,
        importer_dotted="pkg.cli",
        importer_is_package=False,
        internal_modules={"pkg", "pkg.cli", "pkg.core"},
    )
    assert result == "pkg"


def test_from_import_external_returns_none() -> None:
    """`from pathlib import Path` resolves to None when pathlib is external."""
    info = ImportInfo(module="pathlib", name="Path", alias=None, line=1)
    result = resolve_import(
        info,
        importer_dotted="pkg.cli",
        importer_is_package=False,
        internal_modules={"pkg", "pkg.cli"},
    )
    assert result is None


def test_from_import_nested_submodule() -> None:
    """`from pkg.utils import helpers` resolves to pkg.utils.helpers if present."""
    info = ImportInfo(module="pkg.utils", name="helpers", alias=None, line=1)
    result = resolve_import(
        info,
        importer_dotted="pkg.cli",
        importer_is_package=False,
        internal_modules={"pkg", "pkg.cli", "pkg.utils", "pkg.utils.helpers"},
    )
    assert result == "pkg.utils.helpers"


def test_from_import_nested_name_falls_back_to_parent() -> None:
    """`from pkg.utils import some_function` resolves to pkg.utils."""
    info = ImportInfo(module="pkg.utils", name="some_function", alias=None, line=1)
    result = resolve_import(
        info,
        importer_dotted="pkg.cli",
        importer_is_package=False,
        internal_modules={"pkg", "pkg.cli", "pkg.utils"},
    )
    assert result == "pkg.utils"


# ---------------------------------------------------------------------------
# Relative imports from a module
# ---------------------------------------------------------------------------


def test_relative_import_single_dot_from_module() -> None:
    """`from . import sibling` inside pkg.module resolves to pkg.sibling."""
    info = ImportInfo(module="", name="sibling", alias=None, line=1, level=1)
    result = resolve_import(
        info,
        importer_dotted="pkg.module",
        importer_is_package=False,
        internal_modules={"pkg", "pkg.module", "pkg.sibling"},
    )
    assert result == "pkg.sibling"


def test_relative_import_with_module_name() -> None:
    """`from .other import x` inside pkg.module resolves to pkg.other."""
    info = ImportInfo(module="other", name="x", alias=None, line=1, level=1)
    result = resolve_import(
        info,
        importer_dotted="pkg.module",
        importer_is_package=False,
        internal_modules={"pkg", "pkg.module", "pkg.other"},
    )
    assert result == "pkg.other"


def test_relative_import_double_dot_from_module() -> None:
    """`from .. import top_sibling` inside pkg.sub.module walks up two levels."""
    info = ImportInfo(module="", name="top_sibling", alias=None, line=1, level=2)
    result = resolve_import(
        info,
        importer_dotted="pkg.sub.module",
        importer_is_package=False,
        internal_modules={"pkg", "pkg.sub", "pkg.sub.module", "pkg.top_sibling"},
    )
    assert result == "pkg.top_sibling"


def test_relative_import_too_many_dots_returns_none() -> None:
    """Walking past the package root returns None."""
    info = ImportInfo(module="", name="x", alias=None, line=1, level=3)
    result = resolve_import(
        info,
        importer_dotted="pkg.module",
        importer_is_package=False,
        internal_modules={"pkg", "pkg.module"},
    )
    assert result is None


# ---------------------------------------------------------------------------
# Relative imports from a package (__init__.py)
# ---------------------------------------------------------------------------


def test_relative_import_single_dot_from_package() -> None:
    """`from . import x` inside pkg/__init__.py resolves to pkg.x."""
    info = ImportInfo(module="", name="utils", alias=None, line=1, level=1)
    result = resolve_import(
        info,
        importer_dotted="pkg",
        importer_is_package=True,
        internal_modules={"pkg", "pkg.utils"},
    )
    assert result == "pkg.utils"


def test_relative_import_double_dot_from_package() -> None:
    """`from .. import x` inside pkg.sub/__init__.py walks up one level."""
    info = ImportInfo(module="", name="top", alias=None, line=1, level=2)
    result = resolve_import(
        info,
        importer_dotted="pkg.sub",
        importer_is_package=True,
        internal_modules={"pkg", "pkg.sub", "pkg.top"},
    )
    assert result == "pkg.top"


def test_relative_import_from_package_with_submodule_hit() -> None:
    """A relative import that matches a submodule prefers the submodule."""
    info = ImportInfo(module="utils", name="helpers", alias=None, line=1, level=1)
    result = resolve_import(
        info,
        importer_dotted="pkg",
        importer_is_package=True,
        internal_modules={"pkg", "pkg.utils", "pkg.utils.helpers"},
    )
    assert result == "pkg.utils.helpers"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_external_relative_import_returns_none() -> None:
    """Relative import resolving to something not in internal_modules returns None."""
    info = ImportInfo(module="missing", name="x", alias=None, line=1, level=1)
    result = resolve_import(
        info,
        importer_dotted="pkg.module",
        importer_is_package=False,
        internal_modules={"pkg", "pkg.module"},
    )
    assert result is None


def test_import_pointing_at_self_returns_self() -> None:
    """A module importing itself by name still resolves (degenerate but legal)."""
    info = ImportInfo(module="pkg.module", name="pkg.module", alias=None, line=1)
    result = resolve_import(
        info,
        importer_dotted="pkg.module",
        importer_is_package=False,
        internal_modules={"pkg", "pkg.module"},
    )
    assert result == "pkg.module"


@pytest.mark.parametrize(
    "raw_module,name,internal,expected",
    [
        ("pkg", "core", {"pkg", "pkg.core"}, "pkg.core"),
        ("pkg", "missing_sub", {"pkg"}, "pkg"),
        ("pkg.sub", "leaf", {"pkg", "pkg.sub", "pkg.sub.leaf"}, "pkg.sub.leaf"),
        ("pkg.sub", "name_only", {"pkg", "pkg.sub"}, "pkg.sub"),
        ("external_pkg", "thing", {"pkg"}, None),
    ],
)
def test_from_import_table(
    raw_module: str,
    name: str,
    internal: set[str],
    expected: str | None,
) -> None:
    """Parameterized matrix of from-import resolutions."""
    info = ImportInfo(module=raw_module, name=name, alias=None, line=1)
    result = resolve_import(
        info,
        importer_dotted="pkg.cli",
        importer_is_package=False,
        internal_modules=internal,
    )
    assert result == expected
