"""Tests for codemap.graph.discovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from codemap.graph.discovery import ModuleRecord, discover_modules


def _touch(path: Path, content: str = "") -> None:
    """Create parent dirs if needed and write content to path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_module_record_is_frozen() -> None:
    """ModuleRecord instances should be immutable."""
    record = ModuleRecord(dotted_path="pkg.core", file_path=Path("/x/pkg/core.py"))
    with pytest.raises((AttributeError, Exception)):
        record.dotted_path = "other"  # type: ignore[misc]


def test_discover_empty_directory(tmp_path: Path) -> None:
    """An empty directory yields no modules."""
    assert discover_modules(tmp_path) == []


def test_discover_single_top_level_script(tmp_path: Path) -> None:
    """A loose .py file at the root has a flat dotted path."""
    _touch(tmp_path / "script.py", "x = 1")
    result = discover_modules(tmp_path)
    assert len(result) == 1
    assert result[0].dotted_path == "script"
    assert result[0].file_path.name == "script.py"


def test_discover_simple_package(tmp_path: Path) -> None:
    """A package with __init__.py and one module yields two records."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "core.py", "x = 1")

    result = discover_modules(tmp_path)
    paths = [r.dotted_path for r in result]
    assert paths == ["pkg", "pkg.core"]


def test_discover_init_resolves_to_package_name(tmp_path: Path) -> None:
    """An __init__.py's dotted path is the package name, not pkg.__init__."""
    _touch(tmp_path / "mypkg" / "__init__.py")
    result = discover_modules(tmp_path)
    assert len(result) == 1
    assert result[0].dotted_path == "mypkg"
    assert result[0].file_path.name == "__init__.py"


def test_discover_nested_packages(tmp_path: Path) -> None:
    """Subpackages produce correctly dotted paths."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "core.py")
    _touch(tmp_path / "pkg" / "utils" / "__init__.py")
    _touch(tmp_path / "pkg" / "utils" / "helpers.py")

    result = discover_modules(tmp_path)
    paths = [r.dotted_path for r in result]
    assert paths == ["pkg", "pkg.core", "pkg.utils", "pkg.utils.helpers"]


def test_discover_skips_venv(tmp_path: Path) -> None:
    """Files under .venv/ are not discovered."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / ".venv" / "lib" / "python3.11" / "site-packages" / "foo.py")

    result = discover_modules(tmp_path)
    paths = [r.dotted_path for r in result]
    assert paths == ["pkg"]


def test_discover_skips_pycache(tmp_path: Path) -> None:
    """Files under __pycache__/ are not discovered."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "pkg" / "__pycache__" / "core.cpython-311.py")

    result = discover_modules(tmp_path)
    paths = [r.dotted_path for r in result]
    assert paths == ["pkg"]


def test_discover_skips_git(tmp_path: Path) -> None:
    """Files under .git/ are not discovered."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / ".git" / "hooks" / "weird.py")

    result = discover_modules(tmp_path)
    paths = [r.dotted_path for r in result]
    assert paths == ["pkg"]


def test_discover_skips_multiple_ignored_dirs(tmp_path: Path) -> None:
    """All ignored directory names are honoured."""
    _touch(tmp_path / "pkg" / "__init__.py")
    _touch(tmp_path / "build" / "lib" / "foo.py")
    _touch(tmp_path / "dist" / "wheel" / "bar.py")
    _touch(tmp_path / ".mypy_cache" / "x.py")
    _touch(tmp_path / ".ruff_cache" / "y.py")
    _touch(tmp_path / ".pytest_cache" / "z.py")
    _touch(tmp_path / "node_modules" / "lol.py")

    result = discover_modules(tmp_path)
    paths = [r.dotted_path for r in result]
    assert paths == ["pkg"]


def test_discover_result_is_sorted(tmp_path: Path) -> None:
    """Results come back sorted by dotted path for determinism."""
    _touch(tmp_path / "zeta.py")
    _touch(tmp_path / "alpha.py")
    _touch(tmp_path / "mu.py")

    result = discover_modules(tmp_path)
    paths = [r.dotted_path for r in result]
    assert paths == ["alpha", "mu", "zeta"]


def test_discover_raises_on_missing_root(tmp_path: Path) -> None:
    """Nonexistent root raises FileNotFoundError."""
    missing = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError):
        discover_modules(missing)


def test_discover_raises_on_file_root(tmp_path: Path) -> None:
    """Passing a file (not a directory) raises NotADirectoryError."""
    f = tmp_path / "not_a_dir.py"
    f.write_text("")
    with pytest.raises(NotADirectoryError):
        discover_modules(f)


def test_discover_returns_absolute_paths(tmp_path: Path) -> None:
    """file_path attributes are absolute, not relative."""
    _touch(tmp_path / "pkg" / "__init__.py")
    result = discover_modules(tmp_path)
    assert result[0].file_path.is_absolute()
