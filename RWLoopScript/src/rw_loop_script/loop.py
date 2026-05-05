"""Ralph-Wiggum loop: one fresh Claude Agent SDK invocation per iteration, per user story.

Each iteration triggers the project's `/speckit-implement` skill, scoped to a
single user story. The Claude Agent SDK runs in the spec-kit project root so
the skill can discover `.specify/`, `.claude/skills/`, and `tasks.md`.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Literal

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

from rw_loop_script.models import ITERATION_SCHEMA, IterationResult, UserStory
from rw_loop_script.prompts import IMPLEMENTER_SYSTEM_PROMPT, implementer_skill_prompt


SettingSource = Literal["user", "project", "local"]


# Tools the implementer is allowed to use. The skill itself orchestrates work
# via Bash, Edit, etc.; `Skill` lets the agent invoke the speckit skill, and
# `Task` lets it spawn the parallel sub-agents the speckit skill is designed
# around. Git commits stay forbidden via the system prompt.
DEFAULT_ALLOWED_TOOLS: list[str] = [
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Bash",
    "TodoWrite",
    "Skill",
    "Task",
]

# Skills enabled for the implementer. `speckit-implement` is the entry point;
# the speckit pipeline often invokes its sibling skills (`speckit-tasks`,
# `speckit-plan`, etc.) so we whitelist the whole speckit family.
DEFAULT_SKILLS: list[str] = [
    "speckit-implement",
    "speckit-tasks",
    "speckit-plan",
    "speckit-analyze",
    "speckit-checklist",
    "speckit-clarify",
    "speckit-constitution",
    "speckit-specify",
]

# Project + local + user setting sources so `.claude/skills/` and
# `.specify/` configuration get loaded into the SDK session.
DEFAULT_SETTING_SOURCES: list[SettingSource] = ["user", "project", "local"]


def _banner(text: str, char: str = "━") -> str:
    line = char * 64
    return f"{line}\n{text}\n{line}"


async def run_one_iteration(
    story: UserStory,
    project_root: Path,
    spec_folder: Path,
    iteration: int,
    max_iterations: int,
    *,
    model: str | None,
    max_turns: int,
    allowed_tools: list[str],
    permission_mode: str,
    skills: list[str],
    setting_sources: list[SettingSource],
) -> IterationResult:
    """Single fresh-context Claude Agent SDK call for the given story.

    `query()` spawns a brand-new session every call — that is the
    Ralph-Wiggum 'clean context' guarantee. The cwd is the spec-kit project
    root so the `/speckit-implement` skill resolves `.specify/` and
    `.claude/skills/` correctly.
    """
    options = ClaudeAgentOptions(
        cwd=str(project_root),
        system_prompt=IMPLEMENTER_SYSTEM_PROMPT,
        allowed_tools=allowed_tools,
        permission_mode=permission_mode,
        max_turns=max_turns,
        output_format={"type": "json_schema", "schema": ITERATION_SCHEMA},
        setting_sources=setting_sources,
        skills=skills,
        **({"model": model} if model else {}),
    )

    structured: dict | None = None
    last_text: str | None = None

    async for message in query(
        prompt=implementer_skill_prompt(
            story=story,
            project_root=project_root,
            spec_folder=spec_folder,
            iteration=iteration,
            max_iterations=max_iterations,
        ),
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock) and block.text.strip():
                    last_text = block.text
                    print(f"  [agent] {block.text.splitlines()[0][:200]}")
        elif isinstance(message, ResultMessage):
            if getattr(message, "structured_output", None):
                structured = message.structured_output
            cost = getattr(message, "total_cost_usd", None)
            duration = getattr(message, "duration_ms", None)
            if cost or duration:
                print(
                    f"  [agent] result: cost=${cost or 0:.4f}, "
                    f"duration={(duration or 0) / 1000:.1f}s"
                )

    if structured is None and last_text:
        try:
            structured = json.loads(last_text)
        except json.JSONDecodeError:
            structured = None

    if structured is None:
        return IterationResult(
            done=False,
            summary="(no structured output from agent)",
            blockers=["agent did not emit structured output"],
        )

    return IterationResult.model_validate(structured)


async def run_story(
    story: UserStory,
    project_root: Path,
    spec_folder: Path,
    *,
    max_iterations: int,
    model: str | None,
    max_turns_per_iter: int,
    allowed_tools: list[str],
    permission_mode: str,
    skills: list[str],
    setting_sources: list[SettingSource],
) -> IterationResult:
    """Loop fresh-context iterations against a single user story until done."""
    print(_banner(f"USER STORY {story.id} — {story.title} ({story.priority})"))
    print(f"Goal: {story.goal}")
    print(f"Tasks: {len(story.tasks)}")
    print(f"Project root (cwd): {project_root}")
    print(f"Max iterations: {max_iterations}")
    print()

    last: IterationResult | None = None
    for i in range(1, max_iterations + 1):
        print(f"── iteration {i}/{max_iterations} ──")
        t0 = time.time()
        try:
            last = await run_one_iteration(
                story=story,
                project_root=project_root,
                spec_folder=spec_folder,
                iteration=i,
                max_iterations=max_iterations,
                model=model,
                max_turns=max_turns_per_iter,
                allowed_tools=allowed_tools,
                permission_mode=permission_mode,
                skills=skills,
                setting_sources=setting_sources,
            )
        except Exception as exc:  # noqa: BLE001 — surface and continue
            print(f"  [loop] iteration crashed: {exc}", file=sys.stderr)
            last = IterationResult(
                done=False,
                summary=f"iteration crashed: {exc}",
                blockers=[str(exc)],
            )

        dt = time.time() - t0
        print(f"  → done={last.done}  ({dt:.1f}s)")
        print(f"  → summary: {last.summary}")
        if last.completed_task_ids:
            print(f"  → completed: {', '.join(last.completed_task_ids)}")
        if last.blockers:
            print(f"  → blockers: {'; '.join(last.blockers)}")
        print()

        if last.done:
            print(f"✔ story {story.id} reported done after {i} iteration(s)")
            return last

    print(f"✗ story {story.id} hit max iterations ({max_iterations}) without done=true")
    return last or IterationResult(
        done=False,
        summary="no iteration produced a result",
    )
