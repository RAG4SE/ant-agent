# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Task completion tool for Ant Agent."""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

from ant_agent.tools.base import AntTool, AntToolResult
from pydantic import BaseModel


class TaskDoneInput(BaseModel):
    """Input schema for task done tool."""
    summary: str
    status: Optional[str] = "completed"


class TaskDoneTool(AntTool):
    """Tool for indicating task completion."""

    name: str = "task_done"
    description: str = "Mark the current task as completed with a summary"
    args_schema: Type[BaseModel] = TaskDoneInput

    def _run(self, summary: str, status: str = "completed") -> AntToolResult:
        """Mark task as done."""
        output = f"Task {status}: {summary}"

        return AntToolResult(
            success=True,
            output=output,
            metadata={
                "status": status,
                "summary": summary,
                "completed": True
            }
        )