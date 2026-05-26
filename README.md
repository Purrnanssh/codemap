<div align="center">
  <h1>CodeMap</h1>
  <p><strong>Cinematic architecture visualization for modern Python codebases.</strong></p>
  <p>
    <code>Python AST</code>
    <span>&nbsp;&nbsp;•&nbsp;&nbsp;</span>
    <code>Tarjan's SCC</code>
    <span>&nbsp;&nbsp;•&nbsp;&nbsp;</span>
    <code>Canvas 2D Engine</code>
  </p>
  <br />
  <a href="https://codemap-teal.vercel.app/?">
    <img src="https://img.shields.io/badge/Launch_Live_Demo-000000?style=for-the-badge&logo=vercel&logoColor=white" alt="Launch Live Demo" />
  </a>
  <br />
  <br />
  <img src="assets/hero.png?v=2" width="100%" alt="CodeMap Dashboard Screenshot" />
</div>

<br />

CodeMap provides deep structural visibility into complex Python repositories. By combining a zero-dependency static analyzer with a high-framerate physics engine, it exposes architectural bottlenecks, cyclic dependencies, and system hotspots in real time—all presented through a cinematic, minimalist interface.

<br />

## Capabilities

- **Static AST Extraction:** Parses Python source code entirely offline to build precise symbol and module-level dependency networks, calculating Fan-In, Fan-Out, and McCabe Complexity.
- **High-Performance Rendering:** Powers dense graphs through a heavily optimized `react-force-graph` engine featuring manual tick interpolation, hardware-accelerated text, and adaptive particle throttling to maintain 60fps at scale.
- **Real-Time Cycle Detection:** Runs Tarjan’s Strongly Connected Components (SCC) algorithm directly on the client to instantly isolate and highlight dangerous circular dependencies.
- **AI Diagnostics:** Provides an extensible abstraction layer to query language models for automated architectural reviews, risk assessments, and module documentation.

<br />

## Architecture

Built for scale and decoupled by design. The extraction logic never blocks the rendering pipeline.

- **`src/codemap` (Analyzer):** A strict, zero-dependency Python CLI utilizing the standard `ast` module. Emits raw topology networks as static JSON.
- **`web/` (Visualizer):** A Vite-powered React environment heavily optimized for canvas performance. Features a bespoke glassmorphism UI, progressive disclosure rendering, and tight Framer Motion physics.

<br />

## Developer Experience

Generate a codebase topology and spin up the dashboard in seconds.

```bash
# 1. Extract the architecture graph
codemap callgraph src/ --format json --output web/public/data.json

# 2. Launch the visualizer
cd web
npm install
npm run dev
```

<br />

## Roadmap

- [x] Core AST extraction and JSON schema definition
- [x] Physics-based canvas and glassmorphism interface
- [x] Client-side module aggregation and SCC cycle detection
- [x] AI Insights engine abstraction
- [ ] Live FastAPI server (`codemap serve`) for dynamic codebase resynchronization
- [ ] Direct LLM API integration for automated refactoring proposals

<br />

---

<div align="center">
  <p>Built for scale. Designed for clarity.</p>
</div>
