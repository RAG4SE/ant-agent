#!/usr/bin/env python3
"""
Test script for Hydra configuration.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ant_agent.utils.hydra_config import load_config
from ant_agent.agent.ant_agent import AntAgent
from ant_agent.utils.trajectory_recorder import TrajectoryRecorder

def test_hydra():
    """Test Hydra configuration system."""
    print("🔍 Testing Hydra Configuration...")

    try:
        # Load configuration
        cfg = load_config()

        print("✅ Configuration loaded successfully!")
        print(f"   Model: {cfg.model.model}")
        print(f"   Provider: {cfg.model.provider}")
        print(f"   Agent: {cfg.agent.name}")

        # Create model config by merging model and provider configs
        from omegaconf import OmegaConf
        from ant_agent.utils.config import LLMProvider

        model_cfg = OmegaConf.merge(cfg.model, cfg.provider)
        # Convert provider string to enum
        if "provider" in model_cfg:
            model_cfg.provider = LLMProvider(model_cfg.provider)

        # Create agent
        agent = AntAgent(
            agent_config=cfg.agent,
            model_config=model_cfg
        )

        print("✅ Agent created successfully!")

        # Test a simple task
        task = "Create a hello world Python script"
        print(f"\n🚀 Running task: {task}")

        response = agent.run(task)
        print(f"✅ Response: {response}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hydra()