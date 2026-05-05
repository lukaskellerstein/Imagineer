# Phase 0 — Research: Imagineer MVP

**Plan**: [`./plan.md`](./plan.md)
**Spec**: [`./spec.md`](./spec.md)

This document resolves every `NEEDS CLARIFICATION` from the plan's Technical Context. Each entry is a self-contained decision with rationale and the alternatives that were rejected.

---

## R1. GPU concurrency model

**Question**: Hunyuan3D-2.1 needs ~5 GB of weights resident and peaks around 8 GB during inference. The host has 16 GB VRAM. How are concurrent generation requests serialized?

**Decision**: Load the pipeline **once** at FastAPI startup (in the `lifespan` context manager) and keep it resident. Serialize generation calls through a single module-level `asyncio.Lock`. Run the synchronous diffusion call via `asyncio.to_thread(...)` so the event loop stays responsive. Queue position = number of `Lock` waiters at the time the request arrives, surfaced to the client via SSE.

**Rationale**:

- One generation at a time is a hard constraint of the hardware (the script's own peak VRAM measurement at `octree_resolution=256` is comfortably under 16 GB for *one* run; concurrent runs OOM).
- Loading the model per-request would pay 30–60 s of disk + GPU cost on every generation. That blows past NFR-001's 3-minute p50 latency.
- An external job queue (Celery, RQ, Dramatiq) and a separate worker process would solve scale-out we don't need at MVP. It also breaks Constitution V's "self-contained stacks" — adding Redis is a third moving part. Rejected.
- Threading the model itself (so the GPU runs two requests in parallel) is impossible at this VRAM budget. Rejected.

**Alternatives considered**:

- Per-request model load — too slow, rejected.
- Celery + Redis worker — over-engineered for a single-host MVP, rejected.
- `multiprocessing.Pool(processes=1)` — same effect as `asyncio.Lock` but adds IPC overhead and complicates GPU memory ownership. Rejected.

---

## R2. Progress streaming to the browser

**Question**: NFR-001 implies generation can take minutes; FR-013 requires progress feedback. How is progress delivered without polling?

**Decision**: Server-Sent Events (SSE) over `text/event-stream`, served by FastAPI as a `StreamingResponse`. Browser side uses the native `EventSource` API. Events emitted: `queued` (with queue position), `loading_model` (only on the very first request after a cold start), `removing_background`, `generating` (coarse-grained, emitted on a timer since the diffusion pipeline does not expose per-step callbacks cleanly), `running_readiness_check`, `done` (with mesh metadata), `error` (with sanitized reason).

**Rationale**:

- One-way server→client push. WebSockets would add bidirectional plumbing we don't need, plus require a separate library or hand-rolled handshake. Rejected.
- Polling works but requires choosing an interval — too short wastes load, too long looks laggy. SSE is built for "tell me when something changes". Rejected.
- SSE has first-class support in FastAPI via `StreamingResponse(generator(), media_type="text/event-stream")`. No new dependency.
- The browser handles automatic reconnection on transient network blips — useful for long-running generations.

**Alternatives considered**:

- WebSockets (`websockets` lib or FastAPI's built-in) — bidirectional plumbing not needed, rejected.
- Long-poll (`/api/generations/{id}/status` with held-open response) — equivalent in spirit but harder to write correctly. Rejected.
- Plain polling — simplest but worst UX. Rejected unless SSE proves problematic.

---

## R3. Intake content-policy detection

**Question**: FR-003 / FR-004 require automated rejection of disallowed content (people / faces, weapons, copyrighted characters, illegal goods). How much of this is automated in v1?

**Decision**: v1 implements **face detection only**, using OpenCV's pre-trained Haar Cascade (`haarcascade_frontalface_default.xml`). If the detector finds at least one face with high confidence, the upload is rejected with a specific reason. All other policy categories (weapons, copyrighted characters, illegal goods) are handled by a Terms-of-Service acceptance checkbox at upload time and operator review at the quote-handoff step. Document this explicitly in the privacy notice.

**Rationale**:

- OpenCV is already a transitive dependency of the Hunyuan3D requirements pinning (`opencv-python>=4.10`). Zero new deps.
- Face detection is the only policy category with a low-false-negative free-tier model that runs on CPU in milliseconds. Other categories require commercial classifiers (cost), large multi-modal models (latency + dependency), or human review. None of those are MVP-shaped.
- A Terms acceptance checkbox is the standard pattern for shifting subjective-content liability to the customer at intake.
- Operator review at the quote-handoff step is already in scope (per Q3 = A); they are the human-in-the-loop catch.

**Alternatives considered**:

- `mediapipe` face detector — more accurate than Haar but adds ~20 MB of native deps. Rejected.
- A general moderation model (e.g., Falconsai NSFW, OpenAI Moderation API) — cost or extra deps for a category that the operator review already covers. Rejected.
- No automated detection, rely on operator review — fails FR-003's "at intake" requirement. Rejected.

---

## R4. Mesh print-readiness check + repair

**Question**: FR-020 / FR-021 / FR-022 require manifold-edge / isolated-component / wall-thickness checks and an auto-repair attempt. Which library?

**Decision**: Use **`trimesh`** (already a Hunyuan3D requirements pin: `trimesh>=4.4`). Manifold check via `mesh.is_watertight` and `mesh.is_winding_consistent`. Component analysis via `mesh.split()` — if more than one component above a 1% volume threshold, mark as multi-component (not printable). Auto-repair via `mesh.fill_holes()` and `mesh.remove_unreferenced_vertices()`. Wall-thickness is **not** measured analytically in v1 — it requires a slicer-grade thickness pass. Instead, v1 derives a heuristic "thinnest feature ≥ 0.8 mm at the customer's chosen scale" from the bounding box and triangle density. Document this as a known approximation; SC-006 monitors the false-positive rate so we can revisit.

**Rationale**:

- `trimesh` is already imported by the reference script's pipeline export path. Adding nothing.
- True wall-thickness measurement requires either a voxelization pass (slow, memory-hungry) or running an actual slicer (PrusaSlicer / Cura) — both out of scope for v1. The heuristic is conservative (it errs toward calling things printable; SC-006 catches false positives in operator follow-up).
- `pymeshlab` is also available (Hunyuan3D pins it) and offers real wall-thickness — keep this on the table for v2 if SC-006 indicates the heuristic is wrong.

**Alternatives considered**:

- `pymeshlab` thickness filter — accurate but slow on a per-request basis; deferred. Rejected for v1.
- `open3d` — extra dependency not yet in the stack. Rejected.
- Skip the readiness check and rely on the print shop to reject bad meshes — violates FR-020/FR-022 and SC-003. Rejected.

---

## R5. Operator-dashboard authentication & delivery

**Question**: NFR-008 requires the operator dashboard to be auth-gated. Constitution V forbids introducing a router library and Redux/Zustand. How is auth implemented and where does the dashboard live?

**Decision**:

- **Auth**: HTTP Basic Auth via a FastAPI dependency. Single password from `OPERATOR_PASSWORD` in `api/.env`. Apply the dependency to every `/api/operator/*` route. Browser handles the credential prompt and re-sends the header on every subsequent fetch within the session.
- **Dashboard delivery**: Single SPA, two top-level views. `App.tsx` reads `window.location.pathname`; if it starts with `/operator`, render `OperatorView`; else render `CustomerView`. No router library. Vite's default SPA serving (`historyApiFallback`-equivalent in dev, `index.html` for any path in production) means `/operator` returns the same `index.html` and the JS picks the right view.

**Rationale**:

- HTTP Basic Auth is a one-line FastAPI dependency. It avoids a session store, a login page, a CSRF token, and "remember me" complexity. For a single human operator who works the dashboard occasionally, the browser's built-in re-prompt is acceptable UX.
- Reading `window.location.pathname` is not "routing" in the sense the constitution prohibits (which targets multi-route SPA frameworks). It is one if-statement branching the top-level component, with no route data, no `<Route>` components, no link interception. PASS V.
- Two Vite entry points (multi-page mode) was considered — clean separation, but adds a config knob and a second `<script>` tag for negligible benefit at this scale. Rejected.
- Server-side rendered Jinja2 dashboard was considered — minimal JS, but adds a templating engine to `api/` and forces the operator UI to live in two places (the JSON API and the rendered HTML). Rejected.

**Alternatives considered**:

- Cookie session with custom login form — more typical UX but requires a session store, login route, CSRF protection. Over-engineered for one user. Rejected.
- OAuth2 / Keycloak — drastically over-engineered for a single password. Rejected.
- Auth at the reverse-proxy layer (nginx basic-auth) — moves the auth concern to infra config the project doesn't yet have. Rejected for v1.

---

## R6. Email transport for quote confirmation

**Question**: FR-041 requires sending a confirmation email when a quote is submitted. Which transport?

**Decision**: SMTP via Python stdlib `smtplib`, called inside `asyncio.to_thread(...)` so it doesn't block the event loop. Configuration in `api/.env`: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`. For local dev the developer can point at Gmail's SMTP with an app password. For staging/prod, swap to a transactional service (Resend, Mailgun) with the same SMTP envelope — no code change.

**Rationale**:

- One email per quote, low volume. A transactional-email SDK (Resend, SendGrid) would add a dependency and an account that we don't need at v1 volume.
- SMTP gives us provider portability: the same code talks to Gmail in dev, a Czech provider in prod, a transactional service later. No vendor lock-in.
- `aiosmtplib` was considered for native async; `smtplib + asyncio.to_thread` is simpler and the throughput delta is irrelevant at this volume.

**Alternatives considered**:

- `aiosmtplib` — async-native but adds a dependency for negligible benefit. Rejected.
- Resend / SendGrid SDK — extra dependency, vendor lock-in, no benefit at v1. Rejected.
- File-based outbox + cron flush — over-engineered. Rejected.

---

## R7. 3D viewer in the browser

**Question**: FR-030 / NFR-004 require an interactive 3D viewer (orbit/pan/zoom) at ≥ 30 fps for meshes up to 1 M triangles. Three.js, react-three-fiber, or model-viewer?

**Decision**: **`@google/model-viewer`** web component. Drop-in `<model-viewer src="..." camera-controls>` element. Loads GLB via the `<model-viewer>` Custom Element, handles orbit/pan/zoom, loading states, accessibility, and progressive rendering out of the box. Wrap in a tiny React component that maps props to attributes.

**Rationale**:

- Read-only viewer is the *only* thing the spec asks for. `<model-viewer>` is the simplest viable option — no scene graph, no manual lighting setup, no camera math.
- It is built on Three.js under the hood, so future migration to react-three-fiber is mechanical if we ever need fine-grained control.
- Bundle size: ~150 KB gzipped. Acceptable for the MVP. Tree-shaking three.js manually would not save much for what we'd build with r3f.
- Constitution-friendly: it is an npm dep (`@google/model-viewer`), no router, no global state.

**Alternatives considered**:

- `@react-three/fiber` + `@react-three/drei` — flexible but means writing our own viewer (lighting, environment map, orbit controls, GLB loader hookup). Rejected for v1.
- Bare Three.js — even more boilerplate than r3f. Rejected.
- BabylonJS — heavier and unfamiliar; no reason to choose it. Rejected.

---

## R8. File storage layout

**Question**: Where do we put uploaded source images and generated GLB meshes?

**Decision**: On disk under `api/storage/`, gitignored. Subdirectories by date: `api/storage/YYYY/MM/DD/<uuid>.<ext>`. The DB stores the relative path; the storage layer knows how to resolve absolute paths from `Settings.storage_dir`. Files are deleted by a small janitor that runs on app startup (and could be invoked manually) per the retention rules in NFR-007: 24 h for anonymous generations, 90 days after a quote is archived.

**Rationale**:

- Local disk is the simplest persistence for a single-host MVP. No S3, no MinIO, no extra config.
- Date-prefixed directories make manual inspection and bulk cleanup easy. They also avoid millions-of-files-in-one-directory pathologies (irrelevant at MVP scale, free at no cost).
- Storing blobs in SQLite was considered. Source images can be 20 MB; SQLite BLOB performance and `vacuum` cost get unpleasant fast. Rejected.
- Cloud object storage (S3) was considered. Adds infra, credentials, a SDK. Defer.

**Alternatives considered**:

- Source images and meshes as SQLite BLOBs — rejected (size, vacuum cost).
- S3 / MinIO — rejected (infra).
- Single flat dir with UUIDs — works but harder to manage by hand. Rejected.

---

## R9. Hunyuan3D-2.1 vendoring strategy

**Question**: The reference script uses `sys.path.insert(0, str(REPO_ROOT / "vendor" / "Hunyuan3D-2.1" / "hy3dshape"))` to import the pipeline directly from a vendored source tree (the upstream repo isn't pip-installable as a single package). How does the API project consume it?

**Decision**: Vendor the upstream repo at `api/vendor/Hunyuan3D-2.1/`. The clone command is in `quickstart.md` and is **not** committed to git (the directory is gitignored — Hunyuan3D is ~3 GB of code + assets and has its own license tree we shouldn't redistribute). The `pipeline.py` module performs the same `sys.path.insert(0, ...)` the reference script does, isolated to one place. Pin the upstream repo to a specific commit hash for reproducibility (recorded in `api/vendor/HUNYUAN3D_COMMIT.txt`).

**Rationale**:

- Matches what already works in the reference script. No surprises.
- Vendoring (vs. submodule) keeps the repo cloneable without `git submodule update --init`. The pinned commit hash in a text file gives us reproducibility.
- The model **weights** download to `~/.cache/huggingface/` on first use — handled by `from_pretrained("tencent/Hunyuan3D-2.1")`. We don't need to vendor weights.
- If a stable PyPI package appears later, swapping is a one-file change.

**Alternatives considered**:

- Git submodule — works but every contributor pays the submodule init dance. Rejected.
- `pip install git+https://...` — the upstream `pyproject.toml` doesn't expose `hy3dshape` as a top-level package. Rejected.
- Forking and packaging ourselves — not worth the maintenance burden. Rejected.

---

## R10. Settings & secrets layout

**Question**: Constitution V mandates `pydantic-settings` from `api/.env`. What goes in there for this feature?

**Decision**: One `Settings` class. Required fields:

- `STORAGE_DIR: Path` — defaults to `api/storage/`
- `OPERATOR_PASSWORD: SecretStr` — required, no default
- `SMTP_HOST: str`
- `SMTP_PORT: int = 587`
- `SMTP_USER: str`
- `SMTP_PASSWORD: SecretStr`
- `SMTP_FROM: str`
- `HUNYUAN3D_VENDOR_DIR: Path` — defaults to `api/vendor/Hunyuan3D-2.1/hy3dshape`
- `HUNYUAN3D_OCTREE_RESOLUTION: int = 256`
- `HUNYUAN3D_STEPS: int = 30`
- `HUNYUAN3D_GUIDANCE: float = 5.0`
- `RETENTION_ANONYMOUS_HOURS: int = 24`
- `RETENTION_ARCHIVED_DAYS: int = 90`

Provide an `api/.env.example` checked into git. The real `api/.env` is gitignored.

**Rationale**: Centralises all environment-specific config. `pydantic-settings` validates types at startup (fails fast — Constitution III). Secrets via `SecretStr` so they don't accidentally show up in logs.

**Alternatives considered**: None — this is the constitution-mandated approach.

---

## Open items intentionally left for `/speckit.tasks`

These are *task-level* decisions, not research questions, so they belong in the next phase:

- Exact file paths under `api/app/routers/` per endpoint group.
- Exact Pydantic model names.
- Specific shadcn/ui components to add (Button, Input, Card, Dialog, Toast — TBD as the UI is built).
- Janitor scheduling: ad-hoc on startup vs. an APScheduler-style timer. Default to startup-only in v1; revisit if data piles up.
