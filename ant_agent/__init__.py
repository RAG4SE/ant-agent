# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""Ant Agent - LangChain-based agent for general purpose software engineering tasks."""

__version__ = "0.1.0"

from ant_agent.agent.base_agent import BaseAgent
from ant_agent.agent.ant_agent import AntAgent
from ant_agent.tools.base import AntTool
from ant_agent.clients.llm_client import LLMClient
from ant_agent.lsp.multilspy_manager import MultilspyLSPManager, get_lsp_manager
from ant_agent.tools.multilspy_lsp_tools import (
    MultilspyToolManager, 
    MultilspyToolFactory,
    global_multilspy_tool_manager
)

__all__ = [
    "BaseAgent", 
    "AntAgent", 
    "LLMClient", 
    "AntTool",
    "MultilspyLSPManager",
    "get_lsp_manager",
    "MultilspyToolManager",
    "MultilspyToolFactory", 
    "global_multilspy_tool_manager"
]