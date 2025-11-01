# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Configuration classes for Ant Agent."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any


class LLMProvider(Enum):
    """Supported LLM providers."""
    
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    GOOGLE = "google"
    OLLAMA = "ollama"
    AZURE = "azure"
    OPENROUTER = "openrouter"
    DOUBAO = "doubao"
    DASHSCOPE = "dashscope"


@dataclass
class ModelConfig:
    """Model configuration for LLM clients."""
    
    model: str
    model_provider: LLMProvider
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    api_version: Optional[str] = None
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    parallel_tool_calls: bool = True
    max_retries: int = 3
    max_tokens: Optional[int] = None
    max_completion_tokens: Optional[int] = None
    supports_tool_calling: bool = True
    candidate_count: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    
    def get_max_tokens_param(self) -> int:
        """Get the maximum tokens parameter value."""
        if self.max_completion_tokens is not None:
            return self.max_completion_tokens
        elif self.max_tokens is not None:
            return self.max_tokens
        else:
            return 4096  # Default value
    
    def should_use_max_completion_tokens(self) -> bool:
        """Determine whether to use the max_completion_tokens parameter."""
        return (
            self.max_completion_tokens is not None
            and self.model_provider == LLMProvider.AZURE
            and ("gpt-5" in self.model or "o3" in self.model or "o4-mini" in self.model)
        )


@dataclass
class AgentConfig:
    """Agent configuration."""
    
    name: str
    model: str
    max_steps: int = 200
    tools: List[str] = None
    enable_lakeview: bool = False
    json_formatter_model: Optional[str] = None
    allow_mcp_servers: List[str] = None
    mcp_servers: Dict[str, Any] = None
    
    def __post_init__(self):
        """Post-initialization to set default values."""
        if self.tools is None:
            self.tools = [
                "bash",
                "edit_tool",
                "create_file",
                "sequential_thinking",
                "task_done"
            ]
        if self.allow_mcp_servers is None:
            self.allow_mcp_servers = []
        if self.mcp_servers is None:
            self.mcp_servers = {}


@dataclass
class TrajectoryConfig:
    """Trajectory recording configuration."""
    
    enabled: bool = True
    output_dir: str = "trajectories"
    output_file: Optional[str] = None
    save_on_completion: bool = True
    include_messages: bool = True
    include_tool_results: bool = True
    include_llm_calls: bool = True
    include_tool_calls: bool = True
    include_system_info: bool = True
    
    def __post_init__(self):
        """Post-initialization to set default values."""
        if self.output_file is None:
            self.output_file = "trajectory.json"


@dataclass
class AppConfig:
    """Application configuration."""
    
    debug: bool = False
    working_dir: Optional[str] = None
    max_steps: int = 200
    task: Optional[str] = None
    trajectory_file: Optional[str] = None
    must_patch: bool = False
    verbose: bool = True
    show_config: bool = False
    agent: Optional[AgentConfig] = None
    model: Optional[ModelConfig] = None
    trajectory: Optional[TrajectoryConfig] = None