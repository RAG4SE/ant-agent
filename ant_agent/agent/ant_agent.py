# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Main Ant Agent implementation with Multilspy LSP support."""

from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any

from ant_agent.agent.base_agent import BaseAgent
from ant_agent.prompt.agent_prompt import get_agent_system_prompt
from ant_agent.tools.bash_tool import BashTool
from ant_agent.tools.edit_tool import EditTool, CreateFileTool
from ant_agent.tools.thinking_tool import SequentialThinkingTool
from ant_agent.tools.task_done_tool import TaskDoneTool
from ant_agent.tools.position_finder_tool import PositionFinderTool
from ant_agent.tools.base import AntTool
from ant_agent.utils.config import AppConfig
from ant_agent.lsp.multilspy_manager import MultilspyLSPManager, get_lsp_manager
from ant_agent.utils.trajectory_recorder import TrajectoryRecorder


class AntAgent(BaseAgent):
    """Main Ant Agent for software engineering tasks with Multilspy LSP support."""

    def __init__(
        self,
        app_config: AppConfig,
        trajectory_recorder: Optional[TrajectoryRecorder] = None,
        **kwargs,
    ):
        """Initialize Ant Agent with Multilspy LSP support.

        Args:
            app_config: Application configuration (AppConfig) containing all settings
            trajectory_recorder: Optional trajectory recorder
            **kwargs: Additional keyword arguments
        """
        # Initialize logger first
        self.logger = logging.getLogger("ant_agent")

        # Create LSP manager from LSP config if enabled
        if app_config.lsp.enabled:
            self.lsp_manager = get_lsp_manager(app_config.lsp)
        else:
            self.lsp_manager = None

        # Create trajectory recorder if not provided and trajectory is enabled
        if trajectory_recorder is None and app_config.trajectory.enabled:
            trajectory_recorder = TrajectoryRecorder(app_config.trajectory)

        super().__init__(app_config, trajectory_recorder, **kwargs)

    def _get_system_prompt(self) -> str:
        """Get the system prompt for Ant Agent based on configured skill."""
        return get_agent_system_prompt(self.app_config.agent.skill)

    def _initialize_tools(self) -> List[AntTool]:
        """Initialize the tools for Ant Agent including Multilspy LSP tools."""

        base_tools = [
            BashTool(working_dir=self.app_config.working_dir),
            EditTool(),
            CreateFileTool(),
            SequentialThinkingTool(),
            TaskDoneTool(),
            PositionFinderTool(working_dir=self.app_config.working_dir),
        ]
        
        # 如果有 LSP 管理器，添加 Multilspy LSP 工具
        if self.lsp_manager:
            lsp_tools = self.lsp_manager.get_available_tools()
            base_tools.extend(lsp_tools)
        
        return base_tools

    def get_lsp_info(self) -> Optional[List[Dict[str, Any]]]:
        """获取 LSP 服务器信息"""
        if self.lsp_manager:
            # 返回所有活动的服务器信息
            servers_info = []
            for language, server in self.lsp_manager.servers.items():
                servers_info.append({
                    'language': language,
                    'status': 'active',
                    'capabilities': self._get_server_capabilities(server)
                })
            return servers_info
        return None

    def get_thinking_summary(self) -> str:
        """Get a summary of the thinking process."""
        return self.thinking_tool.get_thinking_summary()

    def clear_thinking(self) -> None:
        """Clear the thinking process."""
        self.thinking_tool.clear_thoughts()

    @property
    def thinking_tool(self) -> SequentialThinkingTool:
        """Get the thinking tool instance."""
        tool = self.get_tool_by_name("sequential_thinking")
        if tool is None:
            raise ValueError("Sequential thinking tool not found")
        return tool
    
    def _get_server_capabilities(self, server: Any) -> List[str]:
        """获取服务器能力列表"""
        capabilities = []
        
        # 检查各种能力
        if hasattr(server, 'request_hover'):
            capabilities.append('hover')
        if hasattr(server, 'request_document_symbols'):
            capabilities.append('document_symbols')
        if hasattr(server, 'request_definition'):
            capabilities.append('definition')
        if hasattr(server, 'request_references'):
            capabilities.append('references')
        if hasattr(server, 'request_completions'):
            capabilities.append('completions')
        
        return capabilities