---
description: "Reference: Technology stack — React + Vite + Tailwind + shadcn/ui (web), FastAPI + uv (API), SQLite (optional)"
---

# Reference: Technology Stack

## Web (`web/`)

- **Framework**: React 18 with TypeScript (strict mode)
- **Build Tool**: Vite (dev server on port 5173)
- **Styling**: Tailwind CSS — utility-first, no other CSS framework, no separate component CSS files
- **Components**: shadcn/ui — components copied into `web/src/components/ui/` via the shadcn CLI, not a runtime dependency
- **Icons**: `lucide-react`
- **State Management**: Local component state (`useState` / `useReducer`) — no Redux/Zustand
- **HTTP**: native `fetch` (or a thin wrapper) — base URL via `VITE_API_BASE_URL`
- **Routing**: None — single-page app unless explicitly required

## API (`api/`)

- **Framework**: FastAPI on Python 3.12+
- **Package & Env Manager**: `uv` — every command runs through it (`uv sync`, `uv run`, `uv add`); the system `python` / `pip` are never invoked directly
- **Server**: `uvicorn` in dev (with `--reload`), port 8000
- **Validation**: Pydantic v2 — every request/response is a Pydantic model
- **Settings**: `pydantic-settings`, loaded from `api/.env`
- **CORS**: middleware allowing `http://localhost:5173` for local dev

## Database (only when persistence is required)

- **Engine**: SQLite — single file at `api/imagineer.db` (gitignored)
- **Access**: `sqlite3` stdlib for trivial work; SQLAlchemy 2.x once the model count grows
- **Migrations**: schema initialized on startup; introduce a migration tool only if the schema starts churning

## Testing infrastructure

- **UI**: chrome-devtools MCP (`test-chrome` per `.mcp.json`) drives an isolated Chrome instance against the web dev server
- **API**: `curl` for ad-hoc checks; unit tests deferred until the project asks for them

## Scripting & Automation

- Shell scripts only for trivial one-liners
- Otherwise: TypeScript for web-side scripts, Python (`uv run`) for API-side scripts
