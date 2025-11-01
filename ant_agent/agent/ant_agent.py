# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Main Ant Agent implementation."""

from __future__ import annotations

from typing import List

from ant_agent.agent.base_agent import BaseAgent
from ant_agent.prompt.agent_prompt import AGENT_SYSTEM_PROMPT
from ant_agent.tools.bash_tool import BashTool
from ant_agent.tools.edit_tool import EditTool, CreateFileTool
from ant_agent.tools.thinking_tool import SequentialThinkingTool
from ant_agent.tools.task_done_tool import TaskDoneTool
from ant_agent.tools.base import AntTool
from ant_agent.utils.config import ModelConfig
from omegaconf import DictConfig


class AntAgent(BaseAgent):
    """Main Ant Agent for software engineering tasks."""

    def __init__(
        self,
        agent_config: DictConfig,
        model_config: ModelConfig,
        trajectory_recorder=None,
        **kwargs,
    ):
        """Initialize Ant Agent.

        Args:
            agent_config: Agent configuration (DictConfig from Hydra)
            model_config: Model configuration
            trajectory_recorder: Optional trajectory recorder
            **kwargs: Additional keyword arguments
        """
        super().__init__(agent_config, model_config, trajectory_recorder, **kwargs)

    def _get_system_prompt(self) -> str:
        """Get the system prompt for Ant Agent."""
        return AGENT_SYSTEM_PROMPT

    def _initialize_tools(self) -> List[AntTool]:
        """Initialize the tools for Ant Agent."""
        return [
            BashTool(),
            EditTool(),
            CreateFileTool(),
            SequentialThinkingTool(),
            TaskDoneTool(),
        ]

    @property
    def thinking_tool(self) -> SequentialThinkingTool:
        """Get the thinking tool instance."""
        tool = self.get_tool_by_name("sequential_thinking")
        if tool is None:
            raise ValueError("Sequential thinking tool not found")
        return tool

    def get_thinking_summary(self) -> str:
        """Get a summary of the thinking process."""
        return self.thinking_tool.get_thinking_summary()

    def clear_thinking(self) -> None:
        """Clear the thinking process."""
        self.thinking_tool.clear_thoughts()