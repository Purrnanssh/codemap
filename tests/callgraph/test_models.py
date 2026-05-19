"""Tests for callgraph domain models.

Covers construction, immutability, equality, and the qualified-name
helper. These models hold no logic of their own; the goal of these
tests is to lock in the field surface and the ``build_qualified_name``
contract so later layers can rely on them.
"""

from __future__ import annotations

import pytest

from codemap.callgraph.models import (
    CallEdge,
    CallEdgeKind,
    CallSite,
    FunctionNode,
    build_qualified_name,
)


class TestFunctionNode:
    def test_module_level_function(self) -> None:
        node = FunctionNode(
            qualified_name="pkg.mod.foo",
            module="pkg.mod",
            class_name=None,
            name="foo",
            line=10,
            is_method=False,
            is_async=False,
        )

        assert node.qualified_name == "pkg.mod.foo"
        assert node.class_name is None
        assert node.is_method is False
        assert node.is_async is False

    def test_async_function(self) -> None:
        node = FunctionNode(
            qualified_name="pkg.mod.fetch",
            module="pkg.mod",
            class_name=None,
            name="fetch",
            line=5,
            is_method=False,
            is_async=True,
        )

        assert node.is_async is True

    def test_method(self) -> None:
        node = FunctionNode(
            qualified_name="pkg.mod.Widget.render",
            module="pkg.mod",
            class_name="Widget",
            name="render",
            line=22,
            is_method=True,
            is_async=False,
        )

        assert node.class_name == "Widget"
        assert node.is_method is True

    def test_is_immutable(self) -> None:
        node = FunctionNode(
            qualified_name="pkg.mod.foo",
            module="pkg.mod",
            class_name=None,
            name="foo",
            line=10,
            is_method=False,
            is_async=False,
        )

        with pytest.raises(AttributeError):
            node.line = 99  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        a = FunctionNode(
            qualified_name="pkg.mod.foo",
            module="pkg.mod",
            class_name=None,
            name="foo",
            line=10,
            is_method=False,
            is_async=False,
        )
        b = FunctionNode(
            qualified_name="pkg.mod.foo",
            module="pkg.mod",
            class_name=None,
            name="foo",
            line=10,
            is_method=False,
            is_async=False,
        )

        assert a == b
        assert hash(a) == hash(b)

    def test_inequality_when_any_field_differs(self) -> None:
        base = FunctionNode(
            qualified_name="pkg.mod.foo",
            module="pkg.mod",
            class_name=None,
            name="foo",
            line=10,
            is_method=False,
            is_async=False,
        )
        different_line = FunctionNode(
            qualified_name="pkg.mod.foo",
            module="pkg.mod",
            class_name=None,
            name="foo",
            line=11,
            is_method=False,
            is_async=False,
        )

        assert base != different_line


class TestCallSite:
    def test_simple_name_call(self) -> None:
        site = CallSite(
            caller="pkg.mod.foo",
            callee_expression="bar",
            line=15,
        )

        assert site.caller == "pkg.mod.foo"
        assert site.callee_expression == "bar"
        assert site.line == 15

    def test_attribute_chain_call(self) -> None:
        site = CallSite(
            caller="pkg.mod.foo",
            callee_expression="os.path.join",
            line=20,
        )

        assert site.callee_expression == "os.path.join"

    def test_self_method_call(self) -> None:
        site = CallSite(
            caller="pkg.mod.Widget.render",
            callee_expression="self.helper",
            line=8,
        )

        assert site.callee_expression == "self.helper"

    def test_unknown_callee_preserved(self) -> None:
        site = CallSite(
            caller="pkg.mod.foo",
            callee_expression="<unknown>",
            line=30,
        )

        assert site.callee_expression == "<unknown>"

    def test_is_immutable(self) -> None:
        site = CallSite(
            caller="pkg.mod.foo",
            callee_expression="bar",
            line=15,
        )

        with pytest.raises(AttributeError):
            site.line = 99  # type: ignore[misc]


class TestCallEdge:
    def test_internal_edge(self) -> None:
        edge = CallEdge(
            caller="pkg.mod.foo",
            callee="pkg.mod.bar",
            line=15,
            kind=CallEdgeKind.INTERNAL,
        )

        assert edge.caller == "pkg.mod.foo"
        assert edge.callee == "pkg.mod.bar"
        assert edge.kind is CallEdgeKind.INTERNAL

    def test_self_edge(self) -> None:
        edge = CallEdge(
            caller="pkg.mod.Widget.render",
            callee="pkg.mod.Widget.helper",
            line=8,
            kind=CallEdgeKind.SELF,
        )

        assert edge.kind is CallEdgeKind.SELF

    def test_external_edge(self) -> None:
        edge = CallEdge(
            caller="pkg.mod.foo",
            callee="requests.get",
            line=20,
            kind=CallEdgeKind.EXTERNAL,
        )

        assert edge.kind is CallEdgeKind.EXTERNAL

    def test_unresolved_edge(self) -> None:
        edge = CallEdge(
            caller="pkg.mod.foo",
            callee="<unresolved>:self.client.session.get",
            line=25,
            kind=CallEdgeKind.UNRESOLVED,
        )

        assert edge.kind is CallEdgeKind.UNRESOLVED
        assert edge.callee.startswith("<unresolved>:")

    def test_is_immutable(self) -> None:
        edge = CallEdge(
            caller="pkg.mod.foo",
            callee="pkg.mod.bar",
            line=15,
            kind=CallEdgeKind.INTERNAL,
        )

        with pytest.raises(AttributeError):
            edge.line = 99  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        a = CallEdge(
            caller="pkg.mod.foo",
            callee="pkg.mod.bar",
            line=15,
            kind=CallEdgeKind.INTERNAL,
        )
        b = CallEdge(
            caller="pkg.mod.foo",
            callee="pkg.mod.bar",
            line=15,
            kind=CallEdgeKind.INTERNAL,
        )

        assert a == b
        assert hash(a) == hash(b)


class TestCallEdgeKind:
    def test_all_kinds_present(self) -> None:
        assert CallEdgeKind.INTERNAL.value == "internal"
        assert CallEdgeKind.SELF.value == "self"
        assert CallEdgeKind.EXTERNAL.value == "external"
        assert CallEdgeKind.UNRESOLVED.value == "unresolved"

    def test_kinds_are_distinct(self) -> None:
        kinds = {
            CallEdgeKind.INTERNAL,
            CallEdgeKind.SELF,
            CallEdgeKind.EXTERNAL,
            CallEdgeKind.UNRESOLVED,
        }
        assert len(kinds) == 4


class TestBuildQualifiedName:
    def test_module_level_function(self) -> None:
        assert build_qualified_name("pkg.mod", "foo") == "pkg.mod.foo"

    def test_method(self) -> None:
        assert (
            build_qualified_name("pkg.mod", "render", class_name="Widget")
            == "pkg.mod.Widget.render"
        )

    def test_explicit_none_class_name(self) -> None:
        assert (
            build_qualified_name("pkg.mod", "foo", class_name=None)
            == "pkg.mod.foo"
        )

    def test_nested_module_path(self) -> None:
        assert (
            build_qualified_name("a.b.c.d", "func") == "a.b.c.d.func"
        )

    def test_single_segment_module(self) -> None:
        assert build_qualified_name("mod", "foo") == "mod.foo"
