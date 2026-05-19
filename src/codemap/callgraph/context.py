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

from codemap.ast_engine.models import FileAnalysis
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
        from pkg.helpers import util
            -> binding 'util' -> ResolvedName('pkg.helpers.util', True)
        from pkg.helpers import util as u
            -> binding 'u' -> ResolvedName('pkg.helpers.util', True)
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
    import_info,  # type: ignore[no-untyped-def]
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
    internal imports, that is the dotted path inside the project.
    For external imports, it is the import's own ``module`` string
    (or the longer ``module.name`` for from-imports), which gives the
    DOT/JSON exporters something meaningful to render.

    Returns ``(None, None)`` if the import is malformed or cannot be
    given a sensible binding.
    """
    # Determine the local binding name.
    if import_info.alias is not None:
        binding = import_info.alias
    elif import_info.module == import_info.name and import_info.level == 0:
        # Plain ``import x`` or ``import x.y.z``.
        # The local binding is the top-level package.
        binding = import_info.name.split(".")[0]
    else:
        # ``from x import y`` or relative imports.
        # The binding is the name being imported.
        binding = import_info.name

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
        return binding, ResolvedName(
            qualified_name=internal_target,
            is_internal=True,
        )

    # External: build a best-effort qualified name from the import
    # itself, for display in the graph.
    external_qname = _external_qualified_name(import_info)
    if external_qname is None:
        return None, None
    return binding, ResolvedName(
        qualified_name=external_qname,
        is_internal=False,
    )


def _external_qualified_name(import_info) -> str | None:  # type: ignore[no-untyped-def]
    """Build a display qualified name for an external import.

    Used so external nodes in the call graph have human-readable
    names like ``os.path`` or ``requests.get`` rather than synthetic
    placeholders. Returns None for imports too malformed to name.
    """
    if import_info.level > 0:
        # A relative import that did not resolve internally is
        # broken; we cannot give it an external name either.
        return None

    if import_info.module == import_info.name:
        # Plain ``import x`` or ``import x.y.z``.
        return import_info.name

    if not import_info.module:
        return None

    return f"{import_info.module}.{import_info.name}"
