# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""
专门为 ant-agent 定制的 MCP 客户端
针对 lsp-mcp-ant 服务器优化
"""

import asyncio
import json
import logging
import subprocess
import sys
import threading
import queue
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("ant_mcp_client")

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

class AntMCPClient:
    """为 ant-agent 定制的 MCP 客户端"""
    
    def __init__(self, server_config: MCPServerConfig):
        self.server_config = server_config
        self.state = MCPConnectionState.DISCONNECTED
        self.available_tools: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(f"ant_mcp_client.{server_config.name}")
        
        # 进程相关
        self.process: Optional[subprocess.Popen] = None
        self._message_id = 0
        self._pending_requests = {}
        self._running = False
        self._read_thread: Optional[threading.Thread] = None
        self._write_thread: Optional[threading.Thread] = None
        self._request_queue = queue.Queue()
        
    def _next_message_id(self) -> int:
        """生成下一个消息 ID"""
        self._message_id += 1
        return self._message_id
    
    def _send_message(self, message: Dict[str, Any]) -> None:
        """发送消息到服务器"""
        if self.process and self.process.stdin:
            try:
                json_line = json.dumps(message) + '\n'
                self.process.stdin.write(json_line.encode('utf-8'))
                self.process.stdin.flush()
                self.logger.debug(f"发送消息: {json_line.strip()}")
            except Exception as e:
                self.logger.error(f"发送消息失败: {e}")
                raise
    
    def _read_messages(self):
        """从服务器读取消息的线程"""
        while self._running and self.process and self.process.stdout:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                
                message = json.loads(line.decode('utf-8').strip())
                self.logger.debug(f"收到消息: {message}")
                
                # 处理响应
                if 'id' in message and message['id'] in self._pending_requests:
                    # 这是请求的响应
                    future = self._pending_requests.pop(message['id'])
                    if 'error' in message:
                        future.set_exception(Exception(message['error'].get('message', 'Unknown error')))
                    else:
                        future.set_result(message.get('result'))
                elif 'method' in message:
                    # 这是服务器主动发送的消息（如日志、通知等）
                    self.logger.info(f"服务器通知: {message}")
                    
            except json.JSONDecodeError as e:
                self.logger.error(f"解析 JSON 失败: {e}, line: {line}")
            except Exception as e:
                self.logger.error(f"读取消息失败: {e}")
                break
    
    async def _make_request(self, method: str, params: Dict[str, Any]) -> Any:
        """发送请求并等待响应"""
        message_id = self._next_message_id()
        message = {
            "jsonrpc": "2.0",
            "id": message_id,
            "method": method,
            "params": params
        }
        
        # 创建 future 等待响应
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending_requests[message_id] = future
        
        # 发送请求
        await loop.run_in_executor(None, self._send_message, message)
        
        # 等待响应
        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        except asyncio.TimeoutError:
            self._pending_requests.pop(message_id, None)
            raise TimeoutError(f"请求超时: {method}")
    
    async def connect(self, timeout: float = 30.0) -> bool:
        """连接到 MCP 服务器"""
        try:
            self.logger.info(f"启动 MCP 服务器进程: {self.server_config.command} {' '.join(self.server_config.args)}")
            self.state = MCPConnectionState.CONNECTING
            
            # 启动服务器进程
            import os
            env = {**os.environ, **self.server_config.env}
            self.process = subprocess.Popen(
                [self.server_config.command] + self.server_config.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=self.server_config.cwd
            )
            
            # 等待进程启动
            await asyncio.sleep(0.5)
            
            if self.process.poll() is not None:
                # 进程已退出，读取错误信息
                stderr = self.process.stderr.read().decode('utf-8')
                self.logger.error(f"服务器进程启动失败: {stderr}")
                self.state = MCPConnectionState.ERROR
                return False
            
            self._running = True
            
            # 启动读取线程
            self._read_thread = threading.Thread(target=self._read_messages, daemon=True)
            self._read_thread.start()
            
            # 发送初始化请求
            self.logger.debug("正在初始化 MCP 会话...")
            init_result = await self._make_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"subscribe": True, "listChanged": True},
                    "prompts": {"listChanged": True}
                },
                "clientInfo": {
                    "name": "ant-mcp-client",
                    "version": "0.1.0"
                }
            })
            
            self.logger.debug(f"初始化结果: {init_result}")
            
            # 发送 initialized 通知
            await self._make_request("initialized", {})
            
            self.state = MCPConnectionState.CONNECTED
            
            # 获取可用工具
            tools_result = await self._make_request("tools/list", {})
            self.available_tools = tools_result.get('tools', [])
            
            self.logger.info(f"✅ 成功连接到 MCP 服务器")
            self.logger.info(f"📋 可用工具数量: {len(self.available_tools)}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"连接 MCP 服务器失败: {e}")
            self.state = MCPConnectionState.ERROR
            await self.disconnect()
            return False
    
    async def disconnect(self) -> None:
        """断开 MCP 服务器连接"""
        self.logger.info("断开 MCP 服务器连接...")
        
        self._running = False
        
        try:
            # 发送关闭请求
            if self.process and self.state == MCPConnectionState.CONNECTED:
                try:
                    await asyncio.wait_for(
                        self._make_request("shutdown", {}),
                        timeout=5.0
                    )
                except:
                    pass  # 忽略关闭错误
                
                # 发送退出通知
                self._send_message({
                    "jsonrpc": "2.0",
                    "method": "exit",
                    "params": {}
                })
        except:
            pass
        
        # 终止进程
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
                self.process.wait()
            self.process = None
        
        self.state = MCPConnectionState.DISCONNECTED
        self.available_tools = []
        self.logger.info("MCP 连接已断开")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        if self.state != MCPConnectionState.CONNECTED:
            raise RuntimeError("MCP 客户端未连接")
        
        try:
            result = await self._make_request("tools/list", {})
            self.available_tools = result.get('tools', [])
            return self.available_tools
                
        except Exception as e:
            self.logger.error(f"获取工具列表失败: {e}")
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """调用 MCP 工具"""
        if self.state != MCPConnectionState.CONNECTED:
            raise RuntimeError("MCP 客户端未连接")
        
        try:
            self.logger.debug(f"调用工具: {tool_name}, 参数: {arguments}")
            
            result = await self._make_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })
            
            # 提取文本内容
            if result and 'content' in result:
                text_contents = []
                for content in result['content']:
                    if isinstance(content, dict) and content.get('type') == 'text':
                        text_contents.append(content.get('text', ''))
                    elif isinstance(content, str):
                        text_contents.append(content)
                return '\n'.join(text_contents) if text_contents else str(result)
            else:
                return str(result)
                
        except Exception as e:
            error_msg = f"调用工具 {tool_name} 失败: {e}"
            self.logger.error(error_msg)
            return f"错误: {error_msg}"
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.state == MCPConnectionState.CONNECTED
    
    def get_state(self) -> MCPConnectionState:
        """获取连接状态"""
        return self.state