# Goal

I need to have a python project that I can call indepnedently from the rest of the project (use uv), that will implement a ralph wiggum loop, and trigger a Claude Agent SDK.

I want to be able to give to the script folder with speckit specification, the specification should be parsed for each user story, and all tasks within that user story should be implemented by a single Claude agent sdk. As ralp wiggum suggests, each user story needs to have a "clean context" => new claude agent sdk.

In order to parse correctly the user stories and tasks, we could use a single Claude Agent SDK with a structured output.

## Destination

Implement all into folder "RWLoopScript".

## Ralp Wiggum loop

Resources:
1) `~/Projects/Github/ghuntley/how-to-ralph-wiggum`
2) https://ghuntley.com/loop/


## Claude Agent SDK

Source code: 
`~/Projects/Github/anthropic/claude-agent-sdk-python`

Structured output:
`https://platform.claude.com/docs/en/build-with-claude/structured-outputs`

Example on how to use it:
`/home/lukas/Projects/Github/lukaskellerstein/vibe-coding-course/5_Claude_Agent_SDK/python`

## Github speck-kit

Source:
`~/Projects/Github/github/spec-kit`

