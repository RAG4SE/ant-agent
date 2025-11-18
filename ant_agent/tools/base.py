# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Base classes for Ant Agent tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, Union

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field


class AntToolResult(BaseModel):
    """Result of tool execution."""

    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AntTool(BaseTool, ABC):
    """Base class for Ant Agent tools using LangChain."""

    name: str
    description: str
    result: Optional[AntToolResult] = None

    @abstractmethod
    def _run(self, **kwargs: Any) -> AntToolResult:
        """Execute the tool synchronously."""
        pass

    async def _arun(self, **kwargs: Any) -> AntToolResult:
        """Execute the tool asynchronously."""
        # Default to sync execution if async not implemented
        return self._run(**kwargs)

    def run(self, **kwargs: Any) -> AntToolResult:
        """Public method to run the tool."""
        try:
            return self._run(**kwargs)
        except Exception as e:
            return AntToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}"
            )

    async def arun(self, **kwargs: Any) -> AntToolResult:
        """Public method to run the tool asynchronously."""
        try:
            return await self._arun(**kwargs)
        except Exception as e:
            return AntToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}"
            )

    @classmethod
    def get_tool_registry(cls) -> Dict[str, Type[AntTool]]:
        """Get registry of available tools."""
        return {}


class ToolError(Exception):
    """Base exception for tool errors."""

    def __init__(self, message: str, tool_name: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.tool_name = tool_name