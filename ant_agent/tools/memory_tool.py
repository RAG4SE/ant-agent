# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Memory tool for Ant Agent to interact with MemoryManager."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Type

from ant_agent.tools.base import AntTool, AntToolResult
from ant_agent.utils.memory import MemoryManager, shared_memory_manager
from pydantic import BaseModel, Field

# Global namespace for all memory tool operations
memory_tool_namespace = ("agent", "tool", "memory")


class MemoryStoreInput(BaseModel):
    """Input schema for storing memory."""
    key: str = Field(description="The key to store the value under")
    value: Any = Field(description="The value to store in memory")


class MemoryRetrieveInput(BaseModel):
    """Input schema for retrieving memory."""
    key: str = Field(description="The key to retrieve the value for")
    default: Any = Field(
        default=None,
        description="Default value to return if key is not found"
    )


class MemorySearchInput(BaseModel):
    """Input schema for searching memory."""
    pass


class MemoryDeleteInput(BaseModel):
    """Input schema for deleting memory."""
    key: str = Field(description="The key to delete from memory")


class MemoryListInput(BaseModel):
    """Input schema for listing memory keys."""
    pass


class MemoryStoreTool(AntTool):
    """Tool for storing information in memory."""

    name: str = "memory_store"
    description: str = (
        "Store important information in memory for later retrieval. "
        "Use this to save intermediate results, context, or any data that needs to be "
        "accessed later during agent execution."
    )
    args_schema: Type[BaseModel] = MemoryStoreInput
    memory_manager: Optional[MemoryManager] = None

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.memory_manager = shared_memory_manager

    def _run(self, key: str, value: Any) -> AntToolResult:
        """Store a value in memory."""
        try:
            self.memory_manager.store(key, value, memory_tool_namespace)
            return AntToolResult(
                success=True,
                output=f"Successfully stored value under key '{key}' in memory",
                metadata={"key": key, "namespace": memory_tool_namespace}
            )
        except Exception as e:
            return AntToolResult(
                success=False,
                error=f"Failed to store memory: {str(e)}"
            )


class MemoryRetrieveTool(AntTool):
    """Tool for retrieving information from memory."""

    name: str = "memory_retrieve"
    description: str = (
        "Retrieve previously stored information from memory. "
        "Use this to access data that was saved earlier during agent execution."
    )
    args_schema: Type[BaseModel] = MemoryRetrieveInput
    memory_manager: Optional[MemoryManager] = None

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.memory_manager = shared_memory_manager

    def _run(self, key: str, default: Any = None) -> AntToolResult:
        """Retrieve a value from memory."""
        try:
            value = self.memory_manager.retrieve(key, memory_tool_namespace, default)
            if value is None:
                return AntToolResult(
                    success=True,
                    output=f"No value found for key '{key}'",
                    metadata={"key": key, "found": False}
                )

            return AntToolResult(
                success=True,
                output=f"Retrieved value for key '{key}': {str(value)}",
                metadata={"key": key, "value": value, "found": True}
            )
        except Exception as e:
            return AntToolResult(
                success=False,
                error=f"Failed to retrieve memory: {str(e)}"
            )


class MemorySearchTool(AntTool):
    """Tool for searching all items in a memory namespace."""

    name: str = "memory_search"
    description: str = (
        "Search and retrieve all items from a memory namespace. "
        "Use this to see what information is currently stored in memory."
    )
    args_schema: Type[BaseModel] = MemorySearchInput
    memory_manager: Optional[MemoryManager] = None

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.memory_manager = shared_memory_manager

    def _run(self) -> AntToolResult:
        """Search all items in memory."""
        try:
            items = self.memory_manager.get_all(memory_tool_namespace)
            if not items:
                return AntToolResult(
                    success=True,
                    output="No items found in memory",
                    metadata={"items": [], "count": 0}
                )

            # Format the output for better readability
            output_lines = [f"Found {len(items)} items in memory:"]
            for i, item in enumerate(items, 1):
                output_lines.append(f"{i}. Key: {item['key']}, Value: {str(item['value'])}")

            return AntToolResult(
                success=True,
                output="\n".join(output_lines),
                metadata={"items": items, "count": len(items)}
            )
        except Exception as e:
            return AntToolResult(
                success=False,
                error=f"Failed to search memory: {str(e)}"
            )


class MemoryDeleteTool(AntTool):
    """Tool for deleting information from memory."""

    name: str = "memory_delete"
    description: str = (
        "Delete information from memory. "
        "Use this to remove data that is no longer needed."
    )
    args_schema: Type[BaseModel] = MemoryDeleteInput
    memory_manager: Optional[MemoryManager] = None

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.memory_manager = shared_memory_manager

    def _run(self, key: str) -> AntToolResult:
        """Delete a value from memory."""
        try:
            deleted = self.memory_manager.delete(key, memory_tool_namespace)
            if deleted:
                return AntToolResult(
                    success=True,
                    output=f"Successfully deleted key '{key}' from memory",
                    metadata={"key": key, "deleted": True}
                )
            else:
                return AntToolResult(
                    success=True,
                    output=f"Key '{key}' not found in memory",
                    metadata={"key": key, "deleted": False}
                )
        except Exception as e:
            return AntToolResult(
                success=False,
                error=f"Failed to delete memory: {str(e)}"
            )


class MemoryListTool(AntTool):
    """Tool for listing all keys in a memory namespace."""

    name: str = "memory_list_keys"
    description: str = (
        "List all keys currently stored in a memory namespace. "
        "Use this to see what keys are available for retrieval."
    )
    args_schema: Type[BaseModel] = MemoryListInput
    memory_manager: Optional[MemoryManager] = None

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.memory_manager = shared_memory_manager

    def _run(self) -> AntToolResult:
        """List all keys in memory."""
        try:
            keys = self.memory_manager.list_keys(memory_tool_namespace)

            if not keys:
                return AntToolResult(
                    success=True,
                    output="No keys found in memory",
                    metadata={"keys": [], "count": 0}
                )

            return AntToolResult(
                success=True,
                output=f"Keys in memory: {', '.join(keys)}",
                metadata={"keys": keys, "count": len(keys)}
            )
        except Exception as e:
            return AntToolResult(
                success=False,
                error=f"Failed to list memory keys: {str(e)}"
            )