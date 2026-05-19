"""Symbol-level call graph analysis for Python projects.

This package builds on Phase 2's structural parsing and Phase 3's
module-level dependency graph to answer a finer-grained question:
which function calls which? It produces a directed graph where
nodes are functions and methods (identified by qualified name) and
edges represent call relationships.

The package is organised into single-concern modules:

    models       Domain models (this layer holds no logic).
    extractor    Walks function bodies to collect call sites.
    resolver     Turns raw callee expressions into qualified names.
    builder      Assembles the resolved edges into an nx.DiGraph.
    complexity   Cyclomatic complexity per function.
    hotspots     Fan-in, fan-out, and composite scoring.
    exporters    DOT and JSON output writers.
"""
