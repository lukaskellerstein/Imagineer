---
description: Project configuration — architecture, paths, dev environment
---

# Project Config

- **Project**: Imagineer — web app backed by a Python API
- **Architecture**: React (Vite) frontend + FastAPI Python backend; optional SQLite for persistence
- **Structure**: `web/` and `api/` are sibling folders at the repo root. No workspace tooling — each subfolder is a self-contained project (its own `package.json` / `pyproject.toml`, its own dependencies, its own dev server)
- **Frontend stack**: React 18, TypeScript, Vite, Tailwind, shadcn/ui
- **Backend stack**: Python 3.12+, FastAPI, `uv` for environment and packaging
- **DB**: SQLite, added only when persistence is needed; single file under `api/`, gitignored
- **Logs**: dev-server stdout/stderr is captured under `./logs/` at the repo root (gitignored)
