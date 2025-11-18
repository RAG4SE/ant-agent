# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Sequential thinking tool for Ant Agent."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from ant_agent.tools.base import AntTool, AntToolResult
from ant_agent.utils.plan_manager import plan_manager
from pydantic import BaseModel, Field
import re

class ThinkingInput(BaseModel):
    """Input schema for sequential thinking tool."""
    steps: List[str] = Field(
        description="List of steps for planning. When provided, these will be stored as structured plan steps."
    )

class SequentialThinkingTool(AntTool):
    """Tool for sequential thinking and reasoning."""

    name: str = "sequential_thinking"
    description: str = (
        "Use this tool when:\n"
        "1. User request requires multiple steps → create a full plan consisting of several steps.\n"
        "2. Current plan step is so complex that cannot be finished in one go → spawn fine-grained sub-steps for the current step.\n"
        "Never use this tool when want to reason or think, instead of making a plan.\n"
        "For instance, the following is a good result of using sequential_thinking:\n"
        " - Step 1: Analyze super.initialise() in ParsedCode class\n"
        " - Step 2: Check for Functional Error bugs in parent initialise method\n"
        " - Step 3: Store any verified bugs found\n"
        " - Step 4: Complete the analysis\n"
        "However, the following is a bad use\n"
        " - Function signature: public override initialise(element: any, document: ParsedDocument, contract: ParsedContract, isGlobal = false)\n"
        " - Parameter 1: element: any - untyped parameter, could be any object\n"
        " - Parameter 2: document: ParsedDocument - typed parameter from imported ParsedDocument class\n"
        " - Parameter 3: contract: ParsedContract - typed parameter from imported ParsedContract class\n"
        " - Parameter 4: isGlobal = false - optional boolean parameter with default value false\n"
        " - Function calls super.initialise() - depends on parent class implementation\n"
        "This is mere thinking. No need to use sequential_thinking"
        
    )
    args_schema: Type[BaseModel] = ThinkingInput
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
        current_plan = plan_manager.get_current_plan()
        if current_plan:
            steps += current_plan.steps[1:]
        plan_manager.replace_plan(steps)
        
        return AntToolResult(
            success=True,
            output='\n'.join(steps),
        )