# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Sequential thinking tool for Ant Agent."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from ant_agent.tools.base import AntTool, AntToolResult
from pydantic import BaseModel, Field


class ThinkingInput(BaseModel):
    """Input schema for sequential thinking tool."""
    thought: str


class SequentialThinkingTool(AntTool):
    """Tool for sequential thinking and reasoning."""

    name: str = "sequential_thinking"
    description: str = "Think step by step to analyze problems and plan solutions"
    args_schema: Type[BaseModel] = ThinkingInput
    thoughts: List[str] = Field(default_factory=list)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def _run(self, thought: str) -> AntToolResult:
        """Record a thought step."""
        self.thoughts.append(thought)

        thought_num = len(self.thoughts)
        output = f"Thought {thought_num}: {thought}"

        return AntToolResult(
            success=True,
            output=output,
            metadata={
                "thought_number": thought_num,
                "total_thoughts": len(self.thoughts),
                "thought": thought
            }
        )

    def get_thoughts(self) -> List[str]:
        """Get all recorded thoughts."""
        return self.thoughts.copy()

    def clear_thoughts(self) -> None:
        """Clear all recorded thoughts."""
        self.thoughts.clear()

    def get_thinking_summary(self) -> str:
        """Get a summary of the thinking process."""
        if not self.thoughts:
            return "No thoughts recorded yet."

        summary = "Thinking Process:\n"
        for i, thought in enumerate(self.thoughts, 1):
            summary += f"{i}. {thought}\n"
        return summary