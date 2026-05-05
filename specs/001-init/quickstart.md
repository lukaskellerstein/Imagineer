# Quickstart — Imagineer MVP local dev

**Plan**: [`./plan.md`](./plan.md)
**Audience**: a new contributor (or future-you) bringing the project up from a fresh clone, on a Linux box with a 16 GB-class CUDA GPU.

This is the **minimum viable path**: vendor the AI model, install both stacks, configure secrets, run both dev servers, exercise the upload-to-preview flow, then exercise the operator dashboard.

## Prerequisites

- Linux (CUDA-capable). Reference: RTX 4060 Ti, 16 GB VRAM.
- NVIDIA driver supporting CUDA 12.4+ (matches the Hunyuan3D `pyproject.toml` pin).
- Python 3.12+ available on `$PATH` (used only to bootstrap `uv`).
- [`uv`](https://docs.astral.sh/uv/) ≥ 0.5 — `curl -LsSf https://astral.sh/uv/install.sh | sh`.
- Node.js 20+ and `npm` ≥ 10.
- Disk: ~5 GB for Hunyuan3D weights (downloaded to `~/.cache/huggingface/`), ~3 GB for the vendored repo, plus `api/storage/` for uploads/meshes.

## 1. Clone the repo

```sh
git clone <imagineer-remote> imagineer
cd imagineer
```

## 2. Vendor Hunyuan3D-2.1 into `api/`

The upstream repo is not pip-installable as a single package — see [`research.md`](./research.md) §R9. Vendor it instead. The vendor directory is gitignored.

```sh
mkdir -p api/vendor
git clone https://github.com/Tencent/Hunyuan3D-2.1 api/vendor/Hunyuan3D-2.1
git -C api/vendor/Hunyuan3D-2.1 rev-parse HEAD > api/vendor/HUNYUAN3D_COMMIT.txt
```

`api/vendor/HUNYUAN3D_COMMIT.txt` pins the version we tested against. If anyone updates the vendored tree, they MUST update this file in the same change.

## 3. Bring up the API

```sh
cd api
cp .env.example .env
# Edit api/.env and set: OPERATOR_PASSWORD, SMTP_*, SMTP_FROM
uv sync
```

The first `uv sync` will install Torch/CUDA wheels (~3 GB), `rembg` and its ONNX models (~200 MB), and `trimesh`. Allow ~5 minutes on a fast connection.

Start the dev server (per Constitution V):

```sh
mkdir -p ../logs
uv run uvicorn app.main:app --reload --port 8000 > ../logs/api.log 2>&1 &
```

Wait for `Application startup complete` in `../logs/api.log` (the lifespan loads the Hunyuan3D pipeline; expect 30–60 s on the very first run while weights download).

Smoke-check:

```sh
curl -fs http://localhost:8000/health | jq
```

Expected: `{ "ok": true, "model_loaded": true, "gpu": {...} }`.

## 4. Bring up the web app

```sh
cd web
npm install
echo "VITE_API_BASE_URL=http://localhost:8000" > .env.local
npm run dev > ../logs/web.log 2>&1 &
```

Wait for `ready in` and `Local: http://localhost:5173/` in `../logs/web.log` (typical 1–3 seconds).

## 5. Exercise the customer flow

Pick a reference image — `subaru_impreza.png` from the original test repo is fine, or any clean photo with a clearly-isolated subject.

In a browser at `http://localhost:5173`:

1. Upload the image, accept the terms, click **Generate**.
2. Watch the SSE-driven progress: `queued` → `removing_background` → `generating` → `running_readiness_check` → `done`.
3. The 3D viewer (`@google/model-viewer`) loads the GLB. Orbit / pan / zoom should work.
4. The readiness verdict appears below the viewer (`printable`, `auto_repaired`, or `not_printable`).
5. Click **Download** — verify the GLB downloads. Open it in a slicer if available.
6. (If verdict is `printable` or `auto_repaired`) Click **Request a quote**, fill the form (use a real email you can check), submit. You should receive the confirmation email within ~10 s.

If anything fails: read `../logs/api.log` first (per the constitution's diagnostic order — §"Diagnostic order"), then check the browser console via the `test-chrome` MCP.

## 6. Exercise the operator dashboard

In a browser at `http://localhost:5173/operator`:

1. The browser prompts for HTTP Basic Auth credentials. Username: `operator`. Password: whatever is in `api/.env` `OPERATOR_PASSWORD`.
2. The dashboard lists `new` quotes. Click one.
3. Verify you can preview the source image, download the GLB, and read the customer's form.
4. Click **Mark responded**. The quote moves out of the `new` filter; it is still findable under `responded`.

## 7. Reset & start over

To wipe local state:

```sh
rm -f api/imagineer.db
rm -rf api/storage/*
```

The schema is recreated on the next `uvicorn` startup (per Constitution V — schema initialized on startup, no migration tool).

To clear cached weights (rare — only useful if a Hunyuan3D update breaks things):

```sh
rm -rf ~/.cache/huggingface/hub/models--tencent--Hunyuan3D-2.1
```

## Common failure modes

| Symptom | First place to look |
|---------|---------------------|
| `uv run uvicorn` exits during startup with `CUDA not available` | `nvidia-smi` — driver not loaded, or `CUDA_VISIBLE_DEVICES` is masking the GPU |
| `Application startup complete` never appears | `logs/api.log` for a `from_pretrained` failure (network or HF cache permission issues) |
| Model loads but generation hangs | `nvidia-smi` while a job is running — check VRAM is filling; if not, the asyncio.Lock is held by a prior crashed task. Restart `uvicorn`. |
| Web app shows "Network Error" on upload | `logs/api.log` first; then `mcp__test-chrome__list_network_requests` to see the actual response status |
| 3D viewer is blank but no console error | The GLB download succeeded but `model-viewer` couldn't parse it — open the file in `glTF Viewer` (online) to confirm it's valid |
| Confirmation email never arrives | `logs/api.log` for SMTP errors; check `SMTP_PASSWORD` / app-password if Gmail; confirm the `From:` address matches an authenticated mailbox |

## What this quickstart does NOT cover

- Production deployment (out of scope for v1; one-host single-operator).
- Choosing a Czech print shop (Q3 = A — manual handoff; the operator does this off-platform).
- Adding new shadcn/ui components (`npx shadcn@latest add <component>` from `web/`; the constitution requires the CLI, not a node_module dep).
