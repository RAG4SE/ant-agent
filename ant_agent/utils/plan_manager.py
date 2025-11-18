"""
Plan Management System for Intelligent Continuation Prompts

This module implements a linked-list structure for managing analysis plans
and generating context-aware continuation prompts.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import json
from datetime import datetime


@dataclass
class PlanNode:
    """Represents a single plan node in the plan hierarchy"""
    id: str
    steps: List[str] = field(default_factory=list)

    def removes_current_step(self):
        if self.is_complete():
            raise ValueError("removes_current_step: this plan is completed")
        self.steps = self.steps[1:]

    def is_complete(self) -> bool:
        """Check if all steps are completed"""
        return len(self.steps) == 0


class PlanManager:
    """Manages the hierarchy of plans for intelligent continuation"""

    def __init__(self):
        self.plan_stack: List[PlanNode] = []
        self.plan_counter = 0
        self.previous_plan_step = ''

    def create_plan(self, steps: List[str]) -> PlanNode:
        """Create a new plan node"""
        self.plan_counter += 1
        plan_id = f"plan_{self.plan_counter}_{int(datetime.now().timestamp())}"

        plan = PlanNode(
            id=plan_id,
            steps=steps,
        )
        
        self.push_plan(plan)

        return plan

    def replace_plan(self, steps: List[str]) -> PlanNode:
        """Create a new plan node and replace the current plan with this new plan"""
        self.plan_counter += 1
        plan_id = f"plan_{self.plan_counter}_{int(datetime.now().timestamp())}"

        plan = PlanNode(
            id=plan_id,
            steps=steps,
        )
        
        self.pop_plan()
        self.push_plan(plan)
        
        return plan

    def push_plan(self, plan: PlanNode) -> None:
        """Add plan to the stack"""
        self.plan_stack.append(plan)

    def pop_plan(self) -> Optional[PlanNode]:
        """Remove and return the top plan from stack"""
        if self.plan_stack:
            return self.plan_stack.pop()
        return None

    def get_current_plan(self) -> Optional[PlanNode]:
        """Get the current active plan (top of stack)"""
        return self.plan_stack[-1] if self.plan_stack else None

    def has_active_plans(self) -> bool:
        """Check if there are any active plans"""
        return len(self.plan_stack) > 0

    def generate_continuation_prompt(self) -> str:
        current_plan = self.get_current_plan()
        if not current_plan:
            raise ValueError(f"No plan...")
        if current_plan.is_complete():
            return "The current plan has been finished. Now call plan_complete tool"
            # raise ValueError(f"No steps remained for plan {current_plan.id}")
        if current_plan.steps[0] == self.previous_plan_step:
            return f"Continue with the unaccomplished plan step: {current_plan.steps[0]}"
        self.previous_plan_step = current_plan.steps[0]
        prompt = f"Now the current plan step is {current_plan.steps[0]}\n"
        prompt += "And the subsequent plan steps are:\n"
        for i, step in enumerate(current_plan.steps[1:], 1):
            prompt += f"{i}: {step}\n"
        return prompt

    def clear_all_plans(self) -> None:
        """Clear all plans (reset state)"""
        self.plan_stack.clear()
        self.plan_counter = 0


# Global plan manager instance
plan_manager = PlanManager()