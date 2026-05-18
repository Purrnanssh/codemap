"""Smoke tests for the ast_engine subpackage skeleton.

These tests do not verify behavior. They verify that the subpackage
exists and is importable. They will be expanded in later steps as
real logic is added.
"""

import codemap.ast_engine
import codemap.ast_engine.models
import codemap.ast_engine.parser


def test_ast_engine_subpackage_is_importable() -> None:
    """The ast_engine subpackage can be imported."""
    assert codemap.ast_engine is not None


def test_models_module_is_importable() -> None:
    """The models module can be imported."""
    assert codemap.ast_engine.models is not None


def test_parser_module_is_importable() -> None:
    """The parser module can be imported."""
    assert codemap.ast_engine.parser is not None
