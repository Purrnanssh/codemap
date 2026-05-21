# Changelog

All notable changes to CodeMap are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-05-22

### Added
- Symbol-level call graph (`codemap.callgraph` subpackage) that tracks which function calls which across the codebase.
- McCabe cyclomatic complexity computed per function and attached to graph nodes.
- Hotspot scoring (`complexity × fan-in`) to surface the functions most worth refactoring attention.
- Three-stage call resolver: per-module name binding, dotted attribute chains, and `self.x` method dispatch.
- `from x import y` binding expansion so imported symbols resolve to their fully qualified names.
- DOT and JSON exporters for downstream visualization (Graphviz) or tooling.
- `codemap callgraph <path>` CLI command with `--format`, `--output`, `--hotspots`, and `--min-complexity` flags.
- End-to-end integration tests against a committed fixture monolith.
- 200+ new tests, bringing the suite to 367 passing tests.

### Changed
- README now documents all four phases and includes a sample `codemap callgraph` invocation.
- Project status moved from "in active development" to "released."

## [0.3.0] - 2026-05-19

### Added
- `codemap.graph` subpackage implementing project-wide module discovery and dependency analysis.
- Module discovery with dotted-path resolution that skips venvs, caches, and VCS metadata.
- Import resolver that disambiguates submodules from re-exported names and handles relative imports.
- NetworkX-backed `DiGraph` of module dependencies with parse-error tolerance (broken files do not abort the scan).
- Deterministic circular dependency detection via Johnson's algorithm.
- `codemap scan <directory>` CLI command with CI-friendly exit codes (`0` clean, `1` scan failed, `2` cycles detected).
- Rich-formatted dependency-graph summary renderer.

### Fixed
- AST engine now captures the `level` attribute on `ImportFrom` nodes, enabling correct relative-import resolution.

## [0.2.0] - 2026-05-18

### Added
- `codemap.ast_engine` subpackage backed by Python's standard library `ast` module.
- Immutable, slotted domain models for parsed source elements.
- Import extraction supporting `import x`, `from x import y`, aliases, dotted paths, and relative imports.
- Top-level function extraction (sync and async).
- Class extraction with methods.
- Call-site extraction for `Name` and `Attribute` callees, with `<unknown>` placeholders for the rest.
- `parse_file(path)` entry point for full-file analysis.
- `codemap analyze <path>` CLI command with Rich-formatted output.

### Project foundation (initially shipped under v0.2.0)
- `src/` layout with `pyproject.toml` (hatchling backend).
- Typer-based CLI with `hello` and `version` subcommands.
- Ruff + mypy + pytest tooling configuration.
- GitHub Actions CI matrix on Python 3.11 and 3.12.
- 85 tests passing across engine and CLI at release.

[0.4.0]: https://github.com/Purrnanssh/codemap/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Purrnanssh/codemap/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Purrnanssh/codemap/releases/tag/v0.2.0
