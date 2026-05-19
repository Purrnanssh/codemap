"""Resolve raw call sites into typed call graph edges.

The resolver bridges Phase 4's extractor and the call graph builder.
Given a ``CallSite`` (a raw callee expression captured from one
function body) and the ``ModuleContext`` for the caller's module,
it produces a ``CallEdge`` whose ``kind`` tells the rest of the
pipeline how to interpret the target.

This module handles two shapes of callee expression:

    Bare name      foo                  -> look up 'foo' in context
    Dotted chain   a.b.c                -> look up 'a', append '.b.c'

The ``self.x`` shape is handled in a sibling layer (step 3c) which
needs the project-wide class -> methods index. The sentinel
``<unknown>`` from Phase 2's parser always becomes UNRESOLVED.

The resolver is intentionally optimistic about cross-module names:
if ``util`` resolves to internal module ``pkg.helpers`` and the call
is ``util.do_thing()``, we emit an INTERNAL edge to
``pkg.helpers.do_thing`` without checking that ``do_thing`` actually
exists there. The builder validates against the full node index and
downgrades to UNRESOLVED if the target is missing.
"""

from __future__ import annotations

from codemap.ast_engine.parser import UNKNOWN_CALLEE
from codemap.callgraph.context import ModuleContext
from codemap.callgraph.models import CallEdge, CallEdgeKind, CallSite

UNRESOLVED_PREFIX = "<unresolved>:"


def resolve_call(
    call_site: CallSite,
    context: ModuleContext,
) -> CallEdge:
    """Resolve one call site into a typed call edge.

    Args:
        call_site: A raw call site from the extractor.
        context: The name resolution table for the module containing
            the caller. The caller's qualified name on the call site
            must already start with ``context.module`` for the lookup
            to make sense.

    Returns:
        A ``CallEdge`` whose ``kind`` reflects how the callee was
        resolved. EXTERNAL and UNRESOLVED edges carry synthetic
        callee names; INTERNAL and SELF edges name real project
        functions (subject to validation by the builder for INTERNAL).

    Note:
        ``self.x`` expressions are not handled here; they fall
        through to UNRESOLVED. Add ``self.x`` resolution in step 3c.
    """
    expression = call_site.callee_expression

    if expression == UNKNOWN_CALLEE:
        return _unresolved_edge(call_site, expression)

    # Bare name: a single identifier with no dots.
    if "." not in expression:
        return _resolve_bare_name(call_site, expression, context)

    # Dotted chain: at least one dot.
    return _resolve_dotted_chain(call_site, expression, context)


def _resolve_bare_name(
    call_site: CallSite,
    name: str,
    context: ModuleContext,
) -> CallEdge:
    """Resolve a single-identifier callee like ``foo``."""
    resolved = context.names.get(name)
    if resolved is None:
        return _unresolved_edge(call_site, name)

    kind = (
        CallEdgeKind.INTERNAL
        if resolved.is_internal
        else CallEdgeKind.EXTERNAL
    )
    return CallEdge(
        caller=call_site.caller,
        callee=resolved.qualified_name,
        line=call_site.line,
        kind=kind,
    )


def _resolve_dotted_chain(
    call_site: CallSite,
    expression: str,
    context: ModuleContext,
) -> CallEdge:
    """Resolve a dotted callee like ``util.do_thing`` or ``a.b.c``.

    Splits the expression on the first dot. The head is looked up in
    the module context; if it resolves, the target qualified name is
    built by appending the rest of the chain to the resolved target.

    Examples (assuming ``util`` is internal pointing to
    ``pkg.helpers``, ``os`` is external pointing to ``os``, and
    ``zzz`` is not in the context):

        util.do_thing       -> INTERNAL, pkg.helpers.do_thing
        util.sub.do_thing   -> INTERNAL, pkg.helpers.sub.do_thing
        os.path.join        -> EXTERNAL, os.path.join
        zzz.something       -> UNRESOLVED, <unresolved>:zzz.something
    """
    head, _, rest = expression.partition(".")

    resolved = context.names.get(head)
    if resolved is None:
        return _unresolved_edge(call_site, expression)

    target_qname = f"{resolved.qualified_name}.{rest}"
    kind = (
        CallEdgeKind.INTERNAL
        if resolved.is_internal
        else CallEdgeKind.EXTERNAL
    )
    return CallEdge(
        caller=call_site.caller,
        callee=target_qname,
        line=call_site.line,
        kind=kind,
    )


def _unresolved_edge(call_site: CallSite, expression: str) -> CallEdge:
    """Construct an UNRESOLVED edge with a synthetic callee name."""
    return CallEdge(
        caller=call_site.caller,
        callee=f"{UNRESOLVED_PREFIX}{expression}",
        line=call_site.line,
        kind=CallEdgeKind.UNRESOLVED,
    )
