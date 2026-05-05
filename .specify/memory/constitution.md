<!--
SYNC IMPACT REPORT
==================
Version change: (none) → 1.0.0
Bump rationale: MAJOR — initial ratification of the Imagineer constitution for
the project at 8_Practical_Code/3. The .specify/ tree did not previously exist;
this commit creates it and codifies the rules already authored in
.claude/CLAUDE.md and .claude/rules/*.md as binding governance.

Source materials (verbatim authority for the principles below):
  - .claude/CLAUDE.md — the five-step Understand → Plan → Implement → Test →
    Report workflow.
  - .claude/rules/01-project-config.md — Imagineer = React/Vite web + FastAPI
    Python API, sibling folders web/ and api/, optional SQLite, ./logs/.
  - .claude/rules/02-understand.md — read code, reproduce bugs before fixing.
  - .claude/rules/03-plan.md — plan + user approval; trivial changes excepted.
  - .claude/rules/05-implement.md — clean-as-you-go; no git commit without
    explicit instruction; mermaid for diagrams; stack-specific rules.
  - .claude/rules/06-testing.md — DoD checklist; test-chrome MCP for UI; curl
    for API; truncated logs at ./logs/; diagnostic order.
  - .claude/rules/08-report.md — what was implemented, what was tested with
    evidence, doc-update status.
  - .claude/rules/09-code-quality.md — KISS, DRY, YAGNI, SOLID; <20-line
    functions ideal, <100 max; fail fast; no TODOs; no commented-out code.
  - .claude/rules/10-tech-stack.md — concrete stack constraints for web/, api/,
    DB, testing, scripting.
  - .claude/rules/11-communication.md — direct technical tone, "why" over
    "what", explicit tradeoffs.

Modified principles: (none — initial ratification)
Added sections:
  - Core Principles I–V
  - Technology Stack Constraints
  - Development Workflow & Quality Gates
  - Governance

Templates requiring updates:
  - ✅ .specify/templates/constitution-template.md — copied from sibling project
    8_Practical_Code/2 to seed future amendments via /speckit-constitution.
  - ⚠ .specify/templates/plan-template.md — not present; create when the first
    /speckit-plan run is performed (Constitution Check section will reference
    this file by relative path).
  - ⚠ .specify/templates/spec-template.md — not present; create alongside
    plan-template.md.
  - ⚠ .specify/templates/tasks-template.md — not present; create alongside the
    plan/spec templates.
  - ✅ .claude/CLAUDE.md, .claude/rules/*.md — already consistent (this
    constitution is derived from them; keep them in sync on every amendment).

Deferred / TODO:
  - TODO(SPECKIT_TEMPLATES): seed .specify/templates/{plan,spec,tasks}-template.md
    on the first feature spec; the constitution does not block their absence
    until /speckit-plan is invoked.
-->

# Imagineer Constitution

## Core Principles

### I. Workflow Discipline (NON-NEGOTIABLE)

Every prompt that produces a code change MUST follow the five-step workflow in
order: **Understand → Plan → Implement → Test → Report**. Steps MUST NOT be
skipped or reordered. The Plan step MAY be skipped only for trivial changes
(typo, one-line fix, config tweak), and only after the agent explicitly states
what it will do before proceeding. For bug reports the Understand step MUST
include reproducing the issue (via the test-chrome MCP, `./logs/web.log`,
`./logs/api.log`, or `curl`) before any fix is attempted.

**Rationale**: The web frontend and FastAPI backend are independent processes
with their own dev servers, dependency managers, and log files. Ad-hoc edits
without a planning step produce regressions across the React↔FastAPI boundary
that are expensive to diagnose. Process discipline is cheaper than debugging.

### II. Test Before Report (NON-NEGOTIABLE)

No change MAY be reported as complete without prior runtime verification. The
agent MUST write a Definition of Done checklist into the conversation before
the Test step begins, then exercise the change end-to-end:

- **UI / frontend changes** MUST be verified through the `test-chrome` MCP
  against `http://localhost:5173`, with `mcp__test-chrome__list_console_messages`
  inspected for unexpected errors before declaring success.
- **API changes** MUST be verified by hitting the endpoint with `curl` (or
  `fetch` via `mcp__test-chrome__evaluate_script`) and confirming response
  shape, status code, and headers.
- **Full-stack changes** MUST satisfy both checks above.
- **Non-testable changes** (docs, config, build scripts) MUST state explicitly
  why no runtime test applies.

If the agent cannot verify the change at runtime, it MUST say so out loud
rather than claim success. The user is never the agent's QA.

**Rationale**: TypeScript and Pydantic verify code correctness, not feature
correctness. "Looks right" changes have repeatedly broken at runtime in this
project family. Self-verification is the agent's responsibility.

### III. Simplicity & YAGNI

Code MUST favor the simplest design that satisfies current requirements.
Speculative abstractions, unused indirection, and forward-compatibility
scaffolds are forbidden. Functions SHOULD remain under 20 lines and MUST stay
under 100. Names MUST be self-documenting; comments explain *why*, never
*what*. Errors MUST fail fast and explicitly with typed exceptions and clear
messages; silent catches and generic 200-with-error-body shapes are forbidden.
Inputs MUST be validated at system boundaries (FastAPI route signatures via
Pydantic, fetch wrappers, file I/O), not redundantly in internal helpers.

`TODO` comments are forbidden — open work goes into spec-kit task files or
GitHub issues, never code. Commented-out "just in case" code MUST be deleted.
Premature optimization MUST be avoided; compiler/linter warnings MUST NOT be
ignored.

**Rationale**: A two-layer (web/api) project with optional SQLite already
carries enough surface for divergence. Every additional abstraction multiplies
the places where the frontend, backend, and DB schema can drift apart.

### IV. Continuous Cleanliness

Code MUST be cleaned as it is written, not "later". Dead code (unused
functions, variables, imports, types, commented-out blocks) MUST be removed in
the same change that orphans it. Refactor improvements MUST be applied
immediately when an issue is observed, not deferred. After writing code, the
agent MUST review comments, prune imports, and check for unintended side
effects before moving to the Test step.

Diagrams MUST be authored in mermaid. The agent MUST NOT run `git commit`,
`git push`, or any destructive git command unless the user explicitly
instructs it. This applies even when the change appears complete and the user
seems likely to approve — commit semantics belong to the user.

**Rationale**: Sloppy code rot compounds with the operational surface (two dev
servers, two log files, optional DB) and makes the diagnostic loop unreliable.
The git prohibition exists because the user maintains commit history
deliberately.

### V. Self-Contained Stacks

`web/` and `api/` are sibling folders at the repo root and MUST remain
self-contained projects. Each owns its own dependency manifest (`package.json`
for `web/`, `pyproject.toml` for `api/`), its own dependencies, and its own
dev server. Workspace tooling (npm/pnpm/yarn workspaces, monorepo build
graphs) MUST NOT be introduced. Cross-folder imports are forbidden — the only
contract between the two is the HTTP API.

The frontend MUST stay on React 18 + TypeScript (strict mode) + Vite +
Tailwind + shadcn/ui + `lucide-react`. State management MUST be local
component state (`useState`/`useReducer`); Redux, Zustand, MobX, and
equivalent global stores are forbidden. shadcn/ui components MUST be added via
the shadcn CLI into `web/src/components/ui/` and MUST NOT be pulled from a
node_module. Routing MUST NOT be introduced unless explicitly requested.

The backend MUST stay on Python 3.12+ + FastAPI + Pydantic v2, with `uv` as
the only environment/package manager. The system `python` and `pip` MUST NOT
be invoked directly; every command runs through `uv` (`uv sync`, `uv run`,
`uv add`). Settings MUST be loaded via `pydantic-settings` from `api/.env`.
CORS MUST allow `http://localhost:5173` for local dev. Untyped dicts MUST NOT
cross the API boundary.

Persistence is OPTIONAL. When introduced, it MUST be a single SQLite file at
`api/imagineer.db` (gitignored), accessed via `sqlite3` stdlib for trivial
work or SQLAlchemy 2.x once the model count grows. The schema MUST be
initialized on app startup; a migration tool MUST NOT be added until the
schema starts churning. Populated DB files MUST NOT be committed.

**Rationale**: The two-folder architecture is the entire reason this project
is approachable. Workspace tooling, framework switches, or mixing global
state libraries would erase that property and force every new contributor to
relearn the build graph.

## Technology Stack Constraints

The constraints in Principle V are authoritative. The list below is the
condensed reference and MUST stay in sync with `.claude/rules/10-tech-stack.md`
and `.claude/rules/05-implement.md`:

- **Web (`web/`)**: React 18, TypeScript strict, Vite (dev port 5173),
  Tailwind, shadcn/ui (components copied via CLI into
  `web/src/components/ui/`), `lucide-react` icons, native `fetch` with base
  URL via `VITE_API_BASE_URL`. No router. No global state libraries. No
  separate component CSS files. No CSS framework other than Tailwind. `any`
  is forbidden unless documented inline with the specific reason.
- **API (`api/`)**: Python 3.12+, FastAPI, Pydantic v2, `uvicorn --reload`
  (dev port 8000), `uv` for everything. Routers grouped by feature in
  `api/app/routers/` and registered on the FastAPI app in `api/app/main.py`.
  Settings via `pydantic-settings` from `api/.env`. CORS for
  `http://localhost:5173`.
- **Database (when needed)**: SQLite single file at `api/imagineer.db`
  (gitignored). `sqlite3` stdlib by default; SQLAlchemy 2.x once warranted.
  Schema initialized on startup.
- **Testing infrastructure**: chrome-devtools MCP (`test-chrome` per
  `.mcp.json`) drives an isolated Chrome instance against the web dev server;
  `curl` for ad-hoc API checks. Unit-test frameworks deferred until requested.
- **Scripting & automation**: TypeScript for web-side scripts, Python via
  `uv run` for API-side scripts. Shell scripts only for trivial one-liners.

Deviations from any item above MUST be justified in a Complexity Tracking
entry on the relevant plan and approved by the user before implementation.

## Development Workflow & Quality Gates

The following rules are universal:

- **Plan approval**: For non-trivial changes, the agent MUST present a plan
  and obtain user approval before writing code. Iteration on the plan is
  preferred over rework on the implementation.
- **Definition of Done**: Each change MUST have an explicit DoD checklist
  written into the conversation before the Test step begins.
- **Reporting**: The Report step MUST state what was implemented, what was
  tested with evidence (screenshots, log excerpts, console output, network
  log), and whether spec/feature documentation was updated or why it was
  skipped.
- **Communication standard**: Responses assume 20+ years of software
  engineering experience. Skip basic explanations unless requested. Be
  direct and technical. Focus on *why* a decision was made, not *what* the
  code does. Highlight tradeoffs and alternatives considered.

### Dev server authority

The agent is authorized to start, stop, and restart the web and API dev
servers. The user MUST NOT be asked to run them. Both servers' stdout/stderr
are captured under `./logs/` (gitignored). The log file MUST be truncated on
every restart so it always reflects the current session.

| File              | Source                                |
|-------------------|---------------------------------------|
| `./logs/web.log`  | `web/` Vite dev server                |
| `./logs/api.log`  | `api/` FastAPI dev server (`uvicorn`) |

After backgrounding a dev server, the agent MUST wait for the readiness line
before issuing MCP commands or HTTP calls:

- `web/` Vite: wait for `ready in` and `Local: http://localhost:5173/` in
  `./logs/web.log` (typical startup 1–3 seconds).
- `api/` FastAPI: wait for `Application startup complete` in `./logs/api.log`,
  then verify with `curl -fs http://localhost:8000/health` (or whichever
  liveness endpoint exists) before driving the UI through it.

If a server fails to start (port collision, import error, syntax error,
missing dep), the agent MUST surface the relevant log lines and ask — looping
on retries is forbidden.

### Diagnostic order

When investigating runtime issues, sources MUST be consulted in escalating
cost order; cheaper sources MUST be exhausted before more expensive ones:

1. **Dev-server logs** — `./logs/web.log` (Vite build / HMR errors) and
   `./logs/api.log` (FastAPI tracebacks). Read with the `Read` tool — do not
   `tail -f`; the files are static snapshots truncated on each restart.
2. **Browser console & network** — `mcp__test-chrome__list_console_messages`
   for renderer errors that never reach `./logs/web.log`, and
   `mcp__test-chrome__list_network_requests` for outgoing fetches and their
   status codes.
3. **Isolated API repro** — `curl -sS -X POST
   http://localhost:8000/api/<endpoint> -H 'Content-Type: application/json'
   -d '{...}' | jq` to localize a bug to either the frontend or the API
   without React in the loop.

### Testing surface

- **UI changes**: navigate via `mcp__test-chrome__navigate_page`, resolve
  element uids with `take_snapshot`, drive with `click` / `fill` /
  `fill_form`, verify with `take_screenshot` and DOM inspection, then check
  `list_console_messages` before declaring success.
- **API changes**: `curl` (or `fetch` via `evaluate_script`); confirm
  response shape, status, and headers. If the change affects UI behavior,
  also verify via the web app.
- **Full-stack**: both of the above.
- **Non-testable**: explicitly state why no runtime test is needed.

If a test fails, the agent MUST fix and retest until all DoD items pass. If a
problem cannot be resolved after repeated attempts, the agent MUST ask the
user for help rather than silently looping.

## Governance

This constitution supersedes all other practices in the repository. In any
conflict between this document and a rule file under `.claude/rules/` or
`.claude/CLAUDE.md`, this document wins, and the conflicting rule MUST be
reconciled or removed in the same change that surfaces the conflict.

**Amendment procedure**: Amendments are proposed by editing
`.specify/memory/constitution.md` via the `/speckit-constitution` flow. Each
amendment MUST include an updated Sync Impact Report at the top of the file
listing modified principles, added/removed sections, and the templates
re-validated. Amendments take effect when the file is committed by the user
(the agent MUST NOT commit on its own — see Principle IV).

**Versioning policy**: Semantic versioning applies to this document.

- **MAJOR** — Backward-incompatible governance changes, principle removal, or
  redefinition that invalidates prior compliance reasoning.
- **MINOR** — New principle or section added, or material expansion of an
  existing principle's scope.
- **PATCH** — Clarifications, wording fixes, typo corrections, or refinements
  that do not change the binding meaning.

**Compliance review**: Every PR/review MUST verify compliance with the
principles above. Any complexity that violates a principle MUST be recorded
in the Complexity Tracking section of the relevant plan with the simpler
alternative and the reason it was rejected. Use `.claude/CLAUDE.md` and the
files under `.claude/rules/` for runtime development guidance; both MUST
remain consistent with this constitution and MUST be updated in the same
change as any amendment that affects them.

**Version**: 1.0.0 | **Ratified**: 2026-05-05 | **Last Amended**: 2026-05-05
