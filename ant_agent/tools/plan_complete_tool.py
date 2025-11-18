# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Step completion tool for Ant Agent."""

from __future__ import annotations

from typing import Any, Optional, Type

from ant_agent.tools.base import AntTool, AntToolResult
from ant_agent.utils.plan_manager import plan_manager
from pydantic import BaseModel, Field


class PlanCompleteInput(BaseModel):
    pass


class PlanCompleteTool(AntTool):
    """Tool for marking a plan step as completed."""

    name: str = "plan_complete"
    description: str = """Mark the current plan as completed. Call this tool when you have finished the current plan of your task and are ready to roll back to the previous plan. Only call this if you are confident the plan is complete and you have found results. A plan shows how to accomplish a task or a step of another plan.
    """
    args_schema: Type[BaseModel] = PlanCompleteInput

    def _run(self) -> AntToolResult:
        """Mark plan as complete."""
        
        plan_manager.pop_plan()
        
        if not plan_manager.has_active_plans():
            output = "No plan remained. Call task_done tool to terminate the task."
        else:
            current_plan = plan_manager.get_current_plan()
            current_plan.removes_current_step()
            output = "After finishing the current plan, let's roll back to the previously unfinished plan, the remaining steps of which are:\n" + '\n'.join(current_plan.steps)

        return AntToolResult(
            success=True,
            output=output
        )
