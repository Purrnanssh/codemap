# 🗺️ CodeMap

> Static analysis tool that maps Python codebases — dependency graphs, call graphs, and code complexity visualization.

[![Python](https://img.shields.io/badge/python-3.11-blue?style=flat-square)](https://www.python.org)
[![Status](https://img.shields.io/badge/status-in%20development-orange?style=flat-square)](#status)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

---

## What is CodeMap?

CodeMap reads any Python codebase and tells you how it's wired together:

- **Which files import which** — module-level dependency graph
- **Which functions call which** — call graph at the symbol level
- **Where the tangled parts are** — complexity hotspots and circular dependencies

Point it at any project, get an X-ray of its structure in under 30 seconds.

## Why this exists

When you join a new codebase — or come back to your own after six months — the hardest question is *"where does anything live?"* CodeMap answers that question visually, so you stop guessing and start reading the right files.

## Status

🚧 **In active development.** This README will grow as the tool grows.

- [x] Project scaffold
- [ ] AST parser (Python)
- [ ] Dependency graph builder
- [ ] CLI with `analyze` command
- [ ] Rich terminal output
- [ ] Tests + CI

## Tech stack

- **Python 3.11**
- **Tree-sitter** — language-agnostic AST parsing
- **NetworkX** — graph algorithms
- **Typer + Rich** — beautiful CLI

## Local setup

```bash
git clone https://github.com/Purrnanssh/codemap.git
cd codemap
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## License

MIT — see [LICENSE](LICENSE).

---

*Built by [Purrnanssh Sinha](https://github.com/Purrnanssh).*

