#!/usr/bin/env python3
"""Example demonstrating AntAgent with LSP manager for definition fetching."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from ant_agent.agent.ant_agent import AntAgent
from ant_agent.lsp.multilspy_manager import get_lsp_manager
from ant_agent.utils.config import AppConfig
from ant_agent.utils.trajectory_recorder import TrajectoryRecorder


async def test_lsp_use_for_python():
    # Load configuration from YAML file
    app_config = AppConfig.load_config('ant_config.yaml')
    app_config.working_dir = "./bench/test_var_from_other_file_python"

    # Create AntAgent instance with AppConfig - it will handle all internal configurations
    agent = AntAgent(app_config=app_config)

    # Ask for the definition of get_lsp_manager function call on line 19
    print("Asking agent for the definition in Python...")
    result = await agent.arun("What is the definition of `a` (line 4) in the main.py Return in JSON: {{\"def\": <definition>}}")
    print("Result:", result)

    # Save trajectory with custom name
    trajectory_path = agent.save_trajectory("lsp_definition_query_trajectory_python.json")
    print(f"Trajectory saved to: {trajectory_path}")


async def test_lsp_use_for_solidity():
    # Load configuration from YAML file
    app_config = AppConfig.load_config('ant_config.yaml')
    app_config.working_dir = "./bench/solidity_vulnerable_contracts"

    # Create AntAgent instance with AppConfig - it will handle all internal configurations
    agent = AntAgent(app_config=app_config)

    # Ask for the definition of get_lsp_manager function call on line 19
    print("Asking agent for the definition in Solidity...")
    result = await agent.arun("What is the definition of `IComplexToken` (line 20) in the ComplexToken.sol? Return in JSON: {{\"def\": <definition>}}")
    print("Result:", result)

    # Save trajectory with custom name
    trajectory_path = agent.save_trajectory("lsp_definition_query_trajectory_solidity.json")
    print(f"Trajectory saved to: {trajectory_path}")

async def test_common_use():
    # Load configuration from YAML file
    app_config = AppConfig.load_config('ant_config.yaml')
    app_config.working_dir = "./bench/test_var_from_other_file_python"

    # Create AntAgent instance with AppConfig - it will handle all internal configurations
    agent = AntAgent(app_config=app_config)

    # Ask for the definition of get_lsp_manager function call on line 19
    print("Asking agent for understanding of ant-agent")
    result = await agent.arun("Analyze this repo and tell me what does it do?")
    print("Result:", result)

    # Save trajectory with custom name
    trajectory_path = agent.save_trajectory("repo_understanding.json")
    print(f"Trajectory saved to: {trajectory_path}")
    
    

async def main():
    # print("Test LSP use")
    # await test_lsp_use_for_python()
    # print("Test Python repo understanding")
    # await test_common_use()
    print("Test Solidity repo understanding")
    await test_lsp_use_for_solidity()
    


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())