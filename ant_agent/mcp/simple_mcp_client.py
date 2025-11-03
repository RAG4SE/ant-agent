# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""
简化的 MCP 客户端实现
专门针对 lsp-mcp-ant 服务器优化
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger("simple_mcp_client")

class MCPConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

@dataclass
class MCPServerConfig:
    """MCP 服务器配置"""
    name: str
    command: str
    args: List[str] = None
    env: Dict[str, str] = None
    cwd: Optional[str] = None
    
    def __post_init__(self):
        if self.args is None:
            self.args = []
        if self.env is None:
            self.env = {}

class SimpleMCPClient:
    """简化的 MCP 客户端 - 专门针对 ant-agent 优化"""
    
    def __init__(self, server_config: MCPServerConfig):
        self.server_config = server_config
        self.session: Optional[ClientSession] = None
        self.state = MCPConnectionState.DISCONNECTED
        self.available_tools: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(f"simple_mcp_client.{server_config.name}")
        self._streams = None
        
    async def connect(self, timeout: float = 30.0) -> bool:
        """连接到 MCP 服务器，带超时处理"""
        try:
            self.logger.info(f"连接到 MCP 服务器: {self.server_config.name}")
            self.state = MCPConnectionState.CONNECTING
            
            # 配置服务器参数
            server_params = StdioServerParameters(
                command=self.server_config.command,
                args=self.server_config.args,
                env=self.server_config.env
            )
            
            self.logger.debug(f"服务器参数: {self.server_config.command} {' '.join(self.server_config.args)}")
            
            # 使用超时机制创建连接
            async with asyncio.timeout(timeout):
                # 创建 stdio 客户端
                stdio = stdio_client(server_params)
                self._streams = await stdio.__aenter__()
                read_stream, write_stream = self._streams
                
                # 创建 MCP 会话
                self.session = ClientSession(read_stream, write_stream)
                
                # 初始化会话
                self.logger.debug("正在初始化 MCP 会话...")
                init_result = await self.session.initialize()
                self.logger.debug(f"初始化成功，服务器信息: {init_result.server_info}")
                
                self.state = MCPConnectionState.CONNECTED
                
                # 获取可用工具
                self.logger.debug("正在获取可用工具...")
                tools_result = await self.session.list_tools()
                self.available_tools = [tool.dict() for tool in tools_result.tools]
                
                self.logger.info(f"✅ 成功连接到 MCP 服务器")
                self.logger.info(f"📋 可用工具数量: {len(self.available_tools)}")
                
                return True
                
        except asyncio.TimeoutError:
            self.logger.error(f"连接 MCP 服务器超时 ({timeout}秒)")
            self.state = MCPConnectionState.ERROR
            await self.disconnect()
            return False
        except Exception as e:
            self.logger.error(f"连接 MCP 服务器失败: {e}")
            self.state = MCPConnectionState.ERROR
            await self.disconnect()
            return False
    
    async def disconnect(self) -> None:
        """断开 MCP 服务器连接"""
        self.logger.info("断开 MCP 服务器连接...")
        
        try:
            # 清理会话
            if self.session:
                self.session = None
            
            # 清理流
            if self._streams:
                try:
                    await self._streams[0].aclose()
                    await self._streams[1].aclose()
                except Exception as e:
                    self.logger.debug(f"清理流时出错: {e}")
                self._streams = None
                
        except Exception as e:
            self.logger.debug(f"断开连接时出错: {e}")
        finally:
            self.state = MCPConnectionState.DISCONNECTED
            self.available_tools = []
            self.logger.info("MCP 连接已断开")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        if not self.session or self.state != MCPConnectionState.CONNECTED:
            raise RuntimeError("MCP 客户端未连接")
        
        try:
            result = await self.session.list_tools()
            self.available_tools = [tool.dict() for tool in result.tools]
            return self.available_tools
                
        except Exception as e:
            self.logger.error(f"获取工具列表失败: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """调用 MCP 工具"""
        if not self.session or self.state != MCPConnectionState.CONNECTED:
            raise RuntimeError("MCP 客户端未连接")
        
        try:
            self.logger.debug(f"调用工具: {tool_name}")
            result = await self.session.call_tool(tool_name, arguments)
            
            # 提取文本内容
            if result.content:
                text_contents = []
                for content in result.content:
                    if hasattr(content, 'text') and content.text:
                        text_contents.append(content.text)
                return '\n'.join(text_contents) if text_contents else str(result)
            else:
                return str(result)
                
        except Exception as e:
            error_msg = f"调用工具 {tool_name} 失败: {e}"
            self.logger.error(error_msg)
            return f"错误: {error_msg}"
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.state == MCPConnectionState.CONNECTED and self.session is not None
    
    def get_state(self) -> MCPConnectionState:
        """获取连接状态"""
        return self.state

class LSPMCPClient(SimpleMCPClient):
    """专门为 LSP 优化的 MCP 客户端"""
    
    def __init__(self, server_config: MCPServerConfig):
        super().__init__(server_config)
        self.lsp_capabilities = {
            'hover': False,
            'definition': False,
            'references': False,
            'document_symbols': False,
            'completions': False
        }
    
    async def connect(self, timeout: float = 30.0) -> bool:
        """连接并检测 LSP 能力"""
        success = await super().connect(timeout)
        if success:
            await self._detect_lsp_capabilities()
        return success
    
    async def _detect_lsp_capabilities(self) -> None:
        """检测 LSP 能力"""
        try:
            tools = await self.list_tools()
            
            for tool in tools:
                tool_name = tool.get('name', '').lower()
                
                # 检测各种 LSP 能力
                if 'hover' in tool_name:
                    self.lsp_capabilities['hover'] = True
                elif 'definition' in tool_name:
                    self.lsp_capabilities['definition'] = True
                elif 'references' in tool_name or 'reference' in tool_name:
                    self.lsp_capabilities['references'] = True
                elif 'document' in tool_name and 'symbol' in tool_name:
                    self.lsp_capabilities['document_symbols'] = True
                elif 'completion' in tool_name:
                    self.lsp_capabilities['completions'] = True
            
            self.logger.info(f"LSP 能力检测完成: {self.lsp_capabilities}")
            
        except Exception as e:
            self.logger.error(f"LSP 能力检测失败: {e}")
    
    def has_capability(self, capability: str) -> bool:
        """检查是否支持指定的 LSP 能力"""
        return self.lsp_capabilities.get(capability, False)
    
    def get_lsp_tools(self) -> List[Dict[str, Any]]:
        """获取 LSP 相关的工具"""
        lsp_tools = []
        for tool in self.available_tools:
            tool_name = tool.get('name', '').lower()
            if any(cap in tool_name for cap in ['hover', 'definition', 'references', 'symbol', 'completion']):
                lsp_tools.append(tool)
        return lsp_tools