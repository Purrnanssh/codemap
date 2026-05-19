"""Resolve import strings to internal module dotted paths.

The resolver bridges Phase 2's structural import facts (``ImportInfo``)
and Phase 3's dependency graph. Given an import found in one of our
internal modules, it answers: which other internal module (if any)
does this import refer to?

Imports that point outside the project (stdlib, third-party packages)
resolve to None. The graph builder uses None as a signal to skip
edge creation for that import.
"""

from __future__ import annotations

from codemap.ast_engine.models import ImportInfo


def resolve_import(
    info: ImportInfo,
    importer_dotted: str,
    importer_is_package: bool,
    internal_modules: set[str],
) -> str | None:
    """Resolve a single import to an internal module dotted path.

    Args:
        info: The import to resolve, as extracted by Phase 2.
        importer_dotted: Dotted path of the module containing the import,
            e.g. ``codemap.cli``.
        importer_is_package: True if the importer is an ``__init__.py``.
            Affects how relative imports walk up the package tree.
        internal_modules: Set of all known internal dotted paths. Used
            to distinguish internal from external imports and to resolve
            the submodule-vs-name ambiguity in ``from X import Y``.

    Returns:
        The resolved internal module dotted path on a hit, or None if
        the import is external or unresolvable within the project.
    """
    # Step 1: compute the absolute target module string.
    absolute_module = _to_absolute_module(
        raw_module=info.module,
        level=info.level,
        importer_dotted=importer_dotted,
        importer_is_package=importer_is_package,
    )
    if absolute_module is None:
        # Relative import walked off the top of the package tree.
        return None

    # Step 2: decide what the import is pointing at.
    #
    # `import x` and `import x.y.z`: info.module == info.name, no name
    # disambiguation needed. The target is simply the absolute module.
    #
    # `from x import y`: y could be a submodule of x (an importable
    # file) OR a name (function, class, variable) defined inside x.
    # We resolve by checking which one exists in internal_modules.
    is_from_import = info.module != info.name or info.level > 0

    if is_from_import:
        # Candidate 1: y is a submodule of x. Target = "x.y".
        # Candidate 2: y is a name inside x. Target = "x" itself.
        # Special case: `from . import y` has empty module string, so
        # the candidate submodule is just absolute_module + "." + name.
        if absolute_module:
            candidate_submodule = f"{absolute_module}.{info.name}"
        else:
            # absolute_module == "" can only happen if level==0 and
            # info.module == "", which is malformed source. Bail out.
            return None

        if candidate_submodule in internal_modules:
            return candidate_submodule
        if absolute_module in internal_modules:
            return absolute_module
        return None

    # Plain `import x` or `import x.y.z`. Direct check.
    if absolute_module in internal_modules:
        return absolute_module
    return None


def _to_absolute_module(
    raw_module: str,
    level: int,
    importer_dotted: str,
    importer_is_package: bool,
) -> str | None:
    """Convert a potentially-relative module string to an absolute one.

    For absolute imports (level == 0), the raw module is already
    absolute and is returned unchanged.

    For relative imports (level >= 1), walks up the importer's package
    tree by the appropriate number of steps, then appends raw_module
    if it's non-empty.

    Returns None if the walk would go above the root of the package
    tree (e.g. ``from ... import x`` from a top-level module).
    """
    if level == 0:
        return raw_module

    # Compute how many components to drop from the importer's path.
    # For a module importer at "a.b.c.d":
    #   level=1 -> we want "a.b.c" -> drop 1 part
    # For a package importer at "a.b.c":
    #   level=1 -> we want "a.b.c" -> drop 0 parts
    # So packages drop one fewer component than modules at the same level.
    drop_count = level - 1 if importer_is_package else level
    parts = importer_dotted.split(".") if importer_dotted else []

    if drop_count < 0:
        # Should be unreachable given level >= 1, but defensive.
        return None
    if drop_count > len(parts):
        # Walked past the root.
        return None

    base_parts = parts[: len(parts) - drop_count]
    base = ".".join(base_parts)

    if not base:
        # Walked all the way to the empty root. Relative imports cannot
        # resolve to "no package," so treat as off-the-top.
        return None

    if raw_module:
        return f"{base}.{raw_module}"
    return base
