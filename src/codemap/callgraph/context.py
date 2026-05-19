"""Per-module name resolution context.

A ``ModuleContext`` answers the question: given a bare name as it
appears in this module's source, what qualified name does it refer
to, and is that name internal to the project or external?

The context is built once per module from two inputs:

    - The module's ``FileAnalysis`` (Phase 2 output), which lists
      its top-level functions, classes, and imports.
    - The set of all internal modules in the project, plus Phase 3's
      import resolver, to classify each import as internal or
      external.

The resolver in ``callgraph.resolver`` consumes a ``ModuleContext``
to turn raw callee expressions into resolved ``CallEdge`` instances.
This module performs no AST walking and no call resolution; it
exists purely as a lookup table.

A known limitation: if a module has both a local definition and an
import binding the same name, the import wins. Strictly correct
shadowing would require tracking line numbers and comparing them to
the call site, which is out of scope for Phase 4.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from codemap.ast_engine.models import FileAnalysis, ImportInfo
from codemap.callgraph.models import build_qualified_name
from codemap.graph.resolver import resolve_import


@dataclass(frozen=True, slots=True)
class ResolvedName:
    """A name visible inside a module, resolved to a qualified target.

    The ``qualified_name`` is the target the local binding refers to,
    in the canonical dotted form used as a node key in the call graph.
    The ``is_internal`` flag distinguishes project code (``True``)
    from stdlib or third-party code (``False``); the resolver uses
    this to set ``CallEdgeKind.INTERNAL`` vs ``EXTERNAL``.

    Examples of source that produce this model (assuming
    ``pkg.helpers`` is internal and ``os`` is external):
        def foo() in module pkg.mod
            -> binding 'foo' -> ResolvedName('pkg.mod.foo', True)
        class Widget in module pkg.mod
            -> binding 'Widget' -> ResolvedName('pkg.mod.Widget', True)
        from pkg.helpers import util  (util is a function in pkg.helpers)
            -> binding 'util' -> ResolvedName('pkg.helpers.util', True)
        from pkg.helpers import util as u
            -> binding 'u' -> ResolvedName('pkg.helpers.util', True)
        from pkg import sub  (sub is itself a module)
            -> binding 'sub' -> ResolvedName('pkg.sub', True)
        import os
            -> binding 'os' -> ResolvedName('os', False)
        import os.path
            -> binding 'os' -> ResolvedName('os.path', False)
    """

    qualified_name: str
    is_internal: bool


@dataclass(frozen=True, slots=True)
class ModuleContext:
    """The name resolution table for one module.

    Maps local binding names (as they would appear in this module's
    source) to their resolved targets. Built by
    ``build_module_context`` and consumed by the call resolver.

    The ``module`` field is the dotted path of the module this
    context describes. It is kept on the context so the resolver does
    not need to thread it as a separate argument.

    The ``names`` field maps binding -> ResolvedName. Lookup is a
    direct dict access; the resolver layer handles fallbacks.

    The ``classes`` field maps class name -> tuple of method names
    defined directly on that class. Used by ``self.x`` resolution in
    step 3c. Empty tuples are valid (a class with no methods).
    """

    module: str
    names: dict[str, ResolvedName] = field(default_factory=dict)
    classes: dict[str, tuple[str, ...]] = field(default_factory=dict)


def build_module_context(
    module_dotted: str,
    analysis: FileAnalysis,
    internal_modules: set[str],
    importer_is_package: bool,
) -> ModuleContext:
    """Build a ``ModuleContext`` for one module.

    Walks the module's imports and local definitions, resolves each
    name to its target, and assembles the lookup table.

    Order of insertion matters when names collide: local definitions
    are inserted first, then imports overwrite them. This matches
    Python's runtime behaviour when an import statement follows a
    ``def`` of the same name, which is the common pattern (stub
    function defined for editor hints, real function imported below).

    Args:
        module_dotted: Dotted path of the module being described,
            e.g. ``codemap.cli``.
        analysis: The Phase 2 parse output for this module.
        internal_modules: The set of all dotted paths considered
            internal to the project. Used by Phase 3's
            ``resolve_import`` to classify each import.
        importer_is_package: True if this module is an ``__init__.py``.
            Forwarded to ``resolve_import`` so relative imports are
            walked correctly.

    Returns:
        A populated ``ModuleContext``. The context is immutable; if
        the module has no functions, classes, or imports, the
        ``names`` and ``classes`` dicts will be empty.
    """
    names: dict[str, ResolvedName] = {}
    classes: dict[str, tuple[str, ...]] = {}

    # Locals first: top-level functions and classes are bound by
    # their plain name in the module namespace.
    for func in analysis.functions:
        names[func.name] = ResolvedName(
            qualified_name=build_qualified_name(module_dotted, func.name),
            is_internal=True,
        )

    for cls in analysis.classes:
        names[cls.name] = ResolvedName(
            qualified_name=build_qualified_name(module_dotted, cls.name),
            is_internal=True,
        )
        classes[cls.name] = tuple(method.name for method in cls.methods)

    # Imports overwrite locals on name collision. See module docstring
    # for the rationale and known limitation.
    for import_info in analysis.imports:
        binding, resolved = _resolve_one_import(
            import_info=import_info,
            importer_dotted=module_dotted,
            importer_is_package=importer_is_package,
            internal_modules=internal_modules,
        )
        if binding is None or resolved is None:
            # Malformed or unresolvable import; skip silently. The
            # resolver will fall through to UNRESOLVED for any call
            # that needed this binding.
            continue
        names[binding] = resolved

    return ModuleContext(
        module=module_dotted,
        names=names,
        classes=classes,
    )


def _resolve_one_import(
    import_info: ImportInfo,
    importer_dotted: str,
    importer_is_package: bool,
    internal_modules: set[str],
) -> tuple[str | None, ResolvedName | None]:
    """Resolve a single ``ImportInfo`` to a (binding, target) pair.

    The binding is the name actually introduced into the module's
    namespace: alias if present, else the import's ``name`` field,
    with one exception for plain ``import x.y.z`` where the binding
    is just the top-level package ``x``.

    The target is the qualified name the binding refers to. For
    ``from x import y`` where y is a name (function/class) inside
    module x, the target is ``x.y`` — the qualified name of the
    symbol, not of the containing module. For ``from x import y``
    where y is itself a submodule, the target is ``x.y`` (the
    submodule), which Phase 3's ``resolve_import`` returns directly.
    For plain ``import x``, the target is the module ``x``.

    Returns ``(None, None)`` if the import is malformed or cannot be
    given a sensible binding.
    """
    is_from_import = (
        import_info.module != import_info.name or import_info.level > 0
    )

    # Determine the local binding name.
    if import_info.alias is not None:
        binding = import_info.alias
    elif is_from_import:
        binding = import_info.name
    else:
        # Plain ``import x`` or ``import x.y.z``: the local binding
        # is the top-level package.
        binding = import_info.name.split(".")[0]

    if not binding:
        return None, None

    # Resolve to an internal module if possible.
    internal_target = resolve_import(
        import_info,
        importer_dotted=importer_dotted,
        importer_is_package=importer_is_package,
        internal_modules=internal_modules,
    )

    if internal_target is not None:
        full_qname = _expand_internal_target(
            internal_target=internal_target,
            import_info=import_info,
            is_from_import=is_from_import,
        )
        return binding, ResolvedName(
            qualified_name=full_qname,
            is_internal=True,
        )

    # External: build a best-effort qualified name from the import
    # itself, for display in the graph.
    external_qname = _external_qualified_name(
        import_info, is_from_import=is_from_import
    )
    if external_qname is None:
        return None, None
    return binding, ResolvedName(
        qualified_name=external_qname,
        is_internal=False,
    )


def _expand_internal_target(
    internal_target: str,
    import_info: ImportInfo,
    is_from_import: bool,
) -> str:
    """Expand Phase 3's module-level resolution to a full symbol qname.

    Phase 3's ``resolve_import`` returns the dotted path of the
    *module* the import points at. For ``from x import y``, that is
    either:

        - The submodule ``x.y`` if y is itself an importable module.
          Phase 3 returns ``"x.y"`` in that case. The full qname is
          already complete; nothing to do.

        - The module ``x`` if y is a name (function/class/variable)
          defined inside x. Phase 3 returns ``"x"``. The full qname
          must append ``.y`` to point at the symbol.

    For plain ``import x`` or ``import x.y.z``, the target is the
    module itself and we keep what Phase 3 returned.
    """
    if not is_from_import:
        return internal_target

    # If Phase 3 already returned the submodule form, leave it alone.
    if internal_target.endswith(f".{import_info.name}"):
        return internal_target
    if internal_target == import_info.name:
        # Edge case: ``from . import sibling`` where sibling is the
        # whole base. Should not happen since resolve_import builds
        # base.name in the submodule branch, but be defensive.
        return internal_target

    # Otherwise Phase 3 resolved to the containing module; append
    # the imported name to get the symbol's qualified name.
    return f"{internal_target}.{import_info.name}"


def _external_qualified_name(
    import_info: ImportInfo,
    is_from_import: bool,
) -> str | None:
    """Build a display qualified name for an external import.

    Used so external nodes in the call graph have human-readable
    names like ``os.path`` or ``requests.get`` rather than synthetic
    placeholders. Returns None for imports too malformed to name.
    """
    if import_info.level > 0:
        # A relative import that did not resolve internally is
        # broken; we cannot give it an external name either.
        return None

    if not is_from_import:
        # Plain ``import x`` or ``import x.y.z``: the target is the
        # whole dotted module path.
        return import_info.name

    if not import_info.module:
        return None

    return f"{import_info.module}.{import_info.name}"
