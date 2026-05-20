"""The main service that exercises every Phase 4 feature.

Each function or method in this file is deliberately constructed to
land in a different call-graph or complexity bucket, so that the
integration tests can pin down end-to-end behavior with named
assertions.

The dotted module path this file resolves to (when the fixture root
is the project root) is ``services.processor``.
"""

from __future__ import annotations

import os

import config
from utils import helper


class Processor:
    """A service class exercising self calls and multiple methods."""

    def run(self, items: list[int]) -> list[int]:
        """Process items with branching to give run() real complexity.

        Branches counted:
            for items                       +1
            if item is None                 +1
            if item > 0 and item < limit    +1 if, +1 and
            try/except                      +1 except
        Base 1 + 5 = 6.
        """
        results: list[int] = []
        limit = config.load()["limit"]
        for item in items:
            if item is None:
                continue
            if item > 0 and item < limit:
                try:
                    results.append(self.transform(item))
                except ValueError:
                    pass
        return results

    def transform(self, value: int) -> int:
        """A simple method called via self.transform from run()."""
        return helper(value)

    async def fetch_remote(self, key: str) -> str:
        """An async method to exercise the async flag end to end."""
        return os.environ.get(key, "")


def orchestrate(items: list[int]) -> list[int]:
    """A module-level function exercising same-module internal calls.

    The local-variable call ``processor.run(items)`` does NOT resolve
    to Processor.run; the head ``processor`` is a local variable and
    we don't track its type. That call becomes UNRESOLVED. The
    Processor() instantiation also becomes UNRESOLVED because the
    builder downgrades class targets that are not in the function
    index. That is the correct behavior for Phase 4.
    """
    processor = Processor()
    return processor.run(items)


def invoke_run_directly(processor: Processor, items: list[int]) -> list[int]:
    """A module-level function that calls Processor.run via the class.

    This resolves: ``Processor`` is in the names table pointing at
    the class, and ``Processor.run`` is a real function node, so the
    builder keeps the edge as INTERNAL. This is how we give
    Processor.run a real fan-in for the hotspot test, without
    pretending we have type tracking.
    """
    return Processor.run(processor, items)


def use_dynamic_call() -> int:
    """A function whose only call is unresolvable (a lambda call).

    Used to assert UNRESOLVED edge generation via the <unknown>
    sentinel from Phase 2's _resolve_callee.
    """
    return (lambda x: x + 1)(5)


def use_deep_self_chain() -> None:
    """A function with a call that won't resolve.

    The expression ``self.processor.run`` would require tracking
    ``self.processor``'s type, which Phase 4 does not do. Even though
    this is a module-level function (not a method), the bare name
    ``self`` is not in scope, so the call is unresolvable for a
    second reason too. Either way, the edge ends up UNRESOLVED.
    """
    self.processor.run([1, 2, 3])  # type: ignore[name-defined]
