#!/usr/bin/env python3
"""
Example usage of Ant Agent - 功能与 trae-agent/example.py 一致
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ant_agent.agent.ant_agent import AntAgent
from ant_agent.utils.hydra_config import load_config
from ant_agent.utils.trajectory_recorder import TrajectoryRecorder
from ant_agent.utils.config import ModelConfig, LLMProvider
from omegaconf import OmegaConf


async def run_ant_agent():
    """模仿 trae-agent 的 run_trae_agent 函数，功能一致"""
    
    # 1. 加载配置（类似 trae-agent 的 Config.create）
    config = load_config(
        agent_name="ant_agent",
        model_name="deepseek-chat",  # 可以根据需要修改
        provider_name="deepseek"
    )
    
    # 2. 创建模型配置（将配置转换为 ModelConfig 对象）
    model_cfg = config.model
    provider_cfg = config.provider
    
    # 合并模型和提供商配置
    merged_cfg = OmegaConf.merge(model_cfg, provider_cfg)
    
    # 转换提供商字段名称
    if "provider" in merged_cfg:
        config_dict = OmegaConf.to_container(merged_cfg)
        config_dict['model_provider'] = LLMProvider(config_dict['provider'])
        del config_dict['provider']
        merged_cfg = OmegaConf.create(config_dict)
    
    # 创建 ModelConfig 对象
    model_config = ModelConfig(**merged_cfg)
    
    # 3. 创建Agent（不使用CLI界面，不允许编辑）
    # 使用轨迹录制功能记录中间过程
    trajectory_file = "trajectory.json"
    trajectory_recorder = TrajectoryRecorder(config.trajectory) if config.trajectory.enabled else None
    
    agent = AntAgent(
        agent_config=config.agent,
        model_config=model_config,
        trajectory_recorder=trajectory_recorder
    )
    
    # 4. 运行任务
    task = """List all files"""
    
    # 额外的参数（模仿 trae-agent 的 extra_args 结构）
    project_path = "/Users/mac/repo/deepwiki-cli/bench/test_var_from_other_file_python"
    
    print(f"🚀 Starting Ant Agent...")
    print(f"📁 Project path: {project_path}")
    print(f"📋 Task: {task}")
    print(f"📝 Trajectory file: {trajectory_file}")
    print("-" * 50)
    
    # 运行任务（类似 trae-agent 的 agent.run）
    result = await agent.arun(task)
    
    # 保存轨迹
    if trajectory_recorder:
        saved_file = trajectory_recorder.save()
        print(f"\n📊 Trajectory saved to: {saved_file}")
    
    return result


# 运行（与 trae-agent 相同的入口点）
if __name__ == "__main__":
    result = asyncio.run(run_ant_agent())
    print("=== Agent Answer ===")
    print(result)