#!/usr/bin/env python3
"""Example demonstrating AntAgent with LSP manager for definition fetching."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from ant_agent.agent.ant_agent import AntAgent
from ant_agent.agent.base_agent import BaseAgent
from ant_agent.lsp.multilspy_manager import get_lsp_manager
from ant_agent.utils.config import AppConfig
from ant_agent.utils.trajectory_recorder import TrajectoryRecorder

# Configure logging to show INFO and above messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# You can also set specific loggers to different levels if needed
# logging.getLogger("multilspy_lsp_manager").setLevel(logging.DEBUG)
# logging.getLogger("ant_agent.tools.multilspy_lsp_tools").setLevel(logging.DEBUG)


async def test_lsp_use_for_python():
    # Load configuration from YAML file
    config = {'app': {'debug': True, 'working_dir': './bench/test_var_from_other_file_python', 'max_steps': 200, 'must_patch': False, 'verbose': True, 'show_config': False}, 'agent': {'model': 'deepseek-chat', 'max_steps': 200, 'allow_mcp_servers': [], 'mcp_servers': {}, 'skill': 'SOURCE_CODE_ANALYSIS_WITH_LSP'}, 'model': {'model': 'deepseek-chat', 'model_provider': 'deepseek', 'temperature': 0.5, 'top_p': 1.0, 'top_k': 0, 'parallel_tool_calls': True, 'max_retries': 10, 'max_tokens': 4096, 'max_completion_tokens': None, 'supports_tool_calling': True, 'candidate_count': None, 'stop_sequences': None}, 'lsp': {'enabled': True, 'auto_start': True, 'verbose': False, 'use_async': True, 'languages': ['python', 'typescript', 'javascript', 'java', 'rust', 'go', 'csharp', 'kotlin', 'solidity']}, 'trajectory': {'enabled': True, 'output_dir': 'trajectories', 'output_file': 'trajectory.json', 'save_on_completion': True, 'include_messages': True, 'include_tool_results': True, 'include_llm_calls': True, 'include_tool_calls': True, 'include_system_info': True}}
    app_config = AppConfig.from_dict(config)

    agent = BaseAgent(app_config=app_config)

    # Ask for the definition of get_lsp_manager function call on line 19
    print("Asking agent for the definition in Python...")
    result = await agent.arun("What is the definition of `a` (line 4) in the main.py Return in JSON: {{\"def\": \u003cdefinition\u003e}}")
    print("Result:", result)

    # Save trajectory with custom name
    trajectory_path = agent.save_trajectory("lsp_definition_query_trajectory_python.json")
    print(f"Trajectory saved to: {trajectory_path}")


async def test_lsp_use_for_solidity():
    # Load configuration from YAML file
    config = {'app': {'debug': True, 'working_dir': './bench/solidity_vulnerable_contracts', 'max_steps': 200, 'must_patch': False, 'verbose': True, 'show_config': False}, 'agent': {'model': 'deepseek-chat', 'max_steps': 200, 'allow_mcp_servers': [], 'mcp_servers': {}, 'skill': 'SOURCE_CODE_ANALYSIS_WITH_LSP'}, 'model': {'model': 'deepseek-chat', 'model_provider': 'deepseek', 'temperature': 0.5, 'top_p': 1.0, 'top_k': 0, 'parallel_tool_calls': True, 'max_retries': 10, 'max_tokens': 4096, 'max_completion_tokens': None, 'supports_tool_calling': True, 'candidate_count': None, 'stop_sequences': None}, 'lsp': {'enabled': True, 'auto_start': True, 'verbose': False, 'use_async': True, 'languages': ['python', 'typescript', 'javascript', 'java', 'rust', 'go', 'csharp', 'kotlin', 'solidity']}, 'trajectory': {'enabled': True, 'output_dir': 'trajectories', 'output_file': 'trajectory.json', 'save_on_completion': True, 'include_messages': True, 'include_tool_results': True, 'include_llm_calls': True, 'include_tool_calls': True, 'include_system_info': True}}
    app_config = AppConfig.from_dict(config)

    agent = BaseAgent(app_config=app_config)

    # Ask for the definition of get_lsp_manager function call on line 19
    print("Asking agent for the definition in Solidity...")
    result = await agent.arun("What is the definition of `IComplexToken` (line 20) in the ComplexToken.sol? Return in JSON: {{\"def\": \u003cdefinition\u003e}}")
    print("Result:", result)

    # Save trajectory with custom name
    trajectory_path = agent.save_trajectory("lsp_definition_query_trajectory_solidity.json")
    print(f"Trajectory saved to: {trajectory_path}")


async def test_lsp_use_for_solidity2():
    # Load configuration from YAML file
    config = {'app': {'debug': True, 'working_dir': './bench/solidity-interface-demo', 'max_steps': 200, 'must_patch': False, 'verbose': True, 'show_config': False}, 'agent': {'model': 'deepseek-chat', 'max_steps': 200, 'allow_mcp_servers': [], 'mcp_servers': {}, 'skill': 'SOURCE_CODE_ANALYSIS_WITH_LSP'}, 'model': {'model': 'deepseek-chat', 'model_provider': 'deepseek', 'temperature': 0.5, 'top_p': 1.0, 'top_k': 0, 'parallel_tool_calls': True, 'max_retries': 10, 'max_tokens': 4096, 'max_completion_tokens': None, 'supports_tool_calling': True, 'candidate_count': None, 'stop_sequences': None}, 'lsp': {'enabled': True, 'auto_start': True, 'verbose': False, 'use_async': True, 'languages': ['python', 'typescript', 'javascript', 'java', 'rust', 'go', 'csharp', 'kotlin', 'solidity']}, 'trajectory': {'enabled': True, 'output_dir': 'trajectories', 'output_file': 'trajectory.json', 'save_on_completion': True, 'include_messages': True, 'include_tool_results': True, 'include_llm_calls': True, 'include_tool_calls': True, 'include_system_info': True}}
    app_config = AppConfig.from_dict(config)

    agent = BaseAgent(app_config=app_config)

    # Ask for the definition of get_lsp_manager function call on line 19
    print("Asking agent about Solidity...")
    result = await agent.arun(f"Check if the function call to storeData in file contracts/DataManager.sol at line 113 (0-based) is a call to a function from a thrid-party repo? Return as JSON {{\"answer\": \"yes or no\"}}.")
    print("Result:", result)

    # Save trajectory with custom name
    trajectory_path = agent.save_trajectory("lsp_definition_query_trajectory_solidity2.json")
    print(f"Trajectory saved to: {trajectory_path}")

async def test_lsp_use_for_solidity3():
    # Test SOURCE_CODE_ANALYSIS_WITHOUT_LSP
    config = {'app': {'debug': True, 'working_dir': './bench/solidity-interface-demo', 'max_steps': 200, 'must_patch': False, 'verbose': True, 'show_config': False}, 'agent': {'model': 'deepseek-chat', 'max_steps': 200, 'allow_mcp_servers': [], 'mcp_servers': {}, 'skill': 'SOURCE_CODE_ANALYSIS_WITHOUT_LSP'}, 'model': {'model': 'deepseek-chat', 'model_provider': 'deepseek', 'temperature': 0.5, 'top_p': 1.0, 'top_k': 0, 'parallel_tool_calls': True, 'max_retries': 10, 'max_tokens': 4096, 'max_completion_tokens': None, 'supports_tool_calling': True, 'candidate_count': None, 'stop_sequences': None}, 'lsp': {'enabled': True, 'auto_start': True, 'verbose': False, 'use_async': True, 'languages': ['python', 'typescript', 'javascript', 'java', 'rust', 'go', 'csharp', 'kotlin', 'solidity']}, 'trajectory': {'enabled': True, 'output_dir': 'trajectories', 'output_file': 'trajectory.json', 'save_on_completion': True, 'include_messages': True, 'include_tool_results': True, 'include_llm_calls': True, 'include_tool_calls': True, 'include_system_info': True}}
    app_config = AppConfig.from_dict(config)

    agent = BaseAgent(app_config=app_config)

    # Ask for the definition of get_lsp_manager function call on line 19
    print("Asking agent about Solidity...")
    result = await agent.arun(f"Check if the function call to storeData in file contracts/DataManager.sol at line 113 (0-based) is a call to a function from a thrid-party repo? Return as JSON {{\"answer\": \"yes or no\"}}.")
    print("Result:", result)

    # Save trajectory with custom name
    trajectory_path = agent.save_trajectory("lsp_definition_query_trajectory_solidity3.json")
    print(f"Trajectory saved to: {trajectory_path}")

async def test_common_use():
    # Load configuration from YAML file
    config = {'app': {'debug': True, 'working_dir': './bench/test_var_from_other_file_python', 'max_steps': 200, 'must_patch': False, 'verbose': True, 'show_config': False}, 'agent': {'model': 'deepseek-chat', 'max_steps': 200, 'allow_mcp_servers': [], 'mcp_servers': {}, 'skill': 'SOURCE_CODE_ANALYSIS_WITH_LSP'}, 'model': {'model': 'deepseek-chat', 'model_provider': 'deepseek', 'temperature': 0.5, 'top_p': 1.0, 'top_k': 0, 'parallel_tool_calls': True, 'max_retries': 10, 'max_tokens': 4096, 'max_completion_tokens': None, 'supports_tool_calling': True, 'candidate_count': None, 'stop_sequences': None}, 'lsp': {'enabled': True, 'auto_start': True, 'verbose': False, 'use_async': True, 'languages': ['python', 'typescript', 'javascript', 'java', 'rust', 'go', 'csharp', 'kotlin', 'solidity']}, 'trajectory': {'enabled': True, 'output_dir': 'trajectories', 'output_file': 'trajectory.json', 'save_on_completion': True, 'include_messages': True, 'include_tool_results': True, 'include_llm_calls': True, 'include_tool_calls': True, 'include_system_info': True}}
    app_config = AppConfig.from_dict(config)

    agent = BaseAgent(app_config=app_config)

    # Ask for the definition of get_lsp_manager function call on line 19
    print("Asking agent for understanding of ant-agent")
    result = await agent.arun("Analyze this repo and tell me what does it do?")
    print("Result:", result)

    # Save trajectory with custom name
    trajectory_path = agent.save_trajectory("repo_understanding.json")
    print(f"Trajectory saved to: {trajectory_path}")
    
    
async def fuzzgoat():
    # Load configuration from YAML file
    qwen_coder_config = {'app': {'debug': True, 'working_dir': '/Users/mac/repo/fuzzgoat', 'max_steps': 200, 'must_patch': False, 'verbose': True, 'show_config': False}, 'agent': { 'max_steps': 200, 'allow_mcp_servers': [], 'mcp_servers': {}, 'skill': 'MEMORY_BUG_DETECTION'}, 'model': {'model': 'qwen3-coder-plus', 'model_provider': 'dashscope', 'temperature': 0.5, 'top_p': 1.0, 'top_k': 0, 'parallel_tool_calls': True, 'max_retries': 10, 'max_tokens': 4096, 'max_completion_tokens': None, 'supports_tool_calling': True, 'candidate_count': None, 'stop_sequences': None}, 'lsp': {'enabled': True, 'auto_start': True, 'verbose': False, 'use_async': True, 'languages': ['python', 'typescript', 'javascript', 'java', 'rust', 'go', 'csharp', 'kotlin', 'solidity']}, 'trajectory': {'enabled': True, 'output_dir': 'trajectories', 'output_file': 'fuzzgoat.json', 'save_on_completion': True, 'include_messages': True, 'include_tool_results': True, 'include_llm_calls': True, 'include_tool_calls': True, 'include_system_info': True}}
    
    deepseek_config = {'app': {'debug': True, 'working_dir': '/Users/mac/repo/fuzzgoat', 'max_steps': 200, 'must_patch': False, 'verbose': True, 'show_config': False}, 'agent': { 'max_steps': 200, 'allow_mcp_servers': [], 'mcp_servers': {}, 'skill': 'MEMORY_BUG_DETECTION'}, 'model': {'model': 'deepseek-chat', 'model_provider': 'deepseek', 'temperature': 0.5, 'top_p': 1.0, 'top_k': 0, 'parallel_tool_calls': True, 'max_retries': 10, 'max_tokens': 4096, 'max_completion_tokens': None, 'supports_tool_calling': True, 'candidate_count': None, 'stop_sequences': None}, 'lsp': {'enabled': True, 'auto_start': True, 'verbose': False, 'use_async': True, 'languages': ['python', 'typescript', 'javascript', 'java', 'rust', 'go', 'csharp', 'kotlin', 'solidity']}, 'trajectory': {'enabled': True, 'output_dir': 'trajectories', 'output_file': 'fuzzgoat.json', 'save_on_completion': True, 'include_messages': True, 'include_tool_results': True, 'include_llm_calls': True, 'include_tool_calls': True, 'include_system_info': True}}
    
    ling_config = {'app': {'debug': True, 'working_dir': '/Users/mac/repo/fuzzgoat', 'max_steps': 200, 'must_patch': False, 'verbose': True, 'show_config': False}, 'agent': { 'max_steps': 200, 'allow_mcp_servers': [], 'mcp_servers': {}, 'skill': 'MEMORY_BUG_DETECTION'}, 'model': {'model': 'inclusionAI/Ling-1', 'model_provider': 'siliconflow', 'temperature': 0.5, 'top_p': 1.0, 'top_k': 0, 'parallel_tool_calls': True, 'max_retries': 10, 'max_tokens': 4096, 'max_completion_tokens': None, 'supports_tool_calling': True, 'candidate_count': None, 'stop_sequences': None}, 'lsp': {'enabled': True, 'auto_start': True, 'verbose': False, 'use_async': True, 'languages': ['python', 'typescript', 'javascript', 'java', 'rust', 'go', 'csharp', 'kotlin', 'solidity']}, 'trajectory': {'enabled': True, 'output_dir': 'trajectories', 'output_file': 'fuzzgoat.json', 'save_on_completion': True, 'include_messages': True, 'include_tool_results': True, 'include_llm_calls': True, 'include_tool_calls': True, 'include_system_info': True}}
    
    kimi_config = {'app': {'debug': True, 'working_dir': '/Users/mac/repo/fuzzgoat', 'max_steps': 200, 'must_patch': False, 'verbose': True, 'show_config': False}, 'agent': { 'max_steps': 200, 'allow_mcp_servers': [], 'mcp_servers': {}, 'skill': 'MEMORY_BUG_DETECTION'}, 'model': {'model': 'kimi-k2-turbo-preview', 'model_provider': 'kimi', 'temperature': 0.5, 'top_p': 1.0, 'top_k': 0, 'parallel_tool_calls': True, 'max_retries': 10, 'max_tokens': 4096, 'max_completion_tokens': None, 'supports_tool_calling': True, 'candidate_count': None, 'stop_sequences': None}, 'lsp': {'enabled': True, 'auto_start': True, 'verbose': False, 'use_async': True, 'languages': ['python', 'typescript', 'javascript', 'java', 'rust', 'go', 'csharp', 'kotlin', 'solidity']}, 'trajectory': {'enabled': True, 'output_dir': 'trajectories', 'output_file': 'fuzzgoat.json', 'save_on_completion': True, 'include_messages': True, 'include_tool_results': True, 'include_llm_calls': True, 'include_tool_calls': True, 'include_system_info': True}}
    
    app_config = AppConfig.from_dict(kimi_config)

    agent = BaseAgent(app_config=app_config)

    # Ask for the definition of get_lsp_manager function call on line 19
    print("Bug Detection for fuzzgoat")
    result = await agent.arun("Find all bugs in fuzzgoat.c 's json_parse. You should check the function body and all functions called by json_parse")
    # print("Result:", result)

    # Print memory contents after analysis
    from ant_agent.utils.memory import shared_memory_manager
    from ant_agent.tools.memory_tool import memory_tool_namespace

    print("\n" + "="*60)
    print("📋 MEMORY CONTENTS AFTER ANALYSIS")
    print("="*60)

    # Get all items from memory
    memory_items = shared_memory_manager.get_all(namespace=memory_tool_namespace)
    print([item['value'] for item in memory_items])
    # for item in memory_items:
    #     print(f"{'='*20}{item['key']}{'='*20}")
    #     print(item['value'])
    
    from ant_agent.tools.line_number_prefix_tool import remove_line_numbered_temp_file
    remove_line_numbered_temp_file()
    
    print(f"Trajectory saved to: fuzzgoat.json")


async def main():
    # await test_lsp_use_for_python()
    # await test_common_use()
    # await test_lsp_use_for_solidity()
    # await test_lsp_use_for_solidity2()
    # await test_lsp_use_for_solidity3()
    await fuzzgoat()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
