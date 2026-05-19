"""Domain models for parsed Python source files.

Each class here represents a structural fact extracted from a source
file: an import, a function, a class, a call, or the overall file
analysis. All models are immutable dataclasses with __slots__ for
memory efficiency at scale.

These models hold data only. They do not contain parsing logic. The
parser in ast_engine.parser is responsible for producing them.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ImportInfo:
    """A single import statement found in a source file.

    Examples of source that produce this model:
        import os                  -> module='os', name='os', alias=None, level=0
        import os as operating_sys -> module='os', name='os', alias='operating_sys', level=0
        from pathlib import Path   -> module='pathlib', name='Path', alias=None, level=0
        from x import y as z       -> module='x', name='y', alias='z', level=0
        from . import sibling      -> module='', name='sibling', alias=None, level=1
        from .pkg import foo       -> module='pkg', name='foo', alias=None, level=1
        from ..pkg import bar      -> module='pkg', name='bar', alias=None, level=2

    The ``level`` field mirrors ``ast.ImportFrom.level``:
        0 means absolute (``import x`` or ``from x import y``)
        1 means a single-dot relative import (``from . import y``)
        2 means two-dot (``from .. import y``), and so on.
    """

    module: str
    name: str
    alias: str | None
    line: int
    level: int = 0


@dataclass(frozen=True, slots=True)
class FunctionInfo:
    """A function or method definition found in a source file.

    Captures only the surface signature, not the function body.
    Decorators and return type annotations are intentionally omitted
    in this first version to keep scope small.
    """

    name: str
    line: int
    args: tuple[str, ...]
    is_async: bool


@dataclass(frozen=True, slots=True)
class ClassInfo:
    """A class definition found in a source file.

    Methods defined inside the class are captured as FunctionInfo
    objects in the methods tuple.
    """

    name: str
    line: int
    methods: tuple[FunctionInfo, ...]


@dataclass(frozen=True, slots=True)
class CallInfo:
    """A function or method call site found in a source file.

    The callee field stores the textual name of what was called,
    not a reference to the actual function. Resolution of names to
    real functions happens later in the graph-building phase.
    """

    callee: str
    line: int


@dataclass(frozen=True, slots=True)
class FileAnalysis:
    """The complete structural analysis of a single Python source file.

    This is the top-level return type of the parser. It aggregates
    every other model in this module.
    """

    path: Path
    imports: tuple[ImportInfo, ...] = field(default_factory=tuple)
    functions: tuple[FunctionInfo, ...] = field(default_factory=tuple)
    classes: tuple[ClassInfo, ...] = field(default_factory=tuple)
    calls: tuple[CallInfo, ...] = field(default_factory=tuple)
