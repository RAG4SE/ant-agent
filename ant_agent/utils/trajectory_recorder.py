# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Trajectory recording for Ant Agent."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage

from ant_agent.tools.base import AntToolResult
from ant_agent.utils.config import TrajectoryConfig


class TrajectoryRecorder:
    """Records agent execution trajectories for debugging and analysis."""

    def __init__(self, config: TrajectoryConfig):
        """Initialize trajectory recorder.

        Args:
            config: Trajectory recording configuration (TrajectoryConfig from config.py)
        """
        self.config = config
        self.enabled = config.enabled
        self.output_dir = Path(config.output_dir)
        self.trajectory_data: Dict[str, Any] = {
            "session_info": {
                "start_time": datetime.now().isoformat(),
                "version": "0.1.0",
            },
            "messages": [],
            "tool_calls": [],
            "system_info": {}
        }

        if self.enabled:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the trajectory."""
        if not self.enabled or not self.config.include_llm_calls:
            return

        message_data = {
            "type": type(message).__name__,
            "content": message.content,
            "timestamp": datetime.now().isoformat(),
        }

        # Add role information
        if hasattr(message, 'type'):
            message_data["role"] = message.type
        else:
            # Determine role from message type
            if isinstance(message, SystemMessage):
                message_data["role"] = "system"
            elif isinstance(message, HumanMessage):
                message_data["role"] = "user"
            elif isinstance(message, AIMessage):
                message_data["role"] = "assistant"
            elif isinstance(message, ToolMessage):
                message_data["role"] = "tool"

        # Add additional metadata based on message type
        if hasattr(message, 'tool_calls') and message.tool_calls:
            message_data["tool_calls"] = message.tool_calls

        if hasattr(message, 'additional_kwargs'):
            message_data["additional_kwargs"] = message.additional_kwargs

        # Add tool call ID for tool messages
        if hasattr(message, 'tool_call_id'):
            message_data["tool_call_id"] = message.tool_call_id

        # Add usage information if available
        if hasattr(message, 'usage_metadata') and message.usage_metadata:
            message_data["usage"] = message.usage_metadata

        self.trajectory_data["messages"].append(message_data)

    def add_tool_result(self, result: AntToolResult) -> None:
        """Add a tool execution result to the trajectory."""
        if not self.enabled or not self.config.include_tool_calls:
            return

        tool_data = {
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "metadata": result.metadata,
            "timestamp": datetime.now().isoformat(),
        }

        self.trajectory_data["tool_calls"].append(tool_data)

    def add_system_info(self, info: Dict[str, Any]) -> None:
        """Add system information to the trajectory."""
        if not self.enabled or not self.config.include_system_info:
            return

        self.trajectory_data["system_info"].update(info)

    def save(self, filename: Optional[str] = None) -> str:
        """Save the trajectory to a file.

        Args:
            filename: Optional filename. If not provided, uses config.output_file.

        Returns:
            Path to the saved trajectory file
        """
        if not self.enabled:
            return ""

        # Use config output_file if filename not provided
        if not filename:
            filename = self.config.output_file

        filepath = self.output_dir / filename

        # Update end time
        self.trajectory_data["session_info"]["end_time"] = datetime.now().isoformat()

        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.trajectory_data, f, indent=2, ensure_ascii=False)

        return str(filepath)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the trajectory."""
        if not self.enabled:
            return {"enabled": False}

        return {
            "enabled": True,
            "message_count": len(self.trajectory_data["messages"]),
            "tool_call_count": len(self.trajectory_data["tool_calls"]),
            "session_duration": self._calculate_duration(),
            "successful_tools": sum(1 for call in self.trajectory_data["tool_calls"] if call.get("success", False)),
            "failed_tools": sum(1 for call in self.trajectory_data["tool_calls"] if not call.get("success", True)),
            "output_file": self.config.output_file,
            "output_dir": str(self.output_dir)
        }

    def _calculate_duration(self) -> Optional[str]:
        """Calculate session duration."""
        if "start_time" not in self.trajectory_data["session_info"]:
            return None

        start_time = datetime.fromisoformat(self.trajectory_data["session_info"]["start_time"])
        end_time = datetime.fromisoformat(
            self.trajectory_data["session_info"].get("end_time", datetime.now().isoformat())
        )

        duration = end_time - start_time
        return str(duration)

    def reset(self) -> None:
        """Reset the trajectory recorder."""
        self.trajectory_data = {
            "session_info": {
                "start_time": datetime.now().isoformat(),
                "version": "0.1.0",
            },
            "messages": [],
            "tool_calls": [],
            "system_info": {}
        }