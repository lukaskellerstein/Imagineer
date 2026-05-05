from pathlib import Path
from textwrap import dedent

from rw_loop_script.models import UserStory

__all__ = [
    "PARSER_SYSTEM_PROMPT",
    "IMPLEMENTER_SYSTEM_PROMPT",
    "parser_user_prompt",
    "implementer_user_prompt",
    "implementer_skill_prompt",
]


PARSER_SYSTEM_PROMPT = dedent(
    """
    You are a spec-kit specification parser. You read a folder of GitHub
    spec-kit markdown files and extract a strict, machine-readable list of
    user stories with their associated tasks.

    Spec-kit conventions you can rely on:
      * `spec.md`               — feature specification: contains `User Story N` blocks with `Priority: PX`, an `Independent Test`, `Acceptance Scenarios`, plus functional requirements (FR-###).
      * `tasks.md` (optional)   — task list grouped by user story; tasks are tagged `[USx]` and may carry `[P]` for parallelisable.
      * `plan.md` (optional)    — implementation plan, useful for filling in target file paths.
      * `checklists/*.md`       — review checklists; ignore for task extraction.

    Rules:
      1. One entry per user story exactly as written in `spec.md`. Use ids `US1`, `US2`, …
         in the order the stories appear, regardless of how they are numbered in the document.
      2. `priority` must be one of `P1`/`P2`/`P3`/`P4`/`P5`.
      3. If `tasks.md` exists: copy each task tagged with this story's `[USx]` marker.
         Preserve the original task id (e.g., `T012`).
      4. If `tasks.md` does NOT exist: synthesise tasks from the story's
         acceptance scenarios and the functional requirements that clearly
         belong to this story. Give them ids `US{N}-T{NN}` starting at 01.
      5. `parallel` = true only if the source explicitly marks the task `[P]`
         or the task touches a different file from every other task in the same story.
      6. `files` should list concrete repo-relative paths the task is expected
         to create or edit, drawn from `plan.md`/`tasks.md` when available; otherwise [].
      7. Do not invent stories. Do not merge stories. Do not split a story.
      8. Output strictly the JSON schema you were given. No prose.
    """
).strip()


def parser_user_prompt(spec_folder: Path, files: list[Path]) -> str:
    file_list = "\n".join(f"  - {p.relative_to(spec_folder)}" for p in files)
    return (
        f"Spec folder: {spec_folder}\n\n"
        f"Files in this folder (read every one before answering):\n"
        f"{file_list}\n\n"
        f"Extract the user stories and tasks per the rules in the system "
        f"prompt and return them as JSON matching the provided schema."
    )


IMPLEMENTER_SYSTEM_PROMPT = dedent(
    """
    You are an implementation agent driving a single spec-kit user story to
    completion via the project's `/speckit-implement` skill.

    You run inside a Ralph-Wiggum loop: every invocation is a fresh context.
    You will be re-invoked until you report `done = true` (or the loop hits
    its max-iteration cap).

    Operating rules:
      * Your cwd is the spec-kit project root (the directory containing
        `.specify/`).
      * Always invoke the `/speckit-implement` skill (it is enabled for you)
        and let it drive the implementation. Do not bypass it.
      * Scope every invocation to the single user story named in the user
        prompt. Skip tasks belonging to other stories.
      * Do NOT run `git commit`, `git push`, or any other git-mutating
        command. The human commits.
      * Run the project's tests / type-checks / linters whenever practical
        and surface failures in `blockers` rather than silently ignoring them.
      * If you cannot make progress (e.g. `tasks.md` missing, ambiguous
        requirement, broken dependency), set `done = false` and explain in
        `blockers`. The loop will retry with a fresh context, so leave
        breadcrumbs in code or notes that survive across iterations.
      * Set `done = true` only when EVERY task tagged with this story's id
        is implemented and the story's independent test would pass.
      * Your FINAL message MUST be a JSON object matching the provided
        schema — emit it after the skill has finished.
    """
).strip()


def implementer_skill_prompt(
    story: UserStory
) -> str:
    """Prompt that invokes the /speckit-implement skill scoped to one story."""
    tasks_hint = ""
    if story.tasks:
        ids = ", ".join(t.id for t in story.tasks)
        tasks_hint = f"\nExpected task ids for this story: {ids}"

    scenarios_block = (
        "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(story.acceptance_scenarios))
        or "  (none recorded in spec)"
    )

    return (
        f"/speckit-implement Implement ONLY user story {story.id} "
        f"({story.priority}) — {story.title}.\n"   )


def implementer_user_prompt(
    story: UserStory,
    workspace: Path,
    spec_folder: Path,
    iteration: int,
    max_iterations: int,
) -> str:
    tasks_block = (
        "\n".join(
            f"  - [{t.id}]{' [P]' if t.parallel else ''} {t.description}"
            + (f"  ({', '.join(t.files)})" if t.files else "")
            for t in story.tasks
        )
        or "  (no tasks parsed — derive them from the acceptance scenarios)"
    )
    scenarios_block = (
        "\n".join(f"  {i + 1}. {s}" for i, s in enumerate(story.acceptance_scenarios))
        or "  (none recorded)"
    )

    return (
        f"Iteration {iteration} / {max_iterations} for user story {story.id}.\n"
        f"\n"
        f"── Story ──────────────────────────────────────────────────────\n"
        f"ID:        {story.id}\n"
        f"Title:     {story.title}\n"
        f"Priority:  {story.priority}\n"
        f"Goal:      {story.goal}\n"
        f"\n"
        f"Independent test:\n"
        f"  {story.independent_test or '(none recorded)'}\n"
        f"\n"
        f"Acceptance scenarios:\n"
        f"{scenarios_block}\n"
        f"\n"
        f"Tasks for this story:\n"
        f"{tasks_block}\n"
        f"\n"
        f"── Paths ──────────────────────────────────────────────────────\n"
        f"Workspace (the codebase to change): {workspace}\n"
        f"Spec folder (read-only reference):  {spec_folder}\n"
        f"\n"
        f"── Your job this iteration ────────────────────────────────────\n"
        f"1. Read the spec folder to remind yourself of the story's intent.\n"
        f"2. Read the workspace to discover what is already implemented for\n"
        f"   this story.\n"
        f"3. Pick the next most valuable incomplete task and implement it\n"
        f"   fully (no placeholders or TODOs).\n"
        f"4. Run any relevant tests / type-checks / linters available in the\n"
        f"   workspace. Surface failures in `blockers`.\n"
        f"5. Emit the structured JSON object describing the outcome.\n"
        f"\n"
        f"Set `done = true` only if EVERY task for this story is complete\n"
        f"and the story's independent test would pass. Otherwise return\n"
        f"`done = false` so the loop will spin again with a fresh context."
    )
