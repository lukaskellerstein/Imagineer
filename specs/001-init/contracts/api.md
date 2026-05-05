# Phase 1 — HTTP Contract: web ⇄ api

**Plan**: [`../plan.md`](../plan.md)
**Data model**: [`../data-model.md`](../data-model.md)
**Base URL** (dev): `http://localhost:8000`
**Frontend env var**: `VITE_API_BASE_URL`
**CORS**: `http://localhost:5173` (dev) — Constitution V

This is the **only** contract between `web/` and `api/`. Changes here MUST update both sides in the same change (Constitution V — cross-folder imports forbidden, the HTTP API is the contract).

## Conventions

- All JSON request and response bodies are Pydantic v2 models on the API side and typed-fetch wrappers on the web side. Untyped dicts MUST NOT cross the boundary (Constitution V).
- All ids are UUIDv4 strings.
- All timestamps are ISO-8601 UTC strings (e.g., `2026-05-05T14:32:01.123456+00:00`).
- All error responses are `{ "detail": "<sanitized message>" }` per FastAPI convention. NFR-005: no tracebacks in `detail`.
- Multipart endpoints use `multipart/form-data`. JSON endpoints use `application/json`.

## Authentication

Customer-facing routes are anonymous in v1. Operator routes require **HTTP Basic Auth**:

- Realm: `Imagineer Operator`.
- Username: `operator` (constant).
- Password: from `Settings.OPERATOR_PASSWORD` (`api/.env`).
- Browser handles the auth prompt; subsequent fetches reuse the cached credentials.

A FastAPI dependency `require_operator` is applied to every `/api/operator/*` route.

---

## Customer-facing endpoints

### `POST /api/generations` — start a generation

Submit a source image. Validation runs synchronously; if it passes, the job is enqueued and the route returns immediately with the job id.

**Request**: `multipart/form-data`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `image` | file (PNG / JPEG / WebP) | yes | Max 20 MB, max 4096×4096 px (NFR-002) |
| `seed` | int | no (default random) | Reproducibility for regeneration (FR-015) |
| `accept_terms` | bool | yes (must be `true`) | Required acceptance of the content policy (R3) |

**Validation** (synchronous, before enqueue):

1. File size ≤ 20 MB → else `413 Payload Too Large`.
2. Content-type one of allowed → else `415 Unsupported Media Type`.
3. `accept_terms=true` → else `422 Unprocessable Entity`.
4. Decode image → else `400 Bad Request` "image could not be decoded".
5. Downscale if either dimension > 4096 px (silent, NFR-002).
6. Face detection (R3) → if any face detected: `422 Unprocessable Entity` with `detail: "We can't generate models of people in this version."`.
7. Foreground-subject detectability check (rembg pre-pass, low-confidence threshold) → if subject not detectable: `422 Unprocessable Entity` with actionable tip.

**Response** `202 Accepted`:

```json
{
  "id": "6f3d7c4a-...-...",
  "status": "queued",
  "queue_position": 0
}
```

`queue_position` is the number of waiters currently ahead of this job on the GPU lock (R1). `0` means "running now or starting immediately".

**Errors**:

| Code | When |
|------|------|
| 400 | Image cannot be decoded |
| 413 | File too large |
| 415 | Content-type not allowed |
| 422 | Terms not accepted, face detected, or subject not detectable |

---

### `GET /api/generations/{id}/events` — SSE progress stream

Server-Sent Events. The browser opens this with `new EventSource(...)` after `POST /api/generations` returns, and the server pushes events as the pipeline progresses.

**Response**: `text/event-stream`

Event types (each is one `event:` + `data:` JSON line):

| Event | Data shape | Emitted when |
|-------|-----------|--------------|
| `queued` | `{ "queue_position": int }` | Job is queued; emitted periodically while waiting |
| `loading_model` | `{}` | First-ever generation after a cold start (rare) |
| `removing_background` | `{}` | rembg pass starts |
| `generating` | `{ "elapsed_ms": int, "estimated_total_ms": int }` | Periodically during diffusion (R2 — coarse-grained) |
| `running_readiness_check` | `{}` | trimesh check + repair pass starts |
| `done` | `{ "mesh": MeshSummary }` | Job succeeded; see `MeshSummary` below |
| `error` | `{ "reason": str }` | Job failed; sanitized reason only |

The stream MUST close with `done` or `error`. The browser's automatic `EventSource` reconnect is acceptable — on reconnect we re-emit the latest known state.

**`MeshSummary`** (also returned by other endpoints):

```json
{
  "id": "uuid",
  "generation_job_id": "uuid",
  "triangle_count": 87432,
  "bbox_mm": { "x": 67.5, "y": 42.1, "z": 23.0 },
  "readiness": {
    "verdict": "auto_repaired",
    "repairs": [
      { "operation": "fill_holes", "count": 3 },
      { "operation": "remove_unreferenced_vertices", "count": 12 }
    ]
  },
  "download_url": "/api/generations/{generation_job_id}/mesh"
}
```

**Errors**:

| Code | When |
|------|------|
| 404 | Generation id not found |
| 410 | Generation expired (retention janitor cleared it, NFR-007) |

---

### `GET /api/generations/{id}` — current state (polling fallback)

For browsers without `EventSource` and for re-load on a backgrounded tab. Returns the *current* status and (if done) the `MeshSummary`.

**Response** `200 OK`:

```json
{
  "id": "uuid",
  "status": "queued" | "running" | "success" | "error",
  "queue_position": 0,
  "mesh": MeshSummary | null,
  "error": null | { "reason": "string" }
}
```

---

### `GET /api/generations/{id}/mesh` — download GLB

**Response** `200 OK`:
- `Content-Type: model/gltf-binary`
- `Content-Disposition: attachment; filename="imagineer-{shortid}.glb"`
- Body: GLB binary

Available regardless of readiness verdict (FR-032).

**Errors**:

| Code | When |
|------|------|
| 404 | Generation id not found, or status != `success` |
| 410 | Mesh expired (retention) |

---

### `POST /api/quotes` — submit a quote request

Promotes an anonymous successful generation into a Quote (R8 / data-model.md retention).

**Request** `application/json`:

```json
{
  "generation_job_id": "uuid",
  "email": "user@example.com",
  "name": "optional",
  "message": "optional, max 2000 chars",
  "preferred_material": "optional, max 200 chars",
  "preferred_scale": "optional, max 200 chars"
}
```

**Validation**:

1. `generation_job_id` exists, `status='success'`, has a linked mesh → else `404` or `409`.
2. The linked mesh's `readiness.verdict` is `printable` or `auto_repaired` → else `422 Unprocessable Entity` with `detail: "This mesh is not printable; we can't quote it."` (FR-033).
3. `email` is a valid email per Pydantic `EmailStr` → else `422`.
4. Length caps on `name`, `message`, `preferred_material`, `preferred_scale`.

**Response** `201 Created`:

```json
{
  "id": "uuid",
  "reference": "IMG-6F3D7C4A",
  "created_at": "2026-05-05T14:32:01.123456+00:00",
  "email_sent": true
}
```

`reference` is a human-friendly form of `id` (first 8 hex chars of the UUID, uppercased, with the `IMG-` prefix). The customer sees it in the confirmation email.

**Side effects**:
- A row is created in `quotes` with `status='new'`.
- A confirmation email is sent (FR-041) via SMTP, in `asyncio.to_thread` so the response is not blocked.
- If the SMTP send fails synchronously, the response still returns `201` with `email_sent: false` and the operator sees the bounce flag (FR-044). The quote is created either way — operators must not lose customer requests because of an outbound mail problem.

---

## Operator endpoints (HTTP Basic Auth)

### `GET /api/operator/quotes` — list quotes

**Query parameters**:

| Name | Type | Default | Notes |
|------|------|---------|-------|
| `status` | one of `new`, `responded`, `archived`, `rejected`, or `all` | `new` | |
| `limit` | int | 50 | Max 200 |
| `offset` | int | 0 | |

**Response** `200 OK`:

```json
{
  "quotes": [
    {
      "id": "uuid",
      "reference": "IMG-6F3D7C4A",
      "created_at": "...",
      "updated_at": "...",
      "email": "user@example.com",
      "name": "...",
      "message": "...",
      "preferred_material": "...",
      "preferred_scale": "...",
      "status": "new",
      "email_bounced": false,
      "mesh": MeshSummary,
      "source_image_url": "/api/operator/quotes/{id}/source-image"
    }
  ],
  "total": 42
}
```

`source_image_url` is a relative path the operator UI uses for an `<img>` preview — the route below.

---

### `PATCH /api/operator/quotes/{id}` — update status

**Request** `application/json`:

```json
{ "status": "responded" | "archived" | "rejected" }
```

Status transitions: see `data-model.md` §"State transitions" for `quotes`. Invalid transitions → `409 Conflict`.

**Response** `200 OK` — the updated `Quote` (same shape as one item in the list above).

---

### `GET /api/operator/quotes/{id}/source-image` — original upload

Auth-gated download of the source image. Same `Content-Type` as the upload.

### `GET /api/operator/quotes/{id}/mesh` — GLB

Auth-gated download of the generated GLB. Identical body to `GET /api/generations/{generation_job_id}/mesh` but auth-gated and tied to the quote (so it survives anonymous-retention deletion).

---

## Health

### `GET /health`

**Response** `200 OK`:

```json
{
  "ok": true,
  "model_loaded": true,
  "gpu": {
    "name": "NVIDIA GeForce RTX 4060 Ti",
    "vram_total_mb": 16380,
    "vram_used_mb": 5121
  }
}
```

`model_loaded` is `true` once the lifespan startup has finished loading the Hunyuan3D pipeline. The constitution's dev-server gate (`uvicorn` startup → `Application startup complete`) waits on this.

---

## Pydantic model names (for cross-reference in `tasks.md`)

These are the names the implementation will use; declared here so `/speckit.tasks` can refer to them.

| Model | Purpose |
|-------|---------|
| `GenerationStartResponse` | `POST /api/generations` 202 |
| `GenerationState` | `GET /api/generations/{id}` 200 |
| `MeshSummary` | `mesh` field shared by multiple responses |
| `QuoteCreate` | `POST /api/quotes` body |
| `QuoteCreateResponse` | `POST /api/quotes` 201 |
| `Quote` | Operator-list item / `PATCH` response |
| `QuoteList` | `GET /api/operator/quotes` 200 |
| `QuoteUpdate` | `PATCH /api/operator/quotes/{id}` body |
| `Health` | `GET /health` 200 |

## TypeScript fetch wrappers

The web app imports a single `lib/api.ts` module exposing typed wrappers:

```ts
postGeneration(image: File, opts: { acceptTerms: true; seed?: number }): Promise<GenerationStartResponse>
streamGenerationEvents(id: string, onEvent: (e: GenerationEvent) => void): () => void  // returns close()
getGeneration(id: string): Promise<GenerationState>
postQuote(body: QuoteCreate): Promise<QuoteCreateResponse>
operator.listQuotes(filter): Promise<QuoteList>
operator.updateQuote(id: string, status: QuoteStatus): Promise<Quote>
```

Types are hand-mirrored from the Pydantic models. (No automatic OpenAPI codegen in v1 — Constitution III rejects that scaffold for three endpoint groups.)

## Failure & timeout policy

- **Generation timeout**: if a job stays in `running` for more than 10 minutes (5× the NFR-001 budget), the worker MUST cancel, set `status='error'`, `error_reason='generation_timeout'`, and release the GPU lock. SSE emits `error`.
- **Cold-start budget**: model load is allowed up to 90 s on the very first request after a server restart. Customers in queue see `loading_model` events.
- **CORS preflight**: `OPTIONS` for the listed routes returns `200` with the standard FastAPI middleware headers.
