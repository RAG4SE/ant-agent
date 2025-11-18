# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

import logging
from typing import Dict, List, Any, Optional
from ant_agent.tools.base import AntTool
from ant_agent.mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

class MCPLSPTool(AntTool):
    """MCP LSP 工具基类"""
    
    def __init__(self, mcp_client: MCPClient, tool_name: str, tool_info: Dict[str, Any]):
        super().__init__()
        self.mcp_client = mcp_client
        self.tool_name = tool_name
        self.tool_info = tool_info
        
        # 设置工具名称和描述
        self.name = f"mcp_{tool_name}"
        self.description = tool_info.get("description", f"MCP LSP tool: {tool_name}")
        
        # 解析参数模式
        self._parse_parameters(tool_info.get("inputSchema", {}))
        
    def _parse_parameters(self, input_schema: Dict[str, Any]) -> None:
        """解析 MCP 工具的参数模式"""
        if not input_schema:
            return
            
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        
        for param_name, param_info in properties.items():
            param_type = self._map_json_type_to_python(param_info.get("type", "string"))
            param_desc = param_info.get("description", f"Parameter {param_name}")
            param_required = param_name in required
            
            # 添加到参数定义
            self.add_parameter(
                name=param_name,
                type=param_type,
                description=param_desc,
                required=param_required
            )
    
    def _map_json_type_to_python(self, json_type: str) -> str:
        """将 JSON Schema 类型映射到 Python 类型"""
        type_mapping = {
            "string": "str",
            "number": "float",
            "integer": "int", 
            "boolean": "bool",
            "array": "list",
            "object": "dict"
        }
        return type_mapping.get(json_type, "str")
    
    def _execute(self, **kwargs) -> str:
        """执行 MCP 工具调用"""
        try:
            logger.debug(f"执行 MCP 工具: {self.tool_name}, 参数: {kwargs}")
            
            # 调用 MCP 工具
            result = self.mcp_client.call_tool(self.tool_name, kwargs)
            
            # 处理结果
            if isinstance(result, str):
                return result
            elif isinstance(result, dict):
                return str(result)
            else:
                return str(result)
                
        except Exception as e:
            logger.error(f"MCP 工具调用失败 {self.tool_name}: {e}")
            return f"错误: {str(e)}"

# 具体的 LSP 工具类
class MCPHoverTool(MCPLSPTool):
    """MCP LSP Hover 工具"""
    
    def __init__(self, mcp_client: MCPClient, tool_info: Dict[str, Any]):
        super().__init__(mcp_client, "hover", tool_info)
        self.description = "获取光标位置的悬停信息 (通过 MCP LSP 服务器)"

class MCPDefinitionTool(MCPLSPTool):
    """MCP LSP Definition 工具"""
    
    def __init__(self, mcp_client: MCPClient, tool_info: Dict[str, Any]):
        super().__init__(mcp_client, "definition", tool_info)
        self.description = "跳转到定义 (通过 MCP LSP 服务器)"

class MCPReferencesTool(MCPLSPTool):
    """MCP LSP References 工具"""
    
    def __init__(self, mcp_client: MCPClient, tool_info: Dict[str, Any]):
        super().__init__(mcp_client, "references", tool_info)
        self.description = "查找引用 (通过 MCP LSP 服务器)"

class MCPDocumentSymbolsTool(MCPLSPTool):
    """MCP LSP Document Symbols 工具"""
    
    def __init__(self, mcp_client: MCPClient, tool_info: Dict[str, Any]):
        super().__init__(mcp_client, "document_symbols", tool_info)
        self.description = "获取文档符号 (通过 MCP LSP 服务器)"

class MCPCompletionTool(MCPLSPTool):
    """MCP LSP Completion 工具"""
    
    def __init__(self, mcp_client: MCPClient, tool_info: Dict[str, Any]):
        super().__init__(mcp_client, "completion", tool_info)
        self.description = "获取代码补全 (通过 MCP LSP 服务器)"

# 工具工厂
class MCPToolFactory:
    """MCP LSP 工具工厂"""
    
    # LSP 工具类型映射
    LSP_TOOL_TYPES = {
        "hover": MCPHoverTool,
        "definition": MCPDefinitionTool,
        "references": MCPReferencesTool,
        "document_symbols": MCPDocumentSymbolsTool,
        "completion": MCPCompletionTool
    }
    
    @classmethod
    def create_tool(cls, mcp_client: MCPClient, tool_info: Dict[str, Any]) -> Optional[MCPLSPTool]:
        """创建 MCP LSP 工具实例"""
        tool_name = tool_info.get("name", "").lower()
        
        # 查找匹配的 LSP 工具类型
        for lsp_type, tool_class in cls.LSP_TOOL_TYPES.items():
            if lsp_type in tool_name:
                logger.info(f"创建 LSP 工具: {tool_class.__name__} for {tool_name}")
                return tool_class(mcp_client, tool_info)
        
        # 如果没有特定匹配，创建通用工具
        logger.info(f"创建通用 MCP 工具: {tool_name}")
        return MCPLSPTool(mcp_client, tool_name, tool_info)
    
    @classmethod
    def create_lsp_tools(cls, mcp_client: MCPClient) -> List[MCPLSPTool]:
        """为 MCP 客户端创建所有 LSP 工具"""
        tools = []
        
        try:
            # 获取可用工具
            available_tools = mcp_client.list_tools()
            logger.info(f"发现 {len(available_tools)} 个 MCP 工具")
            
            for tool_info in available_tools:
                tool = cls.create_tool(mcp_client, tool_info)
                if tool:
                    tools.append(tool)
            
            logger.info(f"成功创建 {len(tools)} 个 LSP 工具")
            return tools
            
        except Exception as e:
            logger.error(f"创建 LSP 工具失败: {e}")
            return []

# 工具管理器
class MCPLSPToolManager:
    """MCP LSP 工具管理器"""
    
    def __init__(self):
        self.mcp_clients = {}
        self.tools = {}
        self.logger = logging.getLogger(__name__)
    
    def register_mcp_client(self, name: str, mcp_client: MCPClient) -> None:
        """注册 MCP 客户端"""
        self.mcp_clients[name] = mcp_client
        
        # 为该客户端创建工具
        try:
            lsp_tools = MCPToolFactory.create_lsp_tools(mcp_client)
            for tool in lsp_tools:
                tool_key = f"{name}.{tool.name}"
                self.tools[tool_key] = tool
                self.logger.info(f"注册工具: {tool_key}")
            
            self.logger.info(f"MCP 客户端 {name} 注册成功，创建了 {len(lsp_tools)} 个工具")
            
        except Exception as e:
            self.logger.error(f"为 MCP 客户端 {name} 创建工具失败: {e}")
    
    def get_tool(self, name: str) -> Optional[MCPLSPTool]:
        """获取工具"""
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[MCPLSPTool]:
        """获取所有工具"""
        return list(self.tools.values())
    
    def get_tools_by_client(self, client_name: str) -> List[MCPLSPTool]:
        """获取指定客户端的工具"""
        client_tools = []
        for tool_key, tool in self.tools.items():
            if tool_key.startswith(f"{client_name}."):
                client_tools.append(tool)
        return client_tools
    
    def list_available_tools(self) -> List[str]:
        """列出可用工具名称"""
        return list(self.tools.keys())

# 全局工具管理器实例
global_mcp_tool_manager = MCPLSPToolManager()