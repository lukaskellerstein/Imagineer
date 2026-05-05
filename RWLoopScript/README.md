# RWLoopScript

A standalone Python tool that drives the **Claude Agent SDK** through a
**Ralph-Wiggum loop** over a [spec-kit](https://github.com/github/spec-kit)
feature folder.

## Idea

[Geoffrey Huntley's Ralph-Wiggum loop](https://ghuntley.com/loop/) keeps
calling Claude in a tight while-loop with a fixed prompt — each iteration is
a *fresh context*, which avoids Claude tripping over its own past output.

Spec-kit organises a feature into **user stories**, each with its own set of
**tasks**. The natural marriage:

> One user story → one fresh-context Claude Agent SDK invocation
> (with optional re-iteration *inside* a story until every task in that
> story reports done).

This script does exactly that:

1. A single Claude Agent SDK call with **structured output** parses the spec
   folder into `UserStory[]` (each with its own `Task[]`).
2. The runner iterates the stories in priority order (P1 → P5).
3. For each story, it runs up to `--max-iterations` fresh `query()` calls.
   Each call:
   * uses the spec-kit project root (the directory containing `.specify/`)
     as cwd — auto-detected by walking up from `--spec-folder`,
   * has the project's `.claude/skills/` enabled via `setting_sources`,
   * invokes the `/speckit-implement` skill scoped to that one story,
   * returns a structured `{done, summary, completed_task_ids, blockers}`.
4. As soon as a story returns `done=true`, the loop moves to the next story.

## Install

```sh
cd RWLoopScript
uv sync
```

The Claude Agent SDK shells out to the `claude` CLI. Install Claude Code
once and authenticate it (`claude login`) before running this script.

## Usage

### Parse only — sanity-check the parser

```sh
uv run rw-loop --spec-folder ../specs/001-init --list-only
```

Prints every parsed user story with its tasks and exits without invoking the
implementer.

### Implement one story

```sh
uv run rw-loop \
  --spec-folder ../specs/001-init \
  --story       US1 \
  --max-iterations 3
```

### Implement every story in priority order

```sh
uv run rw-loop \
  --spec-folder ../specs/001-init \
  --max-iterations 5
```

The spec-kit project root (cwd for every Claude Agent SDK call) is
auto-detected by walking up from `--spec-folder` until a `.specify/` folder
is found. Pass `--project-root /path` to override.

### Useful flags

| flag                 | default        | meaning                                                                                                |
| -------------------- | -------------- | ------------------------------------------------------------------------------------------------------ |
| `--project-root`     | auto-detected  | Spec-kit project root (must contain `.specify/`). Used as the agent's cwd.                             |
| `--max-iterations`   | `1`            | How many fresh-context Claude Agent SDK calls to run per story before giving up.                       |
| `--max-turns`        | `200`          | Cap on tool-using turns *inside* a single iteration. `/speckit-implement` is multi-step — keep it big. |
| `--model`            | SDK default    | Override the model (e.g., `claude-opus-4-7`, `claude-sonnet-4-6`).                                     |
| `--permission-mode`  | `acceptEdits`  | Tool-permission mode for the agent. `bypassPermissions` is full YOLO.                                  |
| `--story`            | (all)          | Run a single story id, e.g. `US2`.                                                                     |
| `--list-only`        | `false`        | Just parse + print the spec, then exit.                                                                |

## What the agent is and is not allowed to do

Allowed tools: `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Bash`, `TodoWrite`,
`Skill`, `Task`. (`Skill` is needed to invoke `/speckit-implement`; `Task`
is what the speckit pipeline uses to spin parallel sub-agents.)

Enabled skills (via `setting_sources=['user','project','local']`):
`speckit-implement`, `speckit-tasks`, `speckit-plan`, `speckit-analyze`,
`speckit-checklist`, `speckit-clarify`, `speckit-constitution`,
`speckit-specify`.

The implementer system prompt explicitly forbids `git commit`, `git push`
and any other git-mutating command — the human runs git themselves.

## Project layout

```
RWLoopScript/
├── pyproject.toml
├── README.md
└── src/rw_loop_script/
    ├── __main__.py
    ├── cli.py        # argparse + orchestration
    ├── models.py     # Pydantic models + JSON schemas for structured output
    ├── parser.py     # spec folder → ParsedSpec
    ├── prompts.py    # parser + implementer prompts
    └── loop.py       # fresh-context iteration loop per story
```

## How "clean context" is enforced

The SDK's `query()` is stateless: every call spins up a brand-new session
with no memory of prior calls (see the SDK examples under
`vibe-coding-course/5_Claude_Agent_SDK/python/1_single_agent/`). This script
calls `query()` once per iteration, which is exactly the Ralph-Wiggum
guarantee — the agent cannot poison its own future iterations.
