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

## Status

🚧 **In active development.**

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

**Phase 3, Dependency graph** 🔜
- [ ] Multi-file project analysis
- [ ] Module-level dependency graph
- [ ] Circular dependency detection

**Phase 4, Complexity and visualization** 🔜
- [ ] Cyclomatic complexity per function
- [ ] Hotspot detection
- [ ] Graph export (DOT, JSON, HTML)

## Tech stack

- **Python 3.11+**
- **`ast`** (Python standard library) for parsing
- **Typer + Rich** for the CLI and pretty terminal output
- **pytest + ruff** for testing and linting

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


