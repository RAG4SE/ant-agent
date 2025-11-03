# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""
基于 Multilspy 的 LSP 管理器
自动处理 LSP 服务器的下载、安装、启动和管理
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from contextlib import asynccontextmanager

from multilspy import LanguageServer, SyncLanguageServer
from multilspy.multilspy_config import MultilspyConfig, Language
from multilspy.multilspy_logger import MultilspyLogger
from multilspy.multilspy_exceptions import MultilspyException

from ant_agent.tools.base import AntTool, AntToolResult
from ant_agent.tools.multilspy_lsp_tools import (
    MultilspyHoverTool, MultilspyDocumentSymbolTool, MultilspyDefinitionTool,
    MultilspyReferencesTool, MultilspyCompletionTool, set_tool_context,
    global_multilspy_tool_manager
)
from ant_agent.utils.config import LSPConfig

class MultilspyLSPManager:
    """基于 Multilspy 的 LSP 管理器"""
    
    def __init__(self, config: LSPConfig):
        self.config = config
        self.workspace_path = Path(config.workspace).absolute()
        self.logger = logging.getLogger("multilspy_lsp_manager")
        
        # LSP 服务器实例
        self.servers: Dict[str, LanguageServer] = {}
        
        # 语言到服务器的映射
        self.language_to_server: Dict[str, str] = {}
        
        # 扩展名到语言的映射
        self.extension_to_language: Dict[str, Language] = {}
        
        # 初始化映射
        self._initialize_mappings()
    
    def _initialize_mappings(self) -> None:
        """初始化文件扩展名到语言的映射"""
        self.extension_to_language = {
            '.py': Language.PYTHON,
            '.pyi': Language.PYTHON,
            '.pyx': Language.PYTHON,
            '.java': Language.JAVA,
            '.class': Language.JAVA,
            '.js': Language.JAVASCRIPT,
            '.jsx': Language.JAVASCRIPT,
            '.ts': Language.TYPESCRIPT,
            '.tsx': Language.TYPESCRIPT,
            '.rs': Language.RUST,
            '.go': Language.GO,
            '.cs': Language.CSHARP,
            '.cshtml': Language.CSHARP,
            '.csproj': Language.CSHARP,
            '.sln': Language.CSHARP,
            '.kt': Language.KOTLIN,
            '.kts': Language.KOTLIN,
            '.dart': Language.DART,
            '.rb': Language.RUBY,
            '.rbw': Language.RUBY,
            '.rake': Language.RUBY,
            '.gemspec': Language.RUBY,
            '.sol': Language.SOLIDITY,
        }
    
    def get_language_for_file(self, file_path: str) -> Optional[Language]:
        """根据文件路径获取对应的语言"""
        path = Path(file_path)
        extension = path.suffix.lower()
        return self.extension_to_language.get(extension)
    
    def get_server_for_language(self, language: Language) -> Optional[LanguageServer]:
        """获取指定语言的 LSP 服务器"""
        language_str = language.value
        
        # 如果服务器已存在，直接返回
        if language_str in self.servers:
            return self.servers[language_str]
        
        # 创建新的服务器实例
        try:
            self.logger.info(f"创建 {language_str} 的 LSP 服务器...")
            
            # 创建 Multilspy 配置
            multilspy_config = MultilspyConfig.from_dict({
                "code_language": language_str,
                "verbose": self.config.verbose
            })
            
            # 创建 logger
            multilspy_logger = MultilspyLogger()
            
            # 创建语言服务器
            if self.config.use_async:
                server = LanguageServer.create(
                    multilspy_config, 
                    multilspy_logger, 
                    str(self.workspace_path)
                )
            else:
                server = SyncLanguageServer.create(
                    multilspy_config, 
                    multilspy_logger, 
                    str(self.workspace_path)
                )
            
            self.servers[language_str] = server
            self.language_to_server[language_str] = language_str
            
            self.logger.info(f"✅ 成功创建 {language_str} 的 LSP 服务器")
            return server
            
        except Exception as e:
            self.logger.error(f"创建 {language_str} 的 LSP 服务器失败: {e}")
            return None
    
    async def start_all_servers(self) -> Dict[str, bool]:
        """启动所有配置的 LSP 服务器"""
        results = {}
        
        # 需要支持的语言列表
        languages_to_start = [
            Language.PYTHON,
            Language.JAVASCRIPT,
            Language.TYPESCRIPT,
            Language.JAVA,
            Language.RUST,
            Language.GO,
            Language.CSHARP,
            Language.KOTLIN,
            Language.SOLIDITY
        ]
        
        for language in languages_to_start:
            try:
                server = self.get_server_for_language(language)
                if server:
                    # 异步启动服务器
                    if hasattr(server, 'start_server'):
                        async with server.start_server():
                            results[language.value] = True
                            self.logger.info(f"✅ {language.value} LSP 服务器已启动")
                    else:
                        # 同步启动
                        with server.start_server():
                            results[language.value] = True
                            self.logger.info(f"✅ {language.value} LSP 服务器已启动")
                else:
                    results[language.value] = False
                    
            except Exception as e:
                self.logger.error(f"启动 {language.value} LSP 服务器失败: {e}")
                results[language.value] = False
        
        return results
    
    async def stop_all_servers(self) -> None:
        """停止所有 LSP 服务器"""
        for language, server in self.servers.items():
            try:
                if hasattr(server, 'stop'):
                    await server.stop()
                self.logger.info(f"🛑 {language} LSP 服务器已停止")
            except Exception as e:
                self.logger.error(f"停止 {language} LSP 服务器失败: {e}")
        
        self.servers.clear()
    
    def get_available_tools(self) -> List[AntTool]:
        """获取所有可用的 LSP 工具"""
        # 使用全局 multilspy 工具管理器
        return global_multilspy_tool_manager.create_tools_for_workspace(
            str(self.workspace_path),
            languages=self.config.languages
        )
    
    def _create_tools_for_server(self, server: LanguageServer, language: Language) -> List[AntTool]:
        """为指定的服务器创建工具（已废弃，使用全局工具管理器）"""
        # 这个方法现在由全局工具管理器处理
        return []

# 全局管理器实例
_lsp_manager: Optional[MultilspyLSPManager] = None

def get_lsp_manager(config: LSPConfig) -> MultilspyLSPManager:
    """获取全局 LSP 管理器实例"""
    global _lsp_manager
    if _lsp_manager is None:
        _lsp_manager = MultilspyLSPManager(config)
    return _lsp_manager