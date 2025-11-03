# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""
MCP 管理器
负责管理 MCP 客户端和工具的生命周期
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from ant_agent.mcp.mcp_client import MCPClient, LSPMCPClient, MCPServerConfig
from ant_agent.tools.mcp_lsp_tools import MCPLSPToolManager, MCPToolFactory

logger = logging.getLogger(__name__)

class MCPManager:
    """MCP 管理器 - 管理 MCP 客户端和工具"""
    
    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self.tool_manager = MCPLSPToolManager()
        self.logger = logging.getLogger(__name__)
        self._initialized = False
    
    async def initialize(self, config_file: Optional[str] = None) -> bool:
        """初始化 MCP 管理器"""
        if self._initialized:
            self.logger.info("MCP 管理器已初始化")
            return True
        
        try:
            self.logger.info("初始化 MCP 管理器...")
            
            # 加载配置
            configs = await self._load_configurations(config_file)
            
            # 创建并连接 MCP 客户端
            for config in configs:
                await self._create_and_connect_client(config)
            
            self._initialized = True
            self.logger.info("✅ MCP 管理器初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"MCP 管理器初始化失败: {e}")
            return False
    
    async def _load_configurations(self, config_file: Optional[str] = None) -> List[MCPServerConfig]:
        """加载 MCP 服务器配置"""
        configs = []
        
        # 默认配置 - lsp-mcp-ant 服务器 (我们为 ant-agent 定制的版本)
        default_config = MCPServerConfig(
            name="lsp-mcp-ant",
            command="node",
            args=["/Users/mac/repo/lsp-mcp-ant/dist/index.js", "--verbose"],
            env={"NODE_ENV": "production"}
        )
        configs.append(default_config)
        
        # TODO: 从配置文件加载更多配置
        if config_file and Path(config_file).exists():
            self.logger.info(f"从配置文件加载: {config_file}")
            # 这里可以添加 JSON/YAML 配置文件的解析
        
        return configs
    
    async def _create_and_connect_client(self, config: MCPServerConfig) -> bool:
        """创建并连接 MCP 客户端"""
        try:
            self.logger.info(f"创建 MCP 客户端: {config.name}")
            
            # 创建 LSP MCP 客户端
            client = LSPMCPClient(config)
            
            # 连接到服务器
            self.logger.info(f"连接到 MCP 服务器: {config.name}")
            success = await client.connect()
            
            if success:
                self.clients[config.name] = client
                
                # 注册工具
                self.tool_manager.register_mcp_client(config.name, client)
                
                self.logger.info(f"✅ MCP 客户端 {config.name} 连接成功")
                return True
            else:
                self.logger.error(f"MCP 客户端 {config.name} 连接失败")
                return False
                
        except Exception as e:
            self.logger.error(f"创建 MCP 客户端 {config.name} 失败: {e}")
            return False
    
    async def shutdown(self) -> None:
        """关闭所有 MCP 客户端"""
        self.logger.info("正在关闭 MCP 管理器...")
        
        for name, client in self.clients.items():
            try:
                self.logger.info(f"断开 MCP 客户端: {name}")
                await client.disconnect()
            except Exception as e:
                self.logger.error(f"断开 MCP 客户端 {name} 失败: {e}")
        
        self.clients.clear()
        self._initialized = False
        self.logger.info("MCP 管理器已关闭")
    
    def get_client(self, name: str) -> Optional[MCPClient]:
        """获取 MCP 客户端"""
        return self.clients.get(name)
    
    def get_all_clients(self) -> Dict[str, MCPClient]:
        """获取所有 MCP 客户端"""
        return self.clients.copy()
    
    def get_tool_manager(self) -> MCPLSPToolManager:
        """获取工具管理器"""
        return self.tool_manager
    
    def list_available_tools(self) -> List[str]:
        """列出所有可用工具"""
        return self.tool_manager.list_available_tools()
    
    def get_tool(self, name: str) -> Optional[Any]:
        """获取工具"""
        return self.tool_manager.get_tool(name)
    
    def get_lsp_capabilities(self, client_name: str = "lsp-mcp") -> Dict[str, bool]:
        """获取 LSP 能力"""
        client = self.clients.get(client_name)
        if isinstance(client, LSPMCPClient):
            return client.lsp_capabilities
        return {}
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态信息"""
        status = {
            "initialized": self._initialized,
            "clients": {},
            "tools": {
                "total": len(self.tool_manager.tools),
                "available": list(self.tool_manager.tools.keys())
            }
        }
        
        # 客户端状态
        for name, client in self.clients.items():
            status["clients"][name] = {
                "connected": client.is_connected(),
                "state": client.get_state().value,
                "tools_count": len(client.available_tools)
            }
            
            # LSP 能力
            if isinstance(client, LSPMCPClient):
                status["clients"][name]["lsp_capabilities"] = client.lsp_capabilities
        
        return status

# 全局 MCP 管理器实例
global_mcp_manager = MCPManager()

# 便利函数
async def initialize_mcp_manager(config_file: Optional[str] = None) -> bool:
    """初始化全局 MCP 管理器"""
    return await global_mcp_manager.initialize(config_file)

async def shutdown_mcp_manager() -> None:
    """关闭全局 MCP 管理器"""
    await global_mcp_manager.shutdown()

def get_mcp_manager() -> MCPManager:
    """获取全局 MCP 管理器"""
    return global_mcp_manager

def get_mcp_tool_manager() -> MCPLSPToolManager:
    """获取全局 MCP 工具管理器"""
    return global_mcp_manager.tool_manager

# 上下文管理器
class MCPManagerContext:
    """MCP 管理器上下文管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
    
    async def __aenter__(self):
        await initialize_mcp_manager(self.config_file)
        return global_mcp_manager
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await shutdown_mcp_manager()