"""Command-line entry point for the Ralph-Wiggum spec-kit loop runner."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import anyio

from rw_loop_script.loop import (
    DEFAULT_ALLOWED_TOOLS,
    DEFAULT_SETTING_SOURCES,
    DEFAULT_SKILLS,
    run_story,
)
from rw_loop_script.models import ParsedSpec, UserStory
from rw_loop_script.parser import parse_spec_folder


PRIORITY_ORDER = {"P1": 1, "P2": 2, "P3": 3, "P4": 4, "P5": 5}


def detect_project_root(spec_folder: Path) -> Path | None:
    """Walk up from the spec folder until we find a `.specify/` directory.

    Spec-kit projects always have `.specify/` at the project root, so this is
    the canonical marker. Returns None if no marker is found.
    """
    spec_folder = spec_folder.resolve()
    for candidate in (spec_folder, *spec_folder.parents):
        if (candidate / ".specify").is_dir():
            return candidate
    return None


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rw-loop",
        description=(
            "Ralph-Wiggum loop driver for spec-kit folders. Parses user "
            "stories, then runs one fresh Claude Agent SDK invocation per "
            "story (and per iteration within a story), each one calling the "
            "project's /speckit-implement skill scoped to that story."
        ),
    )
    p.add_argument(
        "--spec-folder",
        required=True,
        type=Path,
        help="Path to a spec-kit feature folder (containing spec.md and friends).",
    )
    p.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help=(
            "Spec-kit project root (the directory containing `.specify/`). "
            "This is the cwd used for every Claude Agent SDK invocation. "
            "If omitted, auto-detected by walking up from --spec-folder until "
            "`.specify/` is found."
        ),
    )
    p.add_argument(
        "--max-iterations",
        type=int,
        default=1,
        help="Max fresh-context iterations per user story (default: 1).",
    )
    p.add_argument(
        "--story",
        type=str,
        default=None,
        help="Run a single story by id (e.g. US2). Default: run all stories.",
    )
    p.add_argument(
        "--list-only",
        action="store_true",
        help="Parse the spec folder, print the extracted stories, and exit.",
    )
    p.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model to use for both parser and implementer (default: SDK default).",
    )
    p.add_argument(
        "--max-turns",
        type=int,
        default=200,
        help=(
            "Max agent turns per iteration of the implementer (default: 200). "
            "The /speckit-implement skill is multi-step; bump this if you see "
            "it cut off mid-implementation."
        ),
    )
    p.add_argument(
        "--permission-mode",
        type=str,
        default="acceptEdits",
        choices=["default", "acceptEdits", "bypassPermissions", "plan"],
        help=(
            "Permission mode for tool calls. 'acceptEdits' auto-approves "
            "Edit/Write, 'bypassPermissions' is full YOLO mode."
        ),
    )
    return p


def _sort_stories(stories: list[UserStory]) -> list[UserStory]:
    return sorted(stories, key=lambda s: (PRIORITY_ORDER.get(s.priority, 99), s.id))


def _print_parsed(parsed: ParsedSpec) -> None:
    print(f"Parsed {len(parsed.stories)} user story/stories:\n")
    for story in _sort_stories(parsed.stories):
        print(f"  • {story.id} [{story.priority}] {story.title}")
        print(f"      goal: {story.goal}")
        if story.independent_test:
            print(f"      independent test: {story.independent_test}")
        if story.tasks:
            print(f"      tasks ({len(story.tasks)}):")
            for t in story.tasks:
                tag = " [P]" if t.parallel else ""
                files = f"  ({', '.join(t.files)})" if t.files else ""
                print(f"        - {t.id}{tag} {t.description}{files}")
        else:
            print("      tasks: (none — implementer will derive from scenarios)")
        print()


async def _async_main(args: argparse.Namespace) -> int:
    spec_folder: Path = args.spec_folder.resolve()

    print(f"Parsing spec folder: {spec_folder}")
    parsed = await parse_spec_folder(spec_folder, model=args.model)
    _print_parsed(parsed)

    if args.list_only:
        return 0

    project_root: Path | None = args.project_root.resolve() if args.project_root else None
    if project_root is None:
        project_root = detect_project_root(spec_folder)
        if project_root is None:
            print(
                "error: could not auto-detect project root — no `.specify/` "
                "directory found above the spec folder. Pass --project-root.",
                file=sys.stderr,
            )
            return 2
        print(f"Auto-detected project root: {project_root}")

    if not project_root.is_dir():
        print(f"error: project root not found: {project_root}", file=sys.stderr)
        return 2
    if not (project_root / ".specify").is_dir():
        print(
            f"warning: project root {project_root} does not contain `.specify/` — "
            f"the /speckit-implement skill will likely fail.",
            file=sys.stderr,
        )

    stories = _sort_stories(parsed.stories)
    if args.story:
        wanted = args.story.upper()
        stories = [s for s in stories if s.id.upper() == wanted]
        if not stories:
            print(f"error: story '{args.story}' not found in spec", file=sys.stderr)
            return 2

    print(f"Running {len(stories)} story/stories with project_root={project_root}")
    print(
        f"max_iterations={args.max_iterations}  "
        f"permission_mode={args.permission_mode}  "
        f"model={args.model or '(default)'}"
    )
    print()

    failures = 0
    for story in stories:
        result = await run_story(
            story=story,
            project_root=project_root,
            spec_folder=spec_folder,
            max_iterations=args.max_iterations,
            model=args.model,
            max_turns_per_iter=args.max_turns,
            allowed_tools=DEFAULT_ALLOWED_TOOLS,
            permission_mode=args.permission_mode,
            skills=DEFAULT_SKILLS,
            setting_sources=DEFAULT_SETTING_SOURCES,
        )
        if not result.done:
            failures += 1

    if failures:
        print(f"\n{failures} story/stories did not reach done=true.")
        return 1
    print("\nAll stories reported done=true.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    return anyio.run(_async_main, args)


if __name__ == "__main__":
    sys.exit(main())
