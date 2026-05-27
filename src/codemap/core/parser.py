"""Language-agnostic abstraction for repository parsers.

The goal of this module is to decouple the Graph Builder from
language-specific parsing implementations (like Python's AST).
Every supported language will implement BaseParser and emit
standardized intermediate representations (IR).
"""

from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class IRSymbol:
    """A generic representation of a function, method, or struct."""
    name: str
    line: int
    kind: str  # e.g., 'function', 'class', 'method'
    file_path: str


@dataclass
class IRImport:
    """A generic representation of an imported symbol or module."""
    module: str
    name: str
    alias: Optional[str]
    line: int
    is_relative: bool


@dataclass
class IRCall:
    """A generic representation of a function call."""
    callee: str
    line: int


@dataclass
class IRModule:
    """A generic representation of a fully parsed file."""
    path: Path
    imports: List[IRImport] = field(default_factory=list)
    symbols: List[IRSymbol] = field(default_factory=list)
    calls: List[IRCall] = field(default_factory=list)


class BaseParser(ABC):
    """Abstract interface for all language parsers."""
    
    @abstractmethod
    def parse_file(self, filepath: Path) -> IRModule:
        """Parses a single source file and returns its IR."""
        pass
