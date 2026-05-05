# Implementation Plan: Imagineer MVP — From a Picture to a 3D Preview

**Feature Directory**: `specs/001-init/`
**Spec**: [`./spec.md`](./spec.md)
**Created**: 2026-05-05
**Status**: Approved (ready for `/speckit.tasks`)

## Summary

A FastAPI backend in `api/` loads the Hunyuan3D-2.1 shape pipeline once on startup, serializes generation through a single `asyncio.Lock` over the GPU, and streams progress to the browser via Server-Sent Events. A React+Vite SPA in `web/` uploads the source image, renders the resulting GLB with `<model-viewer>`, and lets the customer either download the file or submit a quote-request form that lands in an HTTP-Basic-Auth-gated operator dashboard served as a second view of the same SPA. SQLite (via stdlib `sqlite3`) persists three tables — `generation_jobs`, `meshes`, `quotes` — and source images / meshes live on disk under `api/storage/`. No payment, no shipping, no shop-side API integration: those are all explicit Out-of-Scope items in the spec (Q1 = A).

Deferred to v2 (per spec §"Out of Scope"): text-to-3D, payment, automated print-shop submission, order tracking, customer accounts, multi-shop routing.

## Technical Context

| Area | Choice | Notes |
|------|--------|-------|
| **API language** | Python 3.12+ | Constitution V |
| **API framework** | FastAPI + Pydantic v2 + `uvicorn --reload` (port 8000) | Constitution V |
| **API env/pkg manager** | `uv` only — no system `python` / `pip` | Constitution V |
| **API settings** | `pydantic-settings` from `api/.env` | Constitution V; full schema in [research.md §R10](./research.md#r10-settings--secrets-layout) |
| **AI generator** | Hunyuan3D-2.1 shape pipeline, vendored at `api/vendor/Hunyuan3D-2.1/` | [research.md §R9](./research.md#r9-hunyuan3d-21-vendoring-strategy) |
| **Background removal** | `rembg` (transitive Hunyuan3D dep) | per the reference script |
| **Mesh inspection / repair** | `trimesh` (transitive Hunyuan3D dep) | [research.md §R4](./research.md#r4-mesh-print-readiness-check--repair) |
| **Intake content guard** | OpenCV Haar Cascade face detector + Terms acceptance checkbox | [research.md §R3](./research.md#r3-intake-content-policy-detection) |
| **GPU concurrency** | One asyncio.Lock; pipeline kept resident; generation in `asyncio.to_thread` | [research.md §R1](./research.md#r1-gpu-concurrency-model) |
| **Progress streaming** | Server-Sent Events via FastAPI `StreamingResponse` | [research.md §R2](./research.md#r2-progress-streaming-to-the-browser) |
| **Persistence** | SQLite at `api/imagineer.db` via `sqlite3` stdlib | Constitution V; schema in [data-model.md](./data-model.md) |
| **File storage** | `api/storage/YYYY/MM/DD/<uuid>.<ext>`; gitignored | [research.md §R8](./research.md#r8-file-storage-layout) |
| **Email transport** | SMTP via Python `smtplib` in `asyncio.to_thread` | [research.md §R6](./research.md#r6-email-transport-for-quote-confirmation) |
| **Operator auth** | HTTP Basic Auth, single `OPERATOR_PASSWORD` from `api/.env` | [research.md §R5](./research.md#r5-operator-dashboard-authentication--delivery) |
| **Web language** | TypeScript strict | Constitution V |
| **Web framework** | React 18 + Vite (port 5173) + Tailwind + shadcn/ui + `lucide-react` | Constitution V |
| **3D viewer** | `@google/model-viewer` web component | [research.md §R7](./research.md#r7-3d-viewer-in-the-browser) |
| **Routing** | None. Single SPA. `App.tsx` switches on `window.location.pathname` between `CustomerView` and `OperatorView` | [research.md §R5](./research.md#r5-operator-dashboard-authentication--delivery) |
| **Web state** | `useState` / `useReducer` only | Constitution V |
| **HTTP** | native `fetch`; base URL via `VITE_API_BASE_URL`; typed wrappers in `web/src/lib/api.ts` | Constitution V; shapes in [contracts/api.md](./contracts/api.md) |
| **Testing (UI)** | `test-chrome` MCP at `http://localhost:5173` | Constitution II |
| **Testing (API)** | `curl` and `fetch` via `evaluate_script` | Constitution II |
| **Logs** | `./logs/web.log`, `./logs/api.log`, truncated each restart | Constitution dev-server gate |

No `NEEDS CLARIFICATION` remain — every previously-open question is resolved in [`research.md`](./research.md).

## Constitution Check

Evaluated against `.specify/memory/constitution.md` v1.0.0.

| Principle | Status | How this plan complies |
|-----------|--------|------------------------|
| **I. Workflow Discipline** | PASS | This plan exists; spec was approved before; implementation follows Understand → Plan → Implement → Test → Report. The plan explicitly forbids skipping the Test step. |
| **II. Test Before Report** | PASS | Each phase task in `tasks.md` (next step) will carry a DoD checklist. UI tasks gate on `test-chrome` MCP exercise; API tasks gate on `curl`. The `/health` endpoint provides a deterministic readiness signal for both dev servers. |
| **III. Simplicity & YAGNI** | PASS | Three SQLite tables (no SQLAlchemy yet); stdlib `sqlite3`; stdlib `smtplib`; one `asyncio.Lock` (no Celery/Redis); `<model-viewer>` (no Three.js scene graph); HTTP Basic Auth (no session store, OAuth, or login form); no router lib (`pathname`-based view selection). Every alternative considered and rejected is documented in `research.md`. |
| **IV. Continuous Cleanliness** | PASS | Plan does not introduce TODOs or commented-out scaffolding. Janitor (NFR-007) keeps storage and DB clean automatically. Mermaid diagrams in `data-model.md` per the constitution. No git operations performed by the agent. |
| **V. Self-Contained Stacks** | PASS | `web/` and `api/` remain siblings; no workspace tooling. Frontend stays React 18 + Vite + Tailwind + shadcn/ui + `lucide-react`; only new npm dep is `@google/model-viewer` (non-state, non-routing). Backend stays Python 3.12 + FastAPI + Pydantic v2; only new pip deps beyond the Hunyuan3D set are zero — `opencv-python` is already a Hunyuan3D pin (used here for the Haar Cascade), `rembg` and `trimesh` are already pins. SQLite single file at `api/imagineer.db`. CORS allows `http://localhost:5173`. No global state library. No router. |

**No deviations.** Complexity Tracking section below is empty.

### Constitution post-design re-evaluation

After Phase 1 design (data-model, contracts, quickstart) was complete, I re-evaluated the gates:

- The contract (`contracts/api.md`) introduces no untyped dicts on the API boundary — every request and response has a named Pydantic model. PASS V.
- The data model uses 3 tables, well below the SQLAlchemy threshold ("once the model count grows"). PASS V.
- The operator-view dispatch via `window.location.pathname` is one if-statement; not a routing library. PASS V (per [research.md §R5](./research.md#r5-operator-dashboard-authentication--delivery)).
- The retention janitor is a single function called on app startup, not a scheduler — Constitution III over-engineering check passed.

No regression. PASS overall.

## Project Structure

The tree below shows files this feature adds. Files unrelated to the feature are omitted. Directories already specified in Constitution V's "Repository Structure" are kept identical.

```text
imagineer/
├── .gitignore                                # +api/storage/  +api/imagineer.db  +api/vendor/  +api/.env  +web/.env.local
├── .specify/
│   ├── feature.json                          # already → "specs/001-init"
│   └── templates/
│       └── plan-template.md                  # NEW (this run, seed)
├── specs/001-init/
│   ├── spec.md                               # already approved
│   ├── plan.md                               # this file
│   ├── research.md                           # NEW
│   ├── data-model.md                         # NEW
│   ├── contracts/api.md                      # NEW
│   ├── quickstart.md                         # NEW
│   └── checklists/requirements.md            # already passing
├── api/
│   ├── pyproject.toml                        # +deps: fastapi, pydantic, pydantic-settings, uvicorn, python-multipart, email-validator, torch (cu124), rembg, trimesh, opencv-python (face cascade)
│   ├── uv.lock                               # generated
│   ├── .env                                  # gitignored
│   ├── .env.example                          # NEW — the schema in research.md §R10
│   ├── imagineer.db                          # gitignored, schema-init on startup
│   ├── storage/                              # gitignored
│   ├── vendor/Hunyuan3D-2.1/                 # gitignored, vendored per quickstart §2
│   ├── vendor/HUNYUAN3D_COMMIT.txt           # NEW — pinned commit
│   └── app/
│       ├── main.py                           # NEW — FastAPI app, lifespan (loads pipeline), CORS, router registration
│       ├── settings.py                       # NEW — Settings(BaseSettings)
│       ├── db.py                             # NEW — sqlite3 connection, schema init, retention janitor
│       ├── models.py                         # NEW — Pydantic request/response models named in contracts/api.md
│       ├── storage.py                        # NEW — save/load files in api/storage/, path resolver
│       ├── pipeline.py                       # NEW — Hunyuan3D wrapper, sys.path injection, asyncio.Lock
│       ├── readiness.py                      # NEW — trimesh-based readiness check + auto-repair
│       ├── intake.py                         # NEW — OpenCV face guard + image validation
│       ├── email.py                          # NEW — smtplib helper
│       ├── auth.py                           # NEW — HTTP Basic Auth dependency
│       ├── progress.py                       # NEW — SSE event publisher (per generation_job_id)
│       └── routers/
│           ├── __init__.py
│           ├── health.py                     # GET /health
│           ├── generation.py                 # POST/GET/SSE/download — customer-facing generation
│           ├── quote.py                      # POST /api/quotes
│           └── operator.py                   # operator-only endpoints
└── web/
    ├── package.json                          # +deps: @google/model-viewer
    ├── tsconfig.json                         # already strict
    ├── vite.config.ts                        # already
    ├── tailwind.config.ts                    # already
    ├── components.json                       # shadcn config
    ├── index.html
    ├── .env.local                            # gitignored — VITE_API_BASE_URL
    └── src/
        ├── main.tsx
        ├── App.tsx                           # NEW — pathname dispatch
        ├── views/
        │   ├── CustomerView.tsx              # NEW — upload → preview → download | quote
        │   └── OperatorView.tsx              # NEW — list, details, status updates
        ├── components/
        │   ├── Uploader.tsx                  # NEW — drag-drop + Terms checkbox
        │   ├── PreviewViewer.tsx             # NEW — wraps <model-viewer>
        │   ├── ReadinessBadge.tsx            # NEW
        │   ├── QuoteForm.tsx                 # NEW
        │   ├── OperatorList.tsx              # NEW
        │   ├── OperatorDetail.tsx            # NEW
        │   └── ui/                           # shadcn components added via CLI as needed
        ├── lib/
        │   ├── api.ts                        # NEW — typed fetch wrappers (contracts/api.md §"TypeScript fetch wrappers")
        │   ├── sse.ts                        # NEW — EventSource wrapper, typed events
        │   └── format.ts                     # NEW — small helpers (mm formatting, reference shortcode)
        └── hooks/
            └── useGeneration.ts              # NEW — SSE-driven state machine
```

## Phase 0 — Outline & Research

Output: [`research.md`](./research.md). Ten decisions resolved (R1 GPU concurrency, R2 SSE vs WebSocket, R3 face detection, R4 mesh repair lib, R5 operator auth + delivery, R6 email transport, R7 3D viewer, R8 file storage, R9 Hunyuan3D vendoring, R10 settings schema). Each entry: Decision / Rationale / Alternatives. No `NEEDS CLARIFICATION` markers remain.

## Phase 1 — Design & Contracts

Outputs:

- [`data-model.md`](./data-model.md) — three SQLite tables with full DDL, state-machine diagrams (mermaid), retention rules, and on-disk storage layout.
- [`contracts/api.md`](./contracts/api.md) — six customer-facing endpoints (one of which is the SSE stream), four operator-gated endpoints, the `/health` endpoint, full Pydantic model name registry, the TypeScript fetch-wrapper contract, and the failure/timeout policy.
- [`quickstart.md`](./quickstart.md) — clone → vendor → uv sync → npm install → run both servers → exercise customer flow → exercise operator flow → reset state. Includes a "common failure modes" matrix tied to the constitution's diagnostic order.

### Agent context update

The `update-agent-context.sh claude` script referenced in the speckit-plan skill does not exist in this repo. The constitution is already authoritative, and `.claude/CLAUDE.md` + `.claude/rules/*.md` are kept consistent with it (per the Sync Impact Report at the top of `constitution.md`). No per-feature agent file is needed; the runtime context for `/implement` is the constitution, the plan, the contracts, and the data model — all of which are already in this directory.

## Phase 2 — Task Breakdown (deferred)

`/speckit.tasks` will produce `tasks.md` from this plan plus `data-model.md` and `contracts/api.md`. Tasks will be grouped by phase:

1. **Setup** — initialise `api/pyproject.toml`, `web/package.json`, vendor Hunyuan3D, `.gitignore` updates, `.env.example`.
2. **API foundations** — `settings.py`, `db.py` (schema init), `storage.py`, `models.py`, `auth.py`, `email.py`, `intake.py`, `readiness.py`, `pipeline.py` (with lifespan integration), `progress.py`.
3. **API routers** — `health.py`, `generation.py` (+SSE), `quote.py`, `operator.py`. Each router task carries its own `curl`-based DoD.
4. **Web foundations** — Vite/Tailwind/shadcn config, `App.tsx` pathname dispatch, `lib/api.ts`, `lib/sse.ts`, `hooks/useGeneration.ts`.
5. **Customer view** — `Uploader`, `PreviewViewer`, `ReadinessBadge`, `QuoteForm`, `CustomerView`. Each carries a `test-chrome`-MCP DoD against `localhost:5173`.
6. **Operator view** — `OperatorList`, `OperatorDetail`, `OperatorView`. DoD via `test-chrome` MCP against `localhost:5173/operator` with HTTP Basic credentials.
7. **End-to-end gates** — exercise the full flow per `quickstart.md` §5 and §6; verify SC-001 (upload-to-preview ≤ 10 min p90) on a real reference image; verify the confirmation-email path; verify operator status transitions.
8. **Cleanup** — janitor runs against simulated retention boundaries; logs sanity check; final code-quality sweep per Constitution III/IV.

## Complexity Tracking

(Empty — no constitutional deviations.)
