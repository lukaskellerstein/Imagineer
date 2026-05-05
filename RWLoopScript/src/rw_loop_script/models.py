from typing import Literal

from pydantic import BaseModel, Field

Priority = Literal["P1", "P2", "P3", "P4", "P5"]


class Task(BaseModel):
    id: str
    description: str
    parallel: bool = False
    files: list[str] = Field(default_factory=list)


class UserStory(BaseModel):
    id: str
    title: str
    priority: Priority
    goal: str
    independent_test: str = ""
    acceptance_scenarios: list[str] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)


class ParsedSpec(BaseModel):
    stories: list[UserStory]


class IterationResult(BaseModel):
    done: bool
    summary: str
    completed_task_ids: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)


SPEC_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "stories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "priority": {
                        "type": "string",
                        "enum": ["P1", "P2", "P3", "P4", "P5"],
                    },
                    "goal": {"type": "string"},
                    "independent_test": {"type": "string"},
                    "acceptance_scenarios": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "description": {"type": "string"},
                                "parallel": {"type": "boolean"},
                                "files": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["id", "description", "parallel", "files"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": [
                    "id",
                    "title",
                    "priority",
                    "goal",
                    "independent_test",
                    "acceptance_scenarios",
                    "tasks",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["stories"],
    "additionalProperties": False,
}


ITERATION_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "done": {"type": "boolean"},
        "summary": {"type": "string"},
        "completed_task_ids": {
            "type": "array",
            "items": {"type": "string"},
        },
        "blockers": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["done", "summary", "completed_task_ids", "blockers"],
    "additionalProperties": False,
}
