"""Resolve raw call sites into typed call graph edges.

The resolver bridges Phase 4's extractor and the call graph builder.
Given a ``CallSite`` (a raw callee expression captured from one
function body) and the ``ModuleContext`` for the caller's module,
it produces a ``CallEdge`` whose ``kind`` tells the rest of the
pipeline how to interpret the target.

This module handles three shapes of callee expression:

    Bare name      foo                  -> look up 'foo' in context
    Dotted chain   a.b.c                -> look up 'a', append '.b.c'
    Self method    self.x               -> look up 'x' on caller's class

The sentinel ``<unknown>`` from Phase 2's parser always becomes
UNRESOLVED. Deeper self chains like ``self.helper.do_thing`` are
also UNRESOLVED: resolving them would require tracking what
``self.helper`` returns, which is out of scope for Phase 4.

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
SELF_PREFIX = "self."


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
    """
    expression = call_site.callee_expression

    if expression == UNKNOWN_CALLEE:
        return _unresolved_edge(call_site, expression)

    # self.x: resolve against the caller's enclosing class.
    if expression.startswith(SELF_PREFIX):
        return _resolve_self_call(call_site, expression, context)

    # Bare name: a single identifier with no dots.
    if "." not in expression:
        return _resolve_bare_name(call_site, expression, context)

    # Dotted chain: at least one dot.
    return _resolve_dotted_chain(call_site, expression, context)


def _resolve_self_call(
    call_site: CallSite,
    expression: str,
    context: ModuleContext,
) -> CallEdge:
    """Resolve ``self.x`` against the caller's enclosing class.

    Only ``self.<single_name>`` is resolved; deeper chains like
    ``self.helper.do_thing`` are UNRESOLVED because we cannot track
    what ``self.helper`` returns.

    The caller's class is extracted from the caller's qualified name,
    which for a method has the form ``module.Class.method``. If the
    caller does not have that shape (e.g. ``self.x`` written inside a
    module-level function, which is invalid Python but possible to
    construct), the call falls through to UNRESOLVED.
    """
    after_self = expression[len(SELF_PREFIX):]

    # Reject deeper chains.
    if "." in after_self or not after_self:
        return _unresolved_edge(call_site, expression)

    class_name = _extract_class_name(call_site.caller, context.module)
    if class_name is None:
        return _unresolved_edge(call_site, expression)

    method_names = context.classes.get(class_name)
    if method_names is None or after_self not in method_names:
        return _unresolved_edge(call_site, expression)

    target_qname = f"{context.module}.{class_name}.{after_self}"
    return CallEdge(
        caller=call_site.caller,
        callee=target_qname,
        line=call_site.line,
        kind=CallEdgeKind.SELF,
    )


def _extract_class_name(caller_qname: str, module: str) -> str | None:
    """Extract the enclosing class name from a method's qualified name.

    For a caller qualified name like ``module.Class.method``, returns
    ``Class``. Returns None if the caller is not a method of any
    class in this module (e.g. it is a module-level function with
    qualified name ``module.func``, which has no class segment).
    """
    if not caller_qname.startswith(f"{module}."):
        return None

    remainder = caller_qname[len(module) + 1:]
    parts = remainder.split(".")
    if len(parts) < 2:
        # Module-level function: just one segment after the module.
        return None
    # Method: at least two segments. The class is the second-to-last;
    # for a method directly on a class, that is parts[0].
    return parts[0]


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
