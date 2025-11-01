# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Hydra-based configuration system for Ant Agent."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from hydra import compose, initialize_config_dir
from hydra.core.global_hydra import GlobalHydra
from omegaconf import DictConfig, OmegaConf

from ant_agent.utils.config import LLMProvider


class HydraConfig:
    """Hydra-based configuration manager."""

    def __init__(self, config_dir: Optional[str] = None):
        """Initialize Hydra configuration.

        Args:
            config_dir: Path to configuration directory
        """
        if config_dir is None:
            # Try configs directory first, then fallback to config
            potential_dirs = [
                Path(__file__).parent.parent.parent / "configs",
                Path(__file__).parent.parent.parent / "config",
            ]
            for potential_dir in potential_dirs:
                if potential_dir.exists() and (potential_dir / "config.yaml").exists():
                    config_dir = potential_dir
                    break
            else:
                config_dir = potential_dirs[0]  # fallback to first option

        self.config_dir = Path(config_dir)
        self._cfg: Optional[DictConfig] = None

        # Initialize Hydra
        self._initialize_hydra()

    def _initialize_hydra(self) -> None:
        """Initialize Hydra with custom config directory."""
        # Clear any existing Hydra instance
        if GlobalHydra().is_initialized():
            GlobalHydra.instance().clear()

        # Initialize Hydra with our config directory
        initialize_config_dir(
            config_dir=str(self.config_dir),
            version_base=None,
        )

    def load_config(
        self,
        agent_name: str = "ant_agent",
        model_name: Optional[str] = None,
        provider_name: Optional[str] = None,
        overrides: Optional[list] = None,
    ) -> DictConfig:
        """Load configuration using Hydra.

        Args:
            agent_name: Name of agent configuration
            model_name: Name of model configuration
            provider_name: Name of provider configuration
            overrides: List of override strings

        Returns:
            Combined configuration dictionary
        """
        # Build overrides list
        override_list = overrides or []

        if model_name:
            override_list.append(f"model={model_name}")
        if provider_name:
            override_list.append(f"provider={provider_name}")

        # Compose configuration
        self._cfg = compose(
            config_name="config",
            overrides=override_list,
            return_hydra_config=False,
        )

        return self._cfg

    @property
    def cfg(self) -> DictConfig:
        """Get current configuration."""
        if self._cfg is None:
            self.load_config()
        return self._cfg

    def get_agent_config(self) -> DictConfig:
        """Get agent configuration."""
        return self.cfg.agent

    def get_model_config(self) -> DictConfig:
        """Get model configuration."""
        return self.cfg.model

    def get_provider_config(self) -> DictConfig:
        """Get provider configuration."""
        return self.cfg.provider

    def get_trajectory_config(self) -> DictConfig:
        """Get trajectory configuration."""
        return self.cfg.trajectory

    def merge_model_and_provider_config(self) -> DictConfig:
        """Merge model and provider configurations."""
        model_cfg = self.get_model_config()
        provider_cfg = self.get_provider_config()

        # Create merged config
        merged_cfg = OmegaConf.merge(model_cfg, provider_cfg)

        # Convert provider string to enum
        if "provider" in merged_cfg:
            merged_cfg.provider = LLMProvider(merged_cfg.provider)

        return merged_cfg

    def add_merge_method(self, cfg: DictConfig):
        """Add merge method to configuration object."""
        def merge_method():
            model_cfg = cfg.model
            provider_cfg = cfg.provider

            # Create merged config
            merged_cfg = OmegaConf.merge(model_cfg, provider_cfg)

            # Convert provider string to enum
            if "provider" in merged_cfg:
                merged_cfg.provider = LLMProvider(merged_cfg.provider)

            return merged_cfg

        # Add method to the config object
        cfg.merge_model_and_provider_config = merge_method
        return cfg

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to regular dictionary."""
        return OmegaConf.to_yaml(self.cfg)

    def save(self, output_path: str) -> None:
        """Save configuration to file."""
        OmegaConf.save(self.cfg, output_path)

    def show_config(self) -> str:
        """Get formatted configuration string for display."""
        return OmegaConf.to_yaml(self.cfg)

    @staticmethod
    def cleanup():
        """Clean up Hydra instance."""
        if GlobalHydra().is_initialized():
            GlobalHydra.instance().clear()


# Global configuration instance
_hydra_config: Optional[HydraConfig] = None


def get_hydra_config(config_dir: Optional[str] = None) -> HydraConfig:
    """Get global Hydra configuration instance.

    Args:
        config_dir: Path to configuration directory

    Returns:
        HydraConfig instance
    """
    global _hydra_config
    if _hydra_config is None:
        _hydra_config = HydraConfig(config_dir)
    return _hydra_config


def load_config(
    agent_name: str = "ant_agent",
    model_name: Optional[str] = None,
    provider_name: Optional[str] = None,
    overrides: Optional[list] = None,
    config_dir: Optional[str] = None,
) -> DictConfig:
    """Load configuration using Hydra.

    Args:
        agent_name: Name of agent configuration
        model_name: Name of model configuration
        provider_name: Name of provider configuration
        overrides: List of override strings
        config_dir: Path to configuration directory

    Returns:
        Combined configuration dictionary
    """
    hydra_config = get_hydra_config(config_dir)
    return hydra_config.load_config(
        agent_name=agent_name,
        model_name=model_name,
        provider_name=provider_name,
        overrides=overrides,
    )