#!/usr/bin/env python3
# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Hydra-based CLI interface for Ant Agent."""

import os
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ant_agent.agent.ant_agent import AntAgent
from ant_agent.utils.trajectory_recorder import TrajectoryRecorder
from ant_agent.utils.hydra_config import load_config, HydraConfig


console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Ant Agent - LangChain-based AI agent for software engineering tasks."""
    pass


@cli.command()
@click.argument("task", required=False)
@click.option("--config", "-c", help="Configuration directory path")
@click.option("--model", "-m", help="Model configuration to use")
@click.option("--provider", "-p", help="Provider configuration to use")
@click.option("--agent", "-a", help="Agent configuration to use", default="ant_agent")
@click.option("--max-steps", type=int, help="Maximum number of steps")
@click.option("--trajectory-file", help="Save trajectory to file")
@click.option("--working-dir", help="Working directory for execution")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option("--show-config", is_flag=True, help="Show configuration and exit")
@click.pass_context
def run(ctx, task: Optional[str], config: Optional[str], model: Optional[str],
         provider: Optional[str], agent: str, max_steps: Optional[int],
         trajectory_file: Optional[str], working_dir: Optional[str],
         debug: bool, show_config: bool):
    """Run a task with Ant Agent using Hydra configuration."""

    try:
        # Build Hydra overrides
        overrides = []

        if max_steps:
            overrides.append(f"max_steps={max_steps}")
        if debug:
            overrides.append("debug=true")
        if task:
            # Quote the task to handle special characters
            overrides.append(f"task=\"{task}\"")
        if trajectory_file:
            overrides.append(f"trajectory_file={trajectory_file}")
        if working_dir:
            overrides.append(f"working_dir={working_dir}")

        # Load configuration
        cfg = load_config(
            agent_name=agent,
            model_name=model,
            provider_name=provider,
            overrides=overrides,
            config_dir=config,
        )

        if show_config:
            console.print("📋 Configuration:", style="bold")
            console.print(cfg)
            return

        # Change working directory if specified
        if cfg.working_dir:
            os.chdir(cfg.working_dir)
            console.print(f"Working directory: {cfg.working_dir}", style="dim")

        # Get configurations
        agent_config = cfg.agent

        # Create model config by merging model and provider configs
        from omegaconf import OmegaConf
        from ant_agent.utils.config import LLMProvider, ModelConfig

        # Load provider config dynamically based on model_provider
        model_cfg = cfg.model
        provider_name = model_cfg.get('provider', 'deepseek')

        # Load the specific provider config
        provider_cfg = load_config(
            agent_name=agent,
            model_name=model,
            provider_name=provider_name,
            config_dir=config,
        ).provider

        # Merge model and provider configs
        merged_cfg = OmegaConf.merge(model_cfg, provider_cfg)

        # Map field names to match ModelConfig
        if "provider" in merged_cfg:
            # Create a new dict with the correct field name
            config_dict = OmegaConf.to_container(merged_cfg)
            config_dict['model_provider'] = LLMProvider(config_dict['provider'])
            del config_dict['provider']
            merged_cfg = OmegaConf.create(config_dict)

        # Convert to ModelConfig object
        model_config = ModelConfig(**merged_cfg)

        trajectory_config = cfg.trajectory

        # Initialize trajectory recorder
        trajectory_recorder = TrajectoryRecorder(trajectory_config) if trajectory_config.enabled else None

        # Display startup information
        console.print(Panel.fit(
            Text("Ant Agent", style="bold blue") + "\n" +
            Text(f"Task: {cfg.task}", style="italic"),
            title="🚀 Starting"
        ))

        # Create agent
        ant_agent = AntAgent(
            agent_config=agent_config,
            model_config=model_config,
            trajectory_recorder=trajectory_recorder
        )

        # Run the task
        response = ant_agent.run(cfg.task)

        console.print("\n" + "="*50)
        console.print("🎯 Result:", style="bold green")
        console.print(response)

        # Show thinking summary if available
        if hasattr(ant_agent, 'get_thinking_summary'):
            thinking_summary = ant_agent.get_thinking_summary()
            if thinking_summary and "No thoughts recorded yet" not in thinking_summary:
                console.print("\n🧠 Thinking Process:")
                console.print(thinking_summary)

        # Save trajectory
        if cfg.trajectory_file or (trajectory_config and trajectory_config.enabled):
            filepath = ant_agent.save_trajectory(cfg.trajectory_file)
            if filepath:
                console.print(f"\n📝 Trajectory saved to: {filepath}", style="dim")

        # Show trajectory summary
        if trajectory_recorder:
            summary = trajectory_recorder.get_summary()
            if summary.get("enabled"):
                console.print(f"\n📊 Session: {summary['message_count']} messages, "
                             f"{summary['tool_call_count']} tool calls, "
                             f"{summary.get('session_duration', 'unknown')} duration")

    except Exception as e:
        console.print(f"\n❌ Error: {str(e)}", style="red")
        if debug:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)
    finally:
        # Clean up Hydra
        HydraConfig.cleanup()


@cli.command()
@click.option("--config", "-c", help="Configuration directory path")
@click.option("--model", "-m", help="Model configuration to use")
@click.option("--provider", "-p", help="Provider configuration to use")
@click.option("--agent", "-a", help="Agent configuration to use", default="ant_agent")
@click.option("--debug", is_flag=True, help="Enable debug mode")
def show_config(config: Optional[str], model: Optional[str], provider: Optional[str],
                agent: str, debug: bool):
    """Show current configuration."""

    try:
        # Load configuration
        cfg = load_config(
            agent_name=agent,
            model_name=model,
            provider_name=provider,
            config_dir=config,
        )

        console.print("📋 Configuration:", style="bold")
        console.print(cfg)

        # Show available models and providers
        if config:
            config_dir = Path(config)
        else:
            # Try configs directory first, then config
            potential_dirs = [
                Path(__file__).parent.parent / "configs",
                Path(__file__).parent.parent / "config",
            ]
            config_dir = None
            for potential_dir in potential_dirs:
                if potential_dir.exists():
                    config_dir = potential_dir
                    break

        if config_dir:
            # Check both configs/model and model directories
            models_dirs = [config_dir / "model", config_dir / "configs" / "model"]
            providers_dirs = [config_dir / "provider", config_dir / "configs" / "provider"]

            console.print(f"\n🤖 Available Models:")
            for models_dir in models_dirs:
                if models_dir.exists():
                    for model_file in models_dir.glob("*.yaml"):
                        console.print(f"  - {model_file.stem}")

            console.print(f"\n🔌 Available Providers:")
            for providers_dir in providers_dirs:
                if providers_dir.exists():
                    for provider_file in providers_dir.glob("*.yaml"):
                        console.print(f"  - {provider_file.stem}")

    except Exception as e:
        console.print(f"❌ Error loading configuration: {str(e)}", style="red")
        if debug:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)
    finally:
        # Clean up Hydra
        HydraConfig.cleanup()


@cli.command()
@click.option("--config", "-c", help="Configuration directory path")
@click.option("--model", "-m", help="Model configuration to use")
@click.option("--provider", "-p", help="Provider configuration to use")
@click.option("--agent", "-a", help="Agent configuration to use", default="ant_agent")
@click.option("--debug", is_flag=True, help="Enable debug mode")
def interactive(config: Optional[str], model: Optional[str], provider: Optional[str],
                agent: str, debug: bool):
    """Start interactive mode with Ant Agent."""

    try:
        # Load configuration
        cfg = load_config(
            agent_name=agent,
            model_name=model,
            provider_name=provider,
            config_dir=config,
        )

        # Get configurations
        agent_config = cfg.agent

        # Create model config by merging model and provider configs
        from omegaconf import OmegaConf
        from ant_agent.utils.config import LLMProvider, ModelConfig

        # Load provider config dynamically based on model_provider
        model_cfg = cfg.model
        provider_name = model_cfg.get('provider', 'deepseek')

        # Load the specific provider config
        provider_cfg = load_config(
            agent_name=agent,
            model_name=model,
            provider_name=provider_name,
            config_dir=config,
        ).provider

        # Merge model and provider configs
        merged_cfg = OmegaConf.merge(model_cfg, provider_cfg)

        # Map field names to match ModelConfig
        if "provider" in merged_cfg:
            # Create a new dict with the correct field name
            config_dict = OmegaConf.to_container(merged_cfg)
            config_dict['model_provider'] = LLMProvider(config_dict['provider'])
            del config_dict['provider']
            merged_cfg = OmegaConf.create(config_dict)

        # Convert to ModelConfig object
        model_config = ModelConfig(**merged_cfg)

        trajectory_config = cfg.trajectory

        # Initialize trajectory recorder
        trajectory_recorder = TrajectoryRecorder(trajectory_config) if trajectory_config.enabled else None

        console.print(Panel.fit(
            Text("Ant Agent Interactive Mode", style="bold blue") + "\n" +
            Text("Type 'exit' or 'quit' to end the session", style="dim"),
            title="🤖 Welcome"
        ))

        # Create agent
        ant_agent = AntAgent(
            agent_config=agent_config,
            model_config=model_config,
            trajectory_recorder=trajectory_recorder
        )

        while True:
            try:
                task_input = console.input("\n🎯 What would you like me to help you with? ")

                if task_input.lower() in ['exit', 'quit']:
                    console.print("👋 Goodbye!", style="blue")
                    break

                if not task_input.strip():
                    continue

                console.print("🤔 Thinking...")
                response = ant_agent.run(task_input)
                console.print("\n💬 Response:")
                console.print(response)

            except KeyboardInterrupt:
                console.print("\n⚠️  Task interrupted", style="yellow")
                continue
            except Exception as e:
                console.print(f"\n❌ Error: {str(e)}", style="red")
                if debug:
                    import traceback
                    console.print(traceback.format_exc())
                continue

    except Exception as e:
        console.print(f"❌ Error: {str(e)}", style="red")
        if debug:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)
    finally:
        # Clean up Hydra
        HydraConfig.cleanup()


if __name__ == "__main__":
    cli()