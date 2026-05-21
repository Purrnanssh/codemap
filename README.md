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

### Build a call graph

Phase 4 goes one level deeper, from modules down to individual functions:

```bash
codemap callgraph src/
```

You get a symbol-level map of which function calls which, with McCabe complexity attached to every function and a hotspot table that ranks functions by `complexity × fan-in`, the parts of the codebase most worth your attention when reading or refactoring. Sample output (CodeMap analyzing its own source):
```
╭ 📞 CodeMap Call Graph ───────╮
│ src                          │
╰──────────────────────────────╯
╭──────── Stats ───────────────╮
│  Functions             104   │
│  Internal edges         89   │
│  Self edges             17   │
│  External edges         61   │
│  Unresolved edges      262   │
╰──────────────────────────────╯
╭──── Hotspots (top 5) ──────────────────────────────────────────────────╮
│  1  codemap.graph.resolver.resolve_import           cx 8  fan-in 2  16 │
│  2  codemap.callgraph.extractor._handle_call        cx 6  fan-in 2  12 │
│  3  codemap.graph.discovery.discover_modules        cx 6  fan-in 2  12 │
│  4  codemap.ast_engine.parser._resolve_callee       cx 5  fan-in 2  10 │
│  5  codemap.callgraph.builder.build_call_graph      cx 9  fan-in 1   9 │
╰────────────────────────────────────────────────────────────────────────╯
```

**Export the graph for visualization.** Pipe to Graphviz or feed to your own tooling:

```bash
codemap callgraph src/ --format dot --output callgraph.dot
codemap callgraph src/ --format json --output callgraph.json
```

**Tip on unresolved calls.** Calls to Python builtins (`len`, `str`, `isinstance`), third-party functions, and dynamic dispatch (`self.x()` where `x` is computed) show up as unresolved by design. CodeMap reports them so you can see what your code depends on without pretending to resolve calls it can't statically prove.

**Tip on hotspot scoring.** `complexity × fan-in` ranks functions that are *both* internally complex *and* depended on from many callers. A function with complexity 12 called from one place is a refactoring candidate. A function with complexity 12 called from twenty places is a refactoring priority.

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
