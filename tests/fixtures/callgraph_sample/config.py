"""Configuration accessors for the fixture project.

Contains a single top-level function used to exercise the
attribute-chain internal call pattern (``import config`` then
``config.load()``).
"""

from __future__ import annotations


def load() -> dict[str, int]:
    """Return a fake configuration dict."""
    return {"limit": 10}
