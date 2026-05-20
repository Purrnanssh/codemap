"""Utility helpers used by the fixture project.

Contains a single top-level function so the call graph can assert
cross-module resolution from-import form (``from utils import helper``).
"""

from __future__ import annotations


def helper(value: int) -> int:
    """Return value doubled."""
    return value * 2
