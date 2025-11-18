# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Sequential thinking tool for Ant Agent."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from ant_agent.tools.base import AntTool, AntToolResult
from ant_agent.utils.plan_manager import plan_manager
from pydantic import BaseModel, Field
import re

class ReplanInput(BaseModel):
    """Input schema for sequential thinking tool."""
    steps: List[str] = Field(
        description="List of steps for planning. When provided, these will be stored as structured plan steps."
    )

class ReplanTool(AntTool):
    """Tool for sequential thinking and reasoning."""

    name: str = "replan"
    description: str = """If the current plan step requires a new step-to-step sub-plan, re-plan the remaining steps by 1) spawn more steps to accomplish the current plan step, 2) re-plan the other plan steps to interract with the newly spawned plan steps from the current ones.
    """
    args_schema: Type[BaseModel] = ReplanInput
    # steps: List[str] = Field(default_factory=list)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    def strip_step_numbers(self, steps: List[str]) -> List[str]:
        """
        去掉每条 step 前面的数字序号。
        支持格式：1.  1)  (1)  1-  1–  1—  等，后面可跟空格或制表符。
        返回新的 steps 列表，原列表不变。
        """
        pattern = re.compile(r'^\s*(?:\(\d+\)|\d+[\.\)\-–—]+)\s*')
        return [pattern.sub('', s).strip() for s in steps]

    def _run(self, steps: List[str]) -> AntToolResult:
        """Record a thought step."""

        steps = self.strip_step_numbers(steps)
        plan_manager.pop_plan()
        plan_manager.create_plan(steps)
        
        return AntToolResult(
            success=True,
            output='\n'.join(steps),
        )