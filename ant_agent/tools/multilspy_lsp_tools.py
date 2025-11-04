# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""
Multilspy LSP 工具
基于 multilspy 库提供多语言 LSP 支持
"""

import logging
import ast
from pathlib import Path
from typing import Dict, List, Optional, Any, Type, Union
from ant_agent.tools.base import AntTool, AntToolResult
from multilspy import SyncLanguageServer
from multilspy.multilspy_config import MultilspyConfig
from multilspy.multilspy_logger import MultilspyLogger
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# 工具状态管理器
class ToolState:
    """管理工具状态的辅助类"""
    
    def __init__(self):
        self.servers: Dict[str, SyncLanguageServer] = {}
        self.workspace_paths: Dict[str, str] = {}
        self.languages: Dict[str, str] = {}
    
    def get_server(self, tool_name: str) -> Optional[SyncLanguageServer]:
        """获取工具的服务器"""
        return self.servers.get(tool_name)
    
    def set_server(self, tool_name: str, server: SyncLanguageServer) -> None:
        """设置工具的服务器"""
        self.servers[tool_name] = server
    
    def get_workspace_path(self, tool_name: str) -> Optional[str]:
        """获取工具的工作空间路径"""
        return self.workspace_paths.get(tool_name)
    
    def set_workspace_path(self, tool_name: str, path: str) -> None:
        """设置工具的工作空间路径"""
        self.workspace_paths[tool_name] = path
    
    def get_language(self, tool_name: str) -> Optional[str]:
        """获取工具的语言"""
        return self.languages.get(tool_name)
    
    def set_language(self, tool_name: str, language: str) -> None:
        """设置工具的语言"""
        self.languages[tool_name] = language

# 全局工具状态
_global_tool_state = ToolState()

# 输入模型
class LSPPositionInput(BaseModel):
    """LSP 位置输入模型"""
    file_path: str = Field(description="文件路径（相对于工作目录）")
    line: int = Field(description="行号（从0开始）")
    character: int = Field(description="字符位置（从0开始）")

class LSPFileInput(BaseModel):
    """LSP 文件输入模型"""
    file_path: str = Field(description="文件路径（相对于工作目录）")

# Definition 工具
class MultilspyDefinitionTool(AntTool):
    """Multilspy Definition 工具"""

    name: str = "multilspy_definition"
    description: str = "跳转到代码的定义 (基于 Multilspy)"
    args_schema: Type[BaseModel] = LSPPositionInput
    language: str
    workspace_path: str

    def __init__(self, language: str, workspace_path: str, **kwargs):
        # Set language and workspace_path before calling super().__init__ to pass Pydantic validation
        kwargs['language'] = language
        kwargs['workspace_path'] = workspace_path
        super().__init__(**kwargs)
        self.name = f"multilspy_{language}_definition"
        self.description = f"""Find the definition location of {language.upper()} functions, classes, and variables using LSP.

When to use:
- To locate where a function, class, or variable is defined
- For 'go to definition' functionality
- To find the source file containing the implementation

Requirements:
- Use position_finder first to get accurate line/character coordinates
- Works best with precise position data from position_finder

Returns:
- File path and position of the definition
- Multiple results if symbol has multiple definitions"""

        _global_tool_state.set_language(self.name, language)
        _global_tool_state.set_workspace_path(self.name, workspace_path)

    def _get_absolute_path(self, file_path: str) -> str:
        """获取文件的绝对路径"""
        path = Path(file_path)
        if path.is_absolute():
            return str(path)
        else:
            return str(Path(self.workspace_path) / path)

    def start_lsp_server(self) -> None:
        """启动 LSP 服务器，添加工作空间验证和状态检查"""
        existing_server = _global_tool_state.get_server(self.name)

        # 检查现有 server 是否有效且工作空间匹配
        if existing_server is not None:
            try:
                # 验证 server 是否仍然健康
                stored_workspace = _global_tool_state.get_workspace_path(self.name)
                if stored_workspace == self.workspace_path:
                    # 检查 server 是否响应（简单健康检查）
                    logger.debug(f"{self.language} LSP server already exists and workspace matches, reusing")
                    return
                else:
                    # 工作空间不匹配，需要重新创建
                    logger.info(f"工作空间变化: {stored_workspace} -> {self.workspace_path}, 重新创建 {self.language} LSP server")
                    # 尝试停止旧的 server
                    try:
                        if hasattr(existing_server, 'stop'):
                            existing_server.stop()
                    except Exception as e:
                        logger.warning(f"停止旧 server 失败: {e}")
                    # 清除旧的 server
                    _global_tool_state.set_server(self.name, None)
            except Exception as e:
                logger.warning(f"检查现有 server 状态时出错: {e}，将重新创建")
                _global_tool_state.set_server(self.name, None)

        try:
            # Use member variables instead of global state
            if not self.language or not self.workspace_path:
                raise RuntimeError("语言或工作空间路径未设置")

            # 验证工作空间路径存在
            workspace_path_obj = Path(self.workspace_path)
            if not workspace_path_obj.exists():
                raise RuntimeError(f"工作空间路径不存在: {self.workspace_path}")
            if not workspace_path_obj.is_dir():
                raise RuntimeError(f"工作空间路径不是目录: {self.workspace_path}")

            config = MultilspyConfig.from_dict({
                "code_language": self.language,
                "trace_lsp_communication": False,
                "start_independent_lsp_process": True
            })

            multilspy_logger = MultilspyLogger(False)

            logger.info(f"创建 {self.language} LSP 服务器，工作空间: {self.workspace_path}")
            server = SyncLanguageServer.create(
                config,
                multilspy_logger,
                str(workspace_path_obj.absolute())
            )

            _global_tool_state.set_server(self.name, server)
            _global_tool_state.set_workspace_path(self.name, self.workspace_path)
            logger.info(f"✅ {self.language} LSP 服务器创建成功")

        except Exception as e:
            logger.error(f"创建 {self.language} LSP 服务器失败: {e}")
            raise

    def _get_absolute_path(self, file_path: str) -> str:
        """获取文件的绝对路径"""
        path = Path(file_path)
        if path.is_absolute():
            return str(path)
        else:
            return str(Path(self.workspace_path) / path)
    
    def start_lsp_server(self) -> None:
        """启动 LSP 服务器"""
        if _global_tool_state.get_server(self.name) is not None:
            return
            
        try:
            language = _global_tool_state.get_language(self.name)
            workspace_path = _global_tool_state.get_workspace_path(self.name)
            
            if not language or not workspace_path:
                raise RuntimeError("语言或工作空间路径未设置")
            
            config = MultilspyConfig.from_dict({
                "code_language": language,
                "trace_lsp_communication": False,
                "start_independent_lsp_process": True
            })
            
            multilspy_logger = MultilspyLogger(False)
            
            server = SyncLanguageServer.create(
                config, 
                multilspy_logger, 
                workspace_path
            )
            
            _global_tool_state.set_server(self.name, server)
            logger.info(f"{language} LSP 服务器已创建")
            
        except Exception as e:
            logger.error(f"创建 LSP 服务器失败: {e}")
            raise
    
    def _run(self, file_path: str, line: int, character: int) -> AntToolResult:
        """执行 definition 请求"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                self.start_lsp_server()

                # 处理路径：将绝对路径转换为相对于workspace的相对路径
                try:
                    # 如果传入的是相对路径，先转换为绝对路径
                    absolute_path = self._get_absolute_path(file_path)
                    # 然后转换为相对于workspace的相对路径，供multilspy使用
                    relative_path = str(Path(absolute_path).relative_to(self.workspace_path))
                except ValueError as e:
                    return AntToolResult(
                        success=False,
                        error=f"文件路径 {file_path} 不在工作空间 {self.workspace_path} 内: {str(e)}"
                    )

                server = _global_tool_state.get_server(self.name)

                if not server:
                    return AntToolResult(success=False, error="LSP 服务器未启动")

                with server.start_server():
                    # 使用相对路径调用multilspy
                    result = server.request_definition(relative_path, line, character)

                    if result:
                        # 解析LSP定义结果
                        parsed_result = parse_lsp_definition_result(str(result))

                        if parsed_result['success']:
                            # 生成格式化的输出
                            formatted_output = format_lsp_definition_result(parsed_result['definitions'])

                            # 构建元数据
                            metadata = {
                                'definition_count': parsed_result.get('total_definitions', 0),
                                'summary': parsed_result.get('summary', ''),
                                'language': _global_tool_state.get_language(self.name),
                                'file_path': file_path,
                                'position': {'line': line, 'character': character},
                                'retry_count': retry_count
                            }

                            return AntToolResult(
                                success=True,
                                output=formatted_output,
                                metadata=metadata
                            )
                        else:
                            # 解析失败，返回原始结果和错误信息
                            return AntToolResult(
                                success=True,
                                output=str(result),
                                metadata={'parse_error': parsed_result.get('error'), 'retry_count': retry_count}
                            )
                    else:
                        # 没有返回结果，可能是文件读取问题
                        error_detail = f"在 {file_path}:{line}:{character} 没有找到定义"
                        if retry_count < max_retries - 1:
                            logger.warning(f"{error_detail}，尝试重试 #{retry_count + 1}")
                            retry_count += 1
                            continue
                        else:
                            return AntToolResult(
                                success=False,
                                error=error_detail,
                                metadata={'retry_count': retry_count, 'max_retries': max_retries}
                            )

            except FileNotFoundError as e:
                error_detail = f"文件读取失败: 文件 {file_path} 不存在或无法访问"
                if retry_count < max_retries - 1:
                    logger.warning(f"{error_detail}，尝试重试 #{retry_count + 1}")
                    retry_count += 1
                    # 短暂等待后重试
                    import time
                    time.sleep(0.5 * (retry_count + 1))  # 递增等待时间
                    continue
                else:
                    logger.error(f"{error_detail}，已达到最大重试次数")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (重试 {retry_count + 1} 次后仍然失败)",
                        metadata={'error_type': 'file_not_found', 'file_path': file_path, 'retry_count': retry_count}
                    )

            except PermissionError as e:
                error_detail = f"文件权限错误: 无法读取文件 {file_path}"
                if retry_count < max_retries - 1:
                    logger.warning(f"{error_detail}，尝试重试 #{retry_count + 1}")
                    retry_count += 1
                    continue
                else:
                    logger.error(f"{error_detail}，已达到最大重试次数")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (重试 {retry_count + 1} 次后仍然失败)",
                        metadata={'error_type': 'permission_error', 'file_path': file_path, 'retry_count': retry_count}
                    )

            except Exception as e:
                error_detail = f"Definition 请求失败: {type(e).__name__}: {str(e)}"
                logger.error(error_detail)

                if retry_count < max_retries - 1:
                    logger.warning(f"尝试重试 #{retry_count + 1}")
                    retry_count += 1
                    # 短暂等待后重试
                    import time
                    time.sleep(0.5 * (retry_count + 1))
                    continue
                else:
                    logger.error(f"已达到最大重试次数，错误: {error_detail}")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (重试 {retry_count + 1} 次后仍然失败)",
                        metadata={'error_type': type(e).__name__, 'error_message': str(e), 'retry_count': retry_count}
                    )

# References 工具
class MultilspyReferencesTool(AntTool):
    """Multilspy References 工具"""

    name: str = "multilspy_references"
    description: str = "查找代码的引用 (基于 Multilspy)"
    args_schema: Type[BaseModel] = LSPPositionInput
    language: str
    workspace_path: str

    def __init__(self, language: str, workspace_path: str, **kwargs):
        # Set language and workspace_path before calling super().__init__ to pass Pydantic validation
        kwargs['language'] = language
        kwargs['workspace_path'] = workspace_path
        super().__init__(**kwargs)
        self.name = f"multilspy_{language}_references"
        self.description = f"""Find all references to {language.upper()} functions, classes, and variables using LSP.

When to use:
- To see all places where a function is called
- To understand how a class is used throughout the codebase
- To find all usages of a variable or constant
- For impact analysis before making changes

Requirements:
- Use position_finder first to get accurate line/character coordinates
- Point to the exact symbol whose references you want to find

Returns:
- List of all files and positions where the symbol is referenced
- Context around each reference for easy understanding"""

        _global_tool_state.set_language(self.name, language)
        _global_tool_state.set_workspace_path(self.name, workspace_path)
    
    def _get_absolute_path(self, file_path: str) -> str:
        """获取文件的绝对路径"""
        path = Path(file_path)
        if path.is_absolute():
            return str(path)
        else:
            return str(Path(self.workspace_path) / path)

    def start_lsp_server(self) -> None:
        """启动 LSP 服务器"""
        if _global_tool_state.get_server(self.name) is not None:
            return

        try:
            # Use member variables instead of global state
            if not self.language or not self.workspace_path:
                raise RuntimeError("语言或工作空间路径未设置")

            # 验证工作空间路径存在
            workspace_path_obj = Path(self.workspace_path)
            if not workspace_path_obj.exists():
                raise RuntimeError(f"工作空间路径不存在: {self.workspace_path}")
            if not workspace_path_obj.is_dir():
                raise RuntimeError(f"工作空间路径不是目录: {self.workspace_path}")
                raise RuntimeError("语言或工作空间路径未设置")

            config = MultilspyConfig.from_dict({
                "code_language": self.language,
                "trace_lsp_communication": False,
                "start_independent_lsp_process": True
            })

            multilspy_logger = MultilspyLogger(False)

            logger.info(f"创建 {self.language} LSP 服务器，工作空间: {self.workspace_path}")
            server = SyncLanguageServer.create(
                config,
                multilspy_logger,
                str(workspace_path_obj.absolute())
            )

            _global_tool_state.set_server(self.name, server)
            _global_tool_state.set_workspace_path(self.name, self.workspace_path)
            logger.info(f"✅ {self.language} LSP 服务器创建成功")

        except Exception as e:
            logger.error(f"创建 LSP 服务器失败: {e}")
            raise

    def _run(self, file_path: str, line: int, character: int) -> AntToolResult:
        """执行 references 请求"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                self.start_lsp_server()

                # 处理路径：将绝对路径转换为相对于workspace的相对路径
                try:
                    # 如果传入的是相对路径，先转换为绝对路径
                    absolute_path = self._get_absolute_path(file_path)
                    # 然后转换为相对于workspace的相对路径，供multilspy使用
                    relative_path = str(Path(absolute_path).relative_to(self.workspace_path))
                except ValueError as e:
                    return AntToolResult(
                        success=False,
                        error=f"文件路径 {file_path} 不在工作空间 {self.workspace_path} 内: {str(e)}"
                    )

                server = _global_tool_state.get_server(self.name)

                if not server:
                    return AntToolResult(success=False, error="LSP 服务器未启动")

                with server.start_server():
                    # 使用相对路径调用multilspy
                    result = server.request_references(relative_path, line, character)

                    if result:
                        return AntToolResult(
                            success=True,
                            output=str(result),
                            metadata={'retry_count': retry_count}
                        )
                    else:
                        # 没有返回结果，可能是文件读取问题
                        error_detail = f"在 {file_path}:{line}:{character} 没有找到引用"
                        if retry_count < max_retries - 1:
                            logger.warning(f"{error_detail}，尝试重试 #{retry_count + 1}")
                            retry_count += 1
                            continue
                        else:
                            return AntToolResult(
                                success=False,
                                error=error_detail,
                                metadata={'retry_count': retry_count, 'max_retries': max_retries}
                            )

            except FileNotFoundError as e:
                error_detail = f"文件读取失败: 文件 {file_path} 不存在或无法访问"
                if retry_count < max_retries - 1:
                    logger.warning(f"{error_detail}，尝试重试 #{retry_count + 1}")
                    retry_count += 1
                    # 短暂等待后重试
                    import time
                    time.sleep(0.5 * (retry_count + 1))  # 递增等待时间
                    continue
                else:
                    logger.error(f"{error_detail}，已达到最大重试次数")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (重试 {retry_count + 1} 次后仍然失败)",
                        metadata={'error_type': 'file_not_found', 'file_path': file_path, 'retry_count': retry_count}
                    )

            except PermissionError as e:
                error_detail = f"文件权限错误: 无法读取文件 {file_path}"
                if retry_count < max_retries - 1:
                    logger.warning(f"{error_detail}，尝试重试 #{retry_count + 1}")
                    retry_count += 1
                    continue
                else:
                    logger.error(f"{error_detail}，已达到最大重试次数")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (重试 {retry_count + 1} 次后仍然失败)",
                        metadata={'error_type': 'permission_error', 'file_path': file_path, 'retry_count': retry_count}
                    )

            except Exception as e:
                error_detail = f"References 请求失败: {type(e).__name__}: {str(e)}"
                logger.error(error_detail)

                if retry_count < max_retries - 1:
                    logger.warning(f"尝试重试 #{retry_count + 1}")
                    retry_count += 1
                    # 短暂等待后重试
                    import time
                    time.sleep(0.5 * (retry_count + 1))
                    continue
                else:
                    logger.error(f"已达到最大重试次数，错误: {error_detail}")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (重试 {retry_count + 1} 次后仍然失败)",
                        metadata={'error_type': type(e).__name__, 'error_message': str(e), 'retry_count': retry_count}
                    )


# Declaration 工具
class MultilspyDeclarationTool(AntTool):
    """Multilspy Declaration 工具"""

    name: str = "multilspy_declaration"
    description: str = "跳转到代码的声明 (基于 Multilspy)"
    args_schema: Type[BaseModel] = LSPPositionInput
    language: str
    workspace_path: str

    def __init__(self, language: str, workspace_path: str, **kwargs):
        # Set language and workspace_path before calling super().__init__ to pass Pydantic validation
        kwargs['language'] = language
        kwargs['workspace_path'] = workspace_path
        super().__init__(**kwargs)
        self.name = f"multilspy_{language}_declaration"
        self.description = f"""Find the declaration of {language.upper()} functions, classes, and variables using LSP.

When to use:
- To find where a variable or symbol is declared vs where it's implemented
- For interface/abstract class declarations
- To understand the type/signature without seeing implementation
- When declaration and definition are in different locations

Requirements:
- Use position_finder first to get accurate line/character coordinates
- Point to the symbol whose declaration you want to find

Returns:
- File path and position of the declaration
- Type information and signatures for declarations"""

        _global_tool_state.set_language(self.name, language)
        _global_tool_state.set_workspace_path(self.name, workspace_path)

    def _get_absolute_path(self, file_path: str) -> str:
        """获取文件的绝对路径"""
        path = Path(file_path)
        if path.is_absolute():
            return str(path)
        else:
            return str(Path(self.workspace_path) / path)

    def start_lsp_server(self) -> None:
        """启动 LSP 服务器"""
        if _global_tool_state.get_server(self.name) is not None:
            return

        try:
            # Use member variables instead of global state
            if not self.language or not self.workspace_path:
                raise RuntimeError("语言或工作空间路径未设置")

            # 验证工作空间路径存在
            workspace_path_obj = Path(self.workspace_path)
            if not workspace_path_obj.exists():
                raise RuntimeError(f"工作空间路径不存在: {self.workspace_path}")
            if not workspace_path_obj.is_dir():
                raise RuntimeError(f"工作空间路径不是目录: {self.workspace_path}")
                raise RuntimeError("语言或工作空间路径未设置")

            config = MultilspyConfig.from_dict({
                "code_language": self.language,
                "trace_lsp_communication": False,
                "start_independent_lsp_process": True
            })

            multilspy_logger = MultilspyLogger(False)

            server = SyncLanguageServer.create(
                config,
                multilspy_logger,
                self.workspace_path
            )

            _global_tool_state.set_server(self.name, server)
            logger.info(f"✅ 成功启动 {self.language} LSP 服务器")

        except Exception as e:
            logger.error(f"启动 {self.language} LSP 服务器失败: {e}")
            raise RuntimeError(f"无法启动 {self.language} LSP 服务器: {e}")

    def _run(self, file_path: str, line: int, character: int) -> AntToolResult:
        """查找声明"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                self.start_lsp_server()
                server = _global_tool_state.get_server(self.name)

                if not server:
                    return AntToolResult(
                        success=False,
                        error="LSP 服务器未启动"
                    )

                # 处理路径：将绝对路径转换为相对于workspace的相对路径
                try:
                    # 如果传入的是相对路径，先转换为绝对路径
                    absolute_path = self._get_absolute_path(file_path)
                    # 然后转换为相对于workspace的相对路径，供multilspy使用
                    relative_path = str(Path(absolute_path).relative_to(self.workspace_path))
                except ValueError as e:
                    return AntToolResult(
                        success=False,
                        error=f"文件路径 {file_path} 不在工作空间 {self.workspace_path} 内: {str(e)}"
                    )

                # 使用 LSP 查找声明
                with server.start_server():
                    try:
                        # 注意：multilspy 的 request_definition 实际上可以处理声明和定义
                        # 这里我们使用相同的方法，但在描述上区分概念
                        locations = server.request_definition(relative_path, line, character)

                        if not locations:
                            error_detail = f"在 {file_path}:{line}:{character} 没有找到声明"
                            if retry_count < max_retries - 1:
                                logger.warning(f"{error_detail}，尝试重试 #{retry_count + 1}")
                                retry_count += 1
                                continue
                            else:
                                return AntToolResult(
                                    success=False,
                                    error=error_detail,
                                    metadata={'retry_count': retry_count, 'max_retries': max_retries, 'suggestion': '尝试使用 go_to_definition 工具，或检查位置是否正确'}
                                )

                        # 格式化结果
                        formatted_locations = []
                        for loc in locations:
                            formatted_locations.append({
                                "file_path": loc["uri"].replace("file://", ""),
                                "line": loc["range"]["start"]["line"],
                                "character": loc["range"]["start"]["character"],
                                "range": loc["range"]
                            })

                        result = {
                            "declarations_found": len(formatted_locations),
                            "declarations": formatted_locations,
                            "language": _global_tool_state.get_language(self.name),
                            'retry_count': retry_count
                        }

                        return AntToolResult(
                            success=True,
                            output=f"Found {len(formatted_locations)} declaration(s)",
                            metadata=result
                        )

                    except FileNotFoundError as e:
                        error_detail = f"文件读取失败: 文件 {file_path} 不存在或无法访问"
                        if retry_count < max_retries - 1:
                            logger.warning(f"{error_detail}，尝试重试 #{retry_count + 1}")
                            retry_count += 1
                            # 短暂等待后重试
                            import time
                            time.sleep(0.5 * (retry_count + 1))  # 递增等待时间
                            continue
                        else:
                            logger.error(f"{error_detail}，已达到最大重试次数")
                            return AntToolResult(
                                success=False,
                                error=f"{error_detail} (重试 {retry_count + 1} 次后仍然失败)",
                                metadata={'error_type': 'file_not_found', 'file_path': file_path, 'retry_count': retry_count}
                            )

                    except PermissionError as e:
                        error_detail = f"文件权限错误: 无法读取文件 {file_path}"
                        if retry_count < max_retries - 1:
                            logger.warning(f"{error_detail}，尝试重试 #{retry_count + 1}")
                            retry_count += 1
                            continue
                        else:
                            logger.error(f"{error_detail}，已达到最大重试次数")
                            return AntToolResult(
                                success=False,
                                error=f"{error_detail} (重试 {retry_count + 1} 次后仍然失败)",
                                metadata={'error_type': 'permission_error', 'file_path': file_path, 'retry_count': retry_count}
                            )

                    except Exception as e:
                        error_detail = f"Declaration 请求失败: {type(e).__name__}: {str(e)}"
                        logger.error(error_detail)

                        if retry_count < max_retries - 1:
                            logger.warning(f"尝试重试 #{retry_count + 1}")
                            retry_count += 1
                            # 短暂等待后重试
                            import time
                            time.sleep(0.5 * (retry_count + 1))
                            continue
                        else:
                            logger.error(f"已达到最大重试次数，错误: {error_detail}")
                            return AntToolResult(
                                success=False,
                                error=f"{error_detail} (重试 {retry_count + 1} 次后仍然失败)",
                                metadata={'error_type': type(e).__name__, 'error_message': str(e), 'retry_count': retry_count, 'suggestion': '检查文件路径和位置是否正确'}
                            )

            except FileNotFoundError as e:
                error_detail = f"文件读取失败: 文件 {file_path} 不存在或无法访问"
                if retry_count < max_retries - 1:
                    logger.warning(f"{error_detail}，尝试重试 #{retry_count + 1}")
                    retry_count += 1
                    # 短暂等待后重试
                    import time
                    time.sleep(0.5 * (retry_count + 1))  # 递增等待时间
                    continue
                else:
                    logger.error(f"{error_detail}，已达到最大重试次数")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (重试 {retry_count + 1} 次后仍然失败)",
                        metadata={'error_type': 'file_not_found', 'file_path': file_path, 'retry_count': retry_count}
                    )

            except PermissionError as e:
                error_detail = f"文件权限错误: 无法读取文件 {file_path}"
                if retry_count < max_retries - 1:
                    logger.warning(f"{error_detail}，尝试重试 #{retry_count + 1}")
                    retry_count += 1
                    continue
                else:
                    logger.error(f"{error_detail}，已达到最大重试次数")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (重试 {retry_count + 1} 次后仍然失败)",
                        metadata={'error_type': 'permission_error', 'file_path': file_path, 'retry_count': retry_count}
                    )

            except Exception as e:
                error_detail = f"Declaration 工具执行失败: {type(e).__name__}: {str(e)}"
                logger.error(error_detail)

                if retry_count < max_retries - 1:
                    logger.warning(f"尝试重试 #{retry_count + 1}")
                    retry_count += 1
                    # 短暂等待后重试
                    import time
                    time.sleep(0.5 * (retry_count + 1))
                    continue
                else:
                    logger.error(f"已达到最大重试次数，错误: {error_detail}")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (重试 {retry_count + 1} 次后仍然失败)",
                        metadata={'error_type': type(e).__name__, 'error_message': str(e), 'retry_count': retry_count, 'suggestion': '尝试使用 position_finder 获取准确坐标'}
                    )


# 工具工厂
class MultilspyToolFactory:
    """Multilspy 工具工厂"""
    
    # 支持的语言
    SUPPORTED_LANGUAGES = {
        "python": "Python",
        "java": "Java", 
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "rust": "Rust",
        "go": "Go",
        "csharp": "C#",
        "cpp": "C++",
        "ruby": "Ruby",
        "dart": "Dart",
        "solidity": "Solidity",
        "kotlin": "Kotlin"
    }
    
    # 工具类型映射
    TOOL_TYPES = {
        "definition": MultilspyDefinitionTool,
        "references": MultilspyReferencesTool,
        "declaration": MultilspyDeclarationTool
    }
    
    @classmethod
    def create_tools(cls, workspace_path: str, languages: Optional[List[str]] = None) -> List[AntTool]:
        """
        创建 Multilspy LSP 工具
        
        Args:
            workspace_path: 工作目录路径
            languages: 要创建工具的语言列表，如果为 None 则创建所有支持的语言
            
        Returns:
            工具列表
        """
        tools = []
        
        if languages is None:
            languages = list(cls.SUPPORTED_LANGUAGES.keys())
        
        for language in languages:
            if language not in cls.SUPPORTED_LANGUAGES:
                logger.warning(f"不支持的语言: {language}")
                continue
                
            # 为每种语言创建所有类型的工具
            for tool_type, tool_class in cls.TOOL_TYPES.items():
                try:
                    tool = tool_class(language, workspace_path)
                    tools.append(tool)
                    logger.info(f"创建工具: {tool.name}")
                except Exception as e:
                    logger.error(f"创建 {language} 的 {tool_type} 工具失败: {e}")
        
        logger.info(f"成功创建 {len(tools)} 个 Multilspy LSP 工具")
        return tools
    
    @classmethod
    def create_tool(cls, language: str, tool_type: str, workspace_path: str) -> Optional[AntTool]:
        """创建单个工具"""
        if language not in cls.SUPPORTED_LANGUAGES:
            logger.error(f"不支持的语言: {language}")
            return None
            
        if tool_type not in cls.TOOL_TYPES:
            logger.error(f"不支持的工具类型: {tool_type}")
            return None
            
        try:
            tool_class = cls.TOOL_TYPES[tool_type]
            tool = tool_class(language, workspace_path)
            logger.info(f"创建工具: {tool.name}")
            return tool
        except Exception as e:
            logger.error(f"创建 {language} 的 {tool_type} 工具失败: {e}")
            return None

# 工具管理器
class MultilspyToolManager:
    """Multilspy 工具管理器"""
    
    def __init__(self):
        self.tools: Dict[str, AntTool] = {}
        self.logger = logging.getLogger(__name__)
    
    def create_tools_for_workspace(self, workspace_path: str, languages: Optional[List[str]] = None) -> List[AntTool]:
        """为工作空间创建工具"""
        tools = MultilspyToolFactory.create_tools(workspace_path, languages)
        
        for tool in tools:
            self.tools[tool.name] = tool
            
        self.logger.info(f"为工作空间 {workspace_path} 创建了 {len(tools)} 个工具")
        return tools
    
    def get_tool(self, name: str) -> Optional[AntTool]:
        """获取工具"""
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[AntTool]:
        """获取所有工具"""
        return list(self.tools.values())
    
    def get_tools_by_language(self, language: str) -> List[AntTool]:
        """获取指定语言的工具"""
        return [tool for tool in self.tools.values() if tool.name.startswith(f"multilspy_{language}_")]
    
    def list_available_tools(self) -> List[str]:
        """列出可用工具名称"""
        return list(self.tools.keys())

# 全局工具管理器实例
global_multilspy_tool_manager = MultilspyToolManager()

# 工具上下文设置函数（供其他模块使用）
def set_tool_context(tool_name: str, server, language) -> None:
    """设置工具的上下文信息"""
    # 这里可以添加工具上下文的逻辑
    logger.info(f"设置工具 {tool_name} 的上下文: {language.value}")
    pass


def parse_lsp_definition_result(definition_output: str) -> Dict[str, Any]:
    """
    解析LSP definition请求返回的结果
    
    Args:
        definition_output: LSP返回的Python字面量格式字符串
        
    Returns:
        结构化的定义信息，包含以下字段：
        - success: 是否成功解析
        - definitions: 定义列表（如果成功）
        - error: 错误信息（如果失败）
        - summary: 定义摘要信息
    """
    try:
        # 处理空或None输入
        if not definition_output or definition_output.strip() in ['None', '']:
            return {
                "success": True,
                "definitions": [],
                "error": None,
                "summary": "没有找到定义"
            }
        
        # 尝试解析Python字面量
        try:
            # 安全地评估Python字面量表达式
            parsed_result = ast.literal_eval(definition_output.strip())
        except (ValueError, SyntaxError, MemoryError) as e:
            # 如果字面量解析失败，尝试清理和修复常见的格式问题
            cleaned_output = definition_output.strip()
            
            # 处理可能的字符串转义问题
            if cleaned_output.startswith('[') and cleaned_output.endswith(']'):
                try:
                    # 尝试用json解析（更安全）
                    import json
                    parsed_result = json.loads(cleaned_output)
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "definitions": [],
                        "error": f"无法解析定义结果格式: {str(e)}",
                        "summary": "解析失败"
                    }
            else:
                return {
                    "success": False,
                    "definitions": [],
                    "error": f"无效的LSP定义结果格式: {str(e)}",
                    "summary": "解析失败"
                }
        
        # 验证解析结果的基本结构
        if not isinstance(parsed_result, list):
            return {
                "success": False,
                "definitions": [],
                "error": "LSP定义结果应该是列表格式",
                "summary": "格式错误"
            }
        
        # 处理空列表
        if not parsed_result:
            return {
                "success": True,
                "definitions": [],
                "error": None,
                "summary": "没有找到定义"
            }
        
        # 解析每个定义项
        definitions = []
        for i, location in enumerate(parsed_result):
            try:
                # 验证基本结构
                if not isinstance(location, dict):
                    logger.warning(f"定义项 {i} 不是字典格式，跳过")
                    continue
                
                # 提取定义信息
                definition_info = {
                    "index": i + 1,
                    "file_path": location.get("relativePath") or location.get("absolutePath", "未知路径"),
                    "absolute_path": location.get("absolutePath", ""),
                    "relative_path": location.get("relativePath", ""),
                    "uri": location.get("uri", ""),
                    "range": None,
                    "start_position": None,
                    "end_position": None
                }
                
                # 处理范围信息
                range_info = location.get("range")
                if isinstance(range_info, dict):
                    definition_info["range"] = range_info
                    
                    # 提取开始位置
                    start_pos = range_info.get("start")
                    if isinstance(start_pos, dict):
                        definition_info["start_position"] = {
                            "line": start_pos.get("line", -1) + 1,  # 转换为1基索引
                            "character": start_pos.get("character", -1) + 1
                        }
                    
                    # 提取结束位置
                    end_pos = range_info.get("end")
                    if isinstance(end_pos, dict):
                        definition_info["end_position"] = {
                            "line": end_pos.get("line", -1) + 1,  # 转换为1基索引
                            "character": end_pos.get("character", -1) + 1
                        }
                
                # 生成位置描述
                if definition_info["start_position"]:
                    pos = definition_info["start_position"]
                    definition_info["location_desc"] = f"第 {pos['line']} 行，第 {pos['character']} 列"
                else:
                    definition_info["location_desc"] = "未知位置"
                
                # 生成文件类型信息
                file_path = definition_info["file_path"]
                if file_path and file_path != "未知路径":
                    file_ext = Path(file_path).suffix.lower()
                    lang_map = {
                        ".py": "Python",
                        ".js": "JavaScript",
                        ".ts": "TypeScript",
                        ".java": "Java",
                        ".kt": "Kotlin",
                        ".cs": "C#",
                        ".cpp": "C++",
                        ".c": "C",
                        ".rs": "Rust",
                        ".go": "Go",
                        ".rb": "Ruby",
                        ".dart": "Dart",
                        ".sol": "Solidity",
                        ".php": "PHP",
                        ".swift": "Swift",
                        ".scala": "Scala",
                        ".r": "R",
                        ".m": "Objective-C",
                        ".mm": "Objective-C++"
                    }
                    definition_info["language"] = lang_map.get(file_ext, "未知语言")
                else:
                    definition_info["language"] = "未知语言"
                
                definitions.append(definition_info)
                
            except Exception as e:
                logger.warning(f"解析定义项 {i} 时出错: {str(e)}")
                continue
        
        # 生成摘要信息
        if not definitions:
            summary = "没有找到有效的定义"
        elif len(definitions) == 1:
            def_info = definitions[0]
            summary = f"找到 1 个定义：{def_info['language']} 文件 {def_info['file_path']}，{def_info['location_desc']}"
        else:
            # 按语言分组统计
            lang_counts = {}
            for def_info in definitions:
                lang = def_info['language']
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
            
            summary_parts = []
            for lang, count in lang_counts.items():
                summary_parts.append(f"{lang}: {count}个")
            
            summary = f"找到 {len(definitions)} 个定义（{'，'.join(summary_parts)}）"
        
        return {
            "success": True,
            "definitions": definitions,
            "error": None,
            "summary": summary,
            "total_definitions": len(definitions)
        }
        
    except Exception as e:
        error_msg = f"解析LSP定义结果时发生未知错误: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "definitions": [],
            "error": error_msg,
            "summary": "解析失败"
        }


def format_lsp_definition_result(definitions: List[Dict[str, Any]]) -> str:
    """
    格式化LSP定义结果，生成易于大模型理解的文本描述
    
    Args:
        definitions: 解析后的定义列表
        
    Returns:
        格式化的文本描述
    """
    if not definitions:
        return "没有找到定义"
    
    lines = []
    lines.append(f"找到 {len(definitions)} 个定义：")
    
    for i, definition in enumerate(definitions, 1):
        lines.append(f"\n定义 {i}:")
        lines.append(f"  文件: {definition['file_path']}")
        lines.append(f"  语言: {definition['language']}")
        
        if definition['location_desc'] != "未知位置":
            lines.append(f"  位置: {definition['location_desc']}")
        
        if definition['relative_path'] and definition['relative_path'] != definition['file_path']:
            lines.append(f"  相对路径: {definition['relative_path']}")
        
        if definition['uri']:
            lines.append(f"  URI: {definition['uri']}")
        
        # 添加范围信息（如果有）
        if definition['start_position'] and definition['end_position']:
            start = definition['start_position']
            end = definition['end_position']
            if start != end:
                lines.append(f"  范围: 从第 {start['line']} 行第 {start['character']} 列到第 {end['line']} 行第 {end['character']} 列")
    
    return "\n".join(lines)