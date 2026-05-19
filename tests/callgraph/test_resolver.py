"""Tests for the call site resolver.

Covers the two shapes resolve_call handles in step 3b:

    Bare name      foo
    Dotted chain   a.b.c

Plus the <unknown> sentinel and the unresolved fallbacks. The
self.x shape is tested separately in step 3c.

Tests construct ModuleContext instances directly (rather than via
build_module_context) so each test sets up exactly the bindings it
needs.
"""

from __future__ import annotations

from codemap.callgraph.context import ModuleContext, ResolvedName
from codemap.callgraph.models import CallEdgeKind, CallSite
from codemap.callgraph.resolver import (
    UNRESOLVED_PREFIX,
    resolve_call,
)


def _site(callee_expression: str) -> CallSite:
    """Build a CallSite for tests, defaulting caller and line."""
    return CallSite(
        caller="pkg.mod.caller",
        callee_expression=callee_expression,
        line=10,
    )


def _ctx(**names: ResolvedName) -> ModuleContext:
    """Build a ModuleContext with the given name bindings."""
    return ModuleContext(
        module="pkg.mod",
        names=dict(names),
        classes={},
    )


class TestBareNameResolution:
    def test_internal_function(self) -> None:
        ctx = _ctx(foo=ResolvedName("pkg.mod.foo", True))

        edge = resolve_call(_site("foo"), ctx)

        assert edge.caller == "pkg.mod.caller"
        assert edge.callee == "pkg.mod.foo"
        assert edge.kind is CallEdgeKind.INTERNAL
        assert edge.line == 10

    def test_internal_class_instantiation(self) -> None:
        # Calling a class to instantiate it is a call to that class.
        ctx = _ctx(Widget=ResolvedName("pkg.mod.Widget", True))

        edge = resolve_call(_site("Widget"), ctx)

        assert edge.callee == "pkg.mod.Widget"
        assert edge.kind is CallEdgeKind.INTERNAL

    def test_external_name(self) -> None:
        # from os import path; path(...)
        ctx = _ctx(path=ResolvedName("os.path", False))

        edge = resolve_call(_site("path"), ctx)

        assert edge.callee == "os.path"
        assert edge.kind is CallEdgeKind.EXTERNAL

    def test_bare_name_not_in_context(self) -> None:
        edge = resolve_call(_site("mystery"), _ctx())

        assert edge.callee == f"{UNRESOLVED_PREFIX}mystery"
        assert edge.kind is CallEdgeKind.UNRESOLVED


class TestDottedChainResolution:
    def test_internal_module_attribute(self) -> None:
        # from pkg import helpers; helpers.do_thing()
        ctx = _ctx(helpers=ResolvedName("pkg.helpers", True))

        edge = resolve_call(_site("helpers.do_thing"), ctx)

        assert edge.callee == "pkg.helpers.do_thing"
        assert edge.kind is CallEdgeKind.INTERNAL

    def test_internal_deeper_chain(self) -> None:
        # from pkg import helpers; helpers.sub.do_thing()
        ctx = _ctx(helpers=ResolvedName("pkg.helpers", True))

        edge = resolve_call(_site("helpers.sub.do_thing"), ctx)

        assert edge.callee == "pkg.helpers.sub.do_thing"
        assert edge.kind is CallEdgeKind.INTERNAL

    def test_external_dotted_chain(self) -> None:
        # import os; os.path.join(a, b)
        ctx = _ctx(os=ResolvedName("os", False))

        edge = resolve_call(_site("os.path.join"), ctx)

        assert edge.callee == "os.path.join"
        assert edge.kind is CallEdgeKind.EXTERNAL

    def test_aliased_external_chain(self) -> None:
        # import numpy as np; np.array(x)
        ctx = _ctx(np=ResolvedName("numpy", False))

        edge = resolve_call(_site("np.array"), ctx)

        assert edge.callee == "numpy.array"
        assert edge.kind is CallEdgeKind.EXTERNAL

    def test_dotted_head_not_in_context(self) -> None:
        # zzz isn't anywhere we know about.
        edge = resolve_call(_site("zzz.something"), _ctx())

        assert edge.callee == f"{UNRESOLVED_PREFIX}zzz.something"
        assert edge.kind is CallEdgeKind.UNRESOLVED

    def test_aliased_from_import_dotted(self) -> None:
        # from pkg.helpers import util as u; u.do_thing()
        ctx = _ctx(u=ResolvedName("pkg.helpers", True))

        edge = resolve_call(_site("u.do_thing"), ctx)

        assert edge.callee == "pkg.helpers.do_thing"
        assert edge.kind is CallEdgeKind.INTERNAL


class TestUnknownCallee:
    def test_unknown_sentinel_unresolved(self) -> None:
        edge = resolve_call(_site("<unknown>"), _ctx())

        assert edge.kind is CallEdgeKind.UNRESOLVED
        assert edge.callee == f"{UNRESOLVED_PREFIX}<unknown>"

    def test_unknown_sentinel_with_bindings(self) -> None:
        # Even if there are bindings, the sentinel is always unresolved.
        ctx = _ctx(foo=ResolvedName("pkg.mod.foo", True))

        edge = resolve_call(_site("<unknown>"), ctx)

        assert edge.kind is CallEdgeKind.UNRESOLVED


class TestSelfFallsThroughToUnresolved:
    """Step 3b does not resolve self.x; that arrives in 3c.

    These tests pin down the current behaviour so step 3c's tests
    show the change clearly when it lands.
    """

    def test_self_method_call_unresolved_in_step_3b(self) -> None:
        # No 'self' binding in the names table, so it falls through.
        edge = resolve_call(_site("self.helper"), _ctx())

        assert edge.kind is CallEdgeKind.UNRESOLVED
        assert edge.callee == f"{UNRESOLVED_PREFIX}self.helper"


class TestEdgeProperties:
    def test_line_preserved_from_call_site(self) -> None:
        ctx = _ctx(foo=ResolvedName("pkg.mod.foo", True))
        site = CallSite(
            caller="pkg.mod.caller",
            callee_expression="foo",
            line=42,
        )

        edge = resolve_call(site, ctx)

        assert edge.line == 42

    def test_caller_preserved_from_call_site(self) -> None:
        ctx = _ctx(foo=ResolvedName("pkg.mod.foo", True))
        site = CallSite(
            caller="pkg.mod.Widget.render",
            callee_expression="foo",
            line=1,
        )

        edge = resolve_call(site, ctx)

        assert edge.caller == "pkg.mod.Widget.render"
