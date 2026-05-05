# Implementation Plan: [FEATURE NAME]

**Feature Directory**: [feature-directory-path]
**Spec**: [./spec.md]
**Created**: [DATE]
**Status**: [Draft | Approved | In implementation | Done]

## Summary

One paragraph: what this plan delivers, the headline technical approach, and what is explicitly deferred.

## Technical Context

| Area | Choice | Notes |
|------|--------|-------|
| Languages | [...] | |
| Frameworks | [...] | |
| Persistence | [...] | |
| External services | [...] | |
| Testing | [...] | |

Mark unresolved questions as `NEEDS CLARIFICATION: <question>` and resolve every one in `research.md` (Phase 0).

## Constitution Check

For every principle in `.specify/memory/constitution.md`, state explicitly whether the proposed design complies and how.

| Principle | Status | Notes / link to research.md entry |
|-----------|--------|-----------------------------------|
| I. Workflow Discipline | PASS / FAIL | |
| II. Test Before Report | PASS / FAIL | |
| III. Simplicity & YAGNI | PASS / FAIL | |
| IV. Continuous Cleanliness | PASS / FAIL | |
| V. Self-Contained Stacks | PASS / FAIL | |

If any item is FAIL, record the deviation, the simpler alternative considered, and why it was rejected, in **Complexity Tracking** below. The user must approve before implementation begins.

## Project Structure

Repo-root tree showing the files this feature adds or changes. Do not show files unrelated to this feature.

```text
imagineer/
├── api/
│   └── app/
│       └── ...
└── web/
    └── src/
        └── ...
```

## Phase 0 — Outline & Research

Output: `research.md`. Resolve every `NEEDS CLARIFICATION` from Technical Context. Each entry: **Decision / Rationale / Alternatives considered**.

## Phase 1 — Design & Contracts

Outputs:

- `data-model.md` — entities, fields, relationships, state transitions, validation rules.
- `contracts/` — interface contracts (HTTP routes, CLI args, library APIs — whichever applies).
- `quickstart.md` — how a new contributor brings the feature up locally and validates it.

Re-evaluate the Constitution Check after Phase 1 designs are settled. If anything regressed, update Complexity Tracking.

## Phase 2 — Task Breakdown (deferred)

The `/speckit.tasks` command produces `tasks.md`. This plan stops at the end of Phase 1.

## Complexity Tracking

| Deviation | Constitution principle violated | Why simpler alternative was rejected |
|-----------|---------------------------------|--------------------------------------|

(Empty if no deviations.)
