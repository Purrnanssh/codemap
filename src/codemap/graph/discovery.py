"""Discover Python modules within a project directory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Directories we never walk into. Matched by exact name, anywhere in the tree.
_IGNORE_DIRS: frozenset[str] = frozenset(
    {
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".git",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "build",
        "dist",
        "node_modules",
    }
)


@dataclass(frozen=True, slots=True)
class ModuleRecord:
    """A discovered Python module within a project.

    Attributes:
        dotted_path: Importable dotted name relative to the scan root,
            e.g. ``pkg.utils.helpers``. For an ``__init__.py``, this is
            the package's own dotted path, not ``pkg.__init__``.
        file_path: Absolute filesystem path to the ``.py`` file.
    """

    dotted_path: str
    file_path: Path


def _is_ignored(path: Path) -> bool:
    """Return True if any segment of the path matches an ignored directory name."""
    return any(part in _IGNORE_DIRS for part in path.parts)


def _to_dotted_path(py_file: Path, root: Path) -> str:
    """Convert a .py file path to its dotted module path relative to root.

    Rules:
        - ``__init__.py`` represents its parent directory as a package.
        - Other ``.py`` files are flat: ``pkg/core.py`` -> ``pkg.core``.
    """
    relative = py_file.relative_to(root)
    parts = list(relative.parts)

    # Drop the .py suffix from the last part.
    parts[-1] = parts[-1].removesuffix(".py")

    # If the file is __init__.py, the package's dotted path is its parent's.
    if parts[-1] == "__init__":
        parts.pop()

    return ".".join(parts)


def discover_modules(root: Path) -> list[ModuleRecord]:
    """Discover all Python modules within a project directory.

    Walks the tree starting at ``root``, skipping common non-source
    directories (virtualenvs, caches, VCS metadata). Returns one
    ``ModuleRecord`` per ``.py`` file found.

    Results are sorted by dotted path for deterministic output.

    Args:
        root: Project root directory to scan.

    Returns:
        Sorted list of ``ModuleRecord`` instances.

    Raises:
        FileNotFoundError: If ``root`` does not exist.
        NotADirectoryError: If ``root`` exists but is not a directory.
    """
    if not root.exists():
        raise FileNotFoundError(f"Scan root does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Scan root is not a directory: {root}")

    root = root.resolve()
    records: list[ModuleRecord] = []

    for py_file in root.rglob("*.py"):
        # Skip files inside any ignored directory.
        relative_parts = py_file.relative_to(root).parts
        if any(part in _IGNORE_DIRS for part in relative_parts):
            continue

        dotted = _to_dotted_path(py_file, root)
        # An empty dotted path means the root itself was an __init__.py,
        # which shouldn't happen since root must be a directory. Defensive skip.
        if not dotted:
            continue

        records.append(ModuleRecord(dotted_path=dotted, file_path=py_file))

    records.sort(key=lambda r: r.dotted_path)
    return records
