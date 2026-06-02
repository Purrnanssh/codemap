<div align="center">

# CodeMap

**Interactive architecture visualization for modern codebases.**

[![Live Demo](https://img.shields.io/badge/Live-Demo-000000?style=for-the-badge&logo=vercel)](https://codemap.vercel.app/)
[![GitHub Repo](https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github)](https://github.com/Purrnanssh/codemap)
[![License](https://img.shields.io/badge/License-MIT-333333?style=for-the-badge)](https://opensource.org/licenses/MIT)

<br/>

![CodeMap Hero](https://via.placeholder.com/1200x600/111827/ffffff?text=CodeMap+Architecture+Graph)

</div>

---

## Why CodeMap

Navigating a large, unfamiliar codebase is inherently difficult. Developers are typically constrained to reading flat files, traversing deeply nested directories, and relying on global searches to build a mental model of an architecture.

CodeMap transforms this process by parsing your repository into a living, physics-based dependency graph. It exposes the hidden geometry of your software, highlighting critical structural dependencies, identifying highly-coupled architectural hotspots, and revealing the true relationships between functions and modules.

Built for speed and clarity, CodeMap helps engineers accelerate onboarding, discover technical debt, and safely plan refactors with complete spatial awareness.

## Features

- **Automated Repository Ingestion:** Parse public GitHub repositories instantly.
- **Interactive Topologies:** Physics-based rendering of your system's architecture.
- **Granular Views:** Seamlessly toggle between symbol-level and module-level hierarchies.
- **Hotspot Detection:** Automatically isolate highly complex and heavily dependent nodes.
- **Dependency Flow:** Visualize fan-in and fan-out metrics with directional edge streams.
- **AI-Powered Insights:** Automatically synthesize architectural observations and risks.

## Screenshots

<div align="center">

![Architecture Graph](https://via.placeholder.com/1200x600/111827/ffffff?text=Architecture+Graph)
*Interactive symbol-level dependency graph.*

<br/>

![Hotspot Explorer](https://via.placeholder.com/1200x600/111827/ffffff?text=Hotspot+Explorer)
*Identify highly complex and critical architectural hotspots.*

<br/>

![Dependency Inspector](https://via.placeholder.com/1200x600/111827/ffffff?text=Dependency+Inspector)
*Inspect node-specific fan-in and fan-out relationships.*

<br/>

![Module View](https://via.placeholder.com/1200x600/111827/ffffff?text=Module+View)
*Macro-level visualization of module dependencies.*

</div>

## How It Works

Repository Source<br/>
↓<br/>
AST Static Analysis<br/>
↓<br/>
Dependency Extraction<br/>
↓<br/>
Graph Construction<br/>
↓<br/>
Hotspot Detection<br/>
↓<br/>
Interactive Visualization<br/>

## Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React, TypeScript, Vite, D3 / Force Graph, Tailwind CSS, Framer Motion |
| **Backend** | Python, FastAPI, AST Analysis |
| **Deployment** | Vercel (Edge), Railway (Compute) |

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd web
npm install
npm run dev
```

### Environment Variables

Create a `.env` in the `web` directory:

```env
VITE_API_URL=http://localhost:8000
```

## Roadmap

- JavaScript / TypeScript parser integration
- Multi-repository cross-graph visualization
- Advanced AST structural risk detection
- Interactive node-filtering queries
- SVG & JSON graph export
- Direct IDE integrations

## Contributing

We welcome contributions from the community. Please fork the repository, create a feature branch, and submit a pull request for review.

## Author

**Purrnanssh Sinha**  
[github.com/Purrnanssh](https://github.com/Purrnanssh)

*Built with precision for the modern software engineer.*
