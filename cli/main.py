#!/usr/bin/env python3
# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Main CLI interface for Ant Agent."""

import asyncio
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
from ant_agent.utils.config import AppConfig, LLMProvider
from ant_agent.utils.trajectory_recorder import TrajectoryRecorder


console = Console()


def load_app_config(config_path: Optional[str] = None) -> AppConfig:
    """Load application configuration."""
    if config_path and Path(config_path).exists():
        return AppConfig.from_yaml(config_path)

    # Try default locations
    default_paths = [
        "ant_config.yaml",
        "config/ant_config.yaml",
        os.path.expanduser("~/.ant_agent/config.yaml"),
    ]

    for path in default_paths:
        if Path(path).exists():
            console.print(f"Loading configuration from: {path}", style="dim")
            return AppConfig.from_yaml(path)

    console.print("No configuration file found. Using defaults.", style="yellow")
    return AppConfig()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Ant Agent - LangChain-based AI agent for software engineering tasks."""
    pass


@cli.command()
@click.argument("task")
@click.option("--config", "-c", help="Configuration file path")
@click.option("--provider", help="LLM provider to use")
@click.option("--model", help="Model to use")
@click.option("--max-steps", type=int, help="Maximum number of steps")
@click.option("--trajectory-file", help="Save trajectory to file")
@click.option("--working-dir", help="Working directory for execution")
def run(task: str, config: Optional[str], provider: Optional[str], model: Optional[str],
        max_steps: Optional[int], trajectory_file: Optional[str], working_dir: Optional[str]):
    """Run a single task with Ant Agent."""

    # Load configuration
    app_config = load_app_config(config)

    # Change working directory if specified
    if working_dir:
        os.chdir(working_dir)
        console.print(f"Working directory: {working_dir}", style="dim")

    # Get agent and model configurations
    agent_config = app_config.get_agent_config()
    model_config = app_config.get_model_config(agent_config.model)

    # Override with command line options
    if provider:
        if isinstance(provider, str):
            model_config.model_provider = LLMProvider(provider.lower())
        else:
            model_config.model_provider = provider
    if model:
        model_config.model = model
    if max_steps:
        agent_config.max_steps = max_steps

    # Merge provider configurations
    model_config = app_config.merge_provider_configs(model_config)

    # Initialize trajectory recorder
    trajectory_recorder = TrajectoryRecorder(app_config.trajectory)

    try:
        # Create and run agent
        console.print(Panel.fit(
            Text("Ant Agent", style="bold blue") + "\n" +
            Text(f"Task: {task}", style="italic"),
            title="🚀 Starting"
        ))

        agent = AntAgent(agent_config, model_config, trajectory_recorder)

        # Run the task
        response = agent.run(task)

        # Save trajectory
        if trajectory_file or app_config.trajectory.enabled:
            filepath = agent.save_trajectory(trajectory_file)
            if filepath:
                console.print(f"\n📝 Trajectory saved to: {filepath}", style="dim")

        console.print("\n" + "="*50)
        console.print("🎯 Result:", style="bold green")
        console.print(response)

        # Show thinking summary if available
        if hasattr(agent, 'get_thinking_summary'):
            thinking_summary = agent.get_thinking_summary()
            if thinking_summary and "No thoughts recorded yet" not in thinking_summary:
                console.print("\n🧠 Thinking Process:")
                console.print(thinking_summary)

        # Show trajectory summary
        if trajectory_recorder:
            summary = trajectory_recorder.get_summary()
            if summary.get("enabled"):
                console.print(f"\n📊 Session: {summary['message_count']} messages, "
                             f"{summary['tool_call_count']} tool calls, "
                             f"{summary.get('session_duration', 'unknown')} duration")

    except KeyboardInterrupt:
        console.print("\n⚠️  Task interrupted by user", style="yellow")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ Error: {str(e)}", style="red")
        sys.exit(1)


@cli.command()
@click.option("--config", "-c", help="Configuration file path")
def interactive(config: Optional[str]):
    """Start interactive mode with Ant Agent."""

    # Load configuration
    app_config = load_app_config(config)

    # Get agent and model configurations
    agent_config = app_config.get_agent_config()
    model_config = app_config.get_model_config(agent_config.model)

    # Merge provider configurations
    model_config = app_config.merge_provider_configs(model_config)

    console.print(Panel.fit(
        Text("Ant Agent Interactive Mode", style="bold blue") + "\n" +
        Text("Type 'exit' or 'quit' to end the session", style="dim"),
        title="🤖 Welcome"
    ))

    # Create agent
    agent = AntAgent(agent_config, model_config)

    try:
        while True:
            task = console.input("\n🎯 What would you like me to help you with? ")

            if task.lower() in ['exit', 'quit']:
                console.print("👋 Goodbye!", style="blue")
                break

            if not task.strip():
                continue

            try:
                console.print("🤔 Thinking...")
                response = agent.run(task)
                console.print("\n💬 Response:")
                console.print(response)

            except KeyboardInterrupt:
                console.print("\n⚠️  Task interrupted", style="yellow")
                continue
            except Exception as e:
                console.print(f"\n❌ Error: {str(e)}", style="red")
                continue

    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!", style="blue")


@cli.command()
@click.option("--config", "-c", help="Configuration file path")
def show_config(config: Optional[str]):
    """Show current configuration."""

    try:
        app_config = load_app_config(config)

        console.print("📋 Configuration:", style="bold")
        console.print(f"  Agent: {app_config.agent.name if app_config.agent else 'None'}")
        console.print(f"  Model: {app_config.model.model if app_config.model else 'None'}")
        console.print(f"  Provider: {app_config.model.model_provider.value if app_config.model else 'None'}")

        if app_config.agent:
            agent_config = app_config.get_agent_config()
            model_config = app_config.get_model_config()

            console.print(f"\n🤖 Agent ({agent_config.name}):")
            console.print(f"  Model: {model_config.model}")
            console.print(f"  Provider: {model_config.model_provider}")
            console.print(f"  Max Steps: {agent_config.max_steps}")
            console.print(f"  Tools: {', '.join(agent_config.tools) if agent_config.tools else 'None'}")

    except Exception as e:
        console.print(f"❌ Error loading configuration: {str(e)}", style="red")


if __name__ == "__main__":
    cli()