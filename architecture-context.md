# Architecture Context & Tech Stack

## 🛠️ Tech Stack
- **Frontend:** Next.js / React / Tailwind CSS (Clean, dark-themed, responsive dashboard)
- **Backend / Logic:** Python (FastAPI) == housing the core algorithm
- **Data Layer:** SQLite / JSON fixtures (fully reproducible offline)

## 📁 Directory Structure
/project-root
├── /backend            # Core algorithms, data models, validation logic
│   ├── engine.py       # Main computational logic (Dijkstra, CVRP, CSP, LP, etc.)
│   ├── simulator.py    # Scenario generation & data handlers
│   └── main.py         # API endpoints
├── /frontend           # Next.js / React UI components
│   ├── /components     # Reusable UI elements, maps, charts, loaders
│   └── /app            # Pages and routing
├── README.md           # Required submission documentation[span_23](start_span)[span_23](end_span)[span_24](start_span)[span_24](end_span)
├── AI_USAGE.md         # Required AI disclosure log[span_25](start_span)[span_25](end_span)
└── progress-tracker.md # Live scoreboard
