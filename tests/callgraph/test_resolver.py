"""Tests for the call site resolver.

Covers the three shapes resolve_call handles:

    Bare name      foo
    Dotted chain   a.b.c
    Self method    self.x

Plus the <unknown> sentinel and the unresolved fallbacks.

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


def _site(callee_expression: str, caller: str = "pkg.mod.caller") -> CallSite:
    """Build a CallSite for tests, defaulting caller and line."""
    return CallSite(
        caller=caller,
        callee_expression=callee_expression,
        line=10,
    )


def _ctx(
    classes: dict[str, tuple[str, ...]] | None = None,
    **names: ResolvedName,
) -> ModuleContext:
    """Build a ModuleContext with the given name bindings."""
    return ModuleContext(
        module="pkg.mod",
        names=dict(names),
        classes=classes or {},
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
        ctx = _ctx(Widget=ResolvedName("pkg.mod.Widget", True))

        edge = resolve_call(_site("Widget"), ctx)

        assert edge.callee == "pkg.mod.Widget"
        assert edge.kind is CallEdgeKind.INTERNAL

    def test_external_name(self) -> None:
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
        ctx = _ctx(helpers=ResolvedName("pkg.helpers", True))

        edge = resolve_call(_site("helpers.do_thing"), ctx)

        assert edge.callee == "pkg.helpers.do_thing"
        assert edge.kind is CallEdgeKind.INTERNAL

    def test_internal_deeper_chain(self) -> None:
        ctx = _ctx(helpers=ResolvedName("pkg.helpers", True))

        edge = resolve_call(_site("helpers.sub.do_thing"), ctx)

        assert edge.callee == "pkg.helpers.sub.do_thing"
        assert edge.kind is CallEdgeKind.INTERNAL

    def test_external_dotted_chain(self) -> None:
        ctx = _ctx(os=ResolvedName("os", False))

        edge = resolve_call(_site("os.path.join"), ctx)

        assert edge.callee == "os.path.join"
        assert edge.kind is CallEdgeKind.EXTERNAL

    def test_aliased_external_chain(self) -> None:
        ctx = _ctx(np=ResolvedName("numpy", False))

        edge = resolve_call(_site("np.array"), ctx)

        assert edge.callee == "numpy.array"
        assert edge.kind is CallEdgeKind.EXTERNAL

    def test_dotted_head_not_in_context(self) -> None:
        edge = resolve_call(_site("zzz.something"), _ctx())

        assert edge.callee == f"{UNRESOLVED_PREFIX}zzz.something"
        assert edge.kind is CallEdgeKind.UNRESOLVED

    def test_aliased_from_import_dotted(self) -> None:
        ctx = _ctx(u=ResolvedName("pkg.helpers", True))

        edge = resolve_call(_site("u.do_thing"), ctx)

        assert edge.callee == "pkg.helpers.do_thing"
        assert edge.kind is CallEdgeKind.INTERNAL


class TestSelfMethodResolution:
    def test_self_method_hit(self) -> None:
        # Caller is a method of Widget; Widget has 'helper'.
        ctx = _ctx(classes={"Widget": ("render", "helper")})

        edge = resolve_call(
            _site("self.helper", caller="pkg.mod.Widget.render"),
            ctx,
        )

        assert edge.caller == "pkg.mod.Widget.render"
        assert edge.callee == "pkg.mod.Widget.helper"
        assert edge.kind is CallEdgeKind.SELF
        assert edge.line == 10

    def test_self_method_class_has_no_such_method(self) -> None:
        # Widget exists but has no 'missing' method.
        ctx = _ctx(classes={"Widget": ("render",)})

        edge = resolve_call(
            _site("self.missing", caller="pkg.mod.Widget.render"),
            ctx,
        )

        assert edge.kind is CallEdgeKind.UNRESOLVED
        assert edge.callee == f"{UNRESOLVED_PREFIX}self.missing"

    def test_self_method_caller_class_not_in_context(self) -> None:
        # Caller's class isn't in the classes index at all.
        ctx = _ctx(classes={})

        edge = resolve_call(
            _site("self.helper", caller="pkg.mod.Widget.render"),
            ctx,
        )

        assert edge.kind is CallEdgeKind.UNRESOLVED

    def test_self_method_from_module_level_function(self) -> None:
        # 'self.x' written inside a module-level function (invalid
        # Python in practice, but possible to construct). The caller
        # has no class segment, so it cannot be resolved.
        ctx = _ctx(classes={"Widget": ("helper",)})

        edge = resolve_call(
            _site("self.helper", caller="pkg.mod.top_level"),
            ctx,
        )

        assert edge.kind is CallEdgeKind.UNRESOLVED

    def test_self_deeper_chain_unresolved(self) -> None:
        # self.helper.do_thing is calling something on what
        # self.helper returned. We can't track that.
        ctx = _ctx(classes={"Widget": ("helper",)})

        edge = resolve_call(
            _site(
                "self.helper.do_thing",
                caller="pkg.mod.Widget.render",
            ),
            ctx,
        )

        assert edge.kind is CallEdgeKind.UNRESOLVED
        assert edge.callee == f"{UNRESOLVED_PREFIX}self.helper.do_thing"

    def test_self_alone_is_unresolved(self) -> None:
        # 'self' with no attribute would be 'self()', which is
        # calling self as if it were callable. We can't reason
        # about that.
        ctx = _ctx(classes={"Widget": ("helper",)})

        edge = resolve_call(
            _site("self", caller="pkg.mod.Widget.render"),
            ctx,
        )

        # 'self' has no dot, so it goes through the bare-name path,
        # which sees no binding and returns UNRESOLVED.
        assert edge.kind is CallEdgeKind.UNRESOLVED


class TestUnknownCallee:
    def test_unknown_sentinel_unresolved(self) -> None:
        edge = resolve_call(_site("<unknown>"), _ctx())

        assert edge.kind is CallEdgeKind.UNRESOLVED
        assert edge.callee == f"{UNRESOLVED_PREFIX}<unknown>"

    def test_unknown_sentinel_with_bindings(self) -> None:
        ctx = _ctx(foo=ResolvedName("pkg.mod.foo", True))

        edge = resolve_call(_site("<unknown>"), ctx)

        assert edge.kind is CallEdgeKind.UNRESOLVED


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
