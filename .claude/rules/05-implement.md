---
description: "Step 4: Implement — coding rules, web + API stack"
---

# Step 4: Implement

Write clean code from the start. Follow these rules during implementation:

- Do NOT commit via `git` unless explicitly instructed by the user
- When creating diagrams or graphs, use `mermaid`
- Write clean code from the start — don't plan to "clean it up later"
- Refactor continuously — improve code structure immediately when you see issues
- Remove dead code — delete unused functions, variables, imports, and commented code
- After writing code: review comments, clean up imports, check for side effects

## Web (`web/`)

React 18 + TypeScript + Vite + Tailwind + shadcn/ui — a self-contained npm project.

- Single-page app, no router unless explicitly requested
- Local component state (`useState` / `useReducer`) — no Redux/Zustand
- Tailwind utility classes for styling — no separate CSS files for component styles, no other CSS framework
- shadcn/ui components live under `web/src/components/ui/`. Add them via the shadcn CLI (`npx shadcn@latest add <component>`). Do NOT pull them from a node_module
- Icons via `lucide-react`
- API calls via `fetch` (or a thin wrapper); base URL from `import.meta.env.VITE_API_BASE_URL`
- TypeScript strict mode; no `any` unless there's a specific reason — and document it

## API (`api/`)

FastAPI + Python 3.12+ — a self-contained `uv` project.

- All commands run through `uv` (`uv sync`, `uv run uvicorn ...`, `uv add <pkg>`) — never invoke a system `python` or `pip`
- Pydantic v2 models for every request and response — no untyped dicts crossing the API boundary
- Routers grouped by feature in `api/app/routers/`, registered on the FastAPI app in `api/app/main.py`
- CORS configured to allow the web dev origin (`http://localhost:5173`)
- Settings via `pydantic-settings`, loaded from `api/.env`
- Fail fast on bad input — let Pydantic raise; don't catch and return 200s

## Database (only if needed)

- SQLite file at `api/imagineer.db` (gitignored)
- Schema initialized on app startup; no separate migration tooling unless the schema starts to churn
- Access via `sqlite3` stdlib for trivial work, SQLAlchemy 2.x if the model count grows
- Never commit a populated DB file

## Repository Structure

```
imagineer/
├── .gitignore
├── .mcp.json
├── logs/                    # dev-server logs (gitignored)
├── web/                     # self-contained React app
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── components.json      # shadcn config
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   └── ui/          # shadcn components (copied in via CLI)
│       ├── hooks/
│       └── lib/
└── api/                     # self-contained FastAPI app
    ├── pyproject.toml
    ├── uv.lock
    ├── .env
    └── app/
        ├── main.py          # FastAPI app + router registration
        ├── routers/
        ├── models.py        # Pydantic models
        ├── db.py            # SQLite (when needed)
        └── settings.py
```
