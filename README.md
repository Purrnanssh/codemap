# 🗺️ CodeMap

> Static analysis tool that maps Python codebases. Dependency graphs, call graphs, and code complexity visualization.

[![Python](https://img.shields.io/badge/python-3.11-blue?style=flat-square)](https://www.python.org)
[![CI](https://github.com/Purrnanssh/codemap/actions/workflows/ci.yml/badge.svg)](https://github.com/Purrnanssh/codemap/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

---

## What is CodeMap?

CodeMap reads any Python codebase and tells you how it's wired together:

- **Which files import which**, the module-level dependency graph
- **Which functions call which**, the call graph at the symbol level
- **Where the tangled parts are**, complexity hotspots and circular dependencies

Point it at any project, get an X-ray of its structure in under 30 seconds.

## Why this exists

When you join a new codebase, or come back to your own after six months, the hardest question is *"where does anything live?"* CodeMap answers that question visually, so you stop guessing and start reading the right files.

## Quick example

### Analyze a single file

After installation:

```bash
codemap analyze path/to/your_file.py
```

You get a Rich-formatted breakdown of every import, top-level function, class (with its methods), and call site in the file. Sample output (analyzing CodeMap's own CLI module):
╭──── 🗺️  CodeMap Analysis ────╮
│  src/codemap/cli.py          │
╰──────────────────────────────╯
╭──────── Imports (9) ─────────╮
│  future    annotations   │
│  pathlib       Path          │
│  typer         typer         │
│  rich.console  Console       │
│  ...                         │
╰──────────────────────────────╯
╭─────── Functions (4) ────────╮
│  hello      ()       line 30 │
│  version    ()       line 41 │
│  analyze    (path)   line 47 │
│  main       ()       line 72 │
╰──────────────────────────────╯

### Scan a whole project

Phase 3 adds project-wide dependency analysis:

```bash
codemap scan src/
```

You get a digest of your codebase's wiring: total modules, internal vs external imports, the most-imported modules (your foundation layer), any circular dependencies, and any files that failed to parse. Exit codes are CI-friendly: `0` clean, `1` scan failed, `2` cycles detected.

Sample output (CodeMap scanning itself):
╭ 🕸️  CodeMap Dependency Graph ╮
│ src                          │
╰──────────────────────────────╯
╭──────── Stats ───────────────╮
│  Modules               11    │
│  Internal edges        11    │
│  External imports      26    │
│  Cycles                 0    │
│  Parse errors           0    │
╰──────────────────────────────╯
╭──── Top imported ────────────────╮
│  1  codemap.ast_engine.models  3 │
│  2  codemap.ast_engine.parser  2 │
│  3  codemap.version            2 │
│  4  codemap.graph.builder      1 │
│  ...                             │
╰──────────────────────────────────╯

**Tip on the path argument.** Point `codemap scan` at the directory that contains your top-level packages. For a `src/` layout, that's `src/`. For a flat layout (with `mypkg/` at the repo root), that's the repo root. Dotted paths in the output are computed relative to this directory and must match the import strings in your code for resolution to work.

## Status

✅ **Released, v0.4.0.** Feature-complete for the original design.

**Phase 1, Foundation** ✅
- [x] Project scaffold (src layout, pyproject.toml, hatchling)
- [x] Typer CLI with `hello` and `version` commands
- [x] Ruff + mypy + pytest config
- [x] GitHub Actions CI on Python 3.11 and 3.12

**Phase 2, AST parser** ✅
- [x] Domain models (immutable, slotted dataclasses)
- [x] Import extraction (`import x`, `from x import y`, aliases, dotted, relative)
- [x] Top-level function extraction (sync and async)
- [x] Class extraction with methods
- [x] Call-site extraction (Name and Attribute callees, `<unknown>` for the rest)
- [x] `parse_file(path)` integration entry point
- [x] `codemap analyze <path>` CLI command with Rich output
- [x] 85 tests passing across the engine and CLI

**Phase 3, Dependency graph** ✅
- [x] Project-wide module discovery (skips venvs, caches, VCS metadata)
- [x] Import resolver (absolute, relative, submodule vs name disambiguation)
- [x] networkx-backed `nx.DiGraph` of module dependencies
- [x] Deterministic circular dependency detection (Johnson's algorithm via networkx)
- [x] Parse-error tolerance: broken files don't abort the scan
- [x] `codemap scan <directory>` CLI with CI-friendly exit codes
- [x] 167 tests passing across the engine, graph, rendering, and CLI

**Phase 4, Call graph & complexity** ✅
- [x] Symbol-level call graph with three-stage resolver (local names, dotted chains, `self.x` methods)
- [x] McCabe cyclomatic complexity per function
- [x] Hotspot scoring (complexity × fan-in)
- [x] Graph export (DOT and JSON)
- [x] `codemap callgraph <path>` CLI command
- [x] 367 tests passing across all engines, graphs, exporters, and CLIs

## Tech stack

- **Python 3.11+**
- **`ast`** (Python standard library) for parsing
- **`networkx`** for the dependency graph and cycle detection
- **Typer + Rich** for the CLI and pretty terminal output
- **pytest + ruff + mypy** for testing, linting, and type checking

## Local setup

```bash
git clone https://github.com/Purrnanssh/codemap.git
cd codemap
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## License

MIT, see [LICENSE](LICENSE).

---

*Built by [Purrnanssh Sinha](https://github.com/Purrnanssh).*
