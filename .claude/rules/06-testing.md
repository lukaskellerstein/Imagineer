---
description: "Step 4: Testing — define DoD, run dev servers, drive the web app via chrome-devtools MCP, fix and repeat until passing"
---

# Step 4: Testing

**Every code change must be tested before reporting completion. No exceptions.**

## 4a. Define your Definition of Done

Before testing, **write out your DoD checklist in the conversation** so the user can see what you intend to verify. Example:

> **Definition of Done for this task:**
> - [ ] The new component renders correctly in the browser
> - [ ] Clicking the button triggers the expected API call
> - [ ] The API returns the expected response and the UI updates

## 4b. MCP Server

One chrome-devtools MCP server is configured in `.mcp.json`:

| MCP Server | Target | Use For |
|---|---|---|
| `test-chrome` | Isolated Chrome instance launched by the MCP (`--isolate` flag) | All UI verification — navigating the web app, snapshotting, clicking, filling forms, reading the console and network log |

Common tools (all prefixed `mcp__test-chrome__`): `navigate_page`, `new_page`, `take_snapshot`, `take_screenshot`, `click`, `fill`, `fill_form`, `evaluate_script`, `list_console_messages`, `list_network_requests`, `wait_for`, `press_key`, `select_page`.

The MCP launches its own browser — there is no separate CDP port to manage. Once the web dev server is up, just `mcp__test-chrome__navigate_page` to `http://localhost:5173`.

## 4c. Dev servers

The web frontend and API backend are independent processes. Both must be running for full-stack tests; UI-only changes need the web server, API-only changes need the API server.

You are authorized to start, stop, and restart both servers yourself. Do not ask the user to run them.

### Logs

All dev-server stdout/stderr is captured under `./logs/` at the repo root. The directory is gitignored. Truncate the log file on every restart so it always reflects the current session.

| File | Source |
|---|---|
| `./logs/web.log` | `web/` Vite dev server |
| `./logs/api.log` | `api/` FastAPI dev server |

### Web dev server

```sh
cd web && npm run dev > ../logs/web.log 2>&1   # run_in_background=true
```

Wait for `ready in` and a `Local: http://localhost:5173/` line in `./logs/web.log` before navigating. Typical startup is 1–3 seconds. **Never** background the script and immediately fire MCP commands; wait for the readiness line.

### API dev server

```sh
cd api && uv run uvicorn app.main:app --reload --port 8000 > ../logs/api.log 2>&1   # run_in_background=true
```

Wait for `Application startup complete` in `./logs/api.log`. Verify with `curl -fs http://localhost:8000/health` (or whichever liveness endpoint exists) before driving the UI through it.

If a server fails to start (port collision, import error, syntax error, missing dep), surface the relevant log lines and ask — don't loop on retries.

## 4d. Test

**UI / frontend changes** — use the `test-chrome` MCP:

1. Ensure the web dev server is running (and the API server too if the change touches API calls).
2. `mcp__test-chrome__navigate_page` to `http://localhost:5173`.
3. `mcp__test-chrome__take_snapshot` to resolve element uids, then drive the change with `click` / `fill` / `fill_form`.
4. Verify with `take_screenshot` and by inspecting the DOM snapshot.
5. Check `mcp__test-chrome__list_console_messages` for unexpected errors before declaring success.

**API changes** (`api/`):

1. Ensure the API server is running.
2. Hit the endpoint with `curl` (or `mcp__test-chrome__evaluate_script` running `fetch(...)`) and verify the response shape, status code, and headers.
3. If the change affects UI behavior, also verify via the web app per the UI section above.

**Full-stack changes**: both of the above.

**Non-testable changes** (docs, config, build scripts): explicitly state why no runtime test is needed.

## 4e. Fix and repeat

If a test fails: fix the issue, then retest. Repeat until all DoD items pass. If you encounter a problem that you repeatedly cannot resolve, ask the user for help.

## 4f. Diagnostics

When something looks wrong, check these sources in order — cheapest first.

### 4f.1 Dev-server logs — `./logs/`

Both files are truncated on every restart, so they always reflect the current session. Read them with the `Read` tool (don't `tail -f` — they're static snapshots).

- **Web app won't load** → `./logs/web.log` for a Vite build error or HMR failure
- **API request 500s** → `./logs/api.log` for the Python traceback (FastAPI logs every unhandled exception)
- **API request 4xx** → check the request body against the FastAPI route signature; Pydantic validation errors include the offending field and reason

### 4f.2 Browser console & network

Renderer-side errors (React render exceptions, unhandled promises, fetch failures) do **not** appear in `./logs/web.log`. Use the MCP:

- `mcp__test-chrome__list_console_messages` — every console entry on the current page
- `mcp__test-chrome__list_network_requests` — outgoing fetches with status codes (the fastest way to answer "did the call even fire?" / "what did the API return?")

### 4f.3 Reproducing API calls outside the app

For an isolated repro of an API issue, hit the endpoint with `curl` directly — same shape the web app would send, no React in the loop:

```bash
curl -sS -X POST http://localhost:8000/api/<endpoint> \
  -H 'Content-Type: application/json' \
  -d '{...}' | jq
```

This is the fastest way to localize a bug to either the frontend or the API.
