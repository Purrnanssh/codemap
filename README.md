<div align="center">

# CodeMap

**Visualize the architecture of any GitHub repository as an interactive dependency graph.**

[![Live Demo](https://img.shields.io/badge/Live-Demo-0ea5e9?style=for-the-badge&logo=vercel)](https://codemap.vercel.app/)
[![GitHub Stars](https://img.shields.io/github/stars/Purrnanssh/codemap?style=for-the-badge&color=fbbf24)](https://github.com/Purrnanssh/codemap/stargazers)
[![License](https://img.shields.io/badge/License-MIT-334155?style=for-the-badge)](https://opensource.org/licenses/MIT)

</div>

---

## 📸 Screenshots

<div align="center">

| | |
|:---:|:---:|
| ![Landing Page](https://via.placeholder.com/600x350/111827/ffffff?text=Landing+Page) <br> *Landing Page* | ![Graph Visualization](https://via.placeholder.com/600x350/111827/ffffff?text=Graph+Visualization) <br> *Interactive Graph Visualization* |
| ![Hotspot Exploration](https://via.placeholder.com/600x350/111827/ffffff?text=Hotspot+Exploration) <br> *Hotspot Exploration Sidebar* | ![Dependency Analysis](https://via.placeholder.com/600x350/111827/ffffff?text=Dependency+Analysis) <br> *Dependency Analysis Panel* |

</div>

---

## 🎯 Why CodeMap?

Software engineers fundamentally build networks of relationships, yet modern developer tooling forces us to navigate these networks through rigid folder hierarchies, linear files, and isolated search bars. 

When onboarding onto a new codebase, identifying technical debt, or planning a major refactor, spatial context is everything. **CodeMap** solves this by physically mapping codebases into explorable visual systems. It identifies architectural hotspots, highlights high-risk dependencies, and reveals the true structure of the software at a glance.

---

## ✨ Features

- **GitHub Repository Analysis**: Ingest any public GitHub repository instantly via URL.
- **Interactive Dependency Graph**: Explore a living, physics-based network visualization of your codebase.
- **Function & Module Mapping**: Toggle seamlessly between granular symbol-level graphs and macro module-level topologies.
- **Hotspot Detection**: Automatically surface the most complex and heavily relied-upon components.
- **Complexity Analysis**: Evaluate nodes based on cyclomatic complexity and abstract syntax tree characteristics.
- **Fan-In / Fan-Out Metrics**: Immediately visualize data flow and dependency density.
- **Dependency Risk Insights**: Identify central failure points and structural bottlenecks.
- **Repository Architecture Exploration**: Read the map, build spatial memory, and navigate architecture efficiently.

---

## 🏗 Architecture Pipeline

CodeMap executes a rigorous pipeline to transform static code into an interactive topology:

```mermaid
graph LR
    A[Repository URL] --> B[Ingestion & Cloning]
    B --> C[Static Analysis]
    C --> D[Graph Construction]
    D --> E[Hotspot Detection]
    E --> F[Visualization]
    
    style A fill:#1e293b,stroke:#334155,color:#f8fafc
    style B fill:#0ea5e9,stroke:#0284c7,color:#ffffff
    style C fill:#0ea5e9,stroke:#0284c7,color:#ffffff
    style D fill:#0ea5e9,stroke:#0284c7,color:#ffffff
    style E fill:#0ea5e9,stroke:#0284c7,color:#ffffff
    style F fill:#10b981,stroke:#059669,color:#ffffff
```

---

## 💻 Tech Stack

**Frontend**
- **React 18** (Vite)
- **TypeScript**
- **Framer Motion** (Cinematic UI state transitions)
- **Force Graph & D3** (Physics-based visualization)
- **Tailwind CSS** (Design system)

**Backend**
- **Python 3.11**
- **FastAPI** (High-performance async API)
- **AST Parsing** (Language-specific symbol extraction)

**Infrastructure**
- **Vercel** (Frontend edge network)
- **Railway** (Backend compute)

---

## 🚀 Getting Started

### Prerequisites
- Node.js 18+
- Python 3.11+
- Git

### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI server
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd web

# Install dependencies
npm install

# Run the development server
npm run dev
```

### Environment Variables

Create a `.env` file in the `web` directory to point the frontend to the correct API endpoint:

```env
VITE_API_URL=http://localhost:8000
```

---

## 🧭 Example Workflow

1. **Paste GitHub URL**: Enter a repository link on the CodeMap landing page.
2. **Scan Repository**: The backend securely clones and statically analyzes the codebase.
3. **Build Graph**: Data is synthesized into nodes and directional edges.
4. **Explore Hotspots**: Use the sidebar to immediately identify the most complex functions.
5. **Inspect Dependencies**: Click any node to open the inspector panel and view fan-in/fan-out metrics.
6. **Understand Architecture**: Toggle to Module View to see the macro-structure of the application.

---

## 🗺 Future Roadmap

- [ ] **Multi-Language Support**: Extend static analysis beyond Python to JavaScript/TypeScript.
- [ ] **Global Search**: Instantly locate specific symbols and modules within the graph.
- [ ] **Graph Export**: Download architecture maps as high-resolution SVGs or JSON data.
- [ ] **AI Summaries**: Integrate LLMs to auto-generate structural summaries of complex modules.
- [ ] **Team Collaboration**: Shared workspaces and saved architectural views.

---

## 🤝 Contributing

Contributions are welcome. CodeMap is maintained as an open-source project. If you wish to contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 🖋 Author

**Created by Purrnanssh Sinha**  
[GitHub Profile](https://github.com/Purrnanssh)

<br>

<div align="center">
  <sub>Built with precision for the modern software engineer.</sub>
</div>
