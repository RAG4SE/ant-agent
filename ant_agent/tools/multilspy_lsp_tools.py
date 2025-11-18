# Copyright (c) Haoyang Ma
# SPDX-License-Identifier: MIT

"""
Multilspy LSP Tools
Provides multi-language LSP support based on the multilspy library
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

# Tool state manager
class ToolState:
    """Helper class for managing tool state"""
    
    def __init__(self):
        self.servers: Dict[str, SyncLanguageServer] = {}
        self.workspace_paths: Dict[str, str] = {}
        self.languages: Dict[str, str] = {}
    
    def get_server(self, tool_name: str) -> Optional[SyncLanguageServer]:
        """Get tool server"""
        return self.servers.get(tool_name)
    
    def set_server(self, tool_name: str, server: SyncLanguageServer) -> None:
        """Set tool server"""
        self.servers[tool_name] = server
    
    def get_workspace_path(self, tool_name: str) -> Optional[str]:
        """Get tool workspace path"""
        return self.workspace_paths.get(tool_name)
    
    def set_workspace_path(self, tool_name: str, path: str) -> None:
        """Set tool workspace path"""
        self.workspace_paths[tool_name] = path
    
    def get_language(self, tool_name: str) -> Optional[str]:
        """Get tool language"""
        return self.languages.get(tool_name)
    
    def set_language(self, tool_name: str, language: str) -> None:
        """Set tool language"""
        self.languages[tool_name] = language

# Global tool state
_global_tool_state = ToolState()

# Input models
class LSPPositionInput(BaseModel):
    """LSP position input model"""
    file_path: str = Field(description="File path (relative to working directory)")
    line: int = Field(description="Line number (0-based)")
    character: int = Field(description="Character position (0-based)")

class LSPFileInput(BaseModel):
    """LSP file input model"""
    file_path: str = Field(description="File path (relative to working directory)")

# Definition tool
class MultilspyDefinitionTool(AntTool):
    """Multilspy Definition tool"""

    name: str = "multilspy_definition"
    description: str = "Jump to code definition (based on Multilspy)"
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
        """Get absolute file path"""
        path = Path(file_path)
        if path.is_absolute():
            return str(path)
        else:
            return str(Path(self.workspace_path) / path)

    def start_lsp_server(self) -> None:
        """Start LSP server with workspace validation and status checks"""
        existing_server = _global_tool_state.get_server(self.name)

        # Check if existing server is valid and workspace matches
        if existing_server is not None:
            try:
                # Verify if server is still healthy
                stored_workspace = _global_tool_state.get_workspace_path(self.name)
                if stored_workspace == self.workspace_path:
                    # Check if server responds (simple health check)
                    logger.debug(f"{self.language} LSP server already exists and workspace matches, reusing")
                    return
                else:
                    # Workspace mismatch, need Recreating
                    logger.info(f"Workspace changed: {stored_workspace} -> {self.workspace_path}, Recreating {self.language} LSP server")
                    # Try to stop old server
                    try:
                        if hasattr(existing_server, 'stop'):
                            existing_server.stop()
                    except Exception as e:
                        logger.warning(f"Failed to stop old server: {e}")
                    # Clear old server
                    _global_tool_state.set_server(self.name, None)
            except Exception as e:
                logger.warning(f"Error while checking existing server status: {e}, will Recreate")
                _global_tool_state.set_server(self.name, None)

        try:
            # Use member variables instead of global state
            if not self.language or not self.workspace_path:
                raise RuntimeError("Language or workspace path not set")

            # Verify workspace path exists
            workspace_path_obj = Path(self.workspace_path)
            if not workspace_path_obj.exists():
                raise RuntimeError(f"Workspace path does not exist: {self.workspace_path}")
            if not workspace_path_obj.is_dir():
                raise RuntimeError(f"Workspace path is not a directory: {self.workspace_path}")

            config = MultilspyConfig.from_dict({
                "code_language": self.language,
                "trace_lsp_communication": False,
                "start_independent_lsp_process": True
            })

            multilspy_logger = MultilspyLogger(False)

            logger.info(f"Creating {self.language} LSP server, workspace: {self.workspace_path}")
            server = SyncLanguageServer.create(
                config,
                multilspy_logger,
                str(workspace_path_obj.absolute())
            )

            _global_tool_state.set_server(self.name, server)
            _global_tool_state.set_workspace_path(self.name, self.workspace_path)
            logger.info(f"✅ {self.language} LSP server created successfully")

        except Exception as e:
            logger.error(f"Failed to create {self.language} LSP server: {e}")
            raise

    def _get_absolute_path(self, file_path: str) -> str:
        """Get absolute file path"""
        path = Path(file_path)
        if path.is_absolute():
            return str(path)
        else:
            return str(Path(self.workspace_path) / path)
    
    def start_lsp_server(self) -> None:
        """Start LSP server"""
        if _global_tool_state.get_server(self.name) is not None:
            return
            
        try:
            language = _global_tool_state.get_language(self.name)
            workspace_path = _global_tool_state.get_workspace_path(self.name)
            
            if not language or not workspace_path:
                raise RuntimeError("Language or workspace path not set")
            
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
            logger.info(f"{language} LSP server created")
            
        except Exception as e:
            logger.error(f"Failed to create LSP server: {e}")
            raise
    
    def _run(self, file_path: str, line: int, character: int) -> AntToolResult:
        """Execute definition request"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                self.start_lsp_server()

                # Process path: convert absolute path to relative path from workspace
                try:
                    # If relative path is provided, convert to absolute path first
                    absolute_path = self._get_absolute_path(file_path)
                    # Then convert to relative path from workspace for multilspy use
                    relative_path = str(Path(absolute_path).relative_to(self.workspace_path))
                except ValueError as e:
                    return AntToolResult(
                        success=False,
                        error=f"File path {file_path} not in workspace {self.workspace_path} within: {str(e)}"
                    )

                server = _global_tool_state.get_server(self.name)

                if not server:
                    return AntToolResult(success=False, error="LSP server not started")

                with server.start_server():
                    # Call multilspy with relative path
                    result = server.request_definition(relative_path, line, character)

                    if result:
                        # Parse LSP definition result
                        parsed_result = parse_lsp_definition_result(str(result))

                        if parsed_result['success']:
                            # Generate formatted output
                            formatted_output = format_lsp_definition_result(parsed_result['definitions'])

                            # Build metadata
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
                            # Parse failed, return raw result and error message
                            return AntToolResult(
                                success=True,
                                output=str(result),
                                metadata={'parse_error': parsed_result.get('error'), 'retry_count': retry_count}
                            )
                    else:
                        # No result returned, may be file reading issue
                        error_detail = f"At {file_path}:{line}:{character} No definition found"
                        if retry_count < max_retries - 1:
                            logger.warning(f"{error_detail}, Attempting retry #{retry_count + 1}")
                            retry_count += 1
                            continue
                        else:
                            return AntToolResult(
                                success=False,
                                error=error_detail,
                                metadata={'retry_count': retry_count, 'max_retries': max_retries}
                            )

            except FileNotFoundError as e:
                error_detail = f"File read failed: file {file_path} does not exist or cannot be accessed"
                if retry_count < max_retries - 1:
                    logger.warning(f"{error_detail}, Attempting retry #{retry_count + 1}")
                    retry_count += 1
                    # Wait briefly before retry
                    import time
                    time.sleep(0.5 * (retry_count + 1))  # Increasing wait time
                    continue
                else:
                    logger.error(f"{error_detail}，Maximum retry attempts reached")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (retry {retry_count + 1}  attempts still failed))",
                        metadata={'error_type': 'file_not_found', 'file_path': file_path, 'retry_count': retry_count}
                    )

            except PermissionError as e:
                error_detail = f"File permission error: Cannot read file {file_path}"
                if retry_count < max_retries - 1:
                    logger.warning(f"{error_detail}, Attempting retry #{retry_count + 1}")
                    retry_count += 1
                    continue
                else:
                    logger.error(f"{error_detail}，Maximum retry attempts reached")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (retry {retry_count + 1}  attempts still failed))",
                        metadata={'error_type': 'permission_error', 'file_path': file_path, 'retry_count': retry_count}
                    )

            except Exception as e:
                error_detail = f"Definition request failed: {type(e).__name__}: {str(e)}"
                logger.error(error_detail)

                if retry_count < max_retries - 1:
                    logger.warning(f"Attempting retry #{retry_count + 1}")
                    retry_count += 1
                    # Wait briefly before retry
                    import time
                    time.sleep(0.5 * (retry_count + 1))
                    continue
                else:
                    logger.error(f"Maximum retry attempts reached, error: {error_detail}")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (retry {retry_count + 1}  attempts still failed))",
                        metadata={'error_type': type(e).__name__, 'error_message': str(e), 'retry_count': retry_count}
                    )

# References tool
class MultilspyReferencesTool(AntTool):
    """Multilspy References tool"""

    name: str = "multilspy_references"
    description: str = "Find code references (based on Multilspy)"
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
        """Get absolute file path"""
        path = Path(file_path)
        if path.is_absolute():
            return str(path)
        else:
            return str(Path(self.workspace_path) / path)

    def start_lsp_server(self) -> None:
        """Start LSP server"""
        if _global_tool_state.get_server(self.name) is not None:
            return

        try:
            # Use member variables instead of global state
            if not self.language or not self.workspace_path:
                raise RuntimeError("Language or workspace path not set")

            # Verify workspace path exists
            workspace_path_obj = Path(self.workspace_path)
            if not workspace_path_obj.exists():
                raise RuntimeError(f"Workspace path does not exist: {self.workspace_path}")
            if not workspace_path_obj.is_dir():
                raise RuntimeError(f"Workspace path is not a directory: {self.workspace_path}")
                raise RuntimeError("Language or workspace path not set")

            config = MultilspyConfig.from_dict({
                "code_language": self.language,
                "trace_lsp_communication": False,
                "start_independent_lsp_process": True
            })

            multilspy_logger = MultilspyLogger(False)

            logger.info(f"Creating {self.language} LSP server, workspace: {self.workspace_path}")
            server = SyncLanguageServer.create(
                config,
                multilspy_logger,
                str(workspace_path_obj.absolute())
            )

            _global_tool_state.set_server(self.name, server)
            _global_tool_state.set_workspace_path(self.name, self.workspace_path)
            logger.info(f"✅ {self.language} LSP server created successfully")

        except Exception as e:
            logger.error(f"Failed to create LSP server: {e}")
            raise

    def _run(self, file_path: str, line: int, character: int) -> AntToolResult:
        """Execute references request"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                self.start_lsp_server()

                # Process path: convert absolute path to relative path from workspace
                try:
                    # If relative path is provided, convert to absolute path first
                    absolute_path = self._get_absolute_path(file_path)
                    # Then convert to relative path from workspace for multilspy use
                    relative_path = str(Path(absolute_path).relative_to(self.workspace_path))
                except ValueError as e:
                    return AntToolResult(
                        success=False,
                        error=f"File path {file_path} not in workspace {self.workspace_path} within: {str(e)}"
                    )

                server = _global_tool_state.get_server(self.name)

                if not server:
                    return AntToolResult(success=False, error="LSP server not started")

                with server.start_server():
                    # Call multilspy with relative path
                    result = server.request_references(relative_path, line, character)

                    if result:
                        return AntToolResult(
                            success=True,
                            output=str(result),
                            metadata={'retry_count': retry_count}
                        )
                    else:
                        # No result returned, may be file reading issue
                        error_detail = f"At {file_path}:{line}:{character} No references found"
                        if retry_count < max_retries - 1:
                            logger.warning(f"{error_detail}, Attempting retry #{retry_count + 1}")
                            retry_count += 1
                            continue
                        else:
                            return AntToolResult(
                                success=False,
                                error=error_detail,
                                metadata={'retry_count': retry_count, 'max_retries': max_retries}
                            )

            except FileNotFoundError as e:
                error_detail = f"File read failed: file {file_path} does not exist or cannot be accessed"
                if retry_count < max_retries - 1:
                    logger.warning(f"{error_detail}, Attempting retry #{retry_count + 1}")
                    retry_count += 1
                    # Wait briefly before retry
                    import time
                    time.sleep(0.5 * (retry_count + 1))  # Increasing wait time
                    continue
                else:
                    logger.error(f"{error_detail}，Maximum retry attempts reached")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (retry {retry_count + 1}  attempts still failed))",
                        metadata={'error_type': 'file_not_found', 'file_path': file_path, 'retry_count': retry_count}
                    )

            except PermissionError as e:
                error_detail = f"File permission error: Cannot read file {file_path}"
                if retry_count < max_retries - 1:
                    logger.warning(f"{error_detail}, Attempting retry #{retry_count + 1}")
                    retry_count += 1
                    continue
                else:
                    logger.error(f"{error_detail}，Maximum retry attempts reached")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (retry {retry_count + 1}  attempts still failed))",
                        metadata={'error_type': 'permission_error', 'file_path': file_path, 'retry_count': retry_count}
                    )

            except Exception as e:
                error_detail = f"References request failed: {type(e).__name__}: {str(e)}"
                logger.error(error_detail)

                if retry_count < max_retries - 1:
                    logger.warning(f"Attempting retry #{retry_count + 1}")
                    retry_count += 1
                    # Wait briefly before retry
                    import time
                    time.sleep(0.5 * (retry_count + 1))
                    continue
                else:
                    logger.error(f"Maximum retry attempts reached, error: {error_detail}")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (retry {retry_count + 1}  attempts still failed))",
                        metadata={'error_type': type(e).__name__, 'error_message': str(e), 'retry_count': retry_count}
                    )


# Declaration tool
class MultilspyDeclarationTool(AntTool):
    """Multilspy Declaration tool"""

    name: str = "multilspy_declaration"
    description: str = "Jump to code declaration (based on Multilspy)"
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
        """Get absolute file path"""
        path = Path(file_path)
        if path.is_absolute():
            return str(path)
        else:
            return str(Path(self.workspace_path) / path)

    def start_lsp_server(self) -> None:
        """Start LSP server"""
        if _global_tool_state.get_server(self.name) is not None:
            return

        try:
            # Use member variables instead of global state
            if not self.language or not self.workspace_path:
                raise RuntimeError("Language or workspace path not set")

            # Verify workspace path exists
            workspace_path_obj = Path(self.workspace_path)
            if not workspace_path_obj.exists():
                raise RuntimeError(f"Workspace path does not exist: {self.workspace_path}")
            if not workspace_path_obj.is_dir():
                raise RuntimeError(f"Workspace path is not a directory: {self.workspace_path}")
                raise RuntimeError("Language or workspace path not set")

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
            logger.info(f"✅ Successfully started {self.language} LSP server")

        except Exception as e:
            logger.error(f"Failed to start {self.language} LSP server: {e}")
            raise RuntimeError(f"Cannot start {self.language} LSP server: {e}")

    def _run(self, file_path: str, line: int, character: int) -> AntToolResult:
        """Find declaration"""
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                self.start_lsp_server()
                server = _global_tool_state.get_server(self.name)

                if not server:
                    return AntToolResult(
                        success=False,
                        error="LSP server not started"
                    )

                # Process path: convert absolute path to relative path from workspace
                try:
                    # If relative path is provided, convert to absolute path first
                    absolute_path = self._get_absolute_path(file_path)
                    # Then convert to relative path from workspace for multilspy use
                    relative_path = str(Path(absolute_path).relative_to(self.workspace_path))
                except ValueError as e:
                    return AntToolResult(
                        success=False,
                        error=f"File path {file_path} not in workspace {self.workspace_path} within: {str(e)}"
                    )

                # Use LSP Find declaration
                with server.start_server():
                    try:
                        # Note: multilspy's request_definition can actually handle both declaration and definition
                        # Here we use the same method but differentiate in description
                        locations = server.request_definition(relative_path, line, character)

                        if not locations:
                            error_detail = f"At {file_path}:{line}:{character} No declaration found"
                            if retry_count < max_retries - 1:
                                logger.warning(f"{error_detail}, Attempting retry #{retry_count + 1}")
                                retry_count += 1
                                continue
                            else:
                                return AntToolResult(
                                    success=False,
                                    error=error_detail,
                                    metadata={'retry_count': retry_count, 'max_retries': max_retries, 'suggestion': 'Try using go_to_definition tool, or check if position is correct'}
                                )

                        # Format result
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
                        error_detail = f"File read failed: file {file_path} does not exist or cannot be accessed"
                        if retry_count < max_retries - 1:
                            logger.warning(f"{error_detail}, Attempting retry #{retry_count + 1}")
                            retry_count += 1
                            # Wait briefly before retry
                            import time
                            time.sleep(0.5 * (retry_count + 1))  # Increasing wait time
                            continue
                        else:
                            logger.error(f"{error_detail}，Maximum retry attempts reached")
                            return AntToolResult(
                                success=False,
                                error=f"{error_detail} (retry {retry_count + 1}  attempts still failed))",
                                metadata={'error_type': 'file_not_found', 'file_path': file_path, 'retry_count': retry_count}
                            )

                    except PermissionError as e:
                        error_detail = f"File permission error: Cannot read file {file_path}"
                        if retry_count < max_retries - 1:
                            logger.warning(f"{error_detail}, Attempting retry #{retry_count + 1}")
                            retry_count += 1
                            continue
                        else:
                            logger.error(f"{error_detail}，Maximum retry attempts reached")
                            return AntToolResult(
                                success=False,
                                error=f"{error_detail} (retry {retry_count + 1}  attempts still failed))",
                                metadata={'error_type': 'permission_error', 'file_path': file_path, 'retry_count': retry_count}
                            )

                    except Exception as e:
                        error_detail = f"Declaration request failed: {type(e).__name__}: {str(e)}"
                        logger.error(error_detail)

                        if retry_count < max_retries - 1:
                            logger.warning(f"Attempting retry #{retry_count + 1}")
                            retry_count += 1
                            # Wait briefly before retry
                            import time
                            time.sleep(0.5 * (retry_count + 1))
                            continue
                        else:
                            logger.error(f"Maximum retry attempts reached, error: {error_detail}")
                            return AntToolResult(
                                success=False,
                                error=f"{error_detail} (retry {retry_count + 1}  attempts still failed))",
                                metadata={'error_type': type(e).__name__, 'error_message': str(e), 'retry_count': retry_count, 'suggestion': 'Check if file path and position are correct'}
                            )

            except FileNotFoundError as e:
                error_detail = f"File read failed: file {file_path} does not exist or cannot be accessed"
                if retry_count < max_retries - 1:
                    logger.warning(f"{error_detail}, Attempting retry #{retry_count + 1}")
                    retry_count += 1
                    # Wait briefly before retry
                    import time
                    time.sleep(0.5 * (retry_count + 1))  # Increasing wait time
                    continue
                else:
                    logger.error(f"{error_detail}，Maximum retry attempts reached")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (retry {retry_count + 1}  attempts still failed))",
                        metadata={'error_type': 'file_not_found', 'file_path': file_path, 'retry_count': retry_count}
                    )

            except PermissionError as e:
                error_detail = f"File permission error: Cannot read file {file_path}"
                if retry_count < max_retries - 1:
                    logger.warning(f"{error_detail}, Attempting retry #{retry_count + 1}")
                    retry_count += 1
                    continue
                else:
                    logger.error(f"{error_detail}，Maximum retry attempts reached")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (retry {retry_count + 1}  attempts still failed))",
                        metadata={'error_type': 'permission_error', 'file_path': file_path, 'retry_count': retry_count}
                    )

            except Exception as e:
                error_detail = f"Declaration tool execution failed: {type(e).__name__}: {str(e)}"
                logger.error(error_detail)

                if retry_count < max_retries - 1:
                    logger.warning(f"Attempting retry #{retry_count + 1}")
                    retry_count += 1
                    # Wait briefly before retry
                    import time
                    time.sleep(0.5 * (retry_count + 1))
                    continue
                else:
                    logger.error(f"Maximum retry attempts reached, error: {error_detail}")
                    return AntToolResult(
                        success=False,
                        error=f"{error_detail} (retry {retry_count + 1}  attempts still failed))",
                        metadata={'error_type': type(e).__name__, 'error_message': str(e), 'retry_count': retry_count, 'suggestion': 'Try using position_finder to get accurate coordinates'}
                    )


# Tool factory
class MultilspyToolFactory:
    """Multilspy tool factory"""
    
    # Supported languages
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
    
    # Tool type mapping
    TOOL_TYPES = {
        "definition": MultilspyDefinitionTool,
        "references": MultilspyReferencesTool,
        "declaration": MultilspyDeclarationTool
    }
    
    @classmethod
    def create_tools(cls, workspace_path: str, languages: Optional[List[str]] = None) -> List[AntTool]:
        """
        Create Multilspy LSP tools
        
        Args:
            workspace_path: Working directory path
            languages: List of languages to create tools for, if None creates all supported languages
            
        Returns:
            Tool list
        """
        tools = []
        
        if languages is None:
            languages = list(cls.SUPPORTED_LANGUAGES.keys())
        
        for language in languages:
            if language not in cls.SUPPORTED_LANGUAGES:
                logger.warning(f"Unsupported language: {language}")
                continue
                
            # Create all types of tools for each language
            for tool_type, tool_class in cls.TOOL_TYPES.items():
                try:
                    tool = tool_class(language, workspace_path)
                    tools.append(tool)
                    logger.info(f"Creating tool: {tool.name}")
                except Exception as e:
                    logger.error(f"Failed to create {tool_type} tool for {language}: {e}")
        
        logger.info(f"Successfully created {len(tools)}  Multilspy LSP tools")
        return tools
    
    @classmethod
    def create_tool(cls, language: str, tool_type: str, workspace_path: str) -> Optional[AntTool]:
        """Create single tool"""
        if language not in cls.SUPPORTED_LANGUAGES:
            logger.error(f"Unsupported language: {language}")
            return None
            
        if tool_type not in cls.TOOL_TYPES:
            logger.error(f"Unsupported tool type: {tool_type}")
            return None
            
        try:
            tool_class = cls.TOOL_TYPES[tool_type]
            tool = tool_class(language, workspace_path)
            logger.info(f"Creating tool: {tool.name}")
            return tool
        except Exception as e:
            logger.error(f"Failed to create {tool_type} tool for {language}: {e}")
            return None

# Tool manager
class MultilspyToolManager:
    """Multilspy tool manager"""
    
    def __init__(self):
        self.tools: Dict[str, AntTool] = {}
        self.logger = logging.getLogger(__name__)
    
    def create_tools_for_workspace(self, workspace_path: str, languages: Optional[List[str]] = None) -> List[AntTool]:
        """Create tools for workspace"""
        tools = MultilspyToolFactory.create_tools(workspace_path, languages)
        
        for tool in tools:
            self.tools[tool.name] = tool
            
        self.logger.info(f"Created {len(tools)} tools for workspace {workspace_path}")
        return tools
    
    def get_tool(self, name: str) -> Optional[AntTool]:
        """Get tool"""
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[AntTool]:
        """Get all tools"""
        return list(self.tools.values())
    
    def get_tools_by_language(self, language: str) -> List[AntTool]:
        """Get tools for specified language"""
        return [tool for tool in self.tools.values() if tool.name.startswith(f"multilspy_{language}_")]
    
    def list_available_tools(self) -> List[str]:
        """List available tool names"""
        return list(self.tools.keys())

# Global tool manager instance
global_multilspy_tool_manager = MultilspyToolManager()

# Tool context setting function (for use by other modules)
def set_tool_context(tool_name: str, server, language) -> None:
    """Set tool context information"""
    # Tool context logic can be added here
    logger.info(f"Set tool {tool_name}  context: {language.value}")
    pass


def parse_lsp_definition_result(definition_output: str) -> Dict[str, Any]:
    """
    Parse LSP definition request return result
    
    Args:
        definition_output: LSP returned Python literal format string
        
    Returns:
        Structured definition information, includes following fields：
        - success: Whether parsing was successful
        - definitions: Definition list (if successful)
        - error: Error message (if failed)
        - summary: Definition summary information
    """
    try:
        # Handle empty or None input
        if not definition_output or definition_output.strip() in ['None', '']:
            return {
                "success": True,
                "definitions": [],
                "error": None,
                "summary": "No definition found"
            }
        
        # Try parsing Python literal
        try:
            # Safely evaluate Python literal expression
            parsed_result = ast.literal_eval(definition_output.strip())
        except (ValueError, SyntaxError, MemoryError) as e:
            # If literal parsing fails，Try cleaning and fixing common format issues
            cleaned_output = definition_output.strip()
            
            # Handle possible string escaping issues
            if cleaned_output.startswith('[') and cleaned_output.endswith(']'):
                try:
                    # Try parsing with json (safer)
                    import json
                    parsed_result = json.loads(cleaned_output)
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "definitions": [],
                        "error": f"Unable to parse definition result format: {str(e)}",
                        "summary": "Parsing failed"
                    }
            else:
                return {
                    "success": False,
                    "definitions": [],
                    "error": f"Invalid LSP definition result format: {str(e)}",
                    "summary": "Parsing failed"
                }
        
        # Verify basic structure of parsed result
        if not isinstance(parsed_result, list):
            return {
                "success": False,
                "definitions": [],
                "error": "LSP definition result should be list format",
                "summary": "Format error"
            }
        
        # Handle empty list
        if not parsed_result:
            return {
                "success": True,
                "definitions": [],
                "error": None,
                "summary": "No definition found"
            }
        
        # Parse each definition item
        definitions = []
        for i, location in enumerate(parsed_result):
            try:
                # Verify basic structure
                if not isinstance(location, dict):
                    logger.warning(f"Definition item {i} Is not dict format, skipping")
                    continue
                
                # Extract definition information
                definition_info = {
                    "index": i + 1,
                    "file_path": location.get("relativePath") or location.get("absolutePath", "Unknown path"),
                    "absolute_path": location.get("absolutePath", ""),
                    "relative_path": location.get("relativePath", ""),
                    "uri": location.get("uri", ""),
                    "range": None,
                    "start_position": None,
                    "end_position": None
                }
                
                # Handle range information
                range_info = location.get("range")
                if isinstance(range_info, dict):
                    definition_info["range"] = range_info
                    
                    # Extract start position
                    start_pos = range_info.get("start")
                    if isinstance(start_pos, dict):
                        definition_info["start_position"] = {
                            "line": start_pos.get("line", -1) + 1,  # Convert to 1-based index
                            "character": start_pos.get("character", -1) + 1
                        }
                    
                    # Extract end position
                    end_pos = range_info.get("end")
                    if isinstance(end_pos, dict):
                        definition_info["end_position"] = {
                            "line": end_pos.get("line", -1) + 1,  # Convert to 1-based index
                            "character": end_pos.get("character", -1) + 1
                        }
                
                # Generate location description
                if definition_info["start_position"]:
                    pos = definition_info["start_position"]
                    definition_info["location_desc"] = f"Line {pos['line']} line, {pos['character']} column"
                else:
                    definition_info["location_desc"] = "Unknown location"
                
                # Generate file type information
                file_path = definition_info["file_path"]
                if file_path and file_path != "Unknown path":
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
                    definition_info["language"] = lang_map.get(file_ext, "Unknown language")
                else:
                    definition_info["language"] = "Unknown language"
                
                definitions.append(definition_info)
                
            except Exception as e:
                logger.warning(f"Error parsing definition item {i}: {str(e)}")
                continue
        
        # Generate summary information
        if not definitions:
            summary = "No valid definitions found"
        elif len(definitions) == 1:
            def_info = definitions[0]
            summary = f"Found 1 definitions:{def_info['language']} file {def_info['file_path']}，{def_info['location_desc']}"
        else:
            # Group statistics by language
            lang_counts = {}
            for def_info in definitions:
                lang = def_info['language']
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
            
            summary_parts = []
            for lang, count in lang_counts.items():
                summary_parts.append(f"{lang}: {count}")
            
            summary = f"Found {len(definitions)} definitions ({'，'.join(summary_parts)}）"
        
        return {
            "success": True,
            "definitions": definitions,
            "error": None,
            "summary": summary,
            "total_definitions": len(definitions)
        }
        
    except Exception as e:
        error_msg = f"Unknown error occurred while parsing LSP definition result: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "definitions": [],
            "error": error_msg,
            "summary": "Parsing failed"
        }


def format_lsp_definition_result(definitions: List[Dict[str, Any]]) -> str:
    """
    Format LSP definition result, generate easy-to-understand text description for LLM
    
    Args:
        definitions: Parsed definition list
        
    Returns:
        Formatted text description
    """
    if not definitions:
        return "No definition found"
    
    lines = []
    lines.append(f"Found {len(definitions)} definitions:")
    
    for i, definition in enumerate(definitions, 1):
        lines.append(f"\nDefinition {i}:")
        lines.append(f"  File: {definition['file_path']}")
        lines.append(f"  Language: {definition['language']}")
        
        if definition['location_desc'] != "Unknown location":
            lines.append(f"  Location: {definition['location_desc']}")
        
        if definition['relative_path'] and definition['relative_path'] != definition['file_path']:
            lines.append(f"  Relative path: {definition['relative_path']}")
        
        if definition['uri']:
            lines.append(f"  URI: {definition['uri']}")
        
        # Add range information (if available)
        if definition['start_position'] and definition['end_position']:
            start = definition['start_position']
            end = definition['end_position']
            if start != end:
                lines.append(f"  Range: From line {start['line']}, column {start['character']} to line {end['line']}, column {end['character']}")
    
    return "\n".join(lines)