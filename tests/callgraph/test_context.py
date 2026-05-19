"""Tests for the per-module name resolution context.

Covers local definition extraction, import binding (alias, plain,
from-import), internal-vs-external classification, the local/import
collision rule, and the class -> methods index used later by self.x
resolution.

These tests construct ``FileAnalysis`` objects directly from the
Phase 2 model layer rather than parsing source files, so the focus
stays on the context-building logic.
"""

from __future__ import annotations

from pathlib import Path

from codemap.ast_engine.models import (
    ClassInfo,
    FileAnalysis,
    FunctionInfo,
    ImportInfo,
)
from codemap.callgraph.context import (
    ModuleContext,
    ResolvedName,
    build_module_context,
)


def _analysis(
    *,
    imports: tuple[ImportInfo, ...] = (),
    functions: tuple[FunctionInfo, ...] = (),
    classes: tuple[ClassInfo, ...] = (),
) -> FileAnalysis:
    """Build a FileAnalysis for tests, defaulting empty tuples."""
    return FileAnalysis(
        path=Path("sample.py"),
        imports=imports,
        functions=functions,
        classes=classes,
    )


def _func(name: str) -> FunctionInfo:
    return FunctionInfo(name=name, line=1, args=(), is_async=False)


def _cls(name: str, methods: tuple[str, ...] = ()) -> ClassInfo:
    return ClassInfo(
        name=name,
        line=1,
        methods=tuple(_func(m) for m in methods),
    )


class TestLocalDefinitions:
    def test_top_level_function_added(self) -> None:
        analysis = _analysis(functions=(_func("foo"),))

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=analysis,
            internal_modules={"pkg.mod"},
            importer_is_package=False,
        )

        assert "foo" in ctx.names
        assert ctx.names["foo"] == ResolvedName("pkg.mod.foo", True)

    def test_top_level_class_added(self) -> None:
        analysis = _analysis(classes=(_cls("Widget"),))

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=analysis,
            internal_modules={"pkg.mod"},
            importer_is_package=False,
        )

        assert "Widget" in ctx.names
        assert ctx.names["Widget"] == ResolvedName(
            "pkg.mod.Widget", True
        )

    def test_class_methods_indexed(self) -> None:
        analysis = _analysis(
            classes=(_cls("Widget", methods=("render", "update")),)
        )

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=analysis,
            internal_modules={"pkg.mod"},
            importer_is_package=False,
        )

        assert ctx.classes == {"Widget": ("render", "update")}

    def test_class_with_no_methods(self) -> None:
        analysis = _analysis(classes=(_cls("Empty"),))

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=analysis,
            internal_modules={"pkg.mod"},
            importer_is_package=False,
        )

        assert ctx.classes == {"Empty": ()}

    def test_methods_not_in_names_table(self) -> None:
        # Methods are accessed via Widget.render or self.render, never
        # by bare name. They must not appear in the names dict.
        analysis = _analysis(
            classes=(_cls("Widget", methods=("render",)),)
        )

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=analysis,
            internal_modules={"pkg.mod"},
            importer_is_package=False,
        )

        assert "render" not in ctx.names

    def test_empty_module(self) -> None:
        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=_analysis(),
            internal_modules={"pkg.mod"},
            importer_is_package=False,
        )

        assert ctx.module == "pkg.mod"
        assert ctx.names == {}
        assert ctx.classes == {}


class TestExternalImports:
    def test_plain_import(self) -> None:
        # import os
        imp = ImportInfo(module="os", name="os", alias=None, line=1)

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=_analysis(imports=(imp,)),
            internal_modules={"pkg.mod"},
            importer_is_package=False,
        )

        assert ctx.names["os"] == ResolvedName("os", False)

    def test_dotted_import_binds_top_level(self) -> None:
        # import os.path  -> binds 'os', target is 'os.path'
        imp = ImportInfo(
            module="os.path", name="os.path", alias=None, line=1
        )

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=_analysis(imports=(imp,)),
            internal_modules={"pkg.mod"},
            importer_is_package=False,
        )

        assert "os" in ctx.names
        assert ctx.names["os"] == ResolvedName("os.path", False)
        assert "os.path" not in ctx.names

    def test_import_with_alias(self) -> None:
        # import numpy as np
        imp = ImportInfo(
            module="numpy", name="numpy", alias="np", line=1
        )

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=_analysis(imports=(imp,)),
            internal_modules={"pkg.mod"},
            importer_is_package=False,
        )

        assert "np" in ctx.names
        assert ctx.names["np"] == ResolvedName("numpy", False)
        assert "numpy" not in ctx.names

    def test_from_import(self) -> None:
        # from os import path
        imp = ImportInfo(module="os", name="path", alias=None, line=1)

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=_analysis(imports=(imp,)),
            internal_modules={"pkg.mod"},
            importer_is_package=False,
        )

        assert ctx.names["path"] == ResolvedName("os.path", False)

    def test_from_import_with_alias(self) -> None:
        # from os import path as p
        imp = ImportInfo(module="os", name="path", alias="p", line=1)

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=_analysis(imports=(imp,)),
            internal_modules={"pkg.mod"},
            importer_is_package=False,
        )

        assert ctx.names["p"] == ResolvedName("os.path", False)
        assert "path" not in ctx.names


class TestInternalImports:
    def test_internal_from_import_of_name(self) -> None:
        # from pkg.helpers import util, where util is a function/class
        # defined inside pkg.helpers (NOT a submodule). The binding
        # 'util' must resolve to the symbol 'pkg.helpers.util', not
        # to the module 'pkg.helpers'.
        imp = ImportInfo(
            module="pkg.helpers", name="util", alias=None, line=1
        )

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=_analysis(imports=(imp,)),
            internal_modules={"pkg.mod", "pkg.helpers"},
            importer_is_package=False,
        )

        assert ctx.names["util"] == ResolvedName(
            "pkg.helpers.util", True
        )

    def test_internal_submodule_import(self) -> None:
        # from pkg import sub, where pkg.sub is itself an internal
        # module. The binding 'sub' resolves to the submodule.
        imp = ImportInfo(module="pkg", name="sub", alias=None, line=1)

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=_analysis(imports=(imp,)),
            internal_modules={"pkg.mod", "pkg", "pkg.sub"},
            importer_is_package=False,
        )

        assert ctx.names["sub"] == ResolvedName("pkg.sub", True)

    def test_internal_with_alias(self) -> None:
        # from pkg.helpers import util as u  (util is a symbol)
        imp = ImportInfo(
            module="pkg.helpers", name="util", alias="u", line=1
        )

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=_analysis(imports=(imp,)),
            internal_modules={"pkg.mod", "pkg.helpers"},
            importer_is_package=False,
        )

        assert ctx.names["u"] == ResolvedName(
            "pkg.helpers.util", True
        )

    def test_relative_import_internal_submodule(self) -> None:
        # from . import sibling, inside pkg.mod, where pkg.sibling
        # is an internal module.
        imp = ImportInfo(
            module="", name="sibling", alias=None, line=1, level=1
        )

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=_analysis(imports=(imp,)),
            internal_modules={"pkg.mod", "pkg.sibling"},
            importer_is_package=False,
        )

        assert ctx.names["sibling"] == ResolvedName(
            "pkg.sibling", True
        )

    def test_relative_import_internal_symbol(self) -> None:
        # from .helpers import util, inside pkg.mod, where util is a
        # symbol inside pkg.helpers (which is an internal module).
        imp = ImportInfo(
            module="helpers", name="util", alias=None, line=1, level=1
        )

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=_analysis(imports=(imp,)),
            internal_modules={"pkg.mod", "pkg.helpers"},
            importer_is_package=False,
        )

        assert ctx.names["util"] == ResolvedName(
            "pkg.helpers.util", True
        )


class TestCollisions:
    def test_import_overrides_local_def(self) -> None:
        # def foo defined locally, then `from other import foo`.
        # The import wins.
        analysis = _analysis(
            functions=(_func("foo"),),
            imports=(
                ImportInfo(
                    module="other", name="foo", alias=None, line=10
                ),
            ),
        )

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=analysis,
            internal_modules={"pkg.mod"},
            importer_is_package=False,
        )

        assert ctx.names["foo"] == ResolvedName("other.foo", False)

    def test_two_imports_last_wins(self) -> None:
        # If two imports bind the same name, the later one wins,
        # matching Python's runtime behaviour.
        analysis = _analysis(
            imports=(
                ImportInfo(module="a", name="x", alias=None, line=1),
                ImportInfo(module="b", name="x", alias=None, line=2),
            ),
        )

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=analysis,
            internal_modules={"pkg.mod"},
            importer_is_package=False,
        )

        assert ctx.names["x"] == ResolvedName("b.x", False)


class TestMixed:
    def test_realistic_module(self) -> None:
        """A module with locals, externals, and internals all at once."""
        analysis = _analysis(
            imports=(
                ImportInfo(module="os", name="os", alias=None, line=1),
                ImportInfo(
                    module="pkg.helpers",
                    name="util",
                    alias=None,
                    line=2,
                ),
            ),
            functions=(_func("foo"), _func("bar")),
            classes=(_cls("Service", methods=("run", "stop")),),
        )

        ctx = build_module_context(
            module_dotted="pkg.mod",
            analysis=analysis,
            internal_modules={"pkg.mod", "pkg.helpers"},
            importer_is_package=False,
        )

        assert ctx.names == {
            "foo": ResolvedName("pkg.mod.foo", True),
            "bar": ResolvedName("pkg.mod.bar", True),
            "Service": ResolvedName("pkg.mod.Service", True),
            "os": ResolvedName("os", False),
            "util": ResolvedName("pkg.helpers.util", True),
        }
        assert ctx.classes == {"Service": ("run", "stop")}


class TestModuleContextType:
    def test_module_context_is_constructable_directly(self) -> None:
        """Sanity check on the dataclass surface."""
        ctx = ModuleContext(
            module="pkg.mod",
            names={"foo": ResolvedName("pkg.mod.foo", True)},
            classes={"Widget": ("render",)},
        )

        assert ctx.module == "pkg.mod"
        assert ctx.names["foo"].qualified_name == "pkg.mod.foo"
        assert ctx.classes["Widget"] == ("render",)
