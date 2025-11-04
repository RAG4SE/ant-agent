#!/usr/bin/env python3
"""Test script to verify logging configuration."""

import logging
import asyncio
from ant_agent.agent.ant_agent import AntAgent
from ant_agent.utils.config import AppConfig

def test_basic_logging():
    """Test basic logging setup."""
    print("=== Testing Basic Logging ===")
    
    # Test current logging level
    root_logger = logging.getLogger()
    print(f"Root logger level: {root_logger.level}")
    print(f"Root logger handlers: {root_logger.handlers}")
    
    # Test specific loggers
    multilspy_logger = logging.getLogger("multilspy_lsp_manager")
    print(f"Multilspy logger level: {multilspy_logger.level}")
    print(f"Multilspy logger handlers: {multilspy_logger.handlers}")
    
    # Try to log some messages
    print("\n=== Testing Log Messages ===")
    multilspy_logger.info("This is an INFO message from multilspy_lsp_manager")
    multilspy_logger.warning("This is a WARNING message from multilspy_lsp_manager")
    multilspy_logger.error("This is an ERROR message from multilspy_lsp_manager")
    
    # Test the specific message that should appear
    multilspy_logger.info("创建新的 LSP 管理器，工作空间: /test/path")

def test_with_basic_config():
    """Test with basic logging configuration."""
    print("\n=== Testing with basicConfig ===")
    
    # Set up basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test again
    multilspy_logger = logging.getLogger("multilspy_lsp_manager")
    print(f"After basicConfig - Multilspy logger level: {multilspy_logger.level}")
    
    multilspy_logger.info("This INFO message should now appear")
    multilspy_logger.info("创建新的 LSP 管理器，工作空间: /test/path")

async def test_agent_logging():
    """Test logging with actual agent."""
    print("\n=== Testing Agent Logging ===")
    
    # Set up logging first
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load config and create agent
    app_config = AppConfig.load_config('ant_config.yaml')
    app_config.working_dir = "./bench/test_var_from_other_file_python"
    
    print("Creating agent...")
    agent = AntAgent(app_config=app_config)
    print("Agent created successfully")

if __name__ == "__main__":
    test_basic_logging()
    test_with_basic_config()
    asyncio.run(test_agent_logging())
