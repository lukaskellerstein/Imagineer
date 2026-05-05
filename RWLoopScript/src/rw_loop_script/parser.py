"""Parse a spec-kit folder into structured user stories using a single Claude Agent SDK call."""

from __future__ import annotations

import json
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

from rw_loop_script.models import SPEC_SCHEMA, ParsedSpec
from rw_loop_script.prompts import PARSER_SYSTEM_PROMPT, parser_user_prompt


def _collect_markdown(spec_folder: Path) -> list[Path]:
    return sorted(p for p in spec_folder.rglob("*.md") if p.is_file())


async def parse_spec_folder(
    spec_folder: Path,
    *,
    model: str | None = None,
    max_turns: int = 10,
) -> ParsedSpec:
    """Run a single Claude Agent SDK query against the spec folder.

    The agent is given Read/Glob tools so it can open every markdown file in
    the folder. The structured-output schema forces the response into a
    deterministic shape we can deserialise into Pydantic models.
    """
    spec_folder = spec_folder.resolve()
    if not spec_folder.is_dir():
        raise FileNotFoundError(f"spec folder not found: {spec_folder}")

    md_files = _collect_markdown(spec_folder)
    if not md_files:
        raise FileNotFoundError(f"no markdown files in spec folder: {spec_folder}")

    options = ClaudeAgentOptions(
        cwd=str(spec_folder),
        system_prompt=PARSER_SYSTEM_PROMPT,
        allowed_tools=["Read", "Glob", "Grep"],
        permission_mode="bypassPermissions",
        max_turns=max_turns,
        output_format={"type": "json_schema", "schema": SPEC_SCHEMA},
        **({"model": model} if model else {}),
    )

    structured: dict | None = None
    last_text: str | None = None

    async for message in query(
        prompt=parser_user_prompt(spec_folder, md_files),
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    last_text = block.text
        elif isinstance(message, ResultMessage):
            if getattr(message, "structured_output", None):
                structured = message.structured_output

    if structured is None:
        # The SDK didn't surface structured_output. Try to recover by parsing
        # the last assistant text block as JSON — useful when the run hits
        # max_turns with valid JSON in the final message.
        if last_text:
            try:
                structured = json.loads(last_text)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    "parser agent returned no structured output and the final "
                    "text was not valid JSON"
                ) from exc
        else:
            raise RuntimeError("parser agent returned no output at all")

    return ParsedSpec.model_validate(structured)
