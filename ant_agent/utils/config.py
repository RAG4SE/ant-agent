# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Configuration classes for Ant Agent."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, List, Dict, Any
from pathlib import Path

# Import yaml loading - try to use pyyaml first, fallback to ruamel if needed
try:
    import yaml
except ImportError:
    try:
        from ruamel.yaml import YAML
        yaml = YAML()
    except ImportError:
        raise ImportError("Please install pyyaml: pip install pyyaml")


# Module-level logger
logger = logging.getLogger(__name__)


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
    LINGXI = "lingxi"
    KIMI = "kimi"


@dataclass
class ModelConfig:
    """Model configuration for LLM clients."""

    model: str
    model_provider: LLMProvider
    temperature: float
    top_p: float
    top_k: int
    parallel_tool_calls: bool
    max_retries: int
    max_tokens: Optional[int]
    max_completion_tokens: Optional[int]
    supports_tool_calling: bool
    candidate_count: Optional[int]
    stop_sequences: Optional[List[str]]
    
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

    model: str
    max_steps: int
    allow_mcp_servers: List[str]
    mcp_servers: Dict[str, Any]
    skill: str  # Selected skill for the agent


@dataclass
class LSPConfig:
    """LSP configuration for Multilspy LSP Manager."""

    workspace: str
    enabled: bool
    auto_start: bool
    verbose: bool
    use_async: bool
    languages: List[str]


@dataclass
class TrajectoryConfig:
    """Trajectory recording configuration."""

    enabled: bool
    output_dir: str
    output_file: Optional[str]
    save_on_completion: bool
    include_messages: bool
    include_tool_results: bool
    include_llm_calls: bool
    include_tool_calls: bool
    include_system_info: bool


@dataclass
class AppConfig:
    """Application configuration."""
    
    debug: bool
    working_dir: str
    max_steps: int
    must_patch: bool
    verbose: bool
    show_config: bool
    agent: AgentConfig
    model: ModelConfig
    trajectory: TrajectoryConfig
    lsp: LSPConfig

    def __post_init__(self):
        """Post-initialization to set up cross-references."""
        # Ensure working_dir and lsp.workspace are synchronized
        if hasattr(self, 'working_dir') and hasattr(self, 'lsp'):
            # Convert to absolute path for consistency
            abs_working_dir = str(Path(self.working_dir).absolute())
            object.__setattr__(self, 'working_dir', abs_working_dir)
            object.__setattr__(self.lsp, 'workspace', abs_working_dir)

    def __setattr__(self, name, value):
        """Override to sync working_dir changes to lsp.workspace."""
        super().__setattr__(name, value)
        if name == 'working_dir' and hasattr(self, 'lsp'):
            # Sync working_dir changes to lsp.workspace
            abs_path = str(Path(value).absolute())
            super().__setattr__('working_dir', abs_path)
            object.__setattr__(self.lsp, 'workspace', abs_path)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """
        Create AppConfig from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            AppConfig instance
        """
        # Process environment variable references in the format ${oc.env:VAR_NAME}
        processed_data = cls._process_env_vars(data)

        # Create configurations from the loaded data
        agent_data = processed_data['agent']
        agent = AgentConfig(
            model=agent_data['model'],
            max_steps=agent_data['max_steps'],
            allow_mcp_servers=agent_data['allow_mcp_servers'],
            mcp_servers=agent_data['mcp_servers'],
            skill=agent_data['skill']  # Required field
        )

        model_data = processed_data['model']
        provider_str = model_data['model_provider']
        provider = LLMProvider(provider_str.lower()) if isinstance(provider_str, str) else provider_str

        model = ModelConfig(
            model=model_data['model'],
            model_provider=provider,
            temperature=model_data['temperature'],
            top_p=model_data['top_p'],
            top_k=model_data['top_k'],
            parallel_tool_calls=model_data['parallel_tool_calls'],
            max_retries=model_data['max_retries'],
            max_tokens=model_data['max_tokens'],
            max_completion_tokens=model_data['max_completion_tokens'],
            supports_tool_calling=model_data['supports_tool_calling'],
            candidate_count=model_data['candidate_count'],
            stop_sequences=model_data['stop_sequences']
        )

        trajectory_data = processed_data['trajectory']
        trajectory = TrajectoryConfig(
            enabled=trajectory_data['enabled'],
            output_dir=trajectory_data['output_dir'],
            output_file=trajectory_data['output_file'],
            save_on_completion=trajectory_data['save_on_completion'],
            include_messages=trajectory_data['include_messages'],
            include_tool_results=trajectory_data['include_tool_results'],
            include_llm_calls=trajectory_data['include_llm_calls'],
            include_tool_calls=trajectory_data['include_tool_calls'],
            include_system_info=trajectory_data['include_system_info']
        )

        lsp_data = processed_data['lsp'] if 'lsp' in processed_data else {}
        app_config = processed_data['app']
        logger.info(f"LSP workspace: {app_config['working_dir']}")
        lsp = LSPConfig(
            enabled=lsp_data['enabled'],
            workspace=app_config['working_dir'],
            auto_start=lsp_data['auto_start'],
            verbose=lsp_data['verbose'],
            use_async=lsp_data['use_async'],
            languages=lsp_data['languages']
        )

        logger.info(f"Agent working on : {app_config['working_dir']}")
        # Create AppConfig instance
        config = cls(
            debug=app_config['debug'],
            working_dir=app_config['working_dir'],
            max_steps=app_config['max_steps'],
            must_patch=app_config['must_patch'],
            verbose=app_config['verbose'],
            show_config=app_config['show_config'],
            agent=agent,
            model=model,
            trajectory=trajectory,
            lsp=lsp,
        )

        return config

    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'AppConfig':
        """Load configuration from YAML file."""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)
    
    def to_yaml(self, yaml_path: str) -> None:
        """Save configuration to YAML file."""
        data = asdict(self)
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    
    @staticmethod
    def _process_env_vars(data):
        """Process environment variable references in the format ${oc.env:VAR_NAME}."""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                result[key] = AppConfig._process_env_vars(value)
            return result
        elif isinstance(data, list):
            return [AppConfig._process_env_vars(item) for item in data]
        elif isinstance(data, str):
            # Handle environment variable references like ${oc.env:VAR_NAME}
            if data.startswith("${oc.env:") and data.endswith("}"):
                var_name = data[9:-1]  # Extract variable name: ${oc.env:VAR_NAME} -> VAR_NAME
                return os.getenv(var_name, data)  # Return env value or original string if not found
            else:
                return data
        else:
            return data
    
    @staticmethod
    def load_config(config_path: str = "ant_config.yaml") -> 'AppConfig':
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to configuration file (default: ant_config.yaml)

        Returns:
            AppConfig instance loaded from YAML
        """
        return AppConfig.from_yaml(config_path)

    def get_agent_config(self, agent_name: str = None) -> AgentConfig:
        """Get agent configuration."""
        # If a specific agent name is provided but not default, we'd need to support multiple agents
        # For now, return the default agent config
        return self.agent
    
    def get_model_config(self, model_name: str = None) -> ModelConfig:
        """Get model configuration."""
        # If a specific model name is provided but not default, we'd need to support multiple models
        # For now, return the default model config
        return self.model
    