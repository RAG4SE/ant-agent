# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Step completion tool for Ant Agent."""

from __future__ import annotations

from typing import Any, Optional, Type

from ant_agent.tools.base import AntTool, AntToolResult
from ant_agent.utils.plan_manager import plan_manager
from pydantic import BaseModel, Field


class StepCompleteInput(BaseModel):
    pass


class StepCompleteTool(AntTool):
    """Tool for marking a plan step as completed."""

    name: str = "step_complete"
    description: str = """Mark the current plan step as completed. Call this tool when you have finished the current step of your analysis plan and are ready to move to the next step. Only call this if you are confident the step is complete and you have found results.
    """
    args_schema: Type[BaseModel] = StepCompleteInput

    def _run(self) -> AntToolResult:
        """Mark step as complete."""
        if not plan_manager.has_active_plans():
            raise ValueError("No active plan")
            return AntToolResult(
                success=False,
                output="No active plan. Please create a plan first using sequential_thinking.",
                error="No active plan"
            )

        current_plan = plan_manager.get_current_plan()
        if current_plan == None:
            raise ValueError("No plan exists.")
        current_plan.removes_current_step()
        
        if current_plan.is_complete():
            plan_manager.pop_plan()
            current_plan = plan_manager
            output = "After completing this step, the current plan is complete too. Invoke plan_complete tool."
        else:
            output = "After completing this step, there remains the following steps in the current plan:\n" 
            for i, step in enumerate(current_plan.steps, 1):
                output += f"{i}: {step}\n"

        return AntToolResult(
            success=True,
            output=output,
        )
